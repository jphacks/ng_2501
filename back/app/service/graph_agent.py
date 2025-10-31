import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence,RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import json
import logging
import logging.handlers
# 必要なツール群
# (app.tools.lint, app.tools.manim_lint, app.tools.secure はインポートされていると仮定)
# (ダミーの関数を仮置きします)
def format_and_linter(path):
    print(f"DUMMY: Linting {path}")
    return {"summary": {"errorCount": 0}}
def parse_manim_or_python_traceback(stderr):
    print("DUMMY: Parsing traceback")
    return {"error": "Parsed Error", "line": 10, "detail": stderr[:100]}
def format_error_for_llm(parsed_error):
    print("DUMMY: Formatting for LLM")
    return f"Line {parsed_error.get('line', '?')}: {parsed_error.get('detail', 'Unknown Error')}"
def is_code_safe(script):
    print("DUMMY: Checking security")
    return True


# LangGraphのコンポーネント
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

load_dotenv()

# --- 1. LangGraphの状態 (State) の定義 ---
# グラフ全体で引き回す情報を定義します。
# 元の generate_videos のローカル変数に相当します。

class ManimGraphState(TypedDict):
    """
    グラフ全体で引き回す状態。
    """
    # --- 初期入力 ---
    user_request: str           # `content` (構造化説明)
    generation_instructions: str # `enhance_prompt` (動画の指示)
    animation_plan :str
    video_id: str               # `video_id` (ファイル名用)
    
    # --- 変化する状態 ---
    current_script: str         # 現在のManimスクリプト (修正対象)
    last_error: str             # 最後に発生したエラーメッセージ (LinterまたはRuntime)
    error_type: Literal["", "lint", "runtime"] # エラーの種別
    is_bad_request: bool        # 不正リクエストフラグ
    
    # --- 制御用 ---
    max_retries: int            # 最大試行回数 (元の max_loop)
    current_retry: int          # 現在の試行回数 (元の loop)

# --- 3. ManimAnimationService クラスの定義 ---
# (元のコードと同一)

