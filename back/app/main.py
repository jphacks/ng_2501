from fastapi import FastAPI
from app.router import animation

app = FastAPI(
    title="AI Agent Backend",
    description="Modern FastAPI application with clean architecture",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"message": "FastAPI server is running 🚀"}
# ルーター登録
app.include_router(animation.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)