from pydantic import BaseModel

class SampleModel(BaseModel):
    id: int
    name: str
