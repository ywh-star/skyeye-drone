import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'info'
  message: string
}

let seed = 0

export const useUiStore = defineStore('ui', () => {
  const toasts = ref<Toast[]>([])
  const search = ref('')

  function push(message: string, type: Toast['type'] = 'success') {
    const id = ++seed
    toasts.value = [...toasts.value, { id, type, message }]
    window.setTimeout(() => dismiss(id), 3600)
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, search, push, dismiss }
})
