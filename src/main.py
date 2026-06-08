# src/main.py
from fastapi import FastAPI
import uvicorn
import signal
import os

app = FastAPI(title="Personal Brain API")

# 结合 code.txt 中的 5 层架构，这里应导入对应的 Agent 路由
# from app.api.v1 import router as api_router
# app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # 生产模式下由 docker-compose 的 command 启动，此处保留本地调试能力
    uvicorn.run("main:app", host="0.0.0.0", port=8000)