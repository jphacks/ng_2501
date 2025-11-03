from __future__ import annotations

from pathlib import Path


from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException 
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel 
from typing import Optional


from app.service.graph_agent import ManimGraphAnimationService
from back.app.service.agent import ManimRegacyAgentService
from back.app.service.base_agent import SuccessResponse


load_dotenv()

router = APIRouter(tags=["animation"])
workspace_path = Path("/workspaces/ai_agent/back/media/videos") 
script_path = Path("/workspace/ai_agent/tmp")
# ---------- Pydantic Models ----------
class ConceptInput(BaseModel):
    text: str

class Output(BaseModel):
    output: str

class InitialPrompt(BaseModel):
    content: str
    video_id: str
    enhance_prompt: str = ""



# ---------- Service ----------
service = ManimGraphAnimationService()


# ---------- Helpers ----------
def find_latest_video(video_id: str) -> Optional[Path]:
    """
    media/videos/{video_id}/ 以下から最も新しい mp4 を探す。
    典型パス: 480p15/GeneratedScene.mp4 または partial_movie_files 配下の完成ファイル。
    """
    path = workspace_path / video_id / "480p15" / "GeneratedScene.mp4"
    if not path.is_file(): 
        return JSONResponse(status_code=404, content={ "message":"Video not found" }) 
    return FileResponse(path,media_type="video/mp4",filename="GeneratedScene.mp4")



@router.get("/api/animation/{video_id}", summary="生成済み動画の取得")
def get_animation(video_id: str):
    """
    生成済みの動画ファイル（mp4）を返す。
    最終 mp4 が確定パスにない場合でも、サブディレクトリを走査して最新の mp4 を返す。
    """
    # まずは一般的な完成パスを優先的に見る
    common_path = workspace_path / video_id / "480p15" / "GeneratedScene.mp4"
    print(common_path)
    if common_path.is_file():
        return FileResponse(common_path, media_type="video/mp4", filename="GeneratedScene.mp4")

    return JSONResponse(status_code=404, content={"message": "Video not found"})



@router.post("/api/animation")
async def generate_regacy_animation(initial_prompt:InitialPrompt):
    try:
        response: SuccessResponse = service.main(
            video_id=initial_prompt.video_id,
            content=initial_prompt.content,
            enhance_prompt=initial_prompt.enhance_prompt,
            max_loop=3
        )
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/api/regacy_animation")
async def generate_regacy_animation(initial_prompt:InitialPrompt):
    regacy_service = ManimRegacyAgentService()
    try:
        response: SuccessResponse = regacy_service.main(
            video_id=initial_prompt.video_id,
            content=initial_prompt.content,
            enhance_prompt=initial_prompt.enhance_prompt,
            max_loop=3
        )
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))