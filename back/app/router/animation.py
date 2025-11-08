from pathlib import Path

import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException ,Depends
from fastapi.responses import FileResponse, JSONResponse 
from pydantic import BaseModel
from typing import Optional

# from app.service.graph_agent import ManimGraphAnimationService
# from back.app.service.agent import ManimRegacyAgentService
from back.app.service.fast_ai_agent import ManimFastAnimationService
from back.app.service.base_agent import SuccessResponse , PlanResponse
from back.app.model.model import VideoDatabase, get_video_db
from back.app.service.template_service import TemplateService

load_dotenv()

router = APIRouter(tags=["animation"])


script_path = Path(os.getenv("MANIM_SCRIPTS_PATH"))
video_path = Path(os.getenv("VIDEO_OUTPUT_PATH")) 


# ---------- Pydantic Models ----------
class ConceptInput(BaseModel):
    text: str
    additional_instructions: Optional[str] = ""

class Output(BaseModel):
    output: str

class InitialPrompt(BaseModel):
    generation_id:int
    content: str # manim planで作成したプロンプト
    enhance_prompt: str = ""

class EditPrompt(BaseModel):
    generation_id: int
    prior_video_id: str
    enhance_prompt: str

class SearchPrompt(BaseModel):
    content: str
    

# ---------- Service ----------
# service = ManimGraphAnimationService()
service = ManimFastAnimationService()
template_service = TemplateService()


@router.post("/api/plan_animation", response_model=PlanResponse, summary="動画生成の計画立案")
async def plan_animation(
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
async def dev_reset_database(
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
async def get_animation(
    video_id: str,
    ):
    """
    生成済みの動画ファイル（mp4）を返す。
    最終 mp4 が確定パスにない場合でも、サブディレクトリを走査して最新の mp4 を返す。
    """
    # まずは一般的な完成パスを優先的に見る
    common_path = video_path / video_id / "480p15" / "GeneratedScene.mp4"
    print(common_path)
    if common_path.is_file():
        return FileResponse(common_path, media_type="video/mp4", filename="GeneratedScene.mp4")

    return JSONResponse(status_code=404, content={"message": "Video not found"})


@router.get("/api/animation/get_info/{video_id}", summary="生成済み動画のメタ情報取得")
async def get_animation_info(
        video_id: str,
        db: VideoDatabase = Depends(get_video_db)
    ):
    """
    生成済み動画の全情報を取得する。
    """
    video_info = db.get_video(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="Video not found")
    return video_info
@router.post("/api/register_rag/{video_id}", summary="RAG用動画登録API")
async def register_rag_video(
    video_id: str,
    db: VideoDatabase = Depends(get_video_db)
    ):
    """
    テンプレート動画を探すRAG用に動画を登録する
    1. manim_codeの内容をgemini2.5-flash-liteで要約する
    2. 要約した内容を埋め込みベクトル化する
    3. 埋め込みベクトル化した内容を、video_idと要約内容とともにRAGに登録する
    """
    try:
        # script_file = script_path / video_id / f"{video_id}.py"
        script_file = script_path / f"{video_id}.py"

        if not script_file.is_file():
            raise HTTPException(status_code=404, detail=f"Script for video_id {video_id} not found.")

        manim_code = script_file.read_text(encoding="utf-8").strip()
        if not manim_code:
            raise HTTPException(status_code=400, detail="manim_code is empty. Cannot register to RAG.")

        is_success = template_service.add(video_id=video_id, manim_code=manim_code)

        if is_success:
            return JSONResponse(
                status_code=200,
                content={
                    "ok": True,
                    "message": "RAG video registration successful.",
                },
            )
        else:
            raise HTTPException(status_code=500, detail="RAG video registration failed.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG video registration failed: {str(e)}")


@router.post("/api/search_animation", summary="RAG用動画検索API")
async def search_animation(
    search_prompt: SearchPrompt
):
    """
    content(ユーザーが入力した検索内容)と類似度が高いvideo_idと説明文をリスト形式で返す
    例:
    results = [
        {"video_id": "video1", "content": "content1"},
        {"video_id": "video2", "content": "content2"},
    ]
    """
    search_content = search_prompt.content.strip()
    if not search_content:
        raise HTTPException(status_code=400, detail="content must not be empty.")

    try:
        results = template_service.search(
            query=search_content,
            max_gets=10,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return JSONResponse(
        status_code=200,
        content={"results": results},
    )


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

        # 成功した場合のみDBに保存
        if response.ok and response.video_id:
            db.generate_video(
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
    

@router.post("/api/animation/edit", response_model=SuccessResponse, summary="動画編集API")
async def edit_video(
    edit_prompt: EditPrompt,
    db: VideoDatabase = Depends(get_video_db)
):
    try:
        response: SuccessResponse = service.edit(
            generation_id=edit_prompt.generation_id,
            prior_video_id=edit_prompt.prior_video_id,
            enhance_prompt=edit_prompt.enhance_prompt,
            max_loop=3,
        )
        if response.ok and response.video_id and response.video_path:
            db.edit_video(
                prior_video_id=edit_prompt.prior_video_id,
                new_video_path=response.video_path,
                new_video_id=response.video_id,
            )
        return response
    except Exception as e:
        # サービス内例外は 500 で返却
        raise HTTPException(status_code=500, detail=str(e))
