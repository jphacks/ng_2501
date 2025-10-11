# main.py
from fastapi import FastAPI
from app.router import animation
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
app.include_router(animation.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)