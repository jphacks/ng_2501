

from pathlib import Path


from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException ,Depends
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel 
from typing import Optional


from app.service.graph_agent import ManimGraphAnimationService
from back.app.service.agent import ManimRegacyAgentService
from back.app.service.base_agent import SuccessResponse , PlanResponse
from back.app.model.model import VideoDatabase, get_video_db

load_dotenv()

router = APIRouter(tags=["animation"])




workspace_path = Path("/workspaces/ai_agent/back/media/videos") 

# ---------- Pydantic Models ----------
class ConceptInput(BaseModel):
    text: str
    additional_instructions: Optional[str] = ""

class Output(BaseModel):
    output: str

class InitialPrompt(BaseModel):
    generation_id:int
    content: str
    enhance_prompt: str = ""

class EditPrompt(BaseModel):
    db_id:str
    prior_inner_video_id: str
    enhance_prompt: str


# ---------- Service ----------
service = ManimGraphAnimationService()




@router.post("/api/plan_animation", response_model=PlanResponse, summary="動画生成の計画立案")
def plan_animation(
    concept_input: ConceptInput,
    db: VideoDatabase = Depends(get_video_db)
):
    """
    動画生成の計画立案を行う。
    ここで発行した生成IDは基本的にSession IDとしてフロントエンドで保持する
    """
    try:
        # DB に生成セッションを登録し、生成IDを取得
        generate_id = db.generate_prompt()
        print(f"Generated ID: {generate_id}")
        
        
        # 生成IDによって計画立案を実行と保存
        plan_response: PlanResponse = service.plan(
            generation_id=generate_id,
            content=concept_input.text,
            enhance_prompt=concept_input.additional_instructions
        )
        print(plan_response)
        return plan_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning error: {str(e)}")


@router.post("/api/dev/reset_database", summary="【開発用】データベースの完全リセット")
def dev_reset_database(
    db: VideoDatabase = Depends(get_video_db)
):
    """
    【危険な操作】データベースのすべてのテーブルを削除し、
    現在のモデル定義に基づいて再作成します。
    これにより、すべてのデータが失われます。
    開発環境でのスキーマ変更の適用にのみ使用してください。
    """
    try:
        db._drop_and_recreate_tables()
        return JSONResponse(status_code=200, content={"message": "Database has been successfully reset."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")


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
            generation_id=initial_prompt.generation_id,
            content=initial_prompt.content,
            enhance_prompt=initial_prompt.enhance_prompt,
            max_loop=3
        )
        
        video_id = db.generate_video(
            generate_id=initial_prompt.generation_id,
            video_id=response.video_id,
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
