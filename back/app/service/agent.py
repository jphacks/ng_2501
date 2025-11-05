import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser

from app.tools.secure import is_code_safe

from app.service.base_agent import BaseManimAgent



class ManimRegacyAgentService(BaseManimAgent):
    def __init__(self):
        super().__init__(prompt_path="prompt/prompts.toml")
        
    def _load_llm(self, model_type: str):
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))
    
    
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
    
    
    # 抽象クラスの実装
    def generate_video(self, video_id:str, content:str, enhance_prompt:str, max_loop:int=3)->str:
        # スクリプト生成
        script = self.generate_script_with_prompt(
            content,
            enhance_prompt
        )
        loop = 0
        while loop < max_loop:
            video_success = self._execute_script(script, video_id)
            if video_success == "Success":
                return "Success"
            elif video_success == "FileNotFoundError":
                self.base_logger.error(f"File not found during video generation for video_id: {video_id}")
                return "FileNotFoundError"
            else:
                script = self.fix_code_agent(
                    video_id,
                    content,
                    video_success
                )
                continue
        return "error"
        
    