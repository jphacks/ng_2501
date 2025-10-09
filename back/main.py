# main.py
from fastapi import FastAPI
from app.router import sample_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Agent Backend",
    description="Modern FastAPI application with clean architecture",
    version="1.0.0",
)

# CORS（Vercelなどからのアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番ではドメインを限定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(sample_router.router)

@app.get("/")
async def root():
    return {"message": "✅ FastAPI is running successfully!"}
