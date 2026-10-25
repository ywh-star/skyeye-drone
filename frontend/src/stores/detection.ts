import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'
import { api } from '@/api/client'
import type { DetectResult, HistoryItem, SampleDetail, SampleItem } from '@/types'

export interface DetectParams {
  conf: number
  iou: number
  imgsz: number
  modelId: string
}

export const useDetectionStore = defineStore('detection', () => {
  const samples = ref<SampleItem[]>([])
  const currentSample = ref<SampleDetail | null>(null)
  const selectedId = ref('')
  const result = ref<DetectResult | null>(null)
  const history = ref<HistoryItem[]>([])
  const loading = ref(false)
  const error = ref('')
  const activeLabels = ref<string[]>([])
  const showGroundTruth = ref(false)
  const viewMode = ref<'2d' | '3d'>('2d')
  const lastUploadName = ref('')

  const params = reactive<DetectParams>({ conf: 0.25, iou: 0.45, imgsz: 960, modelId: 'coco-yolov8n' })

  const classOptions = computed(() => {
    const map = new Map<string, { label: string; color: string; count: number }>()
    for (const det of result.value?.detections ?? []) {
      const item = map.get(det.label_cn) ?? { label: det.label_cn, color: det.color, count: 0 }
      item.count += 1
      map.set(det.label_cn, item)
    }
    return [...map.values()].sort((a, b) => b.count - a.count)
  })

  const filteredDetections = computed(() => {
    const list = result.value?.detections ?? []
    return activeLabels.value.length ? list.filter((d) => activeLabels.value.includes(d.label_cn)) : list
  })

  const filteredTotal = computed(() => filteredDetections.value.length)

  const avgConfidence = computed(() => {
    const list = filteredDetections.value
    return list.length ? list.reduce((s, d) => s + d.conf, 0) / list.length : 0
  })

  const maxConfidence = computed(() =>
    filteredDetections.value.reduce((m, d) => Math.max(m, d.conf), 0),
  )

  async function loadSamples() {
    samples.value = (await api.samples(24)).items
    if (!selectedId.value && samples.value.length) {
      await selectSample(samples.value[0].id)
    }
  }

  async function selectSample(id: string) {
    selectedId.value = id
    currentSample.value = await api.sample(id)
    activeLabels.value = []
    lastUploadName.value = ''
  }

  async function loadHistory() {
    history.value = (await api.detections(24)).items
  }

  async function runSample() {
    if (!selectedId.value) return
    await run(() => api.detectSample(selectedId.value, {
      conf: params.conf, iou: params.iou, imgsz: params.imgsz, model_id: params.modelId,
    }))
  }

  async function runFile(file: File) {
    lastUploadName.value = file.name
    await run(() => api.detectFile(file, {
      conf: params.conf, iou: params.iou, imgsz: params.imgsz, model_id: params.modelId,
    }))
  }

  async function run(task: () => Promise<DetectResult>) {
    loading.value = true
    error.value = ''
    try {
      result.value = await task()
      activeLabels.value = []
      await loadHistory()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '检测失败'
    } finally {
      loading.value = false
    }
  }

  function toggleLabel(label: string) {
    activeLabels.value = activeLabels.value.includes(label)
      ? activeLabels.value.filter((l) => l !== label)
      : [...activeLabels.value, label]
  }

  function reset() {
    result.value = null
    activeLabels.value = []
    error.value = ''
  }

  return {
    samples, currentSample, selectedId, result, history, loading, error, activeLabels,
    showGroundTruth, viewMode, params, lastUploadName, classOptions, filteredDetections,
    filteredTotal, avgConfidence, maxConfidence,
    loadSamples, selectSample, loadHistory, runSample, runFile, run, toggleLabel, reset,
  }
})
