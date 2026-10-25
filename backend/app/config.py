from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
VISDRONE_DIR = DATA_DIR / "visdrone"
IMAGES_DIR = VISDRONE_DIR / "images"
LABELS_DIR = VISDRONE_DIR / "labels"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
JOB_DIR = DATA_DIR / "training_jobs"
RUNS_DIR = BASE_DIR / "runs"
WEIGHTS_DIR = BASE_DIR / "weights"
DB_PATH = DATA_DIR / "skyeye.db"

for _p in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, JOB_DIR, RUNS_DIR, WEIGHTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

DEFAULT_MODEL = WEIGHTS_DIR / "yolov8n.pt"

VISDRONE_CLASSES = [
    "pedestrian", "people", "bicycle", "car", "van",
    "truck", "tricycle", "awning-tricycle", "bus", "motor",
]

VISDRONE_CLASSES_CN = {
    "pedestrian": "行人",
    "people": "人群",
    "bicycle": "自行车",
    "car": "小汽车",
    "van": "面包车",
    "truck": "卡车",
    "tricycle": "三轮车",
    "awning-tricycle": "棚顶三轮",
    "bus": "公交车",
    "motor": "摩托车",
}

# COCO 预训练模型类别中文名（用于直接推理演示）
COCO_CLASSES_CN = {
    "person": "行人", "bicycle": "自行车", "car": "汽车", "motorcycle": "摩托车",
    "airplane": "飞机", "bus": "公交车", "train": "火车", "truck": "卡车",
    "boat": "船", "traffic light": "信号灯", "bench": "长椅", "bird": "鸟",
    "cat": "猫", "dog": "狗", "horse": "马", "sheep": "羊", "cow": "牛",
    "backpack": "背包", "umbrella": "雨伞", "handbag": "手提包", "suitcase": "行李箱",
    "skateboard": "滑板", "bottle": "瓶子", "cup": "杯子", "chair": "椅子",
    "dining table": "桌子", "potted plant": "盆栽", "bed": "床", "toilet": "马桶",
    "tv": "电视", "laptop": "笔记本", "mouse": "鼠标", "keyboard": "键盘",
    "cell phone": "手机", "book": "书", "clock": "时钟", "vase": "花瓶",
    "scissors": "剪刀", "teddy bear": "玩偶", "hair drier": "吹风机", "toothbrush": "牙刷",
}

PALETTE = [
    "#22d3ee", "#a3e635", "#f59e0b", "#f472b6", "#818cf8",
    "#34d399", "#fb7185", "#facc15", "#38bdf8", "#c084fc",
]
