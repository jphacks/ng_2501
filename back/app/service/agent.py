import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain_core.output_parsers import StrOutputParser

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
    
    
    def generate_script(self, user_prompt: str) -> str:
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
        output = chain.invoke({"user_prompt": user_prompt})
        return output.replace("```python", "").replace("```", "")
    
     # ====== Run Script ======
    def run_script(self, file_name: str, script: str) -> str:
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{file_name}.py")
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
    
    def generate_raw_video(self,video_id,content,enhance_prompt):
        # スクリプト生成
        script = self.generate_script_with_prompt(
            content,
            enhance_prompt
        )
        is_success = self.run_script(
            video_id,
            script=script
        )
        return is_success
    
    
if __name__ == "__main__":
    service = ManimAnimationService()
    prompt = service.explain_concept("微分積分学の基本定理について説明してください。可能な限り容易にしてください。")
    # generate script
    print(prompt)
    script = service.generate_script_with_prompt(
        prompt,
        "可能な限り短いプロンプトにしてください。"
    )
    print(script)
    is_success = service.run_script(
        "next",
        script=script
    )
    print(is_success)