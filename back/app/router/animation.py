from dotenv import load_dotenv
from fastapi import FastAPI, responses
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from fastapi import APIRouter, responses, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.service.agent import ManimAnimationService

router = APIRouter()


load_dotenv()

workspace_path = Path("/workspaces/ai_agent/back/media/videos")
script_path = Path("/workspace/ai_agent/tmp")

class input(BaseModel):
    input: str
    
class Output(BaseModel):
    output: str

class InitialPrompt(BaseModel):
    content: str
    video_id: str
    enhance_prompt : str
    

# 知識の構造化説明をgetするためのルータ


service = ManimAnimationService()
@router.post("/api/prompt", response_model=Output)
def concept_enhance(concept_input: input):
    """
    ユーザーの入力テキストを受け取り、
    ManimAnimationServiceのexplain_concept()で知識構造を生成するエンドポイント。
    """
    result = service.explain_concept(concept_input.input)
    return Output(output=result)
 
@router.post("/api/video_raw", response_class=Output)
async def prompt(prompt: InitialPrompt):
    err =service.generate_raw_video(
        prompt.video_id,
        prompt.content,
        prompt.enhance_prompt
    )
    return Output(output=err)

@router.post('api/animatio/{video_id}',response_class=FileResponse)
def get_animation(video_id:str):
    path = workspace_path / video_id / "480p15" / "GeneratedScene.mp4"
    
    if not path.is_file():
        return responses.JSONResponse(status_code=404, content={
            "message":"Video not found"
        })
    return FileResponse(path,media_type="video/mp4",filename="GeneratedScene.mp4")


    