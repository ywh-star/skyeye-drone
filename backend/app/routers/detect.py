from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import IMAGES_DIR, UPLOAD_DIR
from ..db import insert_detection, list_detections, now_iso
from ..services import visdrone
from ..services.detector import detector

router = APIRouter(tags=["detect"])


def _parse_labels(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


@router.post("/detect")
async def detect(
    file: UploadFile | None = File(None),
    sample: str | None = Form(None),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    imgsz: int = Form(960),
    model_id: str = Form("coco-yolov8n"),
    labels: str | None = Form(None),
) -> dict[str, Any]:
    if sample:
        target = next((p for p in visdrone.list_images() if p.stem == sample), None)
        if not target:
            raise HTTPException(404, "示例图片不存在")
        name = target.name
        source = "VisDrone"
    elif file:
        suffix = Path(file.filename or "upload.jpg").suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            raise HTTPException(400, "仅支持 jpg/png/webp/bmp 图片")
        name = f"{uuid.uuid4().hex[:10]}{suffix}"
        target = UPLOAD_DIR / name
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(400, "图片不能超过 25MB")
        target.write_bytes(content)
        source = "用户上传"
    else:
        raise HTTPException(400, "请上传图片或指定示例")

    try:
        result = detector.detect(
            target, conf=max(0.01, min(0.95, conf)), iou=max(0.05, min(0.95, iou)),
            imgsz=max(320, min(1600, imgsz)), model_id=model_id,
            allowed_labels=_parse_labels(labels),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"推理失败: {exc}") from exc

    record = {
        "id": result["id"],
        "name": name,
        "model": result["model_name"],
        "total": result["total"],
        "avg_conf": result["avg_conf"],
        "latency_ms": result["inference_ms"],
        "created_at": now_iso(),
        "image_url": result["image_url"],
        "output_url": result["output_url"],
        "payload": {
            "counts": result["counts"],
            "detections": result["detections"],
            "source": source,
            "imgsz": imgsz,
            "model_id": result["model_id"],
            "width": result["width"],
            "height": result["height"],
        },
    }
    insert_detection(record)
    return {**result, "source": source, "name": name}


@router.get("/detections")
def detections(limit: int = 20) -> dict[str, Any]:
    return {"items": list_detections(limit=min(100, max(1, limit)))}


@router.get("/samples")
def samples(limit: int = 24) -> dict[str, Any]:
    images = visdrone.list_images()[: max(1, min(60, limit))]
    out = []
    for img in images:
        labels = visdrone.read_label(img.stem)
        width, height = visdrone.image_size(img)
        out.append({
            "id": img.stem,
            "name": img.name,
            "url": f"/media/visdrone/{img.name}",
            "width": width,
            "height": height,
            "gt_count": len(labels),
            "classes": sorted({d["label_cn"] for d in labels}),
            "scene": _scene_of(img.stem),
        })
    return {"items": out, "total": len(visdrone.list_images())}


@router.get("/samples/{stem}")
def sample_detail(stem: str) -> dict[str, Any]:
    try:
        return visdrone.sample_payload(stem)
    except FileNotFoundError as exc:
        raise HTTPException(404, "样本不存在") from exc


def _scene_of(stem: str) -> str:
    """为演示生成稳定的航拍场景标签。"""
    scenes = ["城市主干道", "城郊路口", "工业园区", "居民片区", "快速路匝道", "广场步道"]
    value = sum(ord(c) for c in stem)
    return scenes[value % len(scenes)]


@router.get("/dataset/summary")
def dataset_summary() -> dict[str, Any]:
    if not IMAGES_DIR.exists():
        raise HTTPException(404, "数据集目录不存在")
    return visdrone.summary()


@router.get("/dataset/gallery")
def dataset_gallery(page: int = 1, page_size: int = 12, class_id: int | None = None) -> dict[str, Any]:
    return visdrone.gallery(page=max(1, page), page_size=max(1, min(36, page_size)), class_id=class_id)
