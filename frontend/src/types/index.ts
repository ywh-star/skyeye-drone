export interface ModelInfo {
  id: string
  name: string
  family: 'coco' | 'visdrone'
  task: string
  classes: number
  size_mb: number
  path: string
  note: string
}

export interface DatasetClass {
  id: number
  name: string
  name_cn: string
  color: string
  count: number
}

export interface SystemInfo {
  app: string
  version: string
  python: string
  platform: string
  torch: string
  ultralytics: string
  device: string
  uptime_sec: number
  models: ModelInfo[]
  dataset: { name: string; ready: boolean; images: number }
  frontend: { vue: string; typescript: string; three: string }
}

export interface DetectionItem {
  id: string
  class_id: number
  label: string
  label_cn: string
  conf: number
  x: number
  y: number
  w: number
  h: number
  px: [number, number, number, number]
  color: string
  area_ratio: number
}

export interface DetectResult {
  id: string
  width: number
  height: number
  image_url: string
  output_url: string
  inference_ms: number
  model_id: string
  model_name: string
  model_family: string
  total: number
  avg_conf: number
  counts: Record<string, number>
  detections: DetectionItem[]
  imgsz: number
  source: string
  name: string
}

export interface HistoryItem {
  id: string
  name: string
  model: string
  total: number
  avg_conf: number
  latency_ms: number
  created_at: string
  image_url: string
  output_url: string
  payload: {
    counts: Record<string, number>
    detections: DetectionItem[]
    source: string
    width: number
    height: number
  }
}

export interface SampleItem {
  id: string
  name: string
  url: string
  width: number
  height: number
  gt_count: number
  classes: string[]
  scene: string
}

export interface GroundTruth extends DetectionItem {
  px: [number, number, number, number]
}

export interface SampleDetail extends SampleItem {
  gt: GroundTruth[]
}

export interface DatasetSummary {
  name: string
  split: string
  images: number
  labels: number
  objects: number
  avg_objects: number
  classes: DatasetClass[]
  size_mb: number
  source: string
  license: string
  manifest: Record<string, unknown>
}

export interface GalleryItem {
  id: string
  name: string
  url: string
  width: number
  height: number
  objects: number
  classes: string[]
}

export type TaskStatus = 'running' | 'review' | 'queued' | 'done'
export type TaskPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface TaskItem {
  id: string
  code: string
  name: string
  area: string
  drone: string
  altitude: number
  status: TaskStatus
  progress: number
  detections: number
  cover_km2: number
  started_at: string
  duration_min: number
  assignee: string
  priority: TaskPriority
  reviewer: string
  review_note: string
}

export interface Overview {
  images_processed: number
  objects_found: number
  avg_latency: number
  active_tasks: number
  total_tasks: number
  timeline: { date: string; count: number }[]
  class_top: { label: string; count: number }[]
  dataset: { name: string; images: number; objects: number; classes: DatasetClass[] }
  tasks: TaskItem[]
}

export interface TrainMetric {
  epoch: number
  epochs: number
  box_loss: number
  cls_loss: number
  dfl_loss: number
  mAP50: number
  mAP50_95: number
  lr: number
  ts: string
}

export interface Checkpoint {
  name: string
  size_mb: number
  updated_at: string
  resumable: boolean
  best: boolean
}

export interface ReplayMarker {
  id: string
  label: string
  count: number
  color: string
  x: number
  z: number
  time: number
}

export interface TrainingJob {
  id: string
  status: 'queued' | 'running' | 'stopping' | 'stopped' | 'finished' | 'failed'
  created_at: string
  started_at: string | null
  ended_at: string | null
  device: string
  config: {
    epochs: number
    imgsz: number
    batch: number
    base_model: string
    model_path: string
    data: string
    note: string
  }
  current_epoch: number
  total_epochs: number
  resume_count: number
  best_map50: number
  last_metrics: TrainMetric | null
  checkpoints: Checkpoint[]
  resumed_from?: 'checkpoint' | 'fresh'
}
