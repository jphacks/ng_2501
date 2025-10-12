import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from langdetect import detect
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain_core.output_parsers import StrOutputParser

from app.tools.manim_lint import parse_manim_or_python_traceback, format_error_for_llm
from app.tools.secure import is_code_safe

load_dotenv('./.env.local')

class RegacyManimAnimationService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        prompts_path = base_dir / "regacy_prompt.toml"
        path = str(prompts_path)
        with open(path, 'rb') as f:
            self.prompts = tomllib.load(f)
        self.think_llm = self._load_llm("gemini-2.5-flash")
        self.pro_llm   = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm = self._load_llm("gemini-2.5-flash-lite")
    
    def _load_llm(self, model_type: str):
        if os.getenv('OPENAI_API_KEY'):
            return ChatOpenAI(model='gpt-4o-mini', temperature=0)
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))

    def generate_script(self, user_prompt: str) -> str:
        is_translation = False
        if is_translation == True:
            _, user_prompt = self._llm_en_translation(user_prompt)
        prompt1 = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["chain"]["prompt1"]
        )
        prompt2 = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["chain"]["prompt2"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first= prompt1 | self.think_llm,
            last = prompt2 | self.pro_llm | parser
        )
        
        output = chain.invoke({"user_prompt": user_prompt})
        return output.replace("```python", "").replace("```", "")
    
    def run_script(self, file_name: str, script: str) -> str:
        
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{file_name}.py")
        
        is_secure = is_code_safe(script)
        
        if is_secure:
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
        else:
            return "bad_request"
    
    def fix_script(self, script: str, error: str, file_name: str) -> str:
        
        
        
        error=parse_manim_or_python_traceback(error)
        error=format_error_for_llm(error)
        
        prompt1 = PromptTemplate(
            input_variables=["script", "error"],
            template=self.prompts["error"]["prompt1"]
        )
        prompt2 = PromptTemplate(
            input_variables=["instructions"],
            template=self.prompts["error"]["prompt2"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first= prompt1 | self.think_llm,
            last = prompt2 | self.pro_llm | parser
        )
        messages = {"script": script, "error": error}
        output = chain.invoke(messages)
        return output.replace("```python", "").replace("```", "")

    def generate_animation_with_error_handling(self, user_prompt: str, file_name: str,enhance_prompt:str) -> str:
        
        user_prompt = user_prompt + enhance_prompt
        script = self.generate_script(user_prompt)
        err = self.run_script(file_name, script)
        count = 0
        limit_count = 3
        while err != "Success" and count < limit_count:
            script = self.fix_script(script, err, file_name)
            err = self.run_script(file_name, script)
            count += 1
            if err == "bad_request":
                return "bad_request"
        return "failed"

    

    def run_script_file(self, file_path: Path) -> str:
        
        try:
            subprocess.run(
                ["manim", "-pql", str(file_path), "GeneratedScene"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, check=True
            )
            return "Success"
        except subprocess.CalledProcessError as e:
            return e.stderr
    
    def generate_detail_prompt(self,user_prompt:str)->str:
        # 入力された言語を判定する
        lang,user_prompt = self._llm_en_translation(user_prompt)
        print(lang,user_prompt)
        
        prompt = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["detailed_prompt"]["detailed_prompt"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first= prompt | self.flash_llm,
            last = parser
        )
        output = chain.invoke({"user_prompt":user_prompt})
        # もとに翻訳
        output = self._llm_reverse_translate(lang,output)
        
        return output
    
    def _en_ja_translate(self,user_prompt:str)->str:
        # englishから日本語への翻訳
        prompt = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["translate"]["en_to_ja"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first= prompt | self.lite_llm,
            last = parser
        )
        output = chain.invoke({"user_prompt":user_prompt})
        
        return output
    
    def _ja_en_translate(self,user_prompt:str)->str:
        # 日本語から英語への翻訳
        prompt = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["translate"]["ja_to_en"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(
            first= prompt | self.lite_llm,
            last = parser
        )
        output = chain.invoke({"user_prompt":user_prompt})
        
        return output
    
    def _llm_en_translation(self,user_prompt:str)->tuple[str,str]:
        """
        input: user_prompt
            user_prompt : str
                入力された文章
        output: lang,user_prompt : tuple[str,str]
            lang : str
                入力された言語
            user_prompt : str
                翻訳後の文章 日本語なら英語に、英語はそのまま返される
        """
        # 翻訳
        lang = detect(user_prompt)
        if lang == "ja":
            user_prompt = self._ja_en_translate(user_prompt)
            return lang,user_prompt
        else:
            return lang,user_prompt
    
    def _llm_reverse_translate(self,original_lang:str,prompt)->str:
        """
        input: prompt,lang
            original_lang : str
                    もともとのユーザの言語
            prompt : str
                入力された文章
        output: str
            もともとのユーザーの翻訳後の文章
        """
        
        now_lang = detect(prompt)
        
        if now_lang != original_lang:
            if original_lang == "ja":
                translate_error = self._en_ja_translate(prompt)
            else:
                translate_error = self._ja_en_translate(prompt)
        else:
            translate_error = prompt
        return translate_error
        
        
    
    # ここから下は軽量化のための関数
    
    # 可能ならこここそストリーミングを行いたい
    def generate_instruction(self, user_prompt: str) -> str:
        prompt = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["instruction"]["teacher_prompt"]
        )
        original_lang = detect(user_prompt)
        if original_lang == "ja":
            user_prompt = self._en_ja_translate(user_prompt)
        parser = StrOutputParser()
        chain = prompt | self.flash_llm | parser
        output = chain.invoke({"user_prompt": user_prompt})
        
        original_lang_output = self._llm_reverse_translate(original_lang,output)
        
        return output, original_lang_output
    
    
    
    

if __name__ == "__main__":
    describe = ManimAnimationService()
    print(describe.generate_detail_prompt("半径3の円を書いてください",1))
    