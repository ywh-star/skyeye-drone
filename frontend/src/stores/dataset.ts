import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { DatasetSummary, GalleryItem } from '@/types'

export const useDatasetStore = defineStore('dataset', () => {
  const summary = ref<DatasetSummary | null>(null)
  const items = ref<GalleryItem[]>([])
  const page = ref(1)
  const pageSize = 12
  const total = ref(0)
  const classId = ref<number | undefined>(undefined)
  const loading = ref(false)

  const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
  const topClasses = computed(() =>
    [...(summary.value?.classes ?? [])].sort((a, b) => b.count - a.count),
  )

  async function loadSummary() {
    summary.value = await api.datasetSummary()
  }

  async function loadGallery() {
    loading.value = true
    try {
      const data = await api.gallery(page.value, pageSize, classId.value)
      items.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function setFilter(id?: number) {
    classId.value = id
    page.value = 1
    await loadGallery()
  }

  async function setPage(value: number) {
    page.value = Math.min(pages.value, Math.max(1, value))
    await loadGallery()
  }

  async function init() {
    await Promise.all([loadSummary(), loadGallery()])
  }

  return { summary, items, page, pageSize, total, classId, loading, pages, topClasses, loadSummary, loadGallery, setFilter, setPage, init }
})
