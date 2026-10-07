"""WearWise FastAPI 入口。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analysis, avatars, garments, outfits, tasks, weather
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.models.db import init_db

settings = get_settings()
init_db()

app = FastAPI(title=settings.app_name)
register_error_handlers(app)

# 允许本地前端跨域访问（开发期）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000", "http://localhost:3000",
        "http://127.0.0.1:3001", "http://localhost:3001",
        "http://127.0.0.1:3002", "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(garments.router, prefix=settings.api_prefix)
app.include_router(outfits.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(avatars.router, prefix=settings.api_prefix)
app.include_router(analysis.router, prefix=settings.api_prefix)
app.include_router(weather.router, prefix=settings.api_prefix)

# 静态资源：上传衣物照 / 生成图
app.mount("/static/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")
app.mount("/static/generated", StaticFiles(directory=settings.generated_dir), name="generated")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
