from fastapi import FastAPI
import uvicorn

from src.api_server import app  # 直接复用 api_server.py 中的 app

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=3000)