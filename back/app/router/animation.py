from dotenv import load_dotenv
from fastapi import FastAPI, responses
from pydantic import BaseModel
from pathlib import Path
from fastapi import APIRouter, responses, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.service.agent import ManimAnimationService

router = APIRouter()


load_dotenv()

workspace_path = Path("/workspaces/ai_agent/back/app/service/media/videos")

class input(BaseModel):
    input: str
    
class Output(BaseModel):
    output: str

class Prompt(BaseModel):
    user_prompt: str
    video_id: str
    instruction_type: int

class DetailPrompt(BaseModel):
    user_prompt: str
    instruction_type: int

class Script(BaseModel):
    script: str

# 知識の構造化説明をgetするためのルータ

@router.post("/api/prompt", response_model=Output)
def concept_enhance(concept_input: input):
    """
    ユーザーの入力テキストを受け取り、
    ManimAnimationServiceのexplain_concept()で知識構造を生成するエンドポイント。
    """
    service = ManimAnimationService()
    result = service.explain_concept(concept_input.input)
    return Output(output=result)

