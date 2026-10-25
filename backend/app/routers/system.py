from __future__ import annotations

import platform
import sys
import time
from typing import Any

from fastapi import APIRouter

from ..db import detection_overview, list_tasks
from ..services.detector import detector
from ..services import visdrone

router = APIRouter(prefix="/system", tags=["system"])
START_TS = time.time()


def _pkg_version(name: str) -> str:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:  # noqa: BLE001
        return "未安装"


@router.get("/info")
def info() -> dict[str, Any]:
    models = detector.list_models()
    return {
        "app": "SkyEye 天穹 · 无人机航拍智能检测平台",
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "torch": _pkg_version("torch"),
        "ultralytics": _pkg_version("ultralytics"),
        "device": "CPU",
        "uptime_sec": int(time.time() - START_TS),
        "models": models,
        "dataset": {
            "name": "VisDrone2019-DET",
            "ready": len(visdrone.list_images()) > 0,
            "images": len(visdrone.list_images()),
        },
        "frontend": {"vue": "3.5", "typescript": "5.x", "three": "r172"},
    }


@router.get("/overview")
def overview() -> dict[str, Any]:
    stats = detection_overview()
    tasks = list_tasks()
    dataset = visdrone.summary()
    return {
        **stats,
        "active_tasks": sum(1 for t in tasks if t["status"] == "running"),
        "total_tasks": len(tasks),
        "dataset": {
            "name": dataset["name"],
            "images": dataset["images"],
            "objects": dataset["objects"],
            "classes": dataset["classes"],
        },
        "tasks": tasks[:5],
    }