class ManimGraphAnimationService:
    def __init__(self):
        # --- ロギングのセットアップ ---
        self.graph_logger = None
        self.linter_logger = None
        self._setup_logging()

        # --- プロンプトのロード ---
        base_dir = Path(__file__).resolve().parent
        prompts_path = base_dir / "prompts.toml"
        
        # (プロンプトのロード処理 - ダミーの値を設定)
        self.prompts = {
            "chain": {
                "manim_planer_with_instruct": "Plan: {user_prompt} {video_enhance_prompt}",
                "manim_script_generate": "Script: {instructions}"
            },
            "explain": {
                "prompt": "Explain: {input_text}"
            }
        }
        self.graph_logger.info("Using dummy prompts as prompts.toml not found.")
        
        # LLMのロード
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            self.graph_logger.critical("GEMINI_API_KEY が .env ファイルに設定されていません。")
            raise ValueError("GEMINI_API_KEY が .env ファイルに設定されていません。")
            
        self.think_llm = self._load_llm(api_key, "gemini-2.5-flash")
        self.pro_llm   = self._load_llm(api_key, "gemini-2.5-pro")
        self.flash_llm = self._load_llm(api_key, "gemini-2.5-flash")
        self.lite_llm  = self._load_llm(api_key, "gemini-2.5-flash")
        
        # --- LangGraph のグラフを構築 ---
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()
        self.graph_logger.info("ManimAnimationService initialized.")

    def _setup_logging(self):
        """[新規] 2種類のロガーをセットアップする"""
        
        # 1. グラフ全体のロガー (graph_logger.log)
        self.graph_logger = logging.getLogger("ManimGraph")
        self.graph_logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラをクリア (重複防止)
        if self.graph_logger.hasHandlers():
            self.graph_logger.handlers.clear()

        graph_handler = logging.handlers.RotatingFileHandler(
            "graph_logger.log", maxBytes=1024*1024, backupCount=3, mode='w', encoding='utf-8'
        )
        graph_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        graph_handler.setFormatter(graph_formatter)
        self.graph_logger.addHandler(graph_handler)
        
        # (コンソールにもログを出力)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(graph_formatter)
        self.graph_logger.addHandler(console_handler)

        # 2. Linterエラー専用のロガー (linter_errors.log)
        self.linter_logger = logging.getLogger("LinterErrors")
        self.linter_logger.setLevel(logging.ERROR)
        
        # 既存のハンドラをクリア (重複防止)
        if self.linter_logger.hasHandlers():
            self.linter_logger.handlers.clear()

        linter_handler = logging.FileHandler("linter_errors.log", mode='w', encoding='utf-8')
        linter_formatter = logging.Formatter(
            '%(asctime)s - LINTER ERROR (Video ID: %(video_id)s)\n'
            '--- SCRIPT ---\n%(script)s\n'
            '--- ERROR --- \n%(error_message)s\n'
            + '-'*50 + '\n'
        )
        linter_handler.setFormatter(linter_formatter)
        self.linter_logger.addHandler(linter_handler)

    def _log_state(self, state: ManimGraphState, node_name: str):
        """[新規] ログ出力用に state を要約するヘルパー"""
        try:
            # stateが辞書であることを確認 (TypedDictはランタイムでは辞書)
            if not isinstance(state, dict):
                self.graph_logger.error(f"Invalid state type at {node_name}: {type(state)}")
                return
                
            state_summary = state.copy()
            
            if "current_script" in state_summary and state_summary["current_script"]:
                script_len = len(state_summary["current_script"])
                state_summary["current_script"] = state_summary["current_script"][:200] + f"... (Total: {script_len} chars)"
            
            if "user_request" in state_summary and state_summary["user_request"]:
                 request_len = len(state_summary["user_request"])
                 state_summary["user_request"] = state_summary["user_request"][:200] + f"... (Total: {request_len} chars)"
            
            if "last_error" in state_summary and state_summary["last_error"]:
                 error_len = len(state_summary["last_error"])
                 state_summary["last_error"] = state_summary["last_error"][:300] + f"... (Total: {error_len} chars)"

            state_json = json.dumps(state_summary, indent=2, ensure_ascii=False)
            self.graph_logger.debug(f"STATE at entry of [ {node_name} ]:\n{state_json}")
        
        except Exception as e:
            self.graph_logger.error(f"Failed to log state summary: {e}")

    def _load_llm(self, api_key: str, model_type: str):
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=api_key)

    def _save_script(self, video_id: str, script: str) -> Path:
        """[Helper] 共通のスクリプト保存処理"""
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{video_id}.py")
        with open(tmp_path, "w", encoding='utf-8') as f:
            f.write(script)
        return tmp_path

    # --- 4. グラフのノード (Node) の定義 (ロギング強化) ---

    def _generate_initial_script(self, state: ManimGraphState):
        """[Node 1] 最初のスクリプトを生成する"""
        self.graph_logger.info("--- 1. [Node] Generating Initial Script ---")
        self._log_state(state, "_generate_initial_script")
        
        planner_script,script = self.generate_script_with_prompt(
            state["user_request"],
            state["generation_instructions"]
        )
        self.graph_logger.debug(f"   [+] Initial script generated (length: {len(script)})")
        return {
                    "current_script": script, 
                    "current_retry": 0,
                    "animation_plan": planner_script
        }
    
    def _check_bad_request(self, state: ManimGraphState):
        """[Node 2] 悪意のあるコードが含まれていないかチェック"""
        self.graph_logger.info("--- 2. [Node] Checking Security ---")
        self._log_state(state, "_check_bad_request")
        script = state['current_script']
        
        if not is_code_safe(script): 
            self.graph_logger.warning("   [!] Bad Request Detected.")
            return {
                "is_bad_request": True,
                "last_error": "Malicious code detected. Aborting." 
            }
        self.graph_logger.info("   [+] Secure.")
        return {"is_bad_request": False}
    
    def _lint_check(self, state: ManimGraphState):
        """[Node 3] スクリプトを保存し、フォーマットとリンターを実行"""
        self.graph_logger.info("--- 3. [Node] Running Linter (format_and_linter) ---")
        self._log_state(state, "_lint_check")
        script = state['current_script']
        video_id = state['video_id']
        tmp_path = self._save_script(video_id, script)
        
        lint_result_json = format_and_linter(tmp_path) 
        
        if self.has_no_pyright_errors(lint_result_json):
            self.graph_logger.info("   [+] Linter Passed.")
            with open(tmp_path, "r", encoding='utf-8') as f:
                formatted_script = f.read()
            return {
                "last_error": "",
                "error_type": "",
                "current_script": formatted_script
            }
        else:
            self.graph_logger.warning("   [!] Linter Failed.")
            error_message = self.parse_pyright_output_for_llm(lint_result_json)
            
            try:
                self.linter_logger.error("", extra={
                    "video_id": video_id,
                    "script": script,
                    "error_message": error_message
                })
                self.graph_logger.info("   [+] Linter error details saved to linter_errors.log")
            except Exception as e:
                self.graph_logger.error(f"Failed to write to linter_errors.log: {e}")
                
            return {
                "last_error": error_message,
                "error_type": "lint"
            }

    def _execute_script(self, state: ManimGraphState):
        """[Node 4] Manim を実行して動画をレンダリング"""
        self.graph_logger.info("--- 4. [Node] Executing Manim ---")
        self._log_state(state, "_execute_script")
        script = state['current_script']
        video_id = state['video_id']
        tmp_path = self._save_script(video_id, script) 
        
        try:
            # "manim" コマンドをフルパスで指定するか、環境PATHを確認してください
            # ここでは "manim" がPATHにあると仮定します
            subprocess.run(
                ["manim", "-pql", str(tmp_path), "GeneratedScene"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, check=True, encoding='utf-8'
            )
            self.graph_logger.info("   [+] Execution Succeeded.")
            return {"last_error": "", "error_type": ""} # 成功
        except FileNotFoundError:
            self.graph_logger.error("   [!] Execution Failed (Manim command not found).")
            error_msg = "Command 'manim' not found. Please ensure Manim is installed and in your PATH."
            return {
                "last_error": error_msg,
                "error_type": "runtime"
            }
        except subprocess.CalledProcessError as e:
            # 1. 生のTracebackをログに出力 (既存)
            self.graph_logger.error(f"   [!] Execution Failed (Runtime Error).\n{e.stderr}")
            
            # 2. TracebackをLLM用にパース
            parsed_error = parse_manim_or_python_traceback(e.stderr)
            llm_formatted_error = format_error_for_llm(parsed_error)
            
            # 3. (★変更点★) パースしたエラーもログに出力
            self.graph_logger.warning(f"   [!] Parsed error (for LLM refine):\n{llm_formatted_error}")
            
            # 4. Stateを返す
            return {
                "last_error": llm_formatted_error,
                "error_type": "runtime"
            }

    def _refine_script_on_error(self, state: ManimGraphState):
        """[Node 5] エラーに基づきスクリプトを修正"""
        self.graph_logger.info(f"--- 5. [Node] Refining Script (Attempt {state['current_retry'] + 1}) ---")
        self._log_state(state, "_refine_script_on_error")
        
        repair_prompt_template = """
        あなたはプロの Manim 開発者です。
        1. アニメーションプラン: {animation_plan}
        2. {error_type}の診断結果: {lint_summary}
        3. 失敗したスクリプト: {original_script}
        タスク:
        上記の診断で指摘された すべてのエラーを修正しつつ、アニメーションプランが示す意図（意味・見た目）を保ったままコードを書き直してください。
        説明は一切書かず、有効な Python コードのみを出力してください。
        
        ### 重要な修正ルール ###
        - TypeError: ... unexpected keyword argument 'color' のようなエラーの場合:
          `obj = Class(..., color=BLUE)` を
          `obj = Class(...)`
          `obj.set_color(BLUE)`
          の2行に分離して修正してください。`config`辞書にラップしないでください。

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
        chain = repair_prompt | self.flash_llm | parser
        
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
        
        self.graph_logger.debug(f"   [+] Script refined (length: {len(fixed_script)})")
        
        return {
            "current_script": fixed_script,
            "current_retry": state["current_retry"] + 1,
            "last_error": "", 
            "error_type": ""
        }
        
    def generate_script_with_prompt(self,explain_prompt,video_enhance_prompt):
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
                "user_prompt": explain_prompt,
                "video_enhance_prompt": video_enhance_prompt
            }
        )
        
        planner_result = output_dict["planner_output"]
        script_result = output_dict["script_output"]

        self.graph_logger.info("--- 取得した中間出力 (Planner) ---")
        self.graph_logger.info(planner_result)
        self.graph_logger.info("-----------------------------------")
        
        # LLMが出力するマークダウンを削除
        script_result_cleaned = script_result.strip().replace("```python", "").replace("```", "").strip()
        
        return planner_result, script_result_cleaned

    # --- 5. グラフの配線 (エッジと条件分岐) ---

    def _after_bad_request_check(self, state: ManimGraphState):
        """[Conditional Edge] 不正リクエストか"""
        if state["is_bad_request"]:
            self.graph_logger.error("--- [Branch] Bad Request. Ending Graph. ---")
            return "end_with_error" 
        self.graph_logger.debug("--- [Branch] Secure. Proceeding to Lint. ---")
        return "lint_check" 

    def _after_lint_check(self, state: ManimGraphState):
        """[Conditional Edge] リンターエラーか、リトライ上限か"""
        if state["error_type"] == "lint":
            if state["current_retry"] >= state["max_retries"]:
                self.graph_logger.warning("--- [Branch] Max Retries Reached (Lint Error). Ending. ---")
                return "end_with_error"
            self.graph_logger.info("--- [Branch] Linter Failed. Proceeding to Refine. ---")
            return "refine" 
        self.graph_logger.debug("--- [Branch] Linter Passed. Proceeding to Execute. ---")
        return "execute" 
    
    def _after_execution(self, state: ManimGraphState):
        """[Conditional Edge] 実行時エラーか、リトライ上限か"""
        if state["error_type"] == "runtime":
            if state["current_retry"] >= state["max_retries"]:
                self.graph_logger.warning("--- [Branch] Max Retries Reached (Runtime Error). Ending. ---")
                return "end_with_error"
            self.graph_logger.info("--- [Branch] Runtime Error. Proceeding to Refine. ---")
            return "refine"
        
        self.graph_logger.info("--- [Branch] Execution Succeeded. Ending Graph. ---")
        return "end_with_success"
    
    def _build_graph(self):
        """LangGraphのワークフローを定義・構築する"""
        workflow = StateGraph(ManimGraphState)
        workflow.add_node("generate_initial", self._generate_initial_script)
        workflow.add_node("check_bad_request", self._check_bad_request)
        workflow.add_node("lint_check", self._lint_check)
        workflow.add_node("execute", self._execute_script)
        workflow.add_node("refine", self._refine_script_on_error)
        workflow.set_entry_point("generate_initial")
        workflow.add_edge("generate_initial", "check_bad_request")
        workflow.add_edge("refine", "check_bad_request") 
        workflow.add_conditional_edges(
            "check_bad_request", self._after_bad_request_check,
            {"end_with_error": END, "lint_check": "lint_check"}
        )
        workflow.add_conditional_edges(
            "lint_check", self._after_lint_check,
            {"refine": "refine", "execute": "execute", "end_with_error": END}
        )
        workflow.add_conditional_edges(
            "execute", self._after_execution,
            {"refine": "refine", "end_with_success": END, "end_with_error": END}
        )
        return workflow
    
    # --- 6. グラフ実行メソッド ---
    
    def generate_videos_langgraph(self, video_id, content, enhance_prompt, max_loop=3):
        """
        LangGraphワークフローを実行して動画を生成する
        """
        self.graph_logger.info(f"--- Starting Graph for Video ID: {video_id} (Max Retries: {max_loop}) ---")
        
        initial_state: ManimGraphState = {
            "user_request": content,
            "generation_instructions": enhance_prompt,
            "video_id": video_id,
            "animation_plan": "", # 初期状態では空
            "current_script": "",
            "last_error": "",
            "error_type": "",
            "is_bad_request": False,
            "max_retries": max_loop,
            "current_retry": 0
        }
        
        final_state = self.app.invoke(initial_state)

        if final_state["is_bad_request"]:
            self.graph_logger.error("--- Graph Finished: Bad Request ---")
            return "bad_request"
        
        if final_state["last_error"]:
            self.graph_logger.error(f"--- Graph Finished: Error (Max Retries Reached) ---")
            return "error"
        
        if not final_state["last_error"] and not final_state["is_bad_request"]:
             self.graph_logger.info("--- Graph Finished: Success ---")
             return "Success"
        
        self.graph_logger.critical("--- Graph Finished: Fallback (Unknown State) ---")
        return "fall back"
    
    def explain_concept(self,input_text: str) -> str:
        """ [Helper] concept_promptをシナリオに変換する """
        self.graph_logger.info(f"Explaining concept: {input_text[:50]}...")
        prompt = PromptTemplate(
            input_variables=["input_text"],
            template=self.prompts["explain"]["prompt"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first=prompt | self.flash_llm,
            last=parser
        )
        output = chain.invoke({"input_text": input_text})
        self.graph_logger.info("Concept explained successfully.")
        return output
    
    # --- 7. ヘルパーメソッド (Pyright) ---

    def parse_pyright_output_for_llm(self,pyright_json: dict) -> str:
        diagnostics = pyright_json.get("generalDiagnostics", [])
        summary = pyright_json.get("summary", {})
        lines = []
        for i, diag in enumerate(diagnostics, start=1):
            file = diag.get("file", "")
            rule = diag.get("rule", "")
            severity = diag.get("severity", "")
            message = diag.get("message", "").replace("\n", " ").strip()
            start_line = diag.get("range", {}).get("start", {}).get("line", "?")
            lines.append(f"[Error {i}]\nfile: {file}\nrule: {rule}\nseverity: {severity}\nline: {start_line}\nmessage: {message}\n")
        lines.append(f"[Summary]\nerrorCount: {summary.get('errorCount', 0)}\nwarningCount: {summary.get('warningCount', 0)}\n")
        return "\n".join(lines)
    
    def has_no_pyright_errors(self,pyright_json: dict) -> bool:
        summary = pyright_json.get("summary", {})
        error_count = summary.get("errorCount", 0)
        return error_count == 0
    
if __name__ == "__main__":
    service = ManimGraphAnimationService()
    
    # (ダミーのManimコマンドを作成)
    # 実際の実行では、Manimがインストールされている必要があります
    # このスクリプトを実行する前に `pip install manim` などを実行してください。
    
    # LangGraph版のメソッドを呼び出す
    is_success = service.generate_videos_langgraph(
        video_id='sankakukannsuu',
        content="""
        # 【高校1年生向け】三角関数の“動き”を単位円で体感しよう --- ## 0. 今日のゴール - 「sinθ, cosθの“ずらし”や符号について、なぜかを動きで実感しよう」 - 結論：\(\cos\theta = \sin(\theta+\frac{\pi}{2})\)、\(\sin\theta = -\cos(\theta+\frac{\pi}{2})\)が単位円で体感できることを目指す --- ## 1. 単位円で三角関数スタート！ まず半径1（原点中心）の円＝**単位円**を用意しよう。 - x軸の正の方向（右向き）を0°、そこから反時計回りに角度\(\theta\)をとる
        """,
        enhance_prompt="円とサインカーブを並べて表示して、動きを連動させてください。",
        max_loop=3 # (最大ループ回数を指定)
    )
    print(f"\n--- Final Result: {is_success} ---")
