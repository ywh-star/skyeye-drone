import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { TaskItem } from '@/types'

export const useTaskStore = defineStore('tasks', () => {
  const items = ref<TaskItem[]>([])
  const loading = ref(false)

  const running = computed(() => items.value.filter((t) => t.status === 'running'))
  const queued = computed(() => items.value.filter((t) => t.status === 'queued'))
  const review = computed(() => items.value.filter((t) => t.status === 'review'))
  const done = computed(() => items.value.filter((t) => t.status === 'done'))

  const counts = computed(() => ({
    running: running.value.length,
    review: review.value.length,
    queued: queued.value.length,
    done: done.value.length,
  }))

  async function load(status?: string) {
    loading.value = true
    try {
      items.value = (await api.tasks(status)).items
    } finally {
      loading.value = false
    }
  }

  async function create(payload: {
    name: string; area: string; drone: string; altitude: number; cover_km2: number
    assignee?: string; priority?: string
  }) {
    const task = await api.createTask(payload)
    items.value = [task, ...items.value]
    return task
  }

  async function setStatus(id: string, status: string, reviewer = '', review_note = '') {
    const updated = await api.setTaskStatus(id, status, reviewer, review_note)
    const idx = items.value.findIndex((t) => t.id === id)
    if (idx >= 0) items.value[idx] = updated
    return updated
  }

  async function update(id: string, fields: Record<string, unknown>) {
    const updated = await api.updateTask(id, fields)
    const idx = items.value.findIndex((t) => t.id === id)
    if (idx >= 0) items.value[idx] = updated
    return updated
  }

  async function remove(id: string) {
    await api.deleteTask(id)
    items.value = items.value.filter((t) => t.id !== id)
  }

  return { items, loading, running, queued, review, done, counts, load, create, setStatus, update, remove }
})
