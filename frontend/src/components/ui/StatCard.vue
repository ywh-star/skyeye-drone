<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: number | string
  unit?: string
  accent?: 'cyan' | 'lime' | 'amber' | 'pink' | 'violet'
  delta?: string
  trend?: number[]
  hint?: string
}>(), { unit: '', accent: 'cyan', delta: '', trend: () => [], hint: '' })

const emit = defineEmits<{ (e: 'select'): void }>()

const bars = computed(() => {
  const data = props.trend.length ? props.trend : [4, 6, 5, 8, 7, 10, 9, 12]
  const max = Math.max(...data, 1)
  return data.slice(-12).map((v) => Math.max(8, Math.round((v / max) * 100)))
})
</script>

<template>
  <button class="stat-card panel" :class="accent" type="button" @click="emit('select')">
    <div class="stat-top">
      <span class="stat-label">{{ label }}</span>
      <span class="stat-star">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M12 3v18M3 12h18" stroke-linecap="round" />
        </svg>
      </span>
    </div>
    <div class="stat-main">
      <span class="stat-value">{{ value }}<small v-if="unit">{{ unit }}</small></span>
      <span v-if="delta" class="stat-delta up">{{ delta }}</span>
    </div>
    <div class="stat-foot">
      <div class="spark">
        <i v-for="(bar, index) in bars" :key="index" :style="{ height: `${bar}%` }" />
      </div>
      <span v-if="hint" class="tiny dim">{{ hint }}</span>
    </div>
    <span class="stat-edge" />
  </button>
</template>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 17px;
  text-align: left;
  border-radius: var(--radius-lg);
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}
.stat-card:hover { transform: translateY(-2px); border-color: var(--line-strong); box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35); }

.stat-top { display: flex; align-items: center; justify-content: space-between; }
.stat-star { color: var(--muted); opacity: 0.6; }

.stat-main { display: flex; align-items: baseline; gap: 8px; }
.stat-value { font-family: var(--font-num); font-size: 30px; font-weight: 600; letter-spacing: 0.02em; line-height: 1.1; }
.stat-value small { font-size: 13px; color: var(--muted); margin-left: 3px; font-family: var(--font-ui); }

.stat-foot { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; }

.spark { display: flex; align-items: flex-end; gap: 3px; height: 26px; width: 96px; }
.spark i { flex: 1; border-radius: 2px 2px 0 0; background: currentColor; opacity: 0.35; transition: height 0.6s cubic-bezier(0.22, 1, 0.36, 1); }
.spark i:nth-child(3n) { opacity: 0.75; }

.cyan { color: var(--cyan); }
.lime { color: var(--lime); }
.amber { color: var(--amber); }
.pink { color: var(--pink); }
.violet { color: var(--violet); }

.stat-card .stat-label, .stat-card .stat-value, .stat-card .stat-delta { color: var(--text); }
.stat-card .stat-label { color: var(--muted); }
.stat-card .stat-delta { color: currentColor; }

.stat-edge {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid currentColor;
  opacity: 0.14;
}

.stat-card.cyan { --glow: rgba(34, 211, 238, 0.18); }
.stat-card.cyan::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 44%;
  height: 2px;
  background: linear-gradient(90deg, var(--cyan), transparent);
  opacity: 0.8;
}
.stat-card.lime::after, .stat-card.amber::after, .stat-card.pink::after, .stat-card.violet::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 44%;
  height: 2px;
  background: linear-gradient(90deg, currentColor, transparent);
  opacity: 0.7;
}
</style>
