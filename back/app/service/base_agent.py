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

import uuid
import json
from pydantic import BaseModel
from typing import Optional

from loguru import logger

from app.tools.secure import is_code_safe
from app.tools.manim_linter import ManimLinter
from app.tools.manim_lint import parse_manim_or_python_traceback, format_error_for_llm
from app.tools.diff_patcher import DiffPatcher


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
    message: Optional[str] = None
    video_path: Optional[str] = None
    prompt_path: Optional[str] = None
    manim_code_path: Optional[str] = None
    video_id: Optional[str] = None


class PlanResponse(BaseModel):
    plan: str
    generation_id: Optional[int] = None


class BaseManimAgent(ABC):
    def __init__(self, prompt_path: str = "prompt/prompts.toml"):
        # ログのセットアップ
        self.base_logger = self._setup_logger(logger_name=self.__class__.__name__)
        self.diff_patcher = DiffPatcher(self.base_logger)

        # プロンプトの読み込み
        self.prompts = self._load_prompt(path=prompt_path)
        # LLMの初期化
        self.pro_llm = self._load_llm("gemini-3-pro-preview")
        self.flash_llm = self._load_llm("gemini-3-flash-preview")
        self.lite_llm = self._load_llm("gemini-3-flash-preview")
        self.manim_linter = ManimLinter()

        # ローカル関数のpath関連
        self.workspace_path = Path(os.getenv("WORKSPACE_PATH"))
        self.manim_scripts_path = Path(os.getenv("MANIM_SCRIPTS_PATH"))
        self.video_output_path = Path(os.getenv("VIDEO_OUTPUT_PATH"))
        self.user_instruction_path = Path(os.getenv("USER_INSTRUCTION_PATH"))

    def _process_edit_response(self, *, original_script: str, llm_response: str) -> str:
        """
        Delegate to shared diff patcher utility.
        """
        return self.diff_patcher.process_edit_response(
            original_script=original_script, llm_response=llm_response
        )

    def _setup_logger(self, logger_name: str):
        """
        ログのセットアップ関数
        """
        # log/ ディレクトリが存在しない場合は作成
        if not os.path.exists("log"):
            os.makedirs("log")
        log_file = f"log/{logger_name}.log"
        logger.add(log_file, rotation="10 MB", retention="10 days", level="DEBUG")
        return logger.bind(name=logger_name)

    def _load_prompt(self, path: str):
        """
        プロンプトを指定されたパスから読み込む関数
        prompt.tomlファイルなどのプロンプトを制御する関数は service/prompt/ 以下にまとめること。
        """
        base_dir = (
            Path(__file__).resolve().parent
        )  # 現在のこのファイルのディレクトリを取得する
        prompts_path = base_dir / path
        prompts_path = str(prompts_path)
        with open(prompts_path, "rb") as f:
            prompt_data = tomllib.load(f)
        self.base_logger.info(f"Prompts loaded from {prompts_path}")
        return prompt_data

    def _load_llm(
        self, model_type: str, *, model_provider: str = "google"
    ) -> ChatGoogleGenerativeAI | ChatAnthropic | ChatOpenAI:
        """
        APIによって呼び出す場合のLLMはこの関数の中で定義する。
        例: Google Gemini, Anthropic Claude, OpenAI GPT, xAI grok など
        """

        if model_provider == "google":
            return ChatGoogleGenerativeAI(
                model=model_type, google_api_key=os.getenv("GEMINI_API_KEY")
            )
        elif model_provider == "anthropic":
            # Anthropic ClaudeのAPIキーが設定されている場合
            if os.getenv("ANTHROPIC_API_KEY"):
                return ChatAnthropic(
                    model=model_type, api_key=os.getenv("ANTHROPIC_API_KEY")
                )
        elif model_provider == "openai":
            return ChatOpenAI(
                model_name=model_type, api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            raise ValueError("Unsupported model provider")

    def _load_local_llm(self, model_type: str) -> ChatOllama:
        # ローカルLLMを作動させる場合の関数
        return ChatOllama(model=model_type)

    def _save_script(self, video_id: str, script: str) -> Path:
        """[Helper] 共通のスクリプト保存処理"""
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        tmp_path = Path(f"tmp/{video_id}.py")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(script)

        self.base_logger.info(f"Script saved to {tmp_path}")
        return tmp_path

    def _save_prompt(
        self, generation_id: str, content: str, enhance_prompt: str = ""
    ) -> str:
        """[Helper] 共通のプロンプト保存処理"""

        prompt_dir = self.user_instruction_path

        # ディレクトリが存在しない場合は作成する

        if not os.path.exists(prompt_dir):
            os.makedirs(prompt_dir)

        prompt_json_path = prompt_dir / f"{generation_id}.json"

        # このファイルが存在しない場合は新規作成する

        if not os.path.isfile(prompt_json_path):
            # jsonファイル作成

            with open(prompt_json_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "prompt": [
                            {
                                "trial": 1,
                                "content": content,
                                "enhance_prompt": enhance_prompt,
                            }
                        ]
                    },
                    f,
                    ensure_ascii=False,
                    indent=4,
                )

                self.base_logger.info(f"Prompt saved to {prompt_json_path}")

        else:
            self.base_logger.info(f"Prompt file already exists: {prompt_json_path}")

            # すでにjsonファイルが存在する場合は追加する

            # まずファイルを読み込む

            with open(prompt_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # データ構造を修正

            if not isinstance(data.get("prompt"), list):
                data["prompt"] = [data["prompt"]] if "prompt" in data else []

            # 新しいプロンプトを追加

            trial_number = len(data["prompt"]) + 1

            data["prompt"].append(
                {
                    "trial": trial_number,
                    "content": content,
                    "enhance_prompt": enhance_prompt,
                }
            )
            # ファイルに書き込む
            with open(prompt_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        return f"{generation_id}.json"

    def _get_script(self, video_id: str) -> str:
        """[Helper] manimスクリプトの取得"""
        script_path = self.manim_scripts_path / f"{video_id}.py"
        with open(script_path, "r", encoding="utf-8") as f:
            script = f.read()
        return script

    def _check_code_security(self, code: str) -> bool:
        """[Helper] manimコードの安全性チェック"""
        return is_code_safe(code)

    def _check_code_lint(self, code: str) -> dict:
        """[Helper] manimコードのリンターチェック"""
        return self.manim_linter.check_code(code)

    def _execute_script_low_res(self, script: str, video_id: str) -> str:
        """[Helper] 最低解像度での実行チェック
        副作用: video_idのファイルにスクリプトが保存される
        """
        tmp_path = self._save_script(video_id, script)

        try:
            # -sで最後のフレームのみを保存、-rで解像度を大幅に下げる
            subprocess.run(
                ["manim", "-s", "-r", "64,36", str(tmp_path), "GeneratedScene"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                encoding="utf-8",
            )
            self.base_logger.info(f"Low-res script executed successfully: {tmp_path}")
            return "Success"
        except FileNotFoundError:
            self.base_logger.error(f"File not found: {tmp_path}")
            return "FileNotFoundError"

        except subprocess.CalledProcessError as e:
            parsed_error  = e.stderr
            # parsed_error = parse_manim_or_python_traceback(e.stderr)
            # parsed_error = format_error_for_llm(parsed_error)
            self.base_logger.error(f"Low-res execution failed: {parsed_error}")
            return parsed_error
    
    def _execute_script(self,script:str,video_id:str) -> str:
        """[Helper] manimスクリプトの実行
        副作用: video_idのファイルにスクリプトが保存される

        manimスクリプトが正常に実行される。
        """
        tmp_path = self._save_script(video_id, script)

        try:
            subprocess.run(
                ["manim", "-ql", str(tmp_path), "GeneratedScene"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                encoding="utf-8",
            )
            self.base_logger.info(f"Script executed successfully: {tmp_path}")
            return "Success"
        except FileNotFoundError:
            self.base_logger.error(f"File not found: {tmp_path}")
            return "FileNotFoundError"

        except subprocess.CalledProcessError as e:
            parsed_error  = e.stderr
            # parsed_error  = parse_manim_or_python_traceback(e.stderr)
            # parsed_error =  format_error_for_llm(parsed_error)
            self.base_logger.error(f"Script execution failed: {parsed_error}")
            return parsed_error

    @abstractmethod
    def manim_planner(self, content: str, enhance_prompt: str = "") -> str:
        """
        manimコード生成のための計画立案

        サブクラスで必要ならばオーバーライドして使用する。
        標準実装では flash_llm を使用して計画立案を行う。

        このメソッドでは
        content: 動画生成のためのユーザーの入力
        enhance_prompt: 動画生成を補助するための追加プロンプト

        の二つを受け取り、manimコード生成のための計画を文字列として返す。

        return:str
            manimコード生成のための計画を示す文字列
        """

        pass

    @abstractmethod
    def generate_video(self,video_id:str,content:str,enhance_prompt:str,maxloop:int=3)->str:
        """
        サブクラスで実装されるべき抽象的なメソッド

        このコードの中には動画生成のために必要なロジックを実装する。
        このメソッドの中では、
        video_id: 動画の一意な識別子
        content: manimコード生成のための計画立案（planであることに注意する）
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

    @abstractmethod
    def edit_video(
        self, new_video_id: str, script: str, enhance_prompt: str, max_loop: int = 3
    ) -> str:
        """
        サブクラスで実装されるべき抽象的なメソッド

        このコードの中には動画編集のために必要なロジックを実装する。
        このメソッドの中では、
        script: 既存のmanimスクリプト
        enhance_prompt:動画編集をするための追加プロンプト

        を受け取る。

        return:
            生成の成功または失敗を示す文字列を返す。
            "Success": 成功
            "bad_request": セキュリティチェックに失敗
            "error": そのほかのエラー
            "failed": その他の失敗
        """
        pass

    def plan(self, generation_id, content: str, enhance_prompt: str = "") -> str:
        """
        manimコード生成のための計画立案の共通関数
        """
        try:
            prompt_path = self._save_prompt(generation_id, content, enhance_prompt)
            plan = self.manim_planner(content, enhance_prompt)
            prompt_path: Path = self._save_prompt(generation_id, plan, enhance_prompt)
            self.base_logger.info(f"Plan generated: {generation_id}")
            self.base_logger.debug(f"Plan details: {prompt_path}")

            return PlanResponse(plan=plan, generation_id=generation_id)

        except Exception as e:
            self.base_logger.error(f"Error in plan: {e}")
            return PlanResponse(plan="", generation_id=None)

    def main(
        self, generation_id, content: str, enhance_prompt: str, max_loop: int = 3
    ) -> SuccessResponse:
        """
        動画生成のメイン関数
        """
        # video_id(DBに保存するためのpathを一意にするためのID)
        video_id = str(uuid.uuid4())

        # save prompt
        prompt_path = self._save_prompt(generation_id, content, enhance_prompt)

        is_success = self.generate_video(video_id, content, enhance_prompt, max_loop)

        if is_success == "Success":
            return SuccessResponse(
                ok=True,
                video_id=video_id,
                message="done",
                video_path=str(Path(video_id) / "480p15" / "GeneratedScene.mp4"),
                prompt_path=str(prompt_path),
                manim_code_path=str(f"{video_id}.py"),
            )
        elif is_success == "bad_request":
            return SuccessResponse(
                ok=False,
                message="bad",
                prompt_path=str(prompt_path),
                manim_code_path=str(f"{video_id}.py"),
            )
        else:
            return SuccessResponse(
                ok=False,
                message="failed",
            )

    def edit(self, generation_id: int, prior_video_id: str, enhance_prompt: str, max_loop: int = 3):
        script = self._get_script(prior_video_id)

        new_video_id = str(uuid.uuid4())
        prompt_path = self._save_prompt(generation_id, "", enhance_prompt)
        is_success = self.edit_video(new_video_id, script, enhance_prompt, max_loop)

        if is_success == "Success":
            return SuccessResponse(
                ok=True,
                message="done",
                video_id=new_video_id,
                video_path=str(Path(new_video_id) / "480p15" / "GeneratedScene.mp4"),
                prompt_path=str(prompt_path),
                manim_code_path=str(f"{new_video_id}.py"),
            )
        elif is_success == "bad_request":
            return SuccessResponse(
                ok=False,
                message="bad",
                prompt_path=str(prompt_path),
                manim_code_path=str(f"{new_video_id}.py"),
            )
        else:
            return SuccessResponse(
                ok=False,
                message="failed",
            )
