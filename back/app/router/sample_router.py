from dotenv import load_dotenv
from fastapi import FastAPI, responses
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# 自作モジュール
from manim_generator import ManimAnimationService

load_dotenv('./.env.local')

class Input(BaseModel):
    input: str

class Output(BaseModel):
    output: str

class Prompt(BaseModel):
    user_prompt: str
    video_id: str
    instruction_type: int

class DetailPrompt(BaseModel):
    user_prompt: str
    instruction_type: int

class Script(BaseModel):
    script: str

app = FastAPI(title='LangChain Server', version='1.0')
origins = ["http://localhost:3000",]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

animation_service = ManimAnimationService()

@app.get('/api/get_video/{video_id}')
async def get_video(video_id: str):
    path = workspace_path / video_id / "480p15" / "GeneratedScene.mp4"
    if not path.is_file():
        return responses.JSONResponse(status_code=404, content={'message': 'Video not found'})
    return FileResponse(path, media_type="video/mp4", filename="GeneratedScene.mp4")

@app.post("/api/prompt", response_class=FileResponse)
async def prompt(prompt: Prompt):
    err = animation_service.generate_animation_with_error_handling(prompt.user_prompt, prompt.video_id)
    path = workspace_path / prompt.video_id / "480p15" / "GeneratedScene.mp4"
    if err != "Success":
        return responses.JSONResponse(status_code=500, content={'message': err})
    return FileResponse(path=path, media_type="video/mp4", filename="GeneratedScene.mp4")

@app.get("/api/script_to_animation/{script_file_id}", response_class=FileResponse)
async def get_script_to_animation(script_file_id: str):
    path = Path(f"tmp/{script_file_id}.py")
    if not path.is_file():
        return responses.JSONResponse(status_code=404, content={'message': 'Script not found'})
    err = animation_service.run_script_file(path, script_file_id)
    animation_path = workspace_path / script_file_id / "480p15" / "GeneratedScene.mp4"
    if err != "Success":
        return responses.JSONResponse(status_code=404, content={'message': err})
    return FileResponse(animation_path, media_type="video/mp4", filename="GeneratedScene.mp4")

@app.get("/api/get_script/{script_file_id}")
async def get_script(script_file_id: str):
    path = Path(f"tmp/{script_file_id}.py")
    if not path.is_file():
        return responses.JSONResponse(status_code=404, content={'message': 'Script not found'})
    with open(path) as f:
        content = f.read()
    os.remove(path)
    return responses.JSONResponse(content=content)

@app.post("/api/post_code/{script_file_id}")
async def post_code(script_file_id: str, code: Script):
    err = animation_service.run_script(script_file_id, code.script)
    if err != "Success":
        return responses.JSONResponse(status_code=500, content={'message': err})
    path = workspace_path / script_file_id / "480p15" / "GeneratedScene.mp4"
    return FileResponse(path, media_type="video/mp4", filename="GeneratedScene.mp4")

@app.post("/api/generate_detail_prompt")
async def generate_detail_prompt(prompt:DetailPrompt):
    output = animation_service.generate_detail_prompt(prompt.user_prompt, prompt.instruction_type)
    return responses.JSONResponse(content={'output': output})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=8000)
