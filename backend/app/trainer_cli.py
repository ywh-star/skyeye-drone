"""训练子进程入口：由后端 TrainingRunner 以独立进程启动。

支持两种模式：
1. 全新训练：加载预训练权重，从第 0 轮开始；
2. 断点续训：加载 runs/<job>/weights/last.pt 并 resume=True，从上次完成的 epoch 继续。
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ultralytics import YOLO


def append_metric(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--project", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--resume-from", default="")
    args = parser.parse_args()

    metrics_path = Path(args.metrics)
    if metrics_path.exists() and not args.resume_from:
        metrics_path.unlink()

    def on_train_epoch_end(trainer) -> None:
        losses = trainer.label_loss_items(trainer.tloss, prefix="train")
        metrics = trainer.metrics or {}
        record = {
            "epoch": int(trainer.epoch) + 1,
            "epochs": int(trainer.epochs),
            "box_loss": round(float(losses.get("train/box_loss", 0)), 4),
            "cls_loss": round(float(losses.get("train/cls_loss", 0)), 4),
            "dfl_loss": round(float(losses.get("train/dfl_loss", 0)), 4),
            "mAP50": round(float(metrics.get("metrics/mAP50(B)", 0)), 4),
            "mAP50_95": round(float(metrics.get("metrics/mAP50-95(B)", 0)), 4),
            "lr": round(float((trainer.lr or {}).get("lr0", 0)), 6),
            "ts": time.strftime("%H:%M:%S"),
        }
        append_metric(metrics_path, record)
        print(f"METRIC {json.dumps(record)}", flush=True)

    if args.resume_from:
        weight = Path(args.resume_from)
        if not weight.exists():
            raise SystemExit(f"续训权重不存在: {weight}")
        print(f"[resume] 从 {weight} 继续训练", flush=True)
        model = YOLO(str(weight))
        model.add_callback("on_train_epoch_end", on_train_epoch_end)
        # 必须传检查点路径：resume=True 会让 ultralytics 自动挑选"最新 run"，可能选错任务
        model.train(resume=str(weight))
        return

    print(f"[train] job={args.job_id} data={args.data} epochs={args.epochs}", flush=True)
    model = YOLO(args.model)
    model.add_callback("on_train_epoch_end", on_train_epoch_end)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.job_id,
        exist_ok=True,
        device="cpu",
        workers=0,
        amp=False,
        cache=False,
        plots=True,
        verbose=True,
    )


if __name__ == "__main__":
    main()
