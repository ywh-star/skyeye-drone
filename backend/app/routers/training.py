from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.training import runner

router = APIRouter(prefix="/training", tags=["training"])


class TrainStart(BaseModel):
    epochs: int = Field(default=3, ge=1, le=60)
    imgsz: int = Field(default=320, ge=256, le=640)
    batch: int = Field(default=8, ge=2, le=32)
    base_model: str = "coco-yolov8n"
    note: str = ""


@router.get("/jobs")
def jobs() -> dict[str, Any]:
    return {"items": runner.list()}


@router.post("/jobs")
def start(payload: TrainStart) -> dict[str, Any]:
    try:
        return runner.start(payload.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs/{job_id}")
def job(job_id: str) -> dict[str, Any]:
    try:
        return runner.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "训练任务不存在") from exc


@router.post("/jobs/{job_id}/stop")
def stop(job_id: str) -> dict[str, Any]:
    try:
        return runner.stop(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "训练任务不存在") from exc


@router.post("/jobs/{job_id}/resume")
def resume(job_id: str) -> dict[str, Any]:
    try:
        return runner.resume(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "训练任务不存在") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs/{job_id}/metrics")
def metrics(job_id: str) -> dict[str, Any]:
    return {"items": runner.metrics(job_id), "checkpoints": runner.checkpoints(job_id)}


@router.get("/jobs/{job_id}/log")
def log(job_id: str, lines: int = 200) -> dict[str, Any]:
    return {"lines": runner.log_tail(job_id, max_lines=min(1000, lines))}


@router.get("/jobs/{job_id}/stream")
def stream(job_id: str) -> StreamingResponse:
    return StreamingResponse(
        runner.stream(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
