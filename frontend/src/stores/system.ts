import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { ModelInfo, Overview, SystemInfo } from '@/types'

export const useSystemStore = defineStore('system', () => {
  const info = ref<SystemInfo | null>(null)
  const overview = ref<Overview | null>(null)
  const loading = ref(false)
  const error = ref('')
  const lastSync = ref('')

  const models = computed<ModelInfo[]>(() => info.value?.models ?? [])
  const ready = computed(() => Boolean(info.value?.dataset.ready))

  async function loadInfo() {
    info.value = await api.info()
  }

  async function loadOverview() {
    overview.value = await api.overview()
  }

  async function refresh() {
    loading.value = true
    error.value = ''
    try {
      await Promise.all([loadInfo(), loadOverview()])
      lastSync.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    } catch (err) {
      error.value = err instanceof Error ? err.message : '无法连接后端服务'
    } finally {
      loading.value = false
    }
  }

  return { info, overview, loading, error, lastSync, models, ready, refresh, loadInfo, loadOverview }
})
