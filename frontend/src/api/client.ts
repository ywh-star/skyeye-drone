import type {
  DatasetSummary, DetectResult, GalleryItem, HistoryItem, ModelInfo, Overview,
  SampleDetail, SampleItem, SystemInfo, TaskItem, TrainMetric, TrainingJob, Checkpoint,
} from '@/types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // 超时兜底：防止后端挂起时请求永不返回，导致按钮永久禁用
  const controller = new AbortController()
  const timeoutMs = 15_000
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(path, {
      headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...init,
    })
    if (!res.ok) {
      let message = `请求失败 (${res.status})`
      try {
        const data = await res.json()
        message = data.detail || data.message || message
      } catch { /* ignore */ }
      throw new Error(message)
    }
    return res.json() as Promise<T>
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`请求超时（${timeoutMs / 1000}s），请检查后端服务`)
    }
    throw err
  } finally {
    window.clearTimeout(timer)
  }
}

export interface DetectParams {
  conf: number
  iou: number
  imgsz: number
  model_id: string
  labels?: string[]
}

function detectForm(params: DetectParams, extra: { sample?: string; file?: File }): FormData {
  const form = new FormData()
  form.append('conf', String(params.conf))
  form.append('iou', String(params.iou))
  form.append('imgsz', String(params.imgsz))
  form.append('model_id', params.model_id)
  if (params.labels?.length) form.append('labels', params.labels.join(','))
  if (extra.sample) form.append('sample', extra.sample)
  if (extra.file) form.append('file', extra.file)
  return form
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  info: () => request<SystemInfo>('/api/system/info'),
  overview: () => request<Overview>('/api/system/overview'),

  models: () => request<{ models: ModelInfo[] }>('/api/system/info').then((d) => d.models),

  samples: (limit = 24) => request<{ items: SampleItem[]; total: number }>(`/api/samples?limit=${limit}`),
  sample: (stem: string) => request<SampleDetail>(`/api/samples/${stem}`),

  detectSample: (sample: string, params: DetectParams) =>
    request<DetectResult>('/api/detect', { method: 'POST', body: detectForm(params, { sample }) }),
  detectFile: (file: File, params: DetectParams) =>
    request<DetectResult>('/api/detect', { method: 'POST', body: detectForm(params, { file }) }),

  detections: (limit = 20) => request<{ items: HistoryItem[] }>(`/api/detections?limit=${limit}`),

  datasetSummary: () => request<DatasetSummary>('/api/dataset/summary'),
  gallery: (page = 1, pageSize = 12, classId?: number) =>
    request<{ items: GalleryItem[]; total: number; page: number; page_size: number }>(
      `/api/dataset/gallery?page=${page}&page_size=${pageSize}${classId !== undefined ? `&class_id=${classId}` : ''}`,
    ),

  tasks: (status?: string) =>
    request<{ items: TaskItem[] }>(`/api/tasks${status ? `?status=${status}` : ''}`),
  createTask: (payload: {
    name: string; area: string; drone: string; altitude: number; cover_km2: number
    assignee?: string; priority?: string
  }) =>
    request<TaskItem>('/api/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  setTaskStatus: (id: string, status: string, reviewer = '', review_note = '') =>
    request<TaskItem>(`/api/tasks/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, reviewer, review_note }),
    }),
  updateTask: (id: string, fields: Record<string, unknown>) =>
    request<TaskItem>(`/api/tasks/${id}`, { method: 'PUT', body: JSON.stringify(fields) }),
  deleteTask: (id: string) =>
    request<{ deleted: boolean }>(`/api/tasks/${id}`, { method: 'DELETE' }),

  trainingJobs: () => request<{ items: TrainingJob[] }>('/api/training/jobs'),
  trainingJob: (id: string) => request<TrainingJob>(`/api/training/jobs/${id}`),
  startTraining: (payload: { epochs: number; imgsz: number; batch: number; base_model: string; note: string }) =>
    request<TrainingJob>('/api/training/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  stopTraining: (id: string) => request<TrainingJob>(`/api/training/jobs/${id}/stop`, { method: 'POST' }),
  resumeTraining: (id: string) => request<TrainingJob>(`/api/training/jobs/${id}/resume`, { method: 'POST' }),
  trainingMetrics: (id: string) => request<{ items: TrainMetric[]; checkpoints: Checkpoint[] }>(`/api/training/jobs/${id}/metrics`),
  trainingLog: (id: string, lines = 200) => request<{ lines: string[] }>(`/api/training/jobs/${id}/log?lines=${lines}`),
}

export function mediaUrl(path: string): string {
  return path.startsWith('http') ? path : path
}
