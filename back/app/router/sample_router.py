from fastapi import APIRouter

router = APIRouter(prefix="/sample", tags=["Sample"])

@router.get("/")
async def get_sample():
    return {"message": "This is a sample route"}
