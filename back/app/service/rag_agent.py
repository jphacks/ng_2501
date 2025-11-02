import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from pathlib import Path

from app.tools.lint import format_and_linter
from app.tools.manim_lint import parse_manim_or_python_traceback,format_error_for_llm
from app.tools.secure import is_code_safe


load_dotenv()

class ManimAnimationOnRAGService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        prompts_path = base_dir / "prompts.toml"
        prompts_path = str(prompts_path)
        with open(prompts_path, 'rb') as f:
            self.prompts = tomllib.load(f)
        self.think_llm = self._load_llm("gemini-2.5-flash")
        self.pro_llm   = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm  = self._load_llm("gemini-2.5-flash-lite")
    def _load_llm(self, model_type: str):
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))
    
    # 知識の構造化説明
    def explain_concept(self,input_text: str) -> str:
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
        return output
    
    # スクリプトを作成する最新prompt
    def generate_script_with_prompt(self,explain_prompt,video_enhance_prompt):
        """
        動画のスクリプトを生成する関数
        input:
            explain_prompt : 知識の構造化説明
            video_enhance_prompt : ビデオの動画を指導するプロンプト 
        output:
            script: 動画スクリプト
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
        
        chain = RunnableSequence(
            first= manim_planer | self.flash_llm,
            last= manim_script_prompt | self.pro_llm | parser
        )
        
        output = chain.invoke(
            {
                "user_prompt":explain_prompt,
                "video_enhance_prompt":video_enhance_prompt
            }
        )
        return output.replace("```python", "").replace("```", "")
    
    # コード生成AIエージェント
    def generate_script(self, video_instract_prompt: str) -> str:
        prompt1 = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["chain"]["manim_planer"]
        )
        prompt2 = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["manim_script_generate"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first=prompt1 | self.think_llm,
            last=prompt2 | self.pro_llm | parser
        )
        output = chain.invoke({"user_prompt" : video_instract_prompt})
        return output.replace("```python", "").replace("```", "")
    
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
        rule_to_docs = {}

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

    # --- Inner Error 用 ---
    def rag_search_related_docs_for_innererror(self, inner_error: str, k: int = 3) -> str:
        """
        Manim実行時エラー文字列に対してRAG検索。
        例: AttributeError, ValueError, LaTeX Errorなどを自動解析。
        """
        db = self._load_rag_db()
        seen_urls = set()

        # manim構文・クラス名を優先的に拾う
        manim_refs = re.findall(r"manim[\.\w]+", inner_error)
        base_queries = manim_refs or []

        # 一般的な例外メッセージを抽出
        error_phrases = re.findall(
            r"(?:AttributeError|TypeError|ValueError|LaTeX|ImportError|SyntaxError|NameError).*", inner_error
        )
        if error_phrases:
            base_queries.extend(error_phrases)

        # fallback（文全体の一部）
        if not base_queries:
            base_queries.append(inner_error[:200])

        # 実際の検索
        aggregated_results = []
        for q in base_queries[:4]:  # 最大4クエリ
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
    
    
    def fix_code_agent(self, file_name: str, concept: str, error_info, mode: str = "lint"):
        """
        RAG統合コード修正エージェント。
        mode="lint"       → Pyright JSON (静的エラー)
        mode="innererror" → Manim 実行エラーテキスト
        RAG統合コード修正エージェント。
        - error_info が dict の場合 → Pyright (静的解析)
        - error_info が str の場合 → Manim 実行エラー
        mode は自動判定される
        """
        tmp_path = Path(f"tmp/{file_name}.py")
        with open(tmp_path, "r") as f:
            script = f.read()

        # --- 自動判定 ---
        if mode is None:
            if isinstance(error_info, dict):
                mode = "lint"
            elif isinstance(error_info, str):
                mode = "innererror"
            else:
                raise TypeError(f"Unsupported error_info type: {type(error_info)}")

        # --- Lintモード ---
        if mode == "lint":
            diagnostics = error_info.get("generalDiagnostics", [])
            related_docs = self.rag_search_related_docs_for_diagnostics(diagnostics)
            error_descriptions = "\n\n".join([
                f"[{i+1}] Rule: {d.get('rule','?')}\n"
                f"Severity: {d.get('severity')}\n"
                f"Message: {d.get('message')}"
                for i, d in enumerate(diagnostics[:10])
            ])
            error_context_title = "静的解析（Pyright）診断結果"

        # --- InnerErrorモード ---
        elif mode == "innererror":
            related_docs = self.rag_search_related_docs_for_innererror(error_info)
            error_descriptions = error_info[:800]
            error_context_title = "実行時エラー（Manim Traceback）"

        else:
            raise ValueError(f"Invalid mode: {mode}")

        print(f"🧩 FixCodeAgent Mode: {mode}")


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
        """)
        parser = StrOutputParser()
        chain = repair_prompt | self.pro_llm | parser
        script_fixed = chain.invoke({
            "concept_summary": concept,
            "error_context_title": error_context_title,
            "error_descriptions": error_descriptions,
            "related_docs": related_docs,
            "original_script": script,
        })

        script_clean = script_fixed.replace("```python", "").replace("```", "")
        with open(tmp_path, "w") as f:
            f.write(script_clean)
        return script_clean


    def parse_pyright_output_for_llm(self,pyright_json: dict) -> str:
        """Convert Pyright JSON diagnostics into structured plain text for LLM input."""
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

    def has_no_pyright_errors(self,pyright_json: dict) -> bool:
        """
        Return True if there are no Pyright errors (errorCount == 0), else False.

        Args:
            pyright_json (dict): Parsed Pyright JSON output.

        Returns:
            bool: True if no errors, False otherwise.
        """
        summary = pyright_json.get("summary", {})
        error_count = summary.get("errorCount", 0)
        return error_count == 0
    
     # スクリプト管理するための関数
    def run_script(self, video_id: str, script: str) -> str:
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{video_id}.py")
        with open(tmp_path, "w") as f:
            f.write(script)
        is_secure=is_code_safe(script)
        if is_secure:
            try:
                subprocess.run(
                    ["manim", "-pql", str(tmp_path), "GeneratedScene"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True, check=True
                )
                return "Success"
            except subprocess.CalledProcessError as e:
                return e.stderr
        else:
            return "bad_request"
    
    # 動画作成ループをかける
    def generate_videos(self,video_id,content,enhance_prompt):
        # スクリプト生成
        script = self.generate_script_with_prompt(
            content,
            enhance_prompt
        )
        max_loop = 3
        loop = 0
        while loop < max_loop:
             # スクリプトを管理する
            if not os.path.exists("tmp"):
                os.makedirs("tmp")
            tmp_path = Path(f"tmp/{video_id}.py")
            with open(tmp_path, "w") as f:
                f.write(script)
            # tmp_pathに対して、format_and_linterを回す
            err = format_and_linter(tmp_path)
            print(err)

            # ❌ parse_pyright_output_for_llm は LLM用説明テキスト生成なので
            #    fix_code_agent には dict (err) のまま渡す必要がある
            is_success = self.has_no_pyright_errors(err)

            if is_success:
                video_success = self.run_script(video_id, script)
                if video_success == "Success":
                    return 'Success'
                elif video_success == "bad_request":
                    return 'bad_request'
                else:
                    inner_error = parse_manim_or_python_traceback(video_success)
                    inner_error = format_error_for_llm(inner_error)
                    # ✅ inner_error は str なので innererrorモード自動判定でOK
                    script = self.fix_code_agent(video_id, content, inner_error)
                    loop += 1
                    continue
            else:
                # ✅ err は dict, lintモード自動判定でOK
                script = self.fix_code_agent(video_id, content, err)
                loop += 1
                continue
        return "error"
    
if __name__ == "__main__":
    service = ManimAnimationOnRAGService()
    is_success = service.generate_videos(
        video_id='sankakukannsuu',
        content="""
        # 三角関数の“動き”を単位円で体感しよう --- ## 0. 今日のゴール - 「sinθ, cosθの“ずらし”や符号について、なぜかを動きで実感しよう」 - 結論：\(\cos\theta = \sin(\theta+\frac{\pi}{2})\)、\(\sin\theta = -\cos(\theta+\frac{\pi}{2})\)が単位円で体感できることを目指す --- ## 1. 単位円で三角関数スタート！ まず半径1（原点中心）の円**単位円**を用意しよう。 - x軸の正の方向（右向き）を0°、そこから反時計回りに角度\(\theta\)をとるしたがって、  $$ \cos^2 \theta + \sin^2 \theta = 1 $$という **三角関数の基本的な関係式** が得られます
        """,
        enhance_prompt=""
    )
    print(is_success)