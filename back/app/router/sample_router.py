from fastapi import APIRouter
from app.service.sample_service import sample_logic
import pydantic

class AddRequest(pydantic.BaseModel):
    x: int
    y: int

router = APIRouter( tags=["Sample"])

@router.get("/")
async def get_sample():
    return {"message": "This is a sample route"}


@router.post("/add")
async def add_numbers(request: AddRequest):
    result: int = sample_logic(request.x, request.y)
    return {"result": result}

