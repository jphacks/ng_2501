import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain_core.output_parsers import StrOutputParser


from app.tools.lint import format_and_linter
from app.tools.manim_lint import parse_manim_or_python_traceback,format_error_for_llm
from app.tools.secure import is_code_safe

load_dotenv()

class ManimAnimationService:
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
    
    # コード修正エージェント
    def fix_code_agent(self,file_name,concept,lint_summary:str):
        #　リンターにかけてだめだったものを修正するファイル
        tmp_path = Path(f"tmp/{file_name}.py")
        
        with open(tmp_path, "r") as f:
            script = f.read()

        repair_prompt = PromptTemplate(
            input_variables=["concept_summary", "lint_summary", "original_script"],
            template="""
        あなたはプロの Manim 開発者です。

        1. コンセプトの要約

        {concept_summary}

        2. 静的解析の診断結果

        {lint_summary}

        3. 元のスクリプト

        {original_script}

        タスク

        上記の診断で指摘された すべてのエラーを修正しつつ、コンセプトが示す意図（意味・見た目）を保ったままコードを書き直してください。
        説明は一切書かず、有効な Python コードのみを出力してください。

        出力形式
        ```python
        from manim import *
        class GeneratedScene(Scene):
            def construct(self):
                # 必要な Manim object and call animation
                # Text(r"\\frac{{a}}{{b}}")
                # ...
        """
        )
        
        parser = StrOutputParser()
        chain = repair_prompt | self.flash_llm | parser
        
        script = chain.invoke(
            {
                "concept_summary" : concept,
                "lint_summary": lint_summary,
                "original_script":script
            }
        )
        
        with open(tmp_path, "w") as f:
            f.write(script.replace("```python", "").replace("```", ""))
        return script.replace("```python", "").replace("```", "")

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
            err =  format_and_linter(tmp_path)
            print(err)
            err_paser_output_llm=self.parse_pyright_output_for_llm(err)
            is_success = self.has_no_pyright_errors(err)
            if is_success:
                video_success = self.run_script(video_id,script)
                if video_success=="Success":
                    return 'Success'
                elif video_success=="bad_request":
                    return 'bad_request'
                else:
                    inner_error = parse_manim_or_python_traceback(video_success)
                    inner_error = format_error_for_llm(inner_error)
                    script = self.fix_code_agent(video_id,content,inner_error)
                    loop += 1
                    continue
            else:
                script = self.fix_code_agent(video_id,content,err_paser_output_llm)
                loop += 1
                continue
        return "error"
    
if __name__ == "__main__":
    service = ManimAnimationService()
    prompt = service.explain_concept("微分積分学の基本定理について説明してください。可能な限り容易にしてください。")
    # generate script
    is_success = service.generate_videos(
        video_id='sankakukannsuu',
        content="""
        # 【高校1年生向け】三角関数の“動き”を単位円で体感しよう --- ## 0. 今日のゴール - 「sinθ, cosθの“ずらし”や符号について、なぜかを動きで実感しよう」 - 結論：\(\cos\theta = \sin(\theta+\frac{\pi}{2})\)、\(\sin\theta = -\cos(\theta+\frac{\pi}{2})\)が単位円で体感できることを目指す --- ## 1. 単位円で三角関数スタート！ まず半径1（原点中心）の円＝**単位円**を用意しよう。 - x軸の正の方向（右向き）を0°、そこから反時計回りに角度\(\theta\)をとる
        """,
        enhance_prompt=""
    )
    print(is_success)