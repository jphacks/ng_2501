from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException 
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel 

from app.service.agent import ManimAnimationService
from app.service.rag_agent import ManimAnimationOnRAGService

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

class SuccessResponse(BaseModel):
    ok: bool
    video_id: Optional[str] = None
    message: Optional[str] = None
    path: Optional[str] = None


# ---------- Service ----------
service = ManimAnimationService()


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


# ---------- Routes ----------
@router.post("/api/prompt", response_model=Output, summary="コンセプトの構造化説明を生成")
def concept_enhance(concept_input: ConceptInput):
    """
    ユーザー入力テキストを受け取り、知識構造の説明を生成して返す。
    """
    result = service.explain_concept(concept_input.text)
    return Output(output=result)


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


@router.post("/api/animation", response_model=SuccessResponse, summary="動画の生成")
async def generate_animation(initial_prompt: InitialPrompt):
    """
    LLMエージェント経由で Manim 動画を生成する。
    """
    try:
        is_success = service.generate_videos(
            video_id=initial_prompt.video_id,
            content=initial_prompt.content,           
            enhance_prompt=initial_prompt.enhance_prompt or "",
        )
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))

    if is_success == "Success":
        return SuccessResponse(
            ok=True,
            video_id=initial_prompt.video_id,
            message="done",
        )
    elif is_success=="bad_request":
        return SuccessResponse(
            ok=False,
            video_id=initial_prompt.video_id,
            message="bad"
        )
    else:
        return SuccessResponse(
            ok=False,
            video_id=initial_prompt.video_id,
            message="failed",
        )

@router.post("/api/animation_agent_rag_model")
async def generate_rag_animation(initial_prompt: InitialPrompt):
    """
    LLMエージェント経由で Manim 動画を生成する。
    """
    rag_service = ManimAnimationOnRAGService()
    try:
        is_success = rag_service.generate_videos(
            video_id=initial_prompt.video_id,
            content=initial_prompt.content,           
            enhance_prompt=initial_prompt.enhance_prompt or "",
        )
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))

    if is_success == "Success":
        return SuccessResponse(
            ok=True,
            video_id=initial_prompt.video_id,
            message="done",
        )
    elif is_success=="bad_request":
        return SuccessResponse(
            ok=False,
            video_id=initial_prompt.video_id,
            message="bad"
        )
    else:
        return SuccessResponse(
            ok=False,
            video_id=initial_prompt.video_id,
            message="failed",
        )
