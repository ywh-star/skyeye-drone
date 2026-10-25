<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  size?: number
  stroke?: number
  color?: string
  label?: string
  sublabel?: string
}>(), { size: 108, stroke: 8, color: '#22d3ee', label: '', sublabel: '' })

const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - Math.min(100, Math.max(0, props.value)) / 100))
</script>

<template>
  <div class="gauge" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle
        :cx="size / 2" :cy="size / 2" :r="radius"
        fill="none" stroke="rgba(120,190,235,0.14)" :stroke-width="stroke"
      />
      <circle
        :cx="size / 2" :cy="size / 2" :r="radius"
        fill="none" :stroke="color" :stroke-width="stroke" stroke-linecap="round"
        :stroke-dasharray="circumference" :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
        class="gauge-ring"
      />
    </svg>
    <div class="gauge-center">
      <span class="gauge-value mono">{{ Math.round(value) }}<small>%</small></span>
      <span v-if="label" class="gauge-label">{{ label }}</span>
      <span v-if="sublabel" class="gauge-sub">{{ sublabel }}</span>
    </div>
  </div>
</template>

<style scoped>
.gauge { position: relative; flex-shrink: 0; }
.gauge svg { display: block; }
.gauge-ring { transition: stroke-dashoffset 0.9s cubic-bezier(0.22, 1, 0.36, 1); filter: drop-shadow(0 0 6px currentColor); }
.gauge-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; }
.gauge-value { font-size: 23px; font-weight: 600; color: var(--text); line-height: 1; }
.gauge-value small { font-size: 10px; color: var(--muted); margin-left: 1px; }
.gauge-label { font-size: 10px; color: var(--muted); letter-spacing: 0.06em; }
.gauge-sub { font-size: 9px; color: var(--muted); opacity: 0.7; }
</style>
