from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import IMAGES_DIR, OUTPUT_DIR, UPLOAD_DIR
from .db import init_db, seed_tasks
from .routers import detect, system, tasks, training

app = FastAPI(
    title="SkyEye · 无人机航拍智能检测平台",
    description="YOLOv8 + FastAPI 后端，为 Vue 3 课程实验提供检测、数据集与训练能力",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(detect.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(training.router, prefix="/api")

for mount, directory in (
    ("/media/visdrone", IMAGES_DIR),
    ("/media/uploads", UPLOAD_DIR),
    ("/media/outputs", OUTPUT_DIR),
):
    directory.mkdir(parents=True, exist_ok=True)
    app.mount(mount, StaticFiles(directory=directory), name=mount.strip("/").replace("/", "-"))

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_tasks()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "skyeye", "pid": str(os.getpid())}


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str) -> FileResponse:
    """生产模式：静态资源直出，其余路径回退到 index.html 以支持 history 路由。"""
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        raise HTTPException(404, "前端尚未构建，请运行 npm run build")
    target = (FRONTEND_DIST / full_path).resolve()
    if full_path and target.is_file() and FRONTEND_DIST in target.parents:
        return FileResponse(target)
    return FileResponse(index)
