<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DetectionItem } from '@/types'

const props = withDefaults(defineProps<{
  imageUrl: string
  detections: DetectionItem[]
  groundTruth?: DetectionItem[]
  showGroundTruth?: boolean
  loading?: boolean
}>(), { groundTruth: () => [], showGroundTruth: false, loading: false })

const emit = defineEmits<{ (e: 'hover', id: string | null): void }>()

const loaded = ref(false)
const hovered = ref('')
const natural = ref({ w: 0, h: 0 })

const gtVisible = computed(() => props.showGroundTruth && props.groundTruth.length > 0)

function boxStyle(det: DetectionItem) {
  return {
    left: `${det.x * 100}%`,
    top: `${det.y * 100}%`,
    width: `${det.w * 100}%`,
    height: `${det.h * 100}%`,
    '--box-color': det.color,
  }
}

function onLoad(event: Event) {
  const image = event.target as HTMLImageElement
  natural.value = { w: image.naturalWidth, h: image.naturalHeight }
  loaded.value = true
}

function enter(det: DetectionItem) {
  hovered.value = det.label_cn
  emit('hover', det.id)
}

function leave() {
  hovered.value = ''
  emit('hover', null)
}
</script>

<template>
  <div class="viewer" :class="{ loading }">
    <img
      :src="imageUrl"
      alt="航拍影像"
      class="viewer-img"
      :class="{ ready: loaded }"
      @load="onLoad"
    />

    <div v-if="loaded" class="boxes">
      <div
        v-for="det in detections"
        :key="det.id"
        class="box"
        :style="boxStyle(det)"
        @mouseenter="enter(det)"
        @mouseleave="leave"
      >
        <span class="box-corner tl" />
        <span class="box-corner tr" />
        <span class="box-corner bl" />
        <span class="box-corner br" />
        <span class="box-tag" :style="{ background: det.color }">
          {{ det.label_cn }} {{ (det.conf * 100).toFixed(0) }}%
        </span>
      </div>

      <div
        v-for="(det, index) in gtVisible ? groundTruth : []"
        :key="`gt-${index}`"
        class="box gt"
        :style="boxStyle(det)"
      >
        <span class="gt-tag">GT · {{ det.label_cn }}</span>
      </div>
    </div>

    <div v-if="!loaded" class="viewer-placeholder">
      <span class="spinner" />
      <span class="tiny dim">正在载入航拍影像…</span>
    </div>

    <div v-if="loading" class="viewer-scan">
      <div class="scan-line" />
      <div class="scan-label">
        <span class="dot cyan pulse" />
        YOLOv8 推理中 · 正在解算目标框
      </div>
    </div>

    <div class="viewer-hud">
      <span class="mono">{{ natural.w }} × {{ natural.h }}</span>
      <span class="hud-sep">|</span>
      <span>{{ detections.length }} 个可视化目标</span>
      <span v-if="hovered" class="hud-hover">{{ hovered }}</span>
    </div>
  </div>
</template>

<style scoped>
.viewer {
  position: relative;
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 40%, rgba(18, 48, 70, 0.5), rgba(3, 8, 14, 0.95)),
    #04090f;
  border: 1px solid var(--line);
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
}
.viewer-img { width: 100%; height: 100%; object-fit: contain; opacity: 0; transition: opacity 0.3s; }
.viewer-img.ready { opacity: 1; }
.boxes { position: absolute; inset: 0; }
.box {
  position: absolute;
  border: 1.5px solid var(--box-color);
  border-radius: 3px;
  pointer-events: auto;
  cursor: crosshair;
  box-shadow: 0 0 12px color-mix(in srgb, var(--box-color) 35%, transparent);
  transition: background 0.15s, box-shadow 0.15s;
}
.box:hover { background: color-mix(in srgb, var(--box-color) 14%, transparent); box-shadow: 0 0 20px color-mix(in srgb, var(--box-color) 55%, transparent); }
.box-corner { position: absolute; width: 6px; height: 6px; border: 1.5px solid var(--box-color); background: rgba(4, 9, 15, 0.8); }
.box-corner.tl { left: -2px; top: -2px; border-right: 0; border-bottom: 0; }
.box-corner.tr { right: -2px; top: -2px; border-left: 0; border-bottom: 0; }
.box-corner.bl { left: -2px; bottom: -2px; border-right: 0; border-top: 0; }
.box-corner.br { right: -2px; bottom: -2px; border-left: 0; border-top: 0; }
.box-tag {
  position: absolute;
  left: -1px;
  top: -18px;
  font-size: 9px;
  line-height: 15px;
  padding: 0 5px;
  border-radius: 3px 3px 3px 0;
  color: #05121a;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
.box.gt { border: 1.5px dashed rgba(163, 230, 53, 0.85); box-shadow: none; pointer-events: none; }
.gt-tag {
  position: absolute; left: -1px; bottom: -17px;
  font-size: 8px; line-height: 14px; padding: 0 4px; border-radius: 3px;
  background: rgba(163, 230, 53, 0.9); color: #0b1403; font-weight: 700;
}
.viewer-placeholder { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
.viewer-scan { position: absolute; inset: 0; background: rgba(3, 10, 17, 0.45); overflow: hidden; }
.scan-line {
  position: absolute; left: 0; right: 0; height: 30%;
  background: linear-gradient(180deg, transparent, rgba(34, 211, 238, 0.28), transparent);
  animation: sweep 2.4s linear infinite;
}
.scan-label {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-radius: 99px;
  background: rgba(4, 12, 20, 0.85); border: 1px solid rgba(34, 211, 238, 0.35);
  font-size: 11px; color: var(--cyan);
  white-space: nowrap;
}
.viewer-hud {
  position: absolute; left: 10px; top: 10px;
  display: flex; align-items: center; gap: 7px;
  padding: 4px 9px; border-radius: 6px;
  background: rgba(3, 9, 16, 0.7); border: 1px solid var(--line);
  font-size: 10px; color: var(--text-dim);
  backdrop-filter: blur(8px);
}
.hud-sep { color: #32495e; }
.hud-hover { color: var(--cyan); border-left: 1px solid var(--line); padding-left: 7px; }
</style>
