"""从 HuggingFace 拉取 VisDrone2019-DET 验证集子集（图片 + YOLO 标注）。

用法:
    python scripts/fetch_visdrone_subset.py --count 60

说明:
    VisDrone 官方数据集体积较大（train ~6GB），课程演示使用 val 集的均匀抽样，
    脚本可随时调整 --count 拉取更多样本，数据目录结构与 YOLO 官方一致。
"""
from __future__ import annotations

import argparse
import json
import random
import time
import urllib.request
from pathlib import Path

REPO = "banu4prasad/VisDrone-Dataset"
SPLIT = "VisDrone2019-DET-val"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main/{SPLIT}"
RESOLVE = f"https://huggingface.co/datasets/{REPO}/resolve/main/{SPLIT}"

CLASSES = [
    "pedestrian", "people", "bicycle", "car", "van",
    "truck", "tricycle", "awning-tricycle", "bus", "motor",
]

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data" / "visdrone"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "skyeye-course-project"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_files(kind: str) -> list[str]:
    url = f"{API}/{kind}?recursive=false&limit=1000"
    items = fetch_json(url)
    return [i["path"] for i in items if i.get("type") == "file"]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers={"User-Agent": "skyeye-course-project"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    tmp.replace(dest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=2024)
    args = parser.parse_args()

    (DATA / "images").mkdir(parents=True, exist_ok=True)
    (DATA / "labels").mkdir(parents=True, exist_ok=True)

    images = sorted(list_files("images"))
    labels = {Path(p).stem for p in list_files("labels")}
    pool = [p for p in images if Path(p).stem in labels]
    if not pool:
        raise SystemExit("未取到 VisDrone 文件列表，请检查网络")

    random.Random(args.seed).shuffle(pool)
    picked = pool[: args.count]

    ok = 0
    for idx, path in enumerate(picked, 1):
        name = Path(path).name
        stem = Path(path).stem
        try:
            download(f"{RESOLVE}/images/{name}", DATA / "images" / name)
            download(f"{RESOLVE}/labels/{stem}.txt", DATA / "labels" / f"{stem}.txt")
            ok += 1
            print(f"[{idx}/{len(picked)}] {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"跳过 {name}: {exc}")
        time.sleep(0.02)

    yaml_lines = [
        "# VisDrone2019-DET val 抽样（课程实验用）",
        f"path: {DATA.as_posix()}",
        "train: images",
        "val: images",
        "names:",
    ]
    yaml_lines += [f"  {i}: {n}" for i, n in enumerate(CLASSES)]
    (DATA / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    manifest = {
        "source": f"https://huggingface.co/datasets/{REPO}",
        "split": SPLIT,
        "downloaded": ok,
        "seed": args.seed,
        "note": "VisDrone2019-DET 验证集均匀抽样，用于课程实验演示，遵循 CC BY-NC-SA 3.0 协议",
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：{ok} 张图片已写入 {DATA}")


if __name__ == "__main__":
    main()
