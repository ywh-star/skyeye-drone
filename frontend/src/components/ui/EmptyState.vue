<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
  icon?: string
}>()
</script>

<template>
  <div class="empty">
    <div class="empty-icon">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.2">
        <circle cx="12" cy="12" r="8" stroke-dasharray="3 4" />
        <path d="M12 8v5m0 3h.01" stroke-linecap="round" />
      </svg>
    </div>
    <p class="empty-title">{{ title ?? '暂无数据' }}</p>
    <p v-if="description" class="tiny dim">{{ description }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.empty-icon { color: var(--muted); opacity: 0.7; margin-bottom: 4px; }
.empty-title { font-size: 13px; color: var(--text-dim); }
</style>
