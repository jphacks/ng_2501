import os
import json
import time
import uuid
import logging
import subprocess
from functools import wraps
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain_core.output_parsers import StrOutputParser


from app.tools.lint import format_and_linter
from app.tools.manim_lint import parse_manim_or_python_traceback, format_error_for_llm
from app.tools.secure import is_code_safe
from app.tools.embeding_data.manim_rag import ManimDocsRAG


# =========================
# ロギング共通ユーティリティ
# =========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
TRACE_LLM = bool(int(os.getenv("TRACE_LLM_PROMPTS", "0")))
TRIM = int(os.getenv("LOG_TRIM", "1200"))  # 長文をログ出力するときの最大文字数

def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("manim_rag_service")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    handler = logging.StreamHandler()
    fmt = "%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s"
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = _setup_logger()

def _redact(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.replace(os.getenv("GEMINI_API_KEY", "*****") or "*****", "****REDACTED****")
    return s

def _clip(s: str, n: int = TRIM) -> str:
    if not isinstance(s, str):
        return s
    return s if len(s) <= n else s[: n] + f"... <trimmed {len(s)-n} chars>"

def trace(func):
    """関数の入出・所要時間を統一ログ。長文は自動トリム。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        call_id = str(uuid.uuid4())[:8]
        t0 = time.perf_counter()
        try:
            safe_kwargs = {
                k: _clip(_redact(v)) if isinstance(v, str) else v
                for k, v in kwargs.items()
            }
            logger.debug(f"▶️  {func.__name__} start call_id={call_id} kwargs={safe_kwargs}")
            out = func(*args, **kwargs)
            t1 = time.perf_counter()
            logger.debug(f"✅  {func.__name__} end   call_id={call_id} elapsed={t1-t0:.3f}s "
                         f"result_preview={_clip(str(out))}")
            return out
        except Exception as e:
            t1 = time.perf_counter()
            logger.exception(f"💥 {func.__name__} error call_id={call_id} elapsed={t1-t0:.3f}s: {e}")
            raise
    return wrapper

load_dotenv()

class ManimAnimationOnRAGService:
    def __init__(self):
        self.req_id = str(uuid.uuid4())[:8]
        base_dir = Path(__file__).resolve().parent
        prompts_path = base_dir / "prompts.toml"
        prompts_path = str(prompts_path)
        logger.info(f"[{self.req_id}] 初始化 start prompts_path={prompts_path}")
        with open(prompts_path, 'rb') as f:
            self.prompts = tomllib.load(f)

        # LLM読み込み
        self.think_llm = self._load_llm("gemini-2.5-flash")
        self.pro_llm   = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm  = self._load_llm("gemini-2.5-flash-lite")
        self.rag_client = ManimDocsRAG(logger=logger)

        # optional_variables は LangChain の PromptTemplate には無いオプション
        # → 将来の混乱を避けるため警告のみ出し、機能はそのまま（無視される）
        if logger.isEnabledFor(logging.WARNING):
            logger.warning(f"[{self.req_id}] 注意: PromptTemplate に 'optional_variables' は存在しません（無視されます）")

        logger.info(f"[{self.req_id}] 初始化 done")

    def _load_llm(self, model_type: str):
        logger.debug(f"[{self.req_id}] LLMロード model={model_type}")
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))

    # 知識の構造化説明
    @trace
    def explain_concept(self, input_text: str) -> str:
        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] explain_concept.prompt =\n{_clip(self.prompts['explain']['prompt'])}")
            logger.debug(f"[{self.req_id}] explain_concept.vars = {{'input_text': '{_clip(input_text)}'}}")

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
        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] explain_concept.output =\n{_clip(output)}")
        return output

    # スクリプトを作成する最新prompt
    @trace
    def generate_script_with_prompt(self, explain_prompt, video_enhance_prompt):
        """
        動画のスクリプトを生成する関数
        """
        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] generate_script_with_prompt.planner_template =\n"
                         f"{_clip(self.prompts['chain']['manim_planer_with_instruct'])}")
            logger.debug(f"[{self.req_id}] generate_script_with_prompt.script_template =\n"
                         f"{_clip(self.prompts['chain']['manim_script_generate'])}")

        # NOTE: optional_variables は無視される
        manim_planer = PromptTemplate(
            input_variables=['user_prompt', 'video_enhance_prompt'],
            template=self.prompts['chain']['manim_planer_with_instruct']
        )
        parser = StrOutputParser()

        manim_script_prompt = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"]
        )

        t0 = time.perf_counter()
        plan = (manim_planer | self.flash_llm).invoke({
            "user_prompt": explain_prompt,
            "video_enhance_prompt": video_enhance_prompt or ""
        })
        t1 = time.perf_counter()
        logger.info(f"[{self.req_id}] planner LLM elapsed={t1-t0:.3f}s")

        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] planner.output =\n{_clip(str(plan))}")

        t2 = time.perf_counter()
        script = (manim_script_prompt | self.pro_llm | parser).invoke({"instructions": plan})
        t3 = time.perf_counter()
        logger.info(f"[{self.req_id}] script LLM elapsed={t3-t2:.3f}s")

        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] script.raw =\n{_clip(script)}")

        clean = script.replace("```python", "").replace("```", "")
        logger.debug(f"[{self.req_id}] script.cleaned_len={len(clean)}")
        return clean

    # コード生成AIエージェント
    @trace
    def generate_script(self, video_instract_prompt: str) -> str:
        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] generate_script.templates = "
                         f"planner:\n{_clip(self.prompts['chain']['manim_planer'])}\n"
                         f"generator:\n{_clip(self.prompts['chain']['manim_script_generate'])}")

        prompt1 = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["chain"]["manim_planer"]
        )
        prompt2 = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"]
        )
        parser = StrOutputParser()

        t0 = time.perf_counter()
        plan = (prompt1 | self.think_llm).invoke({"user_prompt": video_instract_prompt})
        t1 = time.perf_counter()
        logger.info(f"[{self.req_id}] generate_script.plan elapsed={t1-t0:.3f}s")

        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] generate_script.plan_out =\n{_clip(str(plan))}")

        t2 = time.perf_counter()
        script = (prompt2 | self.pro_llm | parser).invoke({"instructions": plan})
        t3 = time.perf_counter()
        logger.info(f"[{self.req_id}] generate_script.codegen elapsed={t3-t2:.3f}s")

        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] generate_script.raw =\n{_clip(script)}")

        return script.replace("```python", "").replace("```", "")

    # --- Pyright diagnostics 用 ---
    @trace
    def rag_search_related_docs_for_diagnostics(self, diagnostics: list[dict], k: int = 2) -> str:
        return self.rag_client.diagnostics_report(
            diagnostics,
            k=k,
            log_context=self.req_id,
        )

    # --- Inner Error 用 ---
    @trace
    def rag_search_related_docs_for_innererror(self, inner_error: str, k: int = 3) -> str:
        return self.rag_client.runtime_error_report(
            inner_error,
            k=k,
            log_context=self.req_id,
        )

    @trace
    def fix_code_agent(self, file_name: str, concept: str, error_info, mode: str = "lint"):
        tmp_path = Path(f"tmp/{file_name}.py")
        with open(tmp_path, "r") as f:
            script = f.read()

        # --- 自動判定 ---
        auto_mode = mode
        if mode is None:
            if isinstance(error_info, dict):
                auto_mode = "lint"
            elif isinstance(error_info, str):
                auto_mode = "innererror"
            else:
                raise TypeError(f"Unsupported error_info type: {type(error_info)}")

        logger.info(f"[{self.req_id}] FixCodeAgent mode={auto_mode}")

        # --- Lintモード ---
        if auto_mode == "lint":
            diagnostics = error_info.get("generalDiagnostics", [])
            related_docs = self.rag_search_related_docs_for_diagnostics(diagnostics)
            error_descriptions = "\n\n".join([
                f"[{i+1}] Rule: {d.get('rule','?')}\n"
                f"Severity: {d.get('severity')}\n"
                f"Message: {d.get('message')}"
                for i, d in enumerate(diagnostics[:10])
            ])
            error_context_title = "静的解析（Pyright）診断結果"
            logger.debug(f"[{self.req_id}] FixCodeAgent lint diag_count={len(diagnostics)}")

        # --- InnerErrorモード ---
        elif auto_mode == "innererror":
            related_docs = self.rag_search_related_docs_for_innererror(error_info)
            error_descriptions = _clip(error_info, 2000)
            error_context_title = "実行時エラー（Manim Traceback）"
            logger.debug(f"[{self.req_id}] FixCodeAgent innererror desc_len={len(error_descriptions)}")

        else:
            raise ValueError(f"Invalid mode: {auto_mode}")

        # Repair LLM 呼び出し
        repair_prompt = PromptTemplate(
            input_variables=["concept_summary", "error_context_title", "error_descriptions", "related_docs", "original_script"],
            template=self.prompts["repair"]["prompt_template"]
            if "repair" in self.prompts else """
        あなたはプロのManim開発者であり、Pythonエラー修正の専門家です。
        以下の情報をもとにスクリプトを修正してください。

        ## コンセプト概要
        {concept_summary}

        ## {error_context_title}
        {error_descriptions}

        ## 関連するManim公式ドキュメント（RAG検索結果）
        {related_docs}

        ## 元のスクリプト
        {original_script}

        ---
        タスク:
        - 全てのエラーを修正し、Manim APIの正しい構文・型・引数に合わせる
        - 不要なコメントや説明は書かず、有効なPythonコードのみ出力
        - 日本語フォントを明示指定するようにしてください

        出力フォーマット:
        ```python
        from manim import *
        class GeneratedScene(Scene):
            def construct(self):
                # 修正版コード
        """
        )
        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] repair.prompt =\n{_clip(repair_prompt.template)}")

        parser = StrOutputParser()
        t0 = time.perf_counter()
        script_fixed = (repair_prompt | self.pro_llm | parser).invoke({
            "concept_summary": concept,
            "error_context_title": error_context_title,
            "error_descriptions": error_descriptions,
            "related_docs": related_docs,
            "original_script": script,
        })
        t1 = time.perf_counter()
        logger.info(f"[{self.req_id}] repair LLM elapsed={t1-t0:.3f}s out_len={len(script_fixed)}")

        if TRACE_LLM:
            logger.debug(f"[{self.req_id}] repair.output =\n{_clip(script_fixed)}")

        script_clean = script_fixed.replace("```python", "").replace("```", "")
        with open(tmp_path, "w") as f:
            f.write(script_clean)
        logger.info(f"[{self.req_id}] FixCodeAgent wrote file={tmp_path} size={len(script_clean)}")
        return script_clean

    @trace
    def parse_pyright_output_for_llm(self, pyright_json: dict) -> str:
        diagnostics = pyright_json.get("generalDiagnostics", [])
        summary = pyright_json.get("summary", {})
        logger.debug(f"[{self.req_id}] pyright: errors={summary.get('errorCount',0)} "
                     f"warnings={summary.get('warningCount',0)} files={summary.get('filesAnalyzed',0)}")

        lines = []
        for i, diag in enumerate(diagnostics, start=1):
            file = diag.get("file", "")
            rule = diag.get("rule", "")
            severity = diag.get("severity", "")
            message = diag.get("message", "").replace("\n", " ").strip()
            start_line = diag.get("range", {}).get("start", {}).get("line", "?")

            lines.append(
                f"[Error {i}]\n"
                f"file: {file}\n"
                f"rule: {rule}\n"
                f"severity: {severity}\n"
                f"line: {start_line}\n"
                f"message: {message}\n"
            )

        lines.append(
            "[Summary]\n"
            f"errorCount: {summary.get('errorCount', 0)}\n"
            f"warningCount: {summary.get('warningCount', 0)}\n"
            f"filesAnalyzed: {summary.get('filesAnalyzed', 0)}\n"
            f"timeInSec: {summary.get('timeInSec', 0)}"
        )

        return "\n".join(lines)

    @trace
    def has_no_pyright_errors(self, pyright_json: dict) -> bool:
        summary = pyright_json.get("summary", {})
        error_count = summary.get("errorCount", 0)
        ok = error_count == 0
        logger.info(f"[{self.req_id}] pyright errorCount={error_count} -> ok={ok}")
        return ok

    # スクリプト管理するための関数
    @trace
    def run_script(self, video_id: str, script: str) -> str:
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{video_id}.py")
        with open(tmp_path, "w") as f:
            f.write(script)

        is_secure = is_code_safe(script)
        logger.info(f"[{self.req_id}] run_script path={tmp_path} secure={is_secure}")

        if is_secure:
            try:
                t0 = time.perf_counter()
                proc = subprocess.run(
                    ["manim", "-pql", str(tmp_path), "GeneratedScene"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True, check=True
                )
                t1 = time.perf_counter()
                logger.info(f"[{self.req_id}] manim success elapsed={t1-t0:.3f}s")
                if proc.stdout:
                    logger.debug(f"[{self.req_id}] manim.stdout:\n{_clip(proc.stdout, 3000)}")
                if proc.stderr:
                    logger.debug(f"[{self.req_id}] manim.stderr:\n{_clip(proc.stderr, 3000)}")
                return "Success"
            except subprocess.CalledProcessError as e:
                logger.warning(f"[{self.req_id}] manim failed returncode={e.returncode}")
                if e.stdout:
                    logger.debug(f"[{self.req_id}] manim.stdout:\n{_clip(e.stdout, 3000)}")
                if e.stderr:
                    logger.debug(f"[{self.req_id}] manim.stderr:\n{_clip(e.stderr, 3000)}")
                return e.stderr
        else:
            logger.error(f"[{self.req_id}] run_script rejected by safety checker")
            return "bad_request"

    # 動画作成ループをかける
    @trace
    def generate_videos(self, video_id, content, enhance_prompt):
        logger.info(f"[{self.req_id}] generate_videos start video_id={video_id}")

        # スクリプト生成
        script = self.generate_script_with_prompt(
            content,
            enhance_prompt
        )

        max_loop = 3
        loop = 0
        while loop < max_loop:
            logger.info(f"[{self.req_id}] loop={loop+1}/{max_loop}")

            if not os.path.exists("tmp"):
                os.makedirs("tmp")
            tmp_path = Path(f"tmp/{video_id}.py")
            with open(tmp_path, "w") as f:
                f.write(script)

            # Lint実行
            t0 = time.perf_counter()
            err = format_and_linter(tmp_path)
            t1 = time.perf_counter()
            logger.info(f"[{self.req_id}] lint elapsed={t1-t0:.3f}s")
            logger.debug(f"[{self.req_id}] lint.raw = { _clip(json.dumps(err, ensure_ascii=False), 3000) }")

            is_success = self.has_no_pyright_errors(err)

            if is_success:
                video_success = self.run_script(video_id, script)
                if video_success == "Success":
                    logger.info(f"[{self.req_id}] generate_videos SUCCESS")
                    return 'Success'
                elif video_success == "bad_request":
                    logger.error(f"[{self.req_id}] generate_videos rejected by safety -> stop")
                    return 'bad_request'
                else:
                    # 実行時エラー解析
                    inner_error = parse_manim_or_python_traceback(video_success)
                    inner_error = format_error_for_llm(inner_error)
                    logger.debug(f"[{self.req_id}] inner_error.parsed =\n{_clip(inner_error, 3000)}")
                    script = self.fix_code_agent(video_id, content, inner_error, mode=None)  # 自動判定
                    loop += 1
                    continue
            else:
                # 静的エラーをもとに修復
                script = self.fix_code_agent(video_id, content, err, mode=None)  # 自動判定
                loop += 1
                continue

        logger.error(f"[{self.req_id}] generate_videos reached max_loop -> error")
        return "error"


if __name__ == "__main__":
    service = ManimAnimationOnRAGService()
    is_success = service.generate_videos(
        video_id='sankakukannsuu',
        content="""
        # 三角関数の“動き”を単位円で体感しよう --- ## 0. 今日のゴール - 「sinθ, cosθの“ずらし”や符号について、なぜかを動きで実感しよう」 - 結論：\\(\\cos\\theta = \\sin(\\theta+\\frac{\\pi}{2})\\)、\\(\\sin\\theta = -\\cos(\\theta+\\frac{\\pi}{2})\\)が単位円で体感できることを目指す --- ## 1. 単位円で三角関数スタート！ まず半径1（原点中心）の円**単位円**を用意しよう。 - x軸の正の方向（右向き）を0°、そこから反時計回りに角度\\(\\theta\\)をとるしたがって、  $$ \\cos^2 \\theta + \\sin^2 \\theta = 1 $$という **三角関数の基本的な関係式** が得られます
        """,
        enhance_prompt=""
    )
    print(is_success)
