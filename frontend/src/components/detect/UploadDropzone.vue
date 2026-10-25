<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{ busy?: boolean; compact?: boolean }>(), { busy: false, compact: false })
const emit = defineEmits<{
  (e: 'file', file: File): void
  (e: 'error', message: string): void
}>()

const input = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

function pick() {
  input.value?.click()
}

function handle(file: File | undefined) {
  if (!file || props.busy) return
  if (!/\.(jpe?g|png|webp|bmp)$/i.test(file.name)) {
    emit('error', '仅支持 jpg / png / webp / bmp 格式')
    return
  }
  if (file.size > 25 * 1024 * 1024) {
    emit('error', '图片不能超过 25MB')
    return
  }
  emit('file', file)
}

function onChange(event: Event) {
  const target = event.target as HTMLInputElement
  handle(target.files?.[0])
  target.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  handle(event.dataTransfer?.files?.[0])
}
</script>

<template>
  <div
    class="dropzone"
    :class="{ dragging, compact, busy }"
    role="button"
    tabindex="0"
    @click="pick"
    @keydown.enter="pick"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <input ref="input" type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" hidden @change="onChange" />
    <span class="drop-icon">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.4">
        <path d="M12 16V4m0 0 4 4m-4-4L8 8" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke-linecap="round" />
      </svg>
    </span>
    <div class="drop-text">
      <strong>{{ busy ? '正在推理…' : '拖入航拍影像或点击上传' }}</strong>
      <span class="tiny dim">JPG / PNG / WEBP · 单张不超过 25MB</span>
    </div>
    <span v-if="busy" class="spinner" />
  </div>
</template>

<style scoped>
.dropzone {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(120, 190, 235, 0.28);
  background: rgba(255, 255, 255, 0.018);
  cursor: pointer;
  transition: all 0.2s ease;
}
.dropzone:hover, .dropzone.dragging {
  border-color: rgba(34, 211, 238, 0.6);
  background: rgba(34, 211, 238, 0.06);
}
.dropzone.compact { padding: 10px 12px; }
.drop-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: grid; place-items: center;
  color: var(--cyan); background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.28);
  flex-shrink: 0;
}
.drop-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.drop-text strong { font-size: 12px; font-weight: 550; color: var(--text-dim); }
</style>
