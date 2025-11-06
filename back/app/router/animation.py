

from pathlib import Path


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
# from back.app.service.search_existing_code import SearchExistingCodeService

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
    content: str # manim planで作成したプロンプト
    enhance_prompt: str = ""

class EditPrompt(BaseModel):
    generation_id: int
    prior_video_id: str
    enhance_prompt: str

class SearchRequest(BaseModel):
    """
    既存コード検索のリクエストボディ。
    Attributes
    ----------
    query:
        類似検索に用いる文章。
    threshold:
        類似度の下限値 (0.0 - 1.0)。
    max_gets:
        返却する件数の上限。
    """

    query: str = (
        "単位円を使って、角度θに対応する点P(cosθ, sinθ)が円周上を動く様子を左側に表示してください。"
        "右側にはθを0°から360°まで30°刻みで変化させたときのsinθとcosθの値を表にして表示し、"
        "現在のθの行をハイライトしてください。また、sinθとcosθの符号がどの象限で変わるのか"
        "（第1象限は+,+、第2象限は-,+、第3象限は-,-、第4象限は+,-）を色分けして示してください。"
    )
    threshold: float = 0.8
    max_gets: int = 3

class AddTemplateRequest(BaseModel):
    """
    テンプレートリストに新しいコードを追加するリクエスト。

    Attributes
    ----------
    theme:
        追加するテンプレートの説明・テーマ概要。
    code:
        登録する Manim コード本体。
    """

    theme: str
    code: str


# ---------- Service ----------
# service = ManimGraphAnimationService()
service = ManimFastAnimationService()
# search_service = SearchExistingCodeService()



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


# @router.post("/api/animation/search")
# async def search_existing_animation(request: SearchRequest):
#     """
#     既存のテンプレートから類似するテーマを検索して返す。
#     類似度が threshold 以上のテーマ概要を最大 max_gets 件返却する。
#     """
#     try:
#         results = search_service.search(
#             contents=request.query,
#             thres=request.threshold,
#             max_get=request.max_gets,
#         )
#         themes = [
#             {
#                 "similar": round(score, 4),
#                 "theme": theme,
#             }
#             for theme, score in results
#         ]
#         return {"results": themes}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    

# @router.delete("/api/animation/search")
# async def delete_latest_template():
#     """
#     テンプレートリストから最新のエントリを削除する。
#     """
#     try:
#         entry = search_service.delete_latest()
#         return {
#             "template_id": entry.template_id,
#             "theme": entry.theme,
#         }
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/api/animation/search/add")
# async def add_animation_template(request: AddTemplateRequest):
#     """
#     テンプレートリストに新しいテーマとコードを追加し、埋め込みを更新する。
#     """
#     try:
#         entry = search_service.add(
#             contents=request.theme,
#             code=request.code,
#         )
#         return {
#             "template_id": entry.template_id,
#             "theme": entry.theme,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
