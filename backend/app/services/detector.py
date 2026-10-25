from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from ..config import (
    COCO_CLASSES_CN,
    DEFAULT_MODEL,
    OUTPUT_DIR,
    PALETTE,
    RUNS_DIR,
    VISDRONE_CLASSES,
    VISDRONE_CLASSES_CN,
)

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


class DetectorService:
    """YOLO 模型注册表 + 推理 + 标注绘制。"""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._lock = threading.Lock()

    # ---------- 模型管理 ----------
    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        if DEFAULT_MODEL.exists():
            models.append({
                "id": "coco-yolov8n",
                "name": "YOLOv8n · COCO 预训练",
                "family": "coco",
                "task": "detect",
                "classes": 80,
                "size_mb": round(DEFAULT_MODEL.stat().st_size / 1024 / 1024, 1),
                "path": str(DEFAULT_MODEL),
                "note": "官方通用权重，用于快速验证与课堂演示",
            })

        if RUNS_DIR.exists():
            for weight in sorted(RUNS_DIR.glob("*/weights/best.pt")):
                job_id = weight.parents[1].name
                stat = weight.stat()
                models.append({
                    "id": f"run-{job_id}",
                    "name": f"微调权重 · {job_id}",
                    "family": "visdrone",
                    "task": "detect",
                    "classes": len(VISDRONE_CLASSES),
                    "size_mb": round(stat.st_size / 1024 / 1024, 1),
                    "path": str(weight),
                    "note": "由训练中心基于 VisDrone 子集产出",
                })
        return models

    def resolve(self, model_id: str) -> tuple[Any, dict[str, Any]]:
        models = {m["id"]: m for m in self.list_models()}
        meta = models.get(model_id) or models.get("coco-yolov8n")
        if not meta:
            raise FileNotFoundError("未找到可用权重，请先下载 yolov8n.pt")
        key = meta["id"]
        with self._lock:
            if key not in self._models:
                from ultralytics import YOLO  # 延迟导入，加快服务启动

                self._models[key] = YOLO(meta["path"])
            return self._models[key], meta

    # ---------- 推理 ----------
    def detect(
        self,
        image_path: Path,
        *,
        conf: float = 0.25,
        iou: float = 0.45,
        imgsz: int = 960,
        model_id: str = "coco-yolov8n",
        allowed_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        model, meta = self.resolve(model_id)
        started = time.perf_counter()
        results = model.predict(
            source=str(image_path), conf=conf, iou=iou, imgsz=imgsz,
            device="cpu", verbose=False,
        )
        latency = int((time.perf_counter() - started) * 1000)
        result = results[0]

        with Image.open(image_path) as img:
            width, height = img.size

        detections: list[dict[str, Any]] = []
        names = result.names or {}
        for idx, box in enumerate(result.boxes):
            cls_id = int(box.cls.item())
            raw_label = str(names.get(cls_id, cls_id))
            label_cn = self._label_cn(raw_label, meta["family"])
            if allowed_labels and label_cn not in allowed_labels:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            confidence = float(box.conf.item())
            color = PALETTE[cls_id % len(PALETTE)]
            detections.append({
                "id": f"det-{idx}",
                "class_id": cls_id,
                "label": raw_label,
                "label_cn": label_cn,
                "conf": round(confidence, 4),
                "x": round(x1 / width, 5),
                "y": round(y1 / height, 5),
                "w": round((x2 - x1) / width, 5),
                "h": round((y2 - y1) / height, 5),
                "px": [round(x1), round(y1), round(x2 - x1), round(y2 - y1)],
                "color": color,
                "area_ratio": round((x2 - x1) * (y2 - y1) / (width * height), 5),
            })

        detections.sort(key=lambda d: d["conf"], reverse=True)
        total = len(detections)
        avg_conf = round(sum(d["conf"] for d in detections) / total, 3) if total else 0.0
        counts: dict[str, int] = {}
        for det in detections:
            counts[det["label_cn"]] = counts.get(det["label_cn"], 0) + 1

        output_id = uuid.uuid4().hex[:12]
        output_name = f"{output_id}.jpg"
        annotated = self._annotate(Image.open(image_path).convert("RGB"), detections)
        annotated.save(OUTPUT_DIR / output_name, quality=88, optimize=True)

        return {
            "id": output_id,
            "width": width,
            "height": height,
            "image_url": f"/media/visdrone/{image_path.name}" if image_path.parent.name == "images" else f"/media/uploads/{image_path.name}",
            "output_url": f"/media/outputs/{output_name}",
            "inference_ms": latency,
            "model_id": meta["id"],
            "model_name": meta["name"],
            "model_family": meta["family"],
            "total": total,
            "avg_conf": avg_conf,
            "counts": counts,
            "detections": detections,
            "imgsz": imgsz,
        }

    @staticmethod
    def _label_cn(raw: str, family: str) -> str:
        if family == "visdrone" or raw in VISDRONE_CLASSES:
            return VISDRONE_CLASSES_CN.get(raw, raw)
        return COCO_CLASSES_CN.get(raw, raw)

    def _annotate(self, image: Image.Image, detections: list[dict[str, Any]]) -> Image.Image:
        draw = ImageDraw.Draw(image, "RGBA")
        width, height = image.size
        line = max(2, round(min(width, height) / 320))
        font_size = max(13, min(26, round(min(width, height) / 42)))
        font = _font(font_size)
        chip_h = font_size + 8

        for det in detections:
            x, y, w, h = (det["x"] * width, det["y"] * height, det["w"] * width, det["h"] * height)
            color = det["color"]
            rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
            draw.rectangle([x, y, x + w, y + h], outline=(*rgb, 235), width=line)
            # 四角强调
            corner = max(6, min(w, h) * 0.28)
            for cx, cy, dx, dy in (
                (x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1),
            ):
                draw.line([cx, cy, cx + dx * corner, cy], fill=(*rgb, 255), width=line + 1)
                draw.line([cx, cy, cx, cy + dy * corner], fill=(*rgb, 255), width=line + 1)

            text = f"{det['label_cn']} {det['conf']:.2f}"
            tx, ty = x, max(0, y - chip_h)
            tw = draw.textlength(text, font=font)
            draw.rounded_rectangle(
                [tx, ty, tx + tw + 12, ty + chip_h], radius=4,
                fill=(*rgb, 225), outline=(255, 255, 255, 70), width=1,
            )
            draw.text((tx + 6, ty + 3), text, font=font, fill=(8, 12, 20, 255))
        return image


detector = DetectorService()
