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
        You are a professional Manim developer.

        ## 1. Concept Context
        {concept_summary}

        ## 2. Static Analysis Diagnostics
        {lint_summary}

        ## 3. Original Script
        {original_script}

        ### Task
        Rewrite the code to fix all listed errors while preserving the meaning and visuals implied by the concept.
        Do NOT include explanations; output **only valid Python code**.
        
        ### 出力形式:
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
            f.write(script)
        return script

    def parse_pyright_output_for_llm(pyright_json: dict) -> str:
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

    def has_no_pyright_errors(pyright_json: dict) -> bool:
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
            err_paser_output_llm=self.parse_pyright_output_for_llm(err)
            is_success = self.has_no_pyright_errors(err)
            if is_success:
                video_success = self.run_script(video_id,script)
                if video_success:
                    return 'Success'
                else:
                    inner_error = parse_manim_or_python_traceback(video_success)
                    inner_error = format_error_for_llm(inner_error)
                    script = self.fix_code_agent(video_id,content,inner_error)
                    loop += 1
                    continue
            else:
                script = self.fix_code_agent(video_id,content,err_paser_output_llm)
                loop=+1
                continue
        return "error"
        
        
        
    
    
    
        
        
        
    
    
    
if __name__ == "__main__":
    service = ManimAnimationService()
    prompt = service.explain_concept("微分積分学の基本定理について説明してください。可能な限り容易にしてください。")
    # generate script
    is_success = service.generate_videos(
        video_id='sankakukannsuu',
        content="""
        # 【高校1年生向け】三角関数の“動き”を単位円で体感しよう --- ## 0. 今日のゴール - 「sinθ, cosθの“ずらし”や符号について、なぜかを動きで実感しよう」 - 結論：\(\cos\theta = \sin(\theta+\frac{\pi}{2})\)、\(\sin\theta = -\cos(\theta+\frac{\pi}{2})\)が単位円で体感できることを目指す --- ## 1. 単位円で三角関数スタート！ まず半径1（原点中心）の円＝**単位円**を用意しよう。 - x軸の正の方向（右向き）を0°、そこから反時計回りに角度\(\theta\)をとる。 - このとき単位円上の点\(P\)の座標は \[ P(\cos\theta,\,\sin\theta) \] - 横：\(\cos\theta\) - 縦：\(\sin\theta\) **POINT:** どの\(\theta\)でも\(\cos^2\theta+\sin^2\theta=1\)。 ＝**三角関数の基本式**だね！ --- ## 2. “角度を90°（\(\frac{\pi}{2}\)）ずらす”ってどういうこと？ 次に、点\(P\)を角度90°、つまり\(\frac{\pi}{2}\)進めてみよう。 - 回転後の座標 \[ Q(\cos(\theta+\frac{\pi}{2}),\,\sin(\theta+\frac{\pi}{2})) \] - 実は、これは \[ Q(-\sin\theta,\,\cos\theta) \] となる！ **POINT:** “\(\cos\theta\)”の成分が”\(-\sin\theta\)”に、“\(\sin\theta\)”が“\(\cos\theta\)”に。それぞれ“入れ替わり＋横はマイナス”されてるね。 --- ## 3. 単位円でこの“変化”を見てみる！ - もと：\((\cos\theta,\,\sin\theta)\) の点P - 90°回す：\((-\sin\theta,\,\cos\theta)\) の点Q（矢印で動かして見よう） **解説:** - 右向き（x軸正方向）が0° - そこから\(\theta\)進むとP - さらに90°進むと、横成分と縦成分がどうなるかアニメや図で明示 --- ## 4. 数式の並び替えとゴールの公式 **成分から公式を導出：** - \(\cos(\theta+\frac{\pi}{2}) = -\sin\theta\) - \(\sin(\theta+\frac{\pi}{2}) = \cos\theta\) なので…… \[ \cos\theta = \sin(\theta+\frac{\pi}{2})\\ \sin\theta = -\cos(\theta+\frac{\pi}{2}) \] --- ## 5. 具体的な値でピッタリ体験しよう！ ### (1) \(\theta=0\) のとき - \(\cos 0 = 1\), \(\sin(\frac{\pi}{2}) = 1\) → 一致！ - \(\sin 0 = 0\), \(-\cos(\frac{\pi}{2}) = 0\) → 一致！ ### (2) \(\theta=\frac{\pi}{6}\)（30°） - \(\cos\frac{\pi}{6} = \frac{\sqrt{3}}{2}\), \(\sin(\frac{2\pi}{3}) = \frac{\sqrt{3}}{2}\) → 一致！ - \(\sin\frac{\pi}{6} = \frac{1}{2}\), \(-\cos(\frac{2\pi}{3}) = -(-\frac{1}{2}) = \frac{1}{2}\) → 一致！ ### (3) \(\theta=\frac{\pi}{4}\)（45°） - \(\cos\frac{\pi}{4} = \frac{\sqrt{2}}{2}\), \(\sin(\frac{3\pi}{4}) = \frac{\sqrt{2}}{2}\) → 一致！ - \(\sin\frac{\pi}{4} = \frac{\sqrt{2}}{2}\), \(-\cos(\frac{3\pi}{4}) = -(-\frac{\sqrt{2}}{2}) = \frac{\sqrt{2}}{2}\) → 一致！ **図やアニメで、角度と点の動きの関係を1ステップごとにしっかり見せる** --- ## 6. 180°回した場合（応用） - 180°（\(\pi\)）回すと \[ (\cos(\theta+\pi),\,\sin(\theta+\pi)) = (-\cos\theta,\,-\sin\theta) \] - 点は反対側、両方マイナスになる！ --- ## 7. まとめ - 単位円の“動き”を使えば、\(\cos\theta\)と\(\sin(\theta+\frac{\pi}{2})\)などの関係が**「入れ替わり＋符号」**として自然に分かる - 具体例で数値的にも納得！ - どの角度でもこの関係は成り立つので、丸暗記せず「動き」で理解しよう！
        """,
        enhance_prompt=""
    )
    print(is_success)