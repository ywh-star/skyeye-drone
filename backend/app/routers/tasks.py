from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import create_task, delete_task, list_tasks, update_task, update_task_status

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    area: str = Field(min_length=2, max_length=60)
    drone: str = "Mavic 3E"
    altitude: int = Field(default=150, ge=30, le=500)
    cover_km2: float = Field(default=2.0, ge=0.1, le=50)
    assignee: str = ""
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class TaskStatus(BaseModel):
    status: str
    reviewer: str = ""
    review_note: str = ""


class TaskUpdate(BaseModel):
    name: str | None = None
    area: str | None = None
    drone: str | None = None
    altitude: int | None = None
    cover_km2: float | None = None
    assignee: str | None = None
    priority: str | None = None
    detections: int | None = None
    duration_min: int | None = None


@router.get("")
def get_tasks(status: str | None = Query(default=None)) -> dict[str, Any]:
    return {"items": list_tasks(status)}


@router.post("")
def post_task(payload: TaskCreate) -> dict[str, Any]:
    return create_task(payload.model_dump())


@router.patch("/{task_id}")
def patch_task(task_id: str, payload: TaskStatus) -> dict[str, Any]:
    if payload.status not in {"running", "review", "queued", "done"}:
        raise HTTPException(400, "非法状态")
    task = update_task_status(task_id, payload.status, payload.reviewer, payload.review_note)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.put("/{task_id}")
def put_task(task_id: str, payload: TaskUpdate) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    task = update_task(task_id, data)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.delete("/{task_id}")
def remove_task(task_id: str) -> dict[str, Any]:
    if not delete_task(task_id):
        raise HTTPException(404, "任务不存在")
    return {"deleted": True, "id": task_id}
