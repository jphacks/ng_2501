

from pathlib import Path


from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException ,Depends
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel 
from typing import Optional


from app.service.graph_agent import ManimGraphAnimationService
from back.app.service.agent import ManimRegacyAgentService
from back.app.service.base_agent import SuccessResponse
from back.app.tools.video_data.video_db import VideoDatabase, get_video_db

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

class EditPrompt(BaseModel):
    db_id:str
    prior_inner_video_id: str
    enhance_prompt: str


# ---------- Service ----------
service = ManimGraphAnimationService()



@router.post("/api/init_session", summary="動画生成セッションの初期化")
def initialize_animation_session(
    db: VideoDatabase = Depends(get_video_db)
):
    """
    フロントエンドで「新規作成」を押した時などに呼び出す。
    「生成ID (generate_id)」と「動画ID (video_id)」を採番し、
    クライアント（フロントエンド）に返す。
    """
    try:
        # フロー1: 生成セッションID (generate_id)
        generate_id = db.generate_prompt()
        
        # フロー2: このセッションで「最初に」生成する動画のID (video_id)
        video_id = db.generate_video_seq()
        
        return {
            "generate_id": generate_id,
            "video_id": video_id,
            "message": "Session initialized. Use this video_id for the first generation."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB initialization error: {str(e)}")





@router.get("/api/animation/{video_id}", summary="生成済み動画の取得")
def get_animation(
    video_id: str,
    ):
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
async def generate_regacy_animation(
    initial_prompt:InitialPrompt,
    db: VideoDatabase = Depends(get_video_db)
    ):
    try:
        response: SuccessResponse = service.main(
            content=initial_prompt.content,
            enhance_prompt=initial_prompt.enhance_prompt,
            max_loop=3
        )
        
        db.generate_video(
            video_id=initial_prompt.video_id,
            video_path=response.video_path,
            prompt_path=response.prompt_path,
            manim_code_path=response.manim_code_path
        )
        
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/api/regacy_animation")
async def generate_regacy_animation(
    initial_prompt:InitialPrompt,
    db: VideoDatabase = Depends(get_video_db)
    ):
    regacy_service = ManimRegacyAgentService()
    try:
        response: SuccessResponse = regacy_service.main(
            content=initial_prompt.content,
            enhance_prompt=initial_prompt.enhance_prompt,
            max_loop=3
        )
        
        db.generate_video(
            video_id=initial_prompt.video_id,
            video_path=response.video_path,
            prompt_path=response.prompt_path,
            manim_code_path=response.manim_code_path
        )
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/api/concept_to_animation", response_model=Output, summary="作った動画をEdit出来る")
async def edit_animation(
    edit_prompt: EditPrompt,
    db: VideoDatabase = Depends(get_video_db)
):
    try:
        response: SuccessResponse = service.edit(
            inner_prior_video_id=edit_prompt.prior_inner_video_id,
            enhance_prompt=edit_prompt.enhance_prompt,
            max_loop=3
        )
        db.edit_video(
            video_id=edit_prompt.db_id,
            video_path=response.video_path,
        )
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))
