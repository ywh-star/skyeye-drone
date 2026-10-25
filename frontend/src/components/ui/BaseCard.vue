<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  subtitle?: string
  padded?: boolean
  glow?: boolean
}>(), { title: '', subtitle: '', padded: true, glow: false })
</script>

<template>
  <section class="panel base-card" :class="{ glow }">
    <header v-if="title || $slots.header || $slots.actions" class="panel-head">
      <slot name="header">
        <div>
          <h3 class="panel-title">{{ title }}</h3>
          <p v-if="subtitle" class="card-sub">{{ subtitle }}</p>
        </div>
      </slot>
      <div v-if="$slots.actions" class="card-actions">
        <slot name="actions" />
      </div>
    </header>

    <div class="panel-body" :class="{ tight: !padded }">
      <slot />
    </div>

    <footer v-if="$slots.footer" class="panel-foot">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.base-card { display: flex; flex-direction: column; }
.base-card.glow { border-color: rgba(34, 211, 238, 0.28); box-shadow: 0 0 34px rgba(34, 211, 238, 0.08); }
.base-card :deep(.panel-body) { flex: 1; }
.card-sub { font-size: 11px; color: var(--muted); margin-top: 3px; }
.card-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
</style>
