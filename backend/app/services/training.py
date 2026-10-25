from __future__ import annotations

import codecs
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Generator

from ..config import (
    BASE_DIR,
    IMAGES_DIR,
    JOB_DIR,
    LABELS_DIR,
    RUNS_DIR,
    VISDRONE_CLASSES,
    VISDRONE_DIR,
)


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def prepare_dataset() -> Path:
    """把扁平的 VisDrone 抽样拆分为 YOLO 训练/验证目录（仅首次执行）。"""
    yolo_dir = VISDRONE_DIR / "yolo"
    data_yaml = yolo_dir / "data.yaml"
    split_index = yolo_dir / "images" / "val"
    if data_yaml.exists() and split_index.exists() and any(split_index.iterdir()):
        return data_yaml

    images = sorted(IMAGES_DIR.glob("*.jpg"))
    if not images:
        raise FileNotFoundError("VisDrone 图片为空，请先运行 scripts/fetch_visdrone_subset.py")

    for sub in ("train", "val"):
        (yolo_dir / "images" / sub).mkdir(parents=True, exist_ok=True)
        (yolo_dir / "labels" / sub).mkdir(parents=True, exist_ok=True)

    val_count = max(1, round(len(images) * 0.2))
    for idx, img in enumerate(images):
        subset = "val" if idx % max(1, round(len(images) / val_count)) == 0 else "train"
        target_img = yolo_dir / "images" / subset / img.name
        target_lbl = yolo_dir / "labels" / subset / f"{img.stem}.txt"
        if not target_img.exists():
            shutil.copy2(img, target_img)
        source_lbl = LABELS_DIR / f"{img.stem}.txt"
        if source_lbl.exists() and not target_lbl.exists():
            shutil.copy2(source_lbl, target_lbl)

    lines = [
        f"path: {yolo_dir.as_posix()}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    lines += [f"  {i}: {n}" for i, n in enumerate(VISDRONE_CLASSES)]
    data_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data_yaml


class TrainingRunner:
    def __init__(self) -> None:
        self._procs: dict[str, subprocess.Popen] = {}
        self._stop_flags: dict[str, bool] = {}
        self._lock = threading.Lock()

    # ---------- 路径 ----------
    @staticmethod
    def meta_path(job_id: str) -> Path:
        return JOB_DIR / f"{job_id}.json"

    @staticmethod
    def log_path(job_id: str) -> Path:
        return JOB_DIR / f"{job_id}.log"

    @staticmethod
    def metrics_path(job_id: str) -> Path:
        return JOB_DIR / f"{job_id}.metrics.jsonl"

    # ---------- 任务管理 ----------
    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        model_path = self._resolve_model(payload.get("base_model", "coco-yolov8n"))
        data_yaml = prepare_dataset()

        meta = {
            "id": job_id,
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "started_at": None,
            "ended_at": None,
            "device": "CPU",
            "config": {
                "epochs": int(payload.get("epochs", 3)),
                "imgsz": int(payload.get("imgsz", 320)),
                "batch": int(payload.get("batch", 8)),
                "base_model": payload.get("base_model", "coco-yolov8n"),
                "model_path": model_path,
                "data": str(data_yaml),
                "note": payload.get("note", ""),
            },
            "current_epoch": 0,
            "total_epochs": int(payload.get("epochs", 3)),
            "resume_count": 0,
            "best_map50": 0.0,
            "last_metrics": None,
        }
        self._write_meta(meta)
        self.log_path(job_id).write_text("", encoding="utf-8")
        self._spawn(job_id, resume_from=None)
        return self.get(job_id)

    def resume(self, job_id: str) -> dict[str, Any]:
        meta = self._read_meta(job_id)
        if meta["status"] in {"running", "queued", "stopping"}:
            raise ValueError("任务正在进行中，请先停止再续训")
        done_epochs = len(self.metrics(job_id))
        if meta["status"] == "finished" or done_epochs >= int(meta.get("total_epochs", 1)):
            raise ValueError("任务已完成全部轮次，无需续训")
        last = RUNS_DIR / job_id / "weights" / "last.pt"
        # 无 last.pt（如首个 epoch 未完成即被停止）时回退为按原配置重启任务
        resume_from = last if last.exists() else None
        meta["status"] = "queued"
        meta["resume_count"] = int(meta.get("resume_count", 0)) + 1
        meta["ended_at"] = None
        self._write_meta(meta)
        mode = "断点续训" if resume_from else "无检查点，从头重启"
        with open(self.log_path(job_id), "a", encoding="utf-8") as fh:
            fh.write(f"\n=== {mode} #{meta['resume_count']} · {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        self._spawn(job_id, resume_from=resume_from)
        result = self.get(job_id)
        result["resumed_from"] = "checkpoint" if resume_from else "fresh"
        return result

    def stop(self, job_id: str) -> dict[str, Any]:
        proc = self._procs.get(job_id)
        self._stop_flags[job_id] = True
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=12)
            except subprocess.TimeoutExpired:
                proc.kill()
        meta = self._read_meta(job_id)
        if meta["status"] in {"running", "queued", "stopping"}:
            meta["status"] = "stopped"
            meta["ended_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._write_meta(meta)
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        meta = self._read_meta(job_id)
        metrics = self.metrics(job_id)
        if metrics:
            meta["current_epoch"] = metrics[-1]["epoch"]
            meta["last_metrics"] = metrics[-1]
            meta["best_map50"] = max(m["mAP50"] for m in metrics)
        meta["checkpoints"] = self.checkpoints(job_id)
        return meta

    def list(self) -> list[dict[str, Any]]:
        jobs = []
        for path in sorted(JOB_DIR.glob("job-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                jobs.append(self.get(path.stem))
            except (json.JSONDecodeError, KeyError):
                continue
        return jobs

    def metrics(self, job_id: str) -> list[dict[str, Any]]:
        path = self.metrics_path(job_id)
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        # 续训时 last.pt 会重跑中断轮次，按 epoch 去重保留最新记录
        deduped: dict[int, dict[str, Any]] = {}
        for record in out:
            deduped[int(record.get("epoch", 0))] = record
        return [deduped[key] for key in sorted(deduped)]

    def checkpoints(self, job_id: str) -> list[dict[str, Any]]:
        weight_dir = RUNS_DIR / job_id / "weights"
        if not weight_dir.exists():
            return []
        out = []
        for path in sorted(weight_dir.glob("*.pt")):
            stat = path.stat()
            out.append({
                "name": path.name,
                "size_mb": round(stat.st_size / 1024 / 1024, 1),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "resumable": path.name == "last.pt",
                "best": path.name == "best.pt",
            })
        return out

    def log_tail(self, job_id: str, max_lines: int = 120) -> list[str]:
        path = self.log_path(job_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-max_lines:]

    def stream(self, job_id: str) -> Generator[str, None, None]:
        """SSE：推送日志增量、指标与状态。"""
        path = self.log_path(job_id)
        offset = 0
        last_metrics_count = 0
        terminal = {"finished", "failed", "stopped"}

        def event(name: str, data: Any) -> str:
            return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield event("hello", self.get(job_id))
        while True:
            meta = self._read_meta(job_id)
            new_lines: list[str] = []
            if path.exists():
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    fh.seek(offset)
                    chunk = fh.read()
                    if chunk:
                        offset = fh.tell()
                        new_lines = [ln for ln in chunk.split("\n") if ln.strip()]
            if new_lines:
                yield event("log", {"lines": new_lines[-40:]})

            metrics = self.metrics(job_id)
            if len(metrics) > last_metrics_count:
                last_metrics_count = len(metrics)
                yield event("metrics", metrics)
                yield event("state", self.get(job_id))

            if meta["status"] in terminal:
                yield event("done", self.get(job_id))
                break
            if meta["status"] == "running":
                yield event("state", self.get(job_id))
            yield ": keep-alive\n\n"
            time.sleep(0.8)

    # ---------- 内部 ----------
    def _spawn(self, job_id: str, resume_from: Path | None) -> None:
        meta = self._read_meta(job_id)
        config = meta["config"]
        cmd = [
            sys.executable, "-m", "app.trainer_cli",
            "--job-id", job_id,
            "--data", config["data"],
            "--model", config["model_path"],
            "--epochs", str(config["epochs"]),
            "--imgsz", str(config["imgsz"]),
            "--batch", str(config["batch"]),
            "--project", str(RUNS_DIR),
            "--metrics", str(self.metrics_path(job_id)),
        ]
        if resume_from:
            cmd += ["--resume-from", str(resume_from)]

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        log_file = open(self.log_path(job_id), "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, bufsize=1,
        )
        with self._lock:
            self._procs[job_id] = proc
            self._stop_flags[job_id] = False

        meta["status"] = "running"
        meta["started_at"] = meta.get("started_at") or time.strftime("%Y-%m-%d %H:%M:%S")
        self._write_meta(meta)

        def pump() -> None:
            assert proc.stdout is not None
            buffer = ""
            decoder = codecs.getincrementaldecoder("utf-8")("ignore")
            fd = proc.stdout.fileno()
            while True:
                raw = os.read(fd, 4096)
                if not raw:
                    break
                chunk = decoder.decode(raw)
                buffer += chunk
                buffer = buffer.replace("\r\n", "\n").replace("\r", "\n")
                if "\n" in buffer:
                    parts = buffer.split("\n")
                    buffer = parts.pop()
                    for line in parts:
                        if line.strip():
                            log_file.write(ANSI_RE.sub("", line.rstrip()) + "\n")
                            log_file.flush()
                            if line.startswith("METRIC "):
                                try:
                                    record = json.loads(line[7:])
                                except json.JSONDecodeError:
                                    record = None
                                if record:
                                    current = self._read_meta(job_id)
                                    current["current_epoch"] = record["epoch"]
                                    current["last_metrics"] = record
                                    current["best_map50"] = max(
                                        float(current.get("best_map50") or 0), record["mAP50"]
                                    )
                                    self._write_meta(current)
            if buffer.strip():
                log_file.write(buffer.rstrip() + "\n")
                log_file.flush()
            log_file.close()
            code = proc.wait()
            final = self._read_meta(job_id)
            if self._stop_flags.get(job_id):
                final["status"] = "stopped"
            elif code == 0:
                final["status"] = "finished"
            else:
                final["status"] = "failed"
            final["ended_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._write_meta(final)
            with self._lock:
                self._procs.pop(job_id, None)

        threading.Thread(target=pump, name=f"train-pump-{job_id}", daemon=True).start()

    def _resolve_model(self, model_id: str) -> str:
        from .detector import detector

        models = {m["id"]: m for m in detector.list_models()}
        meta = models.get(model_id) or models.get("coco-yolov8n")
        if not meta:
            raise FileNotFoundError("未找到可用基础权重")
        return meta["path"]

    def _read_meta(self, job_id: str) -> dict[str, Any]:
        return json.loads(self.meta_path(job_id).read_text(encoding="utf-8"))

    def _write_meta(self, meta: dict[str, Any]) -> None:
        self.meta_path(meta["id"]).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )


runner = TrainingRunner()
