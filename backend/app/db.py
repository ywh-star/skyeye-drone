from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any

from .config import DB_PATH

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    with _lock:
        conn = _connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                area TEXT NOT NULL,
                drone TEXT NOT NULL,
                altitude INTEGER NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                detections INTEGER NOT NULL DEFAULT 0,
                cover_km2 REAL NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                duration_min INTEGER NOT NULL DEFAULT 0,
                assignee TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                reviewer TEXT NOT NULL DEFAULT '',
                review_note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS detections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                total INTEGER NOT NULL,
                avg_conf REAL NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                image_url TEXT NOT NULL,
                output_url TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        # 迁移：为已有 tasks 表补齐新字段（SQLite 不支持 IF NOT EXISTS ADD COLUMN，用 try 兜底）
        existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        for col, ddl in [
            ("assignee", "TEXT NOT NULL DEFAULT ''"),
            ("priority", "TEXT NOT NULL DEFAULT 'normal'"),
            ("reviewer", "TEXT NOT NULL DEFAULT ''"),
            ("review_note", "TEXT NOT NULL DEFAULT ''"),
        ]:
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
                except sqlite3.OperationalError:
                    pass
        conn.commit()


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def insert_detection(record: dict[str, Any]) -> None:
    with _lock:
        conn = _connection()
        conn.execute(
            """INSERT INTO detections VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                record["id"], record["name"], record["model"], record["total"],
                record["avg_conf"], record["latency_ms"], record["created_at"],
                record["image_url"], record["output_url"],
                json.dumps(record["payload"], ensure_ascii=False),
            ),
        )
        conn.commit()


def list_detections(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        rows = _connection().execute(
            "SELECT * FROM detections ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        out.append(item)
    return out


def detection_overview() -> dict[str, Any]:
    with _lock:
        conn = _connection()
        images = conn.execute("SELECT COUNT(*) c FROM detections").fetchone()["c"]
        objects = conn.execute("SELECT COALESCE(SUM(total),0) t FROM detections").fetchone()["t"]
        avg_lat = conn.execute("SELECT COALESCE(AVG(latency_ms),0) a FROM detections").fetchone()["a"]
        rows = conn.execute("SELECT created_at, total, payload FROM detections").fetchall()

    timeline: dict[str, int] = {}
    classes: dict[str, int] = {}
    for row in rows:
        day = row["created_at"][:10]
        timeline[day] = timeline.get(day, 0) + row["total"]
        payload = json.loads(row["payload"])
        for det in payload.get("counts", {}).items():
            classes[det[0]] = classes.get(det[0], 0) + det[1]
    return {
        "images_processed": images,
        "objects_found": objects,
        "avg_latency": round(avg_lat, 1),
        "timeline": [{"date": k, "count": v} for k, v in sorted(timeline.items())],
        "class_top": sorted(
            [{"label": k, "count": v} for k, v in classes.items()],
            key=lambda x: x["count"], reverse=True,
        )[:8],
    }


# ---------- 飞行任务 ----------

SEED_TASKS = [
    ("TSK-2401", "滨江路网车流巡检", "滨江区 · 江南大道", "Matrice 350 RTK", 180, "running", 68, 1248, 3.6, "2026-10-24 08:20:00", 46),
    ("TSK-2402", "城郊结合部人群密度评估", "余杭区 · 未来科技城", "Mavic 3E", 120, "running", 41, 862, 1.9, "2026-10-24 09:05:00", 31),
    ("TSK-2403", "快速路事故现场取证", "沪昆高速 K38 段", "Matrice 30T", 220, "review", 100, 2140, 5.2, "2026-10-24 07:10:00", 58),
    ("TSK-2404", "校园周边非机动车治理", "西湖区 · 文三路", "Mavic 3E", 150, "queued", 0, 0, 2.4, "2026-10-24 11:30:00", 0),
    ("TSK-2405", "夜间施工工地安全巡查", "拱墅区 · 运河东岸", "Matrice 350 RTK", 160, "done", 100, 967, 2.8, "2026-10-23 21:40:00", 42),
]


def seed_tasks() -> None:
    with _lock:
        conn = _connection()
        count = conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]
        if count:
            return
        for row in SEED_TASKS:
            conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"task-{row[0]}", *row),
            )
        conn.commit()


def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        conn = _connection()
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY started_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY CASE status "
                "WHEN 'running' THEN 0 WHEN 'queued' THEN 1 WHEN 'review' THEN 2 ELSE 3 END, started_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def create_task(payload: dict[str, Any]) -> dict[str, Any]:
    import random

    code = f"TSK-{random.randint(2406, 2999)}"
    task_id = f"task-{code}"
    record = {
        "id": task_id, "code": code, "name": payload["name"], "area": payload["area"],
        "drone": payload.get("drone", "Mavic 3E"), "altitude": int(payload.get("altitude", 150)),
        "status": "queued", "progress": 0, "detections": 0,
        "cover_km2": float(payload.get("cover_km2", 2.0)),
        "started_at": now_iso(), "duration_min": 0,
        "assignee": payload.get("assignee", ""),
        "priority": payload.get("priority", "normal"),
        "reviewer": "",
        "review_note": "",
    }
    with _lock:
        conn = _connection()
        conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record["id"], record["code"], record["name"], record["area"], record["drone"],
                record["altitude"], record["status"], record["progress"], record["detections"],
                record["cover_km2"], record["started_at"], record["duration_min"],
                record["assignee"], record["priority"], record["reviewer"], record["review_note"],
            ),
        )
        conn.commit()
    return record


def update_task_status(task_id: str, status: str, reviewer: str = "", review_note: str = "") -> dict[str, Any] | None:
    progress = {"running": 5, "review": 100, "queued": 0, "done": 100}.get(status, 0)
    with _lock:
        conn = _connection()
        if status in {"review", "done"}:
            conn.execute(
                "UPDATE tasks SET status=?, progress=?, reviewer=?, review_note=? WHERE id=?",
                (status, progress, reviewer, review_note, task_id),
            )
        else:
            conn.execute("UPDATE tasks SET status=?, progress=? WHERE id=?", (status, progress, task_id))
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def update_task(task_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "area", "drone", "altitude", "cover_km2", "assignee", "priority", "detections", "duration_min"}
    sets = []
    values: list[Any] = []
    for key, val in fields.items():
        if key in allowed:
            sets.append(f"{key}=?")
            values.append(val)
    if not sets:
        return None
    values.append(task_id)
    with _lock:
        conn = _connection()
        conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?", tuple(values))
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def delete_task(task_id: str) -> bool:
    with _lock:
        conn = _connection()
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
    return cur.rowcount > 0
