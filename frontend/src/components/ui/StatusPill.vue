<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ status: string; dot?: boolean }>(), { dot: true })

const labels: Record<string, string> = {
  running: '执行中',
  review: '待复核',
  queued: '排队中',
  done: '已归档',
  finished: '训练完成',
  stopped: '已中断',
  failed: '失败',
  stopping: '中断中',
}

const text = computed(() => labels[props.status] ?? props.status)
</script>

<template>
  <span class="pill" :class="status">
    <span v-if="dot" class="dot" />
    {{ text }}
  </span>
</template>

<style scoped>
.pill .dot { width: 5px; height: 5px; background: currentColor; box-shadow: 0 0 8px currentColor; }
.pill.running .dot, .pill.finished .dot { animation: breathe 1.8s ease-in-out infinite; }
</style>
