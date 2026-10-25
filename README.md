# SkyEye 天穹 · 无人机航拍智能检测平台

基于 **YOLOv8 + Vue 3 + TypeScript + Three.js** 的无人机航拍目标检测课程实验项目。
前端采用 Vue 3 Composition API + TypeScript + Three.js 实现，响应式状态、组件化、路由、状态管理与三维渲染全部服务于检测、数据集、训练等真实业务功能。

## 功能总览

| 模块 | 能力 |
| --- | --- |
| 接入页 `/` | Three.js 城市航拍场景、呼号/口令登录、角色切换、态势统计 |
| 任务控制台 `/console` | 检测概况、ECharts 趋势/类别图、任务流转、系统状态环形仪表 |
| 检测工作台 `/detect` | VisDrone 样本/本地上传、真实 YOLOv8 推理、2D 检测框、3D 立体框、参数调节、类别筛选、历史与 JSON 导出 |
| 三维航迹回放 `/replay` | CatmullRom 闭合航线、无人机飞行、目标落点、相机模式、时间轴与遥测 HUD |
| VisDrone 数据集 `/dataset` | 数据摘要、类别分布、类别筛选、分页画廊、GT 标注弹窗 |
| 模型训练中心 `/training` | CPU 微调、SSE 实时日志/指标、损失与 mAP 曲线、检查点归档、停止与断点续训 |
| 404 | 雷达扫描风格“航迹信号丢失”页 |

## 技术栈

- **前端**：Vue 3.5（Composition API / `<script setup>`）、TypeScript 5.7、Vite 6、Vue Router 4、Pinia 2
- **可视化**：Three.js r172（OrbitControls、程序化城市/地形/航线）、ECharts 5
- **后端**：FastAPI、Uvicorn、Ultralytics YOLOv8、PyTorch（CPU）、Pillow、SQLite
- **数据**：VisDrone2019-DET val 子集（YOLO 5 列归一化标注，10 类）

## 目录结构

```
skyeye-drone/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI 入口、静态资源与 SPA 回退
│   │   ├── config.py              # 路径、类别、调色板
│   │   ├── db.py                  # SQLite 任务/检测记录
│   │   ├── trainer_cli.py         # 训练子进程（新训练 / resume）
│   │   ├── routers/               # system / detect / tasks / training
│   │   └── services/              # detector / visdrone / training
│   ├── data/visdrone/             # 航拍图片与 YOLO 标注
│   ├── runs/                      # 训练产物 <job_id>/weights/{best,last}.pt
│   ├── weights/yolov8n.pt         # COCO 预训练权重
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts          # 泛型请求封装
│   │   ├── components/            # ui / detect / three
│   │   ├── layouts/AppShell.vue
│   │   ├── views/                 # 7 个业务页面
│   │   ├── stores/                # Pinia
│   │   ├── router/                # 路由与懒加载
│   │   ├── directives/reveal.ts   # v-reveal
│   │   └── plugins/skyeye.ts      # 全局插件
│   └── package.json
└── scripts/fetch_visdrone_subset.py
```

## 快速启动

### 1. 后端

项目使用已准备好的 Conda 环境 `agri_drone`（Python 3.10 + torch 2.5.1 CPU + ultralytics 8.4.183）：

```powershell
cd backend
D:\Miniconda3\envs\agri_drone\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

也可以自行创建环境：

```powershell
conda create -n agri_drone python=3.10 -y
conda activate agri_drone
pip install -r backend/requirements.txt
```

首次运行会自动创建 SQLite 表与示例任务。预训练权重默认位于
`backend/weights/yolov8n.pt`（Ultralytics 也会在首次使用时自动下载）。

### 2. 前端开发模式

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`。Vite 已将 `/api` 与 `/media` 代理到 `127.0.0.1:8000`。

### 3. 生产构建（单端口部署）

```powershell
cd frontend
npm run build
```

构建产物 `frontend/dist` 会被 FastAPI 自动挂载，直接访问
`http://127.0.0.1:8000/` 即可；任意前端路由（如 `/dataset`）都会回退到 `index.html`。

## VisDrone 数据集

- 来源：VisDrone2019-DET（天津大学 AISKYEYE 团队），通过 HuggingFace 公开镜像抽样
- 当前子集：20 张真实航拍影像、314 个标注框、10 类目标
- 类别：`pedestrian / people / bicycle / car / van / truck / tricycle / awning-tricycle / bus / motor`
- 标注：YOLO 格式 `class cx cy w h`（归一化），位于 `backend/data/visdrone/labels`
- 下载脚本：

```powershell
python scripts/fetch_visdrone_subset.py --count 60
```

已有文件会自动跳过；网络波动时可重复运行补齐。

## 模型训练与断点续训

训练中心支持：

1. 选择基础权重（COCO `yolov8n` 或已训练任务权重）
2. 配置 epochs / imgsz / batch 并启动 CPU 训练
3. 通过 SSE（`/stream`）实时接收日志、metrics、状态与完成事件
4. 每个 epoch 结束自动写入 `runs/<job_id>/weights/last.pt`，同时保留 `best.pt`
5. 手动停止后点击“断点续训”，从 `last.pt` 恢复优化器与学习率状态，**已完成的 epoch 指标不会丢失**
6. 训练完成后，微调权重会以 `run-<job_id>` 出现在检测工作台的模型下拉框中

相关 API：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/training/jobs` | 任务列表 |
| POST | `/api/training/jobs` | 新建训练 |
| POST | `/api/training/jobs/{id}/stop` | 停止并保留检查点 |
| POST | `/api/training/jobs/{id}/resume` | 断点续训 |
| GET | `/api/training/jobs/{id}/metrics` | 指标与检查点 |
| GET | `/api/training/jobs/{id}/stream` | SSE 实时流 |

> CPU 演示建议 `epochs 1–5 / imgsz 320 / batch 4`；本项目实测 20 张图、12 epoch 约 1 分钟。

## 前端架构

前端按 `views / components / stores / api` 分层，路由懒加载按页面分包；Pinia 统一管理检测、数据集、训练等业务状态；Three.js 负责三维场景与航迹回放，ECharts 负责控制台趋势图表。

## 实验验收清单

- [x] 前端采用 Vue 3 Composition API 与 TypeScript 完成（`vue-tsc` 通过）
- [x] Three.js 三维检测与航迹回放
- [x] YOLOv8 真实推理（CPU）
- [x] VisDrone 真实航拍数据集接入
- [x] 训练管理、SSE 实时指标、检查点归档、断点续训
- [x] 生产构建与 FastAPI 单端口部署
- [x] 浏览器端 8 个页面验收，无控制台错误

## 说明

本项目仅用于课程实验与学习交流。VisDrone 数据版权归原作者所有，使用时请遵循其许可协议（CC BY-SA 3.0）。
