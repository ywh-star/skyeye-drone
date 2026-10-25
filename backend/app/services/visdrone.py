from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

from ..config import (
    COCO_CLASSES_CN,
    IMAGES_DIR,
    LABELS_DIR,
    PALETTE,
    VISDRONE_CLASSES,
    VISDRONE_CLASSES_CN,
)

_size_cache: dict[str, tuple[int, int]] = {}


def image_size(path: Path) -> tuple[int, int]:
    key = str(path)
    if key not in _size_cache:
        with Image.open(path) as img:
            _size_cache[key] = img.size
    return _size_cache[key]


def _parse_label_line(line: str) -> tuple[int, float, float, float, float, bool] | None:
    """返回 (class_id, x, y, w, h, 是否为绝对坐标)。

    兼容 YOLO 归一化格式（5 列）与 VisDrone 原生格式（8 列）。
    """
    parts = line.strip().split()
    if len(parts) < 5:
        return None
    if len(parts) >= 8:
        left, top, w, h = map(float, parts[:4])
        category = int(float(parts[5]))
        return (category - 1, left, top, w, h, True)
    cls = int(float(parts[0]))
    cx, cy, w, h = map(float, parts[1:5])
    return (cls, cx - w / 2, cy - h / 2, w, h, False)


def read_label(stem: str) -> list[dict[str, Any]]:
    path = LABELS_DIR / f"{stem}.txt"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parsed = _parse_label_line(line)
        if not parsed:
            continue
        cls, x, y, w, h, absolute = parsed
        if absolute:
            img_path = next(IMAGES_DIR.glob(f"{stem}.*"), None)
            if not img_path:
                continue
            iw, ih = image_size(img_path)
            x, y, w, h = x / iw, y / ih, w / iw, h / ih
        if cls < 0 or cls >= len(VISDRONE_CLASSES):
            continue
        name = VISDRONE_CLASSES[cls]
        out.append({
            "class_id": cls,
            "label": name,
            "label_cn": VISDRONE_CLASSES_CN[name],
            "color": PALETTE[cls % len(PALETTE)],
            "x": round(max(0.0, x), 5), "y": round(max(0.0, y), 5),
            "w": round(min(1.0, w), 5), "h": round(min(1.0, h), 5),
            "conf": 1.0,
        })
    return out


def list_images() -> list[Path]:
    if not IMAGES_DIR.exists():
        return []
    return sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))


def gallery(page: int = 1, page_size: int = 12, class_id: int | None = None) -> dict[str, Any]:
    images = list_images()
    if class_id is not None:
        filtered = []
        for img in images:
            if any(d["class_id"] == class_id for d in read_label(img.stem)):
                filtered.append(img)
        images = filtered

    total = len(images)
    start = (page - 1) * page_size
    items = []
    for img in images[start:start + page_size]:
        labels = read_label(img.stem)
        w, h = image_size(img)
        classes = sorted({d["label"] for d in labels})
        items.append({
            "id": img.stem,
            "name": img.name,
            "url": f"/media/visdrone/{img.name}",
            "width": w, "height": h,
            "objects": len(labels),
            "classes": classes[:6],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def sample_payload(stem: str) -> dict[str, Any]:
    img = next((p for p in list_images() if p.stem == stem), None)
    if not img:
        raise FileNotFoundError(stem)
    w, h = image_size(img)
    gt = read_label(stem)
    for det in gt:
        det["px"] = [round(det["x"] * w), round(det["y"] * h), round(det["w"] * w), round(det["h"] * h)]
    return {
        "id": stem, "name": img.name, "url": f"/media/visdrone/{img.name}",
        "width": w, "height": h, "gt": gt, "gt_count": len(gt),
    }


def summary() -> dict[str, Any]:
    images = list_images()
    counts = [0] * len(VISDRONE_CLASSES)
    objects = 0
    for img in images:
        for det in read_label(img.stem):
            counts[det["class_id"]] += 1
            objects += 1

    total_bytes = sum(p.stat().st_size for p in images) + sum(
        p.stat().st_size for p in LABELS_DIR.glob("*.txt")
    ) if images else 0
    manifest = {}
    manifest_path = IMAGES_DIR.parent / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    classes = []
    for idx, name in enumerate(VISDRONE_CLASSES):
        classes.append({
            "id": idx, "name": name, "name_cn": VISDRONE_CLASSES_CN[name],
            "color": PALETTE[idx % len(PALETTE)], "count": counts[idx],
        })
    return {
        "name": "VisDrone2019-DET",
        "split": "val 集抽样（无人机航拍）",
        "images": len(images),
        "labels": len(list(LABELS_DIR.glob("*.txt"))),
        "objects": objects,
        "avg_objects": round(objects / max(1, len(images)), 1),
        "classes": classes,
        "size_mb": round(total_bytes / 1024 / 1024, 1),
        "source": "https://huggingface.co/datasets/banu4prasad/VisDrone-Dataset",
        "license": "CC BY-NC-SA 3.0",
        "manifest": manifest,
    }


def pick_stem(index: int) -> str:
    images = list_images()
    if not images:
        raise FileNotFoundError("VisDrone 子集为空，请先运行 scripts/fetch_visdrone_subset.py")
    idx = int(math.fmod(index, len(images)))
    return images[idx].stem


def coco_label_cn(name: str) -> str:
    return COCO_CLASSES_CN.get(name, name)


@lru_cache(maxsize=1)
def class_color_map() -> dict[str, str]:
    return {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(VISDRONE_CLASSES)}
