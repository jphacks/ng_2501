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
        with open("./prompts.toml", 'rb') as f:
            self.prompts = tomllib.load(f)
        self.pro_llm   = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm  = self._load_llm("gemini-2.5-flash")
    
    def _load_llm(self, model_type: str):
        return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))

    # ====== Script Generation ======
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
            first=prompt1 | self.flash_llm,
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
    
    # ====== Auto Fix Script ======
    def fix_script(self, script: str, error: str, file_name: str) -> str:
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
            first=prompt1 | self.think_llm,
            last=prompt2 | self.think_llm | parser
        )
        messages = {"script": script, "error": error}
        output = chain.invoke(messages)
        return output.replace("```python", "").replace("```", "")

    def generate_animation_with_error_handling(self, user_prompt: str, file_name: str) -> str:
        script = self.generate_script(user_prompt)
        err = self.run_script(file_name, script)
        count = 0
        limit_count = 1
        while err != "Success" and count < limit_count:
            script = self.fix_script(script, err, file_name)
            err = self.run_script(file_name, script)
            count += 1
        return err

    # ====== Run Existing Script ======
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
    
    # ====== Detailed Prompt Generation ======
    def generate_detail_prompt(self, user_prompt: str, instruction_type: int) -> str:
        prompt = PromptTemplate(
            input_variables=["instructions", "user_prompt"],
            template=self.prompts["detailed_prompt"]["detailed_prompt"]
        )
        parser = StrOutputParser()
        chain = RunnableSequence(first=prompt | self.flash_llm, last=parser)
        instructions = self.instruction_type_to_str(instruction_type)
        output = chain.invoke({"instructions": instructions, "user_prompt": user_prompt})
        return output
    
    # ====== Instruction Mapping ======
    def instruction_type_to_str(self, instruction_type: int) -> str:
        if instruction_type == 0:
            return self.prompts["detailed_prompt"]["animation_instructions"]
        elif instruction_type == 1:
            return self.prompts["detailed_prompt"]["graph_instructions"]
        elif instruction_type == 2:
            return self.prompts["detailed_prompt"]["formula_transformation_instructions"]
        elif instruction_type == 3:
            return self.prompts["detailed_prompt"]["shape_instructions"]
        else:
            raise ValueError("instruction_typeが不正です")
        
    # ====== Simplified Instruction Generator ======
    def generate_instruction(self, user_prompt: str) -> str:
        prompt = PromptTemplate(
            input_variables=["user_prompt"],
            template=self.prompts["instruction"]["teacher_prompt"]
        )
        parser = StrOutputParser()
        chain = prompt | self.flash_llm | parser
        output = chain.invoke({"user_prompt": user_prompt})
        return output


if __name__ == "__main__":
    describe = ManimAnimationService()
    print(describe.generate_detail_prompt("半径3の円を書いてください", 1))
