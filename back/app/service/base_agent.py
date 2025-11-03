
import os

import subprocess
from pathlib import Path
from dotenv import load_dotenv
import tomllib
from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama



from pydantic import BaseModel 
from typing import Optional

from loguru import logger

from app.tools.secure import is_code_safe
from app.tools.manim_lint import parse_manim_or_python_traceback,format_error_for_llm


load_dotenv()


"""
BaseManimAgentクラス
-----------------------
Manimアニメーションエージェントの基底クラス。
LLMの初期化と共通のユーティリティ関数を提供する関数として定義する。
- LLMの初期化: Google Gemini, Anthropic Claude, OpenAI GPT, xAI grok など複数のモデルプロバイダーに対応。
- 共通ユーティリティ関数: manimの安全性チェック関数やコードフォーマッター、リンター関数など

このクラスはほかのエージェントクラスに継承されて使用される。
特殊メソッド



"""
class SuccessResponse(BaseModel):
    ok: bool
    video_id: Optional[str] = None
    message: Optional[str] = None




class BaseManimAgent(ABC):
    def __init__(self,prompt_path: str = "prompt/prompts.toml"):
        # ログのセットアップ
        self.base_logger = self._setup_logger(logger_name=self.__class__.__name__)
        
        # プロンプトの読み込み
        self.prompts = self._load_prompt(path=prompt_path)
        # LLMの初期化
        self.pro_llm   = self._load_llm("gemini-2.5-pro")
        self.flash_llm = self._load_llm("gemini-2.5-flash")
        self.lite_llm  = self._load_llm("gemini-2.5-flash-lite")
        
        
    def _setup_logger(self,logger_name:str):
        """
        ログのセットアップ関数
        """
        # log/ ディレクトリが存在しない場合は作成
        if not os.path.exists("log"):
            os.makedirs("log")
        log_file = f"log/{logger_name}.log"
        logger.add(log_file, rotation="10 MB", retention="10 days", level="DEBUG")
        self.base_logger.info(f"Logger initialized. Log file: {log_file}")
        return logger.bind(name=logger_name)



    def _load_prompt(self,path:str):
        """
        プロンプトを指定されたパスから読み込む関数
        prompt.tomlファイルなどのプロンプトを制御する関数は service/prompt/ 以下にまとめること。
        """
        base_dir = Path(__file__).resolve().parent # 現在のこのファイルのディレクトリを取得する
        prompts_path = base_dir / path
        prompts_path = str(prompts_path)
        with open(prompts_path, 'rb') as f:
            prompt_data = tomllib.load(f)
        self.base_logger.info(f"Prompts loaded from {prompts_path}")
        return prompt_data
    
    
    def _load_llm(self, model_type: str,*,model_provider: str = "google") -> ChatGoogleGenerativeAI | ChatAnthropic  | ChatOpenAI :
        """
        APIによって呼び出す場合のLLMはこの関数の中で定義する。
        例: Google Gemini, Anthropic Claude, OpenAI GPT, xAI grok など
        """
        
        if model_provider == "google":
            return ChatGoogleGenerativeAI(model=model_type, google_api_key=os.getenv('GEMINI_API_KEY'))
        elif model_provider == "anthropic":
            # Anthropic ClaudeのAPIキーが設定されている場合
            if os.getenv('ANTHROPIC_API_KEY'):
                return ChatAnthropic(model=model_type, api_key=os.getenv('ANTHROPIC_API_KEY'))
        elif model_provider == "openai":
            return ChatOpenAI(model_name=model_type, api_key=os.getenv('OPENAI_API_KEY'))
        else:
            raise ValueError("Unsupported model provider")
        
   
    def _load_local_llm(self,model_type: str) -> ChatOllama:
        # ローカルLLMを作動させる場合の関数
        return ChatOllama(model=model_type)
    
    
    
    def _save_script(self, video_id: str, script: str) -> Path:
        """[Helper] 共通のスクリプト保存処理"""
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{video_id}.py")
        with open(tmp_path, "w", encoding='utf-8') as f:
            f.write(script)

        self.base_logger.info(f"Script saved to {tmp_path}")
        return tmp_path
    
    
    def _check_code_security(self,code:str) -> bool:
        """[Helper] manimコードの安全性チェック"""
        return is_code_safe(code)
    
    
    def _execute_script(self,script:str,video_id:str) -> str:
        """[Helper] manimスクリプトの実行
        副作用: video_idのファイルにスクリプトが保存される
        
        manimスクリプトが正常に実行される。
        """
        tmp_path = self._save_script(video_id, script)
        
        try:
            subprocess.run(
                ["manim", "-pql", str(tmp_path), "GeneratedScene"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, check=True, encoding='utf-8'
            )
            self.base_logger.info(f"Script executed successfully: {tmp_path}")
            return "Success"
        except FileNotFoundError:
            self.base_logger.error(f"File not found: {tmp_path}")
            return "FileNotFoundError"
        
        except subprocess.CalledProcessError as e:
            parsed_error  = parse_manim_or_python_traceback(e.stderr)
            parsed_error =  format_error_for_llm(parsed_error)
            self.base_logger.error(f"Script execution failed: {parsed_error}")
            return parsed_error
        
    @abstractmethod
    def generate_video(self,video_id:str,content:str,enhance_prompt:str,max_loop:int=3)->str:
        """
        サブクラスで実装されるべき抽象的なメソッド
        
        このコードの中には動画生成のために必要なロジックを実装する。
        このメソッドの中では、
        video_id: 動画の一意な識別子
        content: 動画生成のための教材
        enhance_prompt:動画作成をするための追加プロンプト
        
        を受け取る。
        
        return:
            生成の成功または失敗を示す文字列を返す。
            "Success": 成功
            "bad_request": セキュリティチェックに失敗
            "error": そのほかのエラー
            "failed": その他の失敗
        """
        pass

    def main(self,video_id:str,content:str,enhance_prompt:str,max_loop:int=3)-> SuccessResponse:
        """
        動画生成のメイン関数
        """
        is_success = self.generate_video(video_id,content,enhance_prompt,max_loop)

        if is_success == "Success":
            return SuccessResponse(
            ok=True,
            video_id=video_id,
            message="done",
        )
        elif is_success=="bad_request":
            return SuccessResponse(
                ok=False,
                video_id=video_id,
                message="bad"
            )
        else:
            return SuccessResponse(
                ok=False,
                video_id=video_id,
                message="failed",
            )
        