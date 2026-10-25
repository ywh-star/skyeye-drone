import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { TrainMetric, TrainingJob } from '@/types'

export const useTrainingStore = defineStore('training', () => {
  const jobs = ref<TrainingJob[]>([])
  const selectedId = ref('')
  const metrics = ref<TrainMetric[]>([])
  const logs = ref<string[]>([])
  const loading = ref(false)
  const error = ref('')
  const streaming = ref(false)
  let source: EventSource | null = null

  const selected = computed(() => jobs.value.find((j) => j.id === selectedId.value) ?? null)
  const progress = computed(() => {
    const job = selected.value
    if (!job) return 0
    const total = job.total_epochs || job.config.epochs || 1
    return Math.min(100, Math.round((job.current_epoch / total) * 100))
  })
  const activeJobs = computed(() => jobs.value.filter((j) => j.status === 'running' || j.status === 'queued'))

  function upsert(job: TrainingJob) {
    const idx = jobs.value.findIndex((j) => j.id === job.id)
    if (idx >= 0) jobs.value[idx] = job
    else jobs.value.unshift(job)
  }

  async function loadJobs() {
    loading.value = true
    try {
      jobs.value = (await api.trainingJobs()).items
      if (!selectedId.value && jobs.value.length) await selectJob(jobs.value[0].id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载训练任务失败'
    } finally {
      loading.value = false
    }
  }

  async function selectJob(id: string) {
    disconnect()
    selectedId.value = id
    logs.value = []
    metrics.value = []
    try {
      const [job, metricData, logData] = await Promise.all([
        api.trainingJob(id), api.trainingMetrics(id), api.trainingLog(id, 300),
      ])
      upsert(job)
      metrics.value = metricData.items
      logs.value = logData.lines
      connect()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载任务详情失败'
    }
  }

  function connect() {
    disconnect()
    if (!selectedId.value) return
    const url = `/api/training/jobs/${selectedId.value}/stream`
    source = new EventSource(url)
    streaming.value = true

    source.addEventListener('log', (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as { lines: string[] }
      logs.value = [...logs.value, ...payload.lines].slice(-600)
    })
    source.addEventListener('metrics', (event) => {
      metrics.value = JSON.parse((event as MessageEvent).data) as TrainMetric[]
    })
    source.addEventListener('state', (event) => {
      upsert(JSON.parse((event as MessageEvent).data) as TrainingJob)
    })
    source.addEventListener('done', (event) => {
      upsert(JSON.parse((event as MessageEvent).data) as TrainingJob)
      disconnect()
    })
    source.onerror = () => {
      if (source?.readyState === EventSource.CLOSED) streaming.value = false
    }
  }

  function disconnect() {
    source?.close()
    source = null
    streaming.value = false
  }

  async function refresh() {
    if (!selectedId.value) return
    const job = await api.trainingJob(selectedId.value)
    upsert(job)
  }

  async function start(payload: { epochs: number; imgsz: number; batch: number; base_model: string; note: string }) {
    const job = await api.startTraining(payload)
    upsert(job)
    await selectJob(job.id)
    return job
  }

  async function stop() {
    if (!selectedId.value) return
    upsert(await api.stopTraining(selectedId.value))
  }

  async function resume() {
    if (!selectedId.value) return null
    const job = await api.resumeTraining(selectedId.value)
    upsert(job)
    connect()
    return job
  }

  return {
    jobs, selectedId, metrics, logs, loading, error, streaming, selected,
    progress, activeJobs, loadJobs, selectJob, start, stop, resume, refresh, disconnect,
  }
})
