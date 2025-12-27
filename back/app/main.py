from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router import animation, data

app = FastAPI(
    title="AI Agent Backend",
    description="Modern FastAPI application with clean architecture",
    version="1.0.0",
)

# CORS（Vercelなどからのアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # nginxによって制御するようにする
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def root():
    return {"message": "FastAPI server is running 🚀"}
# ルーター登録
app.include_router(animation.router)
app.include_router(data.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
