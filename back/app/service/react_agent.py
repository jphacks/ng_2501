import os
import re
import subprocess
import textwrap
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, Literal, Union

import tomllib
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import StateGraph, END

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from app.tools.lint import format_and_linter
from app.tools.manim_lint import parse_manim_or_python_traceback, format_error_for_llm
from app.tools.secure import is_code_safe

load_dotenv()


# === RAG付き ReAct 用の状態 ===
class RAGAgentState(TypedDict):
    user_prompt: str
    video_id: str
    loops: int
    max_loops: int
    # RAG
    rag_context: Optional[str]
    # Reason/Act
    plan: Optional[str]
    script: Optional[str]
    tmp_path: Optional[str]
    # Lint/Run
    lint_json: Optional[Dict[str, Any]]
    lint_ok: bool
    lint_summary: Optional[str]
    run_ok: Optional[bool]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    # 反省
    last_error_kind: Optional[str]  # "lint" | "runtime" | "security" | None
    last_error_summary: Optional[str]


class ManimAnimationReActService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        prompts_path = base_dir / "prompts.toml"
        with open(str(prompts_path), "rb") as f:
            self.prompts = tomllib.load(f)

        self.think_llm = self._load_llm("gemini-2.5-flash")
        self.pro_llm = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm = self._load_llm("gemini-2.5-flash-lite")

    def _load_llm(self, model_type: str):
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv("GEMINI_API_KEY"))

    # --- 知識の構造化説明（任意） ---
    def explain_concept(self, input_text: str) -> str:
        prompt = PromptTemplate(
            input_variables=["input_text"],
            template=self.prompts["explain"]["prompt"],
        )
        parser = StrOutputParser()
        chain = RunnableSequence(first=prompt | self.flash_llm, last=parser)
        return chain.invoke({"input_text": input_text})

    # --- 既存のスクリプト生成（単発） ---
    def generate_script_with_prompt(self, explain_prompt: str, video_enhance_prompt: str) -> str:
        manim_planer = PromptTemplate(
            input_variables=["user_prompt"],
            optional_variables=["video_enhance_prompt"],
            template=self.prompts["chain"]["manim_planer_with_instruct"],
        )
        parser = StrOutputParser()
        manim_script_prompt = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"],
        )
        chain = RunnableSequence(first=manim_planer | self.flash_llm, last=manim_script_prompt | self.pro_llm | parser)
        output = chain.invoke({"user_prompt": explain_prompt, "video_enhance_prompt": video_enhance_prompt})
        return output.replace("```python", "").replace("```", "")

    # --- 既存のスクリプト生成（簡易） ---
    def generate_script(self, video_instract_prompt: str) -> str:
        prompt1 = PromptTemplate(input_variables=["user_prompt"], template=self.prompts["chain"]["manim_planer"])
        prompt2 = PromptTemplate(input_variables=["instructions"], template=self.prompts["chain"]["manim_script_generate"])
        parser = StrOutputParser()
        chain = RunnableSequence(first=prompt1 | self.think_llm, last=prompt2 | self.pro_llm | parser)
        output = chain.invoke({"user_prompt": video_instract_prompt})
        return output.replace("```python", "").replace("```", "")

    # --- RAG DB をロード ---
    def _load_rag_db(self):
        """Manim公式ドキュメントRAGデータベースをロード"""
        db_dir = Path(__file__).resolve().parent.parent / "tools" / "embeding_data" / "manim_chroma_db"
        embedding_function = HuggingFaceEmbeddings(model_name="jinaai/jina-code-embeddings-1.5b")
        return Chroma(
            collection_name="manim_docs",
            persist_directory=str(db_dir),
            embedding_function=embedding_function,
        )

    # --- Pyright diagnostics 用 ---
    def rag_search_related_docs_for_diagnostics(self, diagnostics: list[dict], k: int = 2) -> str:
        """Pyright診断ごとにRAG検索を行い、ルール別にまとめる"""
        db = self._load_rag_db()
        seen_urls = set()
        rule_to_docs: Dict[str, list[str]] = {}

        for diag in diagnostics:
            message = diag.get("message", "")
            rule = diag.get("rule", "unknown")
            manim_refs = re.findall(r"manim[\.\w]+", message)
            query = " ".join(manim_refs) if manim_refs else message[:160]

            results = db.similarity_search(query, k=k)
            docs = []
            for r in results:
                url = r.metadata.get("source_url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    docs.append(
                        f"- {r.metadata.get('full_name', '')}\n"
                        f"{r.page_content[:400]}...\n"
                        f"URL: {url}\n"
                    )
            if docs:
                rule_to_docs.setdefault(rule, []).extend(docs)

        if not rule_to_docs:
            return "No related documentation found."

        doc_sections = []
        for rule, docs in rule_to_docs.items():
            section = f"### Rule: {rule}\n" + "\n".join(docs[:2])
            doc_sections.append(section)

        return "\n\n".join(doc_sections[:5])

    # --- 実行時エラー用 RAG ---
    def rag_search_related_docs_for_innererror(self, inner_error: str, k: int = 3) -> str:
        db = self._load_rag_db()
        seen_urls = set()

        manim_refs = re.findall(r"manim[\.\w]+", inner_error)
        base_queries = manim_refs or []

        error_phrases = re.findall(
            r"(?:AttributeError|TypeError|ValueError|LaTeX|ImportError|SyntaxError|NameError).*", inner_error
        )
        if error_phrases:
            base_queries.extend(error_phrases)

        if not base_queries:
            base_queries.append(inner_error[:200])

        aggregated_results = []
        for q in base_queries[:4]:
            results = db.similarity_search(q, k=k)
            for r in results:
                url = r.metadata.get("source_url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    aggregated_results.append(
                        f"- {r.metadata.get('full_name', '')}\n"
                        f"{r.page_content[:400]}...\n"
                        f"URL: {url}\n"
                    )

        if not aggregated_results:
            return "No related documentation found."
        return "\n\n".join(aggregated_results[:6])

    # --- RAG統合コード修正エージェント ---
    def fix_code_agent(self, file_name: str, concept: str, error_info, mode: Optional[str] = None) -> str:
        """
        mode="lint"       → Pyright JSON (静的エラー)
        mode="innererror" → Manim 実行エラーテキスト
        mode=None         → 自動判定
        """
        tmp_path = Path(f"tmp/{file_name}.py")
        script = tmp_path.read_text(encoding="utf-8")

        # 自動判定
        if mode is None:
            if isinstance(error_info, dict):
                mode = "lint"
            elif isinstance(error_info, str):
                mode = "innererror"
            else:
                raise TypeError(f"Unsupported error_info type: {type(error_info)}")

        # それぞれのエラー説明とRAGコンテキスト
        if mode == "lint":
            diagnostics = error_info.get("generalDiagnostics", [])
            related_docs = self.rag_search_related_docs_for_diagnostics(diagnostics)
            error_descriptions = "\n\n".join(
                [
                    f"[{i+1}] Rule: {d.get('rule','?')}\n"
                    f"Severity: {d.get('severity')}\n"
                    f"Message: {d.get('message')}"
                    for i, d in enumerate(diagnostics[:10])
                ]
            )
            error_context_title = "静的解析（Pyright）診断結果"
        elif mode == "innererror":
            related_docs = self.rag_search_related_docs_for_innererror(error_info)
            error_descriptions = error_info[:800]
            error_context_title = "実行時エラー（Manim Traceback）"
        else:
            raise ValueError(f"Invalid mode: {mode}")

        repair_prompt = PromptTemplate(
            input_variables=[
                "concept_summary",
                "error_context_title",
                "error_descriptions",
                "related_docs",
                "original_script",
            ],
            template=self.prompts["repair"]["prompt_template"]
            if "repair" in self.prompts
            else """
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
            - 日本語フォントを明示指定してください（Text使用時）

            出力フォーマット:
            ```python
            from manim import *
            class GeneratedScene(Scene):
                def construct(self):
                    # 修正版コード
            """,
        )
        parser = StrOutputParser()
        chain = repair_prompt | self.pro_llm | parser
        script_fixed = chain.invoke(
            {
                "concept_summary": concept,
                "error_context_title": error_context_title,
                "error_descriptions": error_descriptions,
                "related_docs": related_docs,
                "original_script": script,
            }
        )

        script_clean = script_fixed.replace("```python", "").replace("```", "")
        tmp_path.write_text(script_clean, encoding="utf-8")
        return script_clean

    # --- Pyright JSON → LLM向けサマリ ---
    def parse_pyright_output_for_llm(self, pyright_json: dict) -> str:
        diagnostics = pyright_json.get("generalDiagnostics", [])
        summary = pyright_json.get("summary", {})

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

    def has_no_pyright_errors(self, pyright_json: dict) -> bool:
        summary = pyright_json.get("summary", {})
        error_count = summary.get("errorCount", 0)
        return error_count == 0

    # --- 実行 ---
    def run_script(self, video_id: str, script: str) -> str:
        Path("tmp").mkdir(exist_ok=True, parents=True)
        tmp_path = Path(f"tmp/{video_id}.py")
        tmp_path.write_text(script, encoding="utf-8")

        if not is_code_safe(script):
            return "bad_request"

        try:
            subprocess.run(
                ["manim", "-pql", str(tmp_path), "GeneratedScene"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return "Success"
        except subprocess.CalledProcessError as e:
            return e.stderr

    # === RAG: プロンプトから関連文書を集めた短い文脈を作る ===
    def _rag_context_from_prompt(self, user_prompt: str, k: int = 4) -> str:
        db = self._load_rag_db()
        results = db.similarity_search(user_prompt, k=k)
        seen = set()
        chunks = []
        for r in results:
            url = r.metadata.get("source_url", "")
            if url in seen:
                continue
            seen.add(url)
            chunks.append(f"- {r.metadata.get('full_name','')}\n{r.page_content[:400]}...\nURL: {url}\n")
        return "\n".join(chunks[:6]) if chunks else ""

    # === Reason: RAG文脈+直近エラーで Plan を作る ===
    def _plan_with_rag(self, user_prompt: str, rag_context: str, last_error_summary: Optional[str]) -> str:
        pl = PromptTemplate(
            input_variables=["user_prompt", "context", "last_error"],
            template=textwrap.dedent(
                """
                You are a senior Manim (0.18) engineer. Create a concise plan for a minimal, runnable Scene.

                Constraints:
                - Use only manim (numpy optional). No other libs.
                - Prefer MathTex for math; for Japanese use Text with explicit font.
                - Keep it lightweight (-pql). Avoid heavy rendering & TexTemplate unless necessary.
                - If there was a previous error, adapt the plan to fix it.

                ## User prompt
                {user_prompt}

                ## Context from Manim docs (RAG)
                {context}

                ## Last error (optional)
                {last_error}

                ## Output (bullet list with steps / objects / simple animations / pitfalls)
                """
            ),
        )
        parser = StrOutputParser()
        return (pl | self.think_llm | parser).invoke(
            {
                "user_prompt": user_prompt,
                "context": rag_context or "(no extra context)",
                "last_error": last_error_summary or "",
            }
        ).strip()

    # === Act: Plan (+RAG文脈) からスクリプト生成 ===
    def _generate_from_plan_with_context(self, plan_text: str, rag_context: str) -> str:
        merged = f"{plan_text}\n\n### Helpful context from docs\n{rag_context}"
        gen = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"],
        )
        parser = StrOutputParser()
        code = (gen | self.pro_llm | parser).invoke({"instructions": merged})
        return code.replace("```python", "").replace("```", "").strip()

    # === 実行時エラーのサマリ生成 ===
    def _runtime_summary(self, stderr: str) -> str:
        parsed = parse_manim_or_python_traceback(stderr)
        return format_error_for_llm(parsed)

    # === LangGraph ノード群 ===
    def _node_retrieve(self, st: RAGAgentState) -> RAGAgentState:
        st["rag_context"] = self._rag_context_from_prompt(st["user_prompt"], k=4)
        return st

    def _node_plan(self, st: RAGAgentState) -> RAGAgentState:
        st["plan"] = self._plan_with_rag(st["user_prompt"], st.get("rag_context") or "", st.get("last_error_summary"))
        return st

    def _node_generate_or_fix(self, st: RAGAgentState) -> RAGAgentState:
        if st.get("script") is None:
            code = self._generate_from_plan_with_context(st["plan"] or "", st.get("rag_context") or "")
        else:
            # Fix: Lintなら lint_json、Runtimeなら run_stderr を優先
            err = st.get("last_error_summary") or ""
            error_info = st.get("lint_json") if st.get("last_error_kind") == "lint" else (st.get("run_stderr") or err)
            code = self.fix_code_agent(file_name=st["video_id"], concept=st["user_prompt"], error_info=error_info)

        st["script"] = code
        tmp = Path(f"tmp/{st['video_id']}.py")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(code, encoding="utf-8")
        st["tmp_path"] = str(tmp)
        return st

    def _node_format_and_lint(self, st: RAGAgentState) -> RAGAgentState:
        res = format_and_linter(Path(st["tmp_path"]))
        st["lint_json"] = res
        st["lint_ok"] = self.has_no_pyright_errors(res)
        st["last_error_kind"] = None if st["lint_ok"] else "lint"
        st["last_error_summary"] = None if st["lint_ok"] else self.parse_pyright_output_for_llm(res)
        return st

    def _decide_after_lint(self, st: RAGAgentState) -> Literal["run", "fix_or_replan"]:
        return "run" if st.get("lint_ok") else "fix_or_replan"

    def _node_run(self, st: RAGAgentState) -> RAGAgentState:
        # Lint=0 のあと run_script を呼ぶ（グラフ内で実行は一カ所のみ）
        result = self.run_script(st["video_id"], st["script"] or "")
        if result == "Success":
            st["run_ok"] = True
            st["run_stdout"] = ""
            st["run_stderr"] = ""
            st["last_error_kind"] = None
            st["last_error_summary"] = None
        elif result == "bad_request":
            st["run_ok"] = False
            st["run_stdout"] = ""
            st["run_stderr"] = "bad_request"
            st["last_error_kind"] = "security"
            st["last_error_summary"] = "Security policy violation: bad_request"
        else:
            st["run_ok"] = False
            st["run_stdout"] = ""
            st["run_stderr"] = result
            st["last_error_kind"] = "runtime"
            st["last_error_summary"] = self._runtime_summary(result)
        return st

    # Literal に END（変数）は入れられないため Union[object, Literal["fix_or_replan"]] にする
    def _decide_after_run(self, st: RAGAgentState) -> Union[object, Literal["fix_or_replan"]]:
        return END if st.get("run_ok") else "fix_or_replan"

    def _node_fix_or_replan(self, st: RAGAgentState) -> RAGAgentState:
        st["loops"] = int(st.get("loops", 0)) + 1
        return st

    def _decide_continue(self, st: RAGAgentState) -> Union[object, Literal["retrieve"]]:
        return "retrieve" if st.get("loops", 0) < int(st.get("max_loops", 5)) else END

    # === パブリックAPI: RAG×ReAct で最終スクリプトを生成し、実行まで到達させる ===
    def generate_script_langgraph_rag(self, video_instruct_prompt: str, video_id: str, max_loops: int = 5):
        """
        1) RAG → Plan → Generate/Fix → Format+Lint を繰り返し、Lintエラー=0にする
        2) run_script() を実行（グラフ内で一度）
        3) 実行失敗なら ReAct で再計画→修正
        戻り値: (final_script: str, run_ok: bool, final_state: dict)
        """
        g = StateGraph(RAGAgentState)
        g.add_node("retrieve", self._node_retrieve)
        g.add_node("plan", self._node_plan)
        g.add_node("generate_or_fix", self._node_generate_or_fix)
        g.add_node("format_and_lint", self._node_format_and_lint)
        g.add_node("run", self._node_run)
        g.add_node("fix_or_replan", self._node_fix_or_replan)

        g.set_entry_point("retrieve")
        g.add_edge("retrieve", "plan")
        g.add_edge("plan", "generate_or_fix")
        g.add_edge("generate_or_fix", "format_and_lint")
        g.add_conditional_edges("format_and_lint", self._decide_after_lint, {"run": "run", "fix_or_replan": "fix_or_replan"})
        g.add_conditional_edges("run", self._decide_after_run, {END: END, "fix_or_replan": "fix_or_replan"})
        g.add_conditional_edges("fix_or_replan", self._decide_continue, {"retrieve": "retrieve", END: END})

        app = g.compile()
        init: RAGAgentState = {
            "user_prompt": video_instruct_prompt,
            "video_id": video_id,
            "loops": 0,
            "max_loops": max_loops,
            "rag_context": None,
            "plan": None,
            "script": None,
            "tmp_path": None,
            "lint_json": None,
            "lint_ok": False,
            "lint_summary": None,
            "run_ok": None,
            "run_stdout": None,
            "run_stderr": None,
            "last_error_kind": None,
            "last_error_summary": None,
        }
        final = app.invoke(init)
        return final.get("script") or "", bool(final.get("run_ok")), final

    # === 外部呼び出し向け: 生成→（グラフ内で）実行まで ===
    def generate_videos(self, video_id: str, content: str, enhance_prompt: str):
        script, ok, state = self.generate_script_langgraph_rag(content, video_id=video_id, max_loops=5)
        if not script:
            return "error"
        # 実行はグラフ内1回のみ。成功時に最終スクリプトを保存（念のため上書き）
        if ok:
            Path("tmp").mkdir(exist_ok=True, parents=True)
            Path(f"tmp/{video_id}.py").write_text(script, encoding="utf-8")
            return "Success"
        if state.get("last_error_kind") == "security":
            return "bad_request"
        return "error"


if __name__ == "__main__":
    service = ManimAnimationReActService()
    is_success = service.generate_videos(
        video_id="sankakukannsuu",
        content="""
        高1向け。単位円と角度θ、点P(x=cosθ, y=sinθ)を可視化。
        円と点の移動をアニメーションし、最後に cos^2 θ + sin^2 θ = 1 を MathTex で表示。
        日本語テキストは Text で表示（フォント明示）。
        """,
        enhance_prompt="",
    )
    print(is_success)
