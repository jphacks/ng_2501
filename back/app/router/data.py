from pathlib import Path

import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException ,Depends
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel
from typing import Optional
import json

# from app.service.graph_agent import ManimGraphAnimationService
# from back.app.service.agent import ManimRegacyAgentService
from back.app.service.fast_ai_agent import ManimFastAnimationService
from back.app.service.base_agent import SuccessResponse , PlanResponse
from back.app.model.model import VideoDatabase, get_video_db
from back.app.service.template_service import TemplateService

load_dotenv()

router = APIRouter(tags=["data"])

video_path = Path(os.getenv("VIDEO_OUTPUT_PATH"))
script_path = Path(os.getenv("MANIM_SCRIPTS_PATH"))
prompt_path = Path(os.getenv("USER_INSTRUCTION_PATH"))


# ---------- Pydantic Models ----------
# class ConceptInput(BaseModel):
#     text: str
#     additional_instructions: Optional[str] = ""

# class Output(BaseModel):
#     output: str

# class InitialPrompt(BaseModel):
#     generation_id:int
#     content: str # manim planで作成したプロンプト
#     enhance_prompt: str = ""

# class EditPrompt(BaseModel):
#     generation_id: int
#     prior_video_id: str
#     enhance_prompt: str

# class SearchPrompt(BaseModel):
#     content: str
    

# ---------- Service ----------
@router.get("/api/get_video_data/{video_path}", summary="動画内容取得API")
async def get_video_data(
    video_path: str,
    db: VideoDatabase = Depends(get_video_db)
):
    video_path_full = f"{video_path}/{video_path}"
    try:
        with open(video_path_full, 'r') as f:
            video_data = f.read()
        return video_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/get_prompt/{prompt_id}", summary="プロンプト内容取得API")
async def get_prompt(
    prompt_id: int,
    db: VideoDatabase = Depends(get_video_db)
):
    prompt = db.get_prompt(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    
    prompt_path_full = f"{prompt_path}/{prompt.prompt_path}"
    try:
        with open(prompt_path_full, 'r') as f:
            content = f.read()
            # ファイルの中身は JSON 文字列なので、Python の dict/list に変換
            data = json.loads(content)
        # dict/list をそのまま返せば FastAPI が JSON として返してくれる
        return JSONResponse(content=data)
        # または `return data` でもOK（自動で JSON にシリアライズされます）
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON file: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# TODO: 正常に実装
@router.get("/api/get_manim_code/{manim_code_id}", summary="manimコード内容取得API")
async def get_manim_code(
    manim_code_id: int,
    db: VideoDatabase = Depends(get_video_db)
):
    manim_code = db.get_manim_code(manim_code_id)
    if manim_code is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    
    manim_code_path_full = f"{script_path}/{manim_code.manim_code_path}"
    try:
        with open(manim_code_path_full, 'r') as f:
            content = f.read()
        return JSONResponse(content={"manim_code_id": manim_code_id, "content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
