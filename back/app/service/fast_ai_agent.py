from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

# LangGraphのコンポーネント
from typing import TypedDict, Literal

from app.service.base_agent import BaseManimAgent


class ManimGraphState(TypedDict):
    """
    グラフ全体で引き回す状態。
    """

    # --- 初期入力 ---
    user_request: str  # `content` (構造化説明)
    generation_instructions: str  # `enhance_prompt` (動画の指示)
    animation_plan: str  # 生成されたアニメーションプラン
    video_id: str  # `video_id` (ファイル名用)

    # --- 変化する状態 ---
    current_script: str  # 現在のManimスクリプト (修正対象)
    last_error: str  # 最後に発生したエラーメッセージ (LinterまたはRuntime)
    error_type: Literal["", "lint", "runtime"]  # エラーの種別
    is_bad_request: bool  # 不正リクエストフラグ

    # --- 制御用 ---
    max_retries: int  # 最大試行回数 (元の max_loop)
    current_retry: int  # 現在の試行回数 (元の loop)
    mode: Literal["generate", "edit"]  # 動作モード


class ManimFastAnimationService(BaseManimAgent):
    def __init__(self, prompt_path="prompt/fast_ai_prompts.toml"):
        super().__init__(prompt_path)
        # --- LangGraph のグラフを構築 ---
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def generate_script_with_prompt(self, animation_plan: str) -> str:
        """
        生成済みのアニメーションプランから Manim スクリプトを生成する関数
        """
        manim_script_prompt = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"],
        )
        parser = StrOutputParser()

        # プランを instructions として LLM に渡す
        script_chain = manim_script_prompt | self.pro_llm | parser

        script_result = script_chain.invoke({"instructions": animation_plan})

        # LLMが出力するマークダウンを削除
        script_result_cleaned = script_result.strip().replace("```python", "").replace("```", "").strip()

        return script_result_cleaned

    def _generate_initial_script_edit(self, state: ManimGraphState):
        self.base_logger.info("   [+] Edit mode detected. Applying targeted adjustments.")
        edit_prompt = PromptTemplate.from_template(self.prompts["chain"]["fast_ai_edit_initial"])
        parser = StrOutputParser()
        chain = edit_prompt | self.pro_llm | parser
        llm_response = chain.invoke(
            {
                "edit_instructions": state["user_request"],
                "original_script": state["current_script"],
            }
        )
        self.base_logger.debug(f"llm_response: {llm_response}")

        updated_script = self._process_edit_response(
            original_script=state["current_script"],
            llm_response=llm_response,
        )

        if updated_script != state["current_script"]:
            self.base_logger.debug(f"   [+] Applied edit diff (length: {len(updated_script)})")
        else:
            self.base_logger.info("   [=] Edit diff produced no changes. Keeping original script.")

        return {
            "current_script": updated_script,
            "current_retry": 0,
            "last_error": "",
            "error_type": "",
        }

    def _generate_initial_script_generate(self, state: ManimGraphState):
        script = self.generate_script_with_prompt(state["animation_plan"])

        self.base_logger.debug(f"   [+] Initial script generated (length: {len(script)})")
        return {
            "current_script": script,
            "current_retry": 0,
        }

    def _generate_initial_script(self, state: ManimGraphState):
        """[Node 1] 最初のスクリプトを生成する"""
        self.base_logger.info("--- 1. [Node] Generating Initial Script ---")

        if state["mode"] == "edit":
            return self._generate_initial_script_edit(state)
        else:
            return self._generate_initial_script_generate(state)

    def _run_linter_check(self, state: ManimGraphState):
        self.base_logger.info("--- 2. [Node] Running Manim Linter ---")
        lint_result = self._check_code_lint(state["current_script"])
        status = lint_result.get("status")
        issue_count = lint_result.get("issue_count", len(lint_result.get("issues", [])))

        if status == "pass":
            self.base_logger.debug("   [+] Linter check passed with no warnings.")
            return {"last_error": "", "error_type": ""}

        self.base_logger.warning(f"   [-] Linter detected {issue_count} issue(s). Initiating refinement.")
        for issue in lint_result.get("issues", []):
            self.base_logger.debug(
                f"      -> {issue.get('filename')}:{issue.get('lineno')} [{issue.get('code')}] {issue.get('message')}"
            )
        summary = lint_result.get("summary") or ""
        return {"last_error": summary, "error_type": "lint"}

    def _check_bad_request(self, state: ManimGraphState):
        self.base_logger.info("--- 3. [Node] Checking for Bad Request ---")
        is_safe = self._check_code_security(state["current_script"])
        self.base_logger.debug(f"   [+] Code security check: {'Passed' if is_safe else 'Failed'}")
        if not is_safe:
            return {"is_bad_request": True}
        return {"is_bad_request": False}

    def _handle_execution_result(self, execution_result: str, *, stage: str):
        if execution_result == "Success":
            self.base_logger.info(f"   [+] {stage} succeeded.")
            return {
                "last_error": "",
                "error_type": "",
            }
        if execution_result == "bad_request":
            self.base_logger.warning(f"   [-] {stage} detected unsafe code.")
            return {
                "last_error": "The provided script contains unsafe code.",
                "error_type": "runtime",
            }
        if execution_result == "FileNotFoundError":
            self.base_logger.error(f"   [-] {stage} failed: Manim executable not found.")
            return {
                "last_error": "Manim executable not found.",
                "error_type": "runtime",
            }

        self.base_logger.error(f"   [-] {stage} failed with errors.")
        return {
            "last_error": execution_result,
            "error_type": "runtime",
        }

    def _execute_and_handle_errors(self, state: ManimGraphState):
        """[Node 4] スクリプトを実行し、エラーを処理する
        解像度を落とした事前実行 -> 本実行の2段階での実行
        """

        script = state["current_script"]
        video_id = state["video_id"]
        self.base_logger.info("--- 4. [Node] Preflight Execution Check ---")
        preflight_result = self._handle_execution_result(
            self._execute_script_low_res(script, video_id),
            stage="Preflight execution",
        )
        if preflight_result["error_type"]:
            return preflight_result

        self.base_logger.info("--- 4. [Node] Executing Manim ---")
        runtime_result = self._handle_execution_result(
            self._execute_script(script, video_id),
            stage="Runtime execution",
        )
        return runtime_result

    def _refine_script_on_error(self, state: ManimGraphState):
        """[Node 5] エラーに基づきスクリプトを修正"""
        self.base_logger.info(f"--- 5. [Node] Refining Script (Attempt {state['current_retry'] + 1}) ---")

        repair_prompt = PromptTemplate.from_template(self.prompts["chain"]["fast_ai_refine_patch"])

        parser = StrOutputParser()

        # エラー処理1回目はflash_llm、それ以降はpro_llmを使用
        if state["current_retry"] == 0:
            self.base_logger.debug("   [+] Using flash_llm for first refinement.")
            chain = repair_prompt | self.flash_llm | parser
        else:
            self.base_logger.debug("   [+] Using pro_llm for subsequent refinements.")
            chain = repair_prompt | self.pro_llm | parser

        fixed_script_response = chain.invoke(
            {
                "lint_summary": state["last_error"],
                "original_script": state["current_script"],
            }
        )
        self.base_logger.debug(f"llm_response: {fixed_script_response}")

        fixed_script = self._process_edit_response(
            original_script=state["current_script"],
            llm_response=fixed_script_response,
        )

        if fixed_script != state["current_script"]:
            self.base_logger.debug(f"   [+] Script refined via diff (length: {len(fixed_script)})")
        else:
            self.base_logger.info("   [=] Refinement diff produced no changes. Retaining previous script.")

        return {
            "current_script": fixed_script,
            "current_retry": state["current_retry"] + 1,
            "last_error": "",
            "error_type": "",
        }

    def _after_lint_check(self, state: ManimGraphState):
        """[Conditional Edge] リンターエラーか、リトライ上限か"""
        if state["error_type"] == "lint":
            if state["current_retry"] >= state["max_retries"]:
                self.base_logger.warning("--- [Branch] Max Retries Reached (Lint Error). Ending. ---")
                return "end_with_error"
            self.base_logger.info("--- [Branch] Linter Failed. Proceeding to Refine. ---")
            return "refine"
        self.base_logger.debug("--- [Branch] Linter Passed. Proceeding to Security Check. ---")
        return "check_bad_request"

    def _after_bad_request_check(self, state: ManimGraphState):
        """[Conditional Edge] 不正リクエストか"""
        if state["is_bad_request"]:
            self.base_logger.error("--- [Branch] Bad Request. Ending Graph. ---")
            return "end_with_error"
        self.base_logger.debug("--- [Branch] Secure. Proceeding to Execute. ---")
        return "execute"

    def _after_execution(self, state: ManimGraphState):
        """[Conditional Edge] 実行時エラーか、リトライ上限か"""
        if state["error_type"] == "runtime":
            if state["current_retry"] >= state["max_retries"]:
                self.base_logger.warning("--- [Branch] Max Retries Reached (Runtime Error). Ending. ---")
                return "end_with_error"
            self.base_logger.info("--- [Branch] Runtime Error. Proceeding to Refine. ---")
            return "refine"

        self.base_logger.info("--- [Branch] Execution Succeeded. Ending Graph. ---")
        return "end_with_success"

    def _build_graph(self):
        """LangGraphのワークフローを定義・構築する"""
        workflow = StateGraph(ManimGraphState)
        workflow.add_node("generate_initial", self._generate_initial_script)
        workflow.add_node("lint", self._run_linter_check)
        workflow.add_node("check_bad_request", self._check_bad_request)
        workflow.add_node("execute", self._execute_and_handle_errors)
        workflow.add_node("refine", self._refine_script_on_error)
        workflow.set_entry_point("generate_initial")
        workflow.add_edge("generate_initial", "lint")
        workflow.add_edge("refine", "lint")
        workflow.add_conditional_edges(
            "lint",
            self._after_lint_check,
            {
                "refine": "refine",
                "check_bad_request": "check_bad_request",
                "end_with_error": END,
            },
        )
        workflow.add_conditional_edges(
            "check_bad_request",
            self._after_bad_request_check,
            {"execute": "execute", "end_with_error": END},
        )
        workflow.add_conditional_edges(
            "execute",
            self._after_execution,
            {"refine": "refine", "end_with_success": END, "end_with_error": END},
        )
        return workflow

    # ============================================================
    # ==================   Public APIs (same)   ==================
    # ============================================================

    def generate_video(
        self,
        video_id: str,
        content: str,
        enhance_prompt: str,
        maxloop: int = 3,
    ) -> str:
        """
        動画生成のメイン関数
        """
        initial_state: ManimGraphState = {
            "user_request": "",
            "generation_instructions": enhance_prompt,
            "animation_plan": content,
            "video_id": video_id,
            "current_script": "",
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": maxloop,
            "current_retry": 0,
            "mode": "generate",
        }

        final_state = self.app.invoke(initial_state)

        if final_state["is_bad_request"]:
            self.base_logger.error("--- Graph Finished: Bad Request ---")
            return "bad_request"

        if final_state["last_error"]:
            self.base_logger.error(f"--- Graph Finished: Error (Max Retries Reached) ---")
            return "error"

        if not final_state["last_error"] and not final_state["is_bad_request"]:
            self.base_logger.info("--- Graph Finished: Success ---")
            return "Success"

        self.base_logger.critical("--- Graph Finished: Fallback (Unknown State) ---")
        return "fall back"

    def edit_video(
        self,
        video_id: str,
        original_script: str,
        edit_instructions: str,
        maxloop: int = 3,
    ) -> str:
        """
        既存のスクリプトを編集して動画を生成するメイン関数
        """
        initial_state: ManimGraphState = {
            "user_request": edit_instructions,
            "generation_instructions": "",
            "animation_plan": "",
            "video_id": video_id,
            "current_script": original_script,
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": maxloop,
            "current_retry": 0,
            "mode": "edit",
        }

        final_state = self.app.invoke(initial_state)

        if final_state["is_bad_request"]:
            self.base_logger.error("--- Graph Finished: Bad Request ---")
            return "bad_request"

        if final_state["last_error"]:
            self.base_logger.error(f"--- Graph Finished: Error (Max Retries Reached) ---")
            return "error"

        if not final_state["last_error"] and not final_state["is_bad_request"]:
            self.base_logger.info("--- Graph Finished: Success ---")
            return "Success"

        self.base_logger.critical("--- Graph Finished: Fallback (Unknown State) ---")
        return "fall back"

    def manim_planner(self, content: str, enhance_prompt: str) -> str:
        """
        Manimのアニメーションプランを生成する関数
        """
        manim_planer = PromptTemplate(
            input_variables=["user_prompt"],
            optional_variables=["video_enhance_prompt"],
            template=self.prompts["chain"]["manim_planer_with_instruct"],
        )
        parser = StrOutputParser()

        chain = manim_planer | self.lite_llm | parser

        output: str = chain.invoke({"user_prompt": content, "video_enhance_prompt": enhance_prompt})
        self.base_logger.info(f"Manim planner output: {output}")
        return output
