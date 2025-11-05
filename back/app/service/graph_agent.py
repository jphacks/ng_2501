from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence,RunnablePassthrough
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
    user_request: str           # `content` (構造化説明)
    generation_instructions: str # `enhance_prompt` (動画の指示)
    animation_plan :str         # 生成されたアニメーションプラン
    video_id: str               # `video_id` (ファイル名用)
    
    # --- 変化する状態 ---
    current_script: str         # 現在のManimスクリプト (修正対象)
    last_error: str             # 最後に発生したエラーメッセージ (LinterまたはRuntime)
    error_type: Literal["", "lint", "runtime"] # エラーの種別
    is_bad_request: bool        # 不正リクエストフラグ
    
    # --- 制御用 ---
    max_retries: int            # 最大試行回数 (元の max_loop)
    current_retry: int          # 現在の試行回数 (元の loop)
    
    
class ManimGraphAnimationService(BaseManimAgent):
    def __init__(self, prompt_path = "prompt/prompts.toml"):
        super().__init__(prompt_path)
        # --- LangGraph のグラフを構築 ---
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()


    def generate_script_with_prompt(self, contents, video_enhance_prompt):
        """
        動画生成のためのスクリプトを生成する関数
        """
        manim_planer = PromptTemplate(
            input_variables=['user_prompt'],
            optional_variables= ['video_enhance_prompt'],
            template=self.prompts['chain']['manim_planer_with_instruct']
        )
        parser = StrOutputParser() 
        manim_script_prompt = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"]
        )
        # --- 2. チェーンを分割して定義 ---
    
        # (中間出力を生成するチェーン)
        planner_chain = manim_planer | self.lite_llm | parser
        
        # (最終出力を生成するチェーン)
        script_chain = manim_script_prompt | self.pro_llm | parser
        
        chain = RunnablePassthrough.assign(
            planner_output=planner_chain
        ).assign(
            script_output=(lambda x: {"instructions": x["planner_output"]}) | script_chain
        )
        # --- 4. チェーンの実行と結果の取得 ---
    
        output_dict = chain.invoke(
            {
                "user_prompt": contents,
                "video_enhance_prompt": video_enhance_prompt
            }
        )
        
        planner_result = output_dict["planner_output"]
        script_result = output_dict["script_output"]

        self.base_logger.info("--- 取得した中間出力 (Planner) ---")
        self.base_logger.info(planner_result)
        self.base_logger.info("-----------------------------------")
        
        # LLMが出力するマークダウンを削除
        script_result_cleaned = script_result.strip().replace("```python", "").replace("```", "").strip()
        
        return planner_result, script_result_cleaned
    
    def _generate_initial_script(self, state: ManimGraphState):
        """[Node 1] 最初のスクリプトを生成する"""
        self.base_logger.info("--- 1. [Node] Generating Initial Script ---")
        
        planner_script,script = self.generate_script_with_prompt(
            state["user_request"],
            state["generation_instructions"]
        )
        self.base_logger.debug(f"   [+] Initial script generated (length: {len(script)})")
        return {
                    "current_script": script, 
                    "current_retry": 0,
                    "animation_plan": planner_script
        }
    def _check_bad_request(self, state: ManimGraphState):
        self.base_logger.info("--- 2. [Node] Checking for Bad Request ---")
        is_safe = self._check_code_security(state["current_script"])
        self.base_logger.debug(f"   [+] Code security check: {'Passed' if is_safe else 'Failed'}")
        if not is_safe:
            return {
                "is_bad_request": True
            } 
        return {
            "is_bad_request": False
        }
        
    def _execute_and_handle_errors(self, state: ManimGraphState):
        """[Node 3] スクリプトを実行し、エラーを処理する"""
        self.base_logger.info("--- 4. [Node] Executing Manim ---")
        
        script = state["current_script"]
        video_id = state["video_id"]
        execution_result = self._execute_script(script, video_id)
        
        if execution_result == "Success":
            self.base_logger.info("   [+] Script executed successfully.")
            return {
                "last_error": "",
                "error_type": "",
            }
        elif execution_result == "bad_request":
            self.base_logger.warning("   [-] Bad request detected during execution.")
            return {
                "last_error": "The provided script contains unsafe code.",
                "error_type": "runtime",
            }
        elif execution_result=="FileNotFoundError":
            self.base_logger.error("   [-] Manim executable not found.")
            return {
                "last_error": "Manim executable not found.",
                "error_type": "runtime",
            }
        else:
            self.base_logger.error("   [-] Script execution failed with errors.")
            return {
                "last_error": execution_result,
                "error_type": "runtime",
            }
            
    
    def _refine_script_on_error(self, state: ManimGraphState):
        """[Node 5] エラーに基づきスクリプトを修正"""
        self.base_logger.info(f"--- 5. [Node] Refining Script (Attempt {state['current_retry'] + 1}) ---")
        
        repair_prompt_template = """
        あなたはプロの Manim 開発者です。
        1. アニメーションプラン: {animation_plan}
        2. {error_type}の診断結果: {lint_summary}
        3. 失敗したスクリプト: {original_script}
        タスク:
        上記の診断で指摘された すべてのエラーを修正しつつ、アニメーションプランが示す意図（意味・見た目）を保ったままコードを書き直してください。
        説明は一切書かず、有効な Python コードのみを出力してください。

        出力形式:
        ```python
        from manim import *
        class GeneratedScene(Scene):
            def construct(self):
                # ... 修正されたコード ...
        ```
        """
        repair_prompt = PromptTemplate.from_template(repair_prompt_template)
        
        parser = StrOutputParser()
        chain = repair_prompt | self.pro_llm | parser
        
        error_type_str = "静的解析(Lint)" if state["error_type"] == "lint" else "実行時(Runtime)"

        fixed_script = chain.invoke(
            {
                "animation_plan": state["animation_plan"], # user_request の代わりに animation_plan を使用
                "error_type": error_type_str,
                "lint_summary": state["last_error"],
                "original_script": state["current_script"]
            }
        )
        
        # LLMが出力するマークダウンを削除
        fixed_script = fixed_script.strip().replace("```python", "").replace("```", "").strip()
        
        self.base_logger.debug(f"   [+] Script refined (length: {len(fixed_script)})")
        
        return {
            "current_script": fixed_script,
            "current_retry": state["current_retry"] + 1,
            "last_error": "", 
            "error_type": ""
        }
        
        # --- 5. グラフの配線 (エッジと条件分岐) ---

    def _after_bad_request_check(self, state: ManimGraphState):
        """[Conditional Edge] 不正リクエストか"""
        if state["is_bad_request"]:
            self.base_logger.error("--- [Branch] Bad Request. Ending Graph. ---")
            return "end_with_error" 
        self.base_logger.debug("--- [Branch] Secure. Proceeding to Lint. ---")
        return "execute" 

    def _after_lint_check(self, state: ManimGraphState):
        """[Conditional Edge] リンターエラーか、リトライ上限か"""
        if state["error_type"] == "lint":
            if state["current_retry"] >= state["max_retries"]:
                self.base_logger.warning("--- [Branch] Max Retries Reached (Lint Error). Ending. ---")
                return "end_with_error"
            self.base_logger.info("--- [Branch] Linter Failed. Proceeding to Refine. ---")
            return "refine" 
        self.base_logger.debug("--- [Branch] Linter Passed. Proceeding to Execute. ---")
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
        workflow.add_node("check_bad_request", self._check_bad_request)
        workflow.add_node("execute", self._execute_and_handle_errors)
        workflow.add_node("refine", self._refine_script_on_error)
        workflow.set_entry_point("generate_initial")
        workflow.add_edge("generate_initial", "check_bad_request")
        workflow.add_edge("refine", "check_bad_request") 
        workflow.add_conditional_edges(
            "check_bad_request", self._after_bad_request_check,
            {"end_with_error": END, "execute": "execute"}
        )
        workflow.add_conditional_edges(
            "execute", self._after_execution,
            {"refine": "refine", "end_with_success": END, "end_with_error": END}
        )
        return workflow

    def generate_video(self,video_id:str,content:str,enhance_prompt:str,maxloop:int=3)->str:
        """
        動画生成のメイン関数
        """
        initial_state: ManimGraphState = {
            "user_request": content,
            "generation_instructions": enhance_prompt,
            "animation_plan": content,
            "video_id": video_id,
            "current_script": "",
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": maxloop,
            "current_retry": 0,
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
    
    def edit_video(self,video_id:str,original_script:str,edit_instructions:str,maxloop:int=3)->str:
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
    
    def manim_planner(self,content:str,enhance_prompt:str)->str:
        """
        Manimのアニメーションプランを生成する関数
        """
        manim_planer = PromptTemplate(
            input_variables=['user_prompt'],
            optional_variables= ['video_enhance_prompt'],
            template=self.prompts['chain']['manim_planer_with_instruct']
        )
        parser = StrOutputParser()
        
        chain = manim_planer | self.lite_llm | parser
        
        output: str = chain.invoke(
            {
                "user_prompt": content,
                "video_enhance_prompt": enhance_prompt
            }
        )
        self.base_logger.info(f"Manim planner output: {output}")
        return output