<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import RingGauge from '@/components/ui/RingGauge.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { useDetectionStore } from '@/stores/detection'
import { useSystemStore } from '@/stores/system'
import { useTaskStore } from '@/stores/tasks'
import type { ReplayMarker } from '@/types'

// 异步组件：Three.js 航迹回放场景按需加载
const FlightReplayScene = defineAsyncComponent(() => import('@/components/three/FlightReplayScene.vue'))

const tasks = useTaskStore()
const detection = useDetectionStore()
const system = useSystemStore()

const playing = ref(false)
const speed = ref(1)
const cameraMode = ref<'free' | 'follow' | 'top'>('free')
const progress = ref(0)
const telemetry = ref({ altitude: 0, speed: 0, heading: 0, progress: 0 })
const selectedTaskId = ref('')

const markers = computed<ReplayMarker[]>(() => {
  const dets = detection.result?.detections ?? detection.history[0]?.payload?.detections ?? []
  const groups = new Map<string, { label: string; color: string; count: number; sx: number; sz: number }>()
  for (const det of dets) {
    const item = groups.get(det.label_cn) ?? { label: det.label_cn, color: det.color, count: 0, sx: 0, sz: 0 }
    item.count += 1
    item.sx += det.x + det.w / 2
    item.sz += det.y + det.h / 2
    groups.set(det.label_cn, item)
  }
  const list = [...groups.values()].sort((a, b) => b.count - a.count).slice(0, 8)
  const total = list.length || 1
  return list.map((item, index) => ({
    id: `marker-${item.label}`,
    label: item.label,
    color: item.color,
    count: item.count,
    x: (item.sx / item.count - 0.5) * 68,
    z: (item.sz / item.count - 0.5) * 68,
    time: (index + 1) / (total + 1),
  }))
})

const selectedTask = computed(() =>
  tasks.items.find((t) => t.id === selectedTaskId.value) ?? tasks.items[0] ?? null,
)

const markerSource = computed(() => {
  if (detection.result) return `检测批次 ${detection.result.id}`
  if (detection.history[0]) return `历史批次 ${detection.history[0].created_at.slice(5, 16)}`
  return '暂无目标数据'
})

const slider = computed({
  get: () => Math.round(progress.value * 1000),
  set: (value: number) => { progress.value = value / 1000 },
})

function seekMarker(time: number) {
  playing.value = false
  progress.value = time
}

function togglePlay() {
  playing.value = !playing.value
}

onMounted(async () => {
  await Promise.all([tasks.load(), detection.loadHistory(), system.info ? Promise.resolve() : system.refresh()])
  const running = tasks.items.find((t) => t.status === 'running')
  selectedTaskId.value = running?.id ?? tasks.items[0]?.id ?? ''
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1 class="page-title">三维航迹回放</h1>
        <p class="page-sub">Three.js 地形重建 · 飞行航线 · 目标落点态势</p>
      </div>
      <div class="row">
        <span class="chip cyan">WebGL 场景</span>
        <span class="chip mono">{{ markers.length }} 类目标落点</span>
        <button class="btn btn-sm" @click="playing = !playing">{{ playing ? '暂停回放' : '开始回放' }}</button>
      </div>
    </div>

    <div class="replay-grid">
      <BaseCard class="scene-card" :padded="false">
        <template #header>
          <div class="row-between scene-head">
            <div>
              <h3 class="panel-title">航迹态势 · {{ selectedTask?.area ?? '未选择空域' }}</h3>
              <p class="tiny dim">机型 {{ selectedTask?.drone ?? '—' }} · 规划高度 {{ selectedTask?.altitude ?? 0 }}m · 数据源 {{ markerSource }}</p>
            </div>
            <div class="row">
              <StatusPill :status="selectedTask?.status ?? 'queued'" />
              <span class="chip mono">{{ (progress * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </template>

        <div class="scene-wrap">
          <FlightReplayScene
            v-model:progress="progress"
            :markers="markers"
            :playing="playing"
            :speed="speed"
            :camera-mode="cameraMode"
            @telemetry="telemetry = $event"
          />

          <div class="hud">
            <div class="hud-item">
              <span class="upper">ALT</span>
              <b class="mono">{{ telemetry.altitude }}<small>m</small></b>
            </div>
            <div class="hud-item">
              <span class="upper">SPD</span>
              <b class="mono">{{ telemetry.speed }}<small>m/s</small></b>
            </div>
            <div class="hud-item">
              <span class="upper">HDG</span>
              <b class="mono">{{ telemetry.heading }}<small>°</small></b>
            </div>
            <div class="hud-item">
              <span class="upper">FRAME</span>
              <b class="mono">{{ telemetry.progress }}<small>%</small></b>
            </div>
          </div>

          <div class="scene-corner top-left" />
          <div class="scene-corner top-right" />
          <div class="scene-corner bottom-left" />
          <div class="scene-corner bottom-right" />

          <div v-if="!markers.length" class="scene-empty">
            <EmptyState title="尚无目标落点" description="先在检测工作台完成一次检测，目标会自动映射到三维航迹" />
            <RouterLink to="/detect" class="btn btn-primary btn-sm">前往检测</RouterLink>
          </div>
        </div>

        <div class="timeline">
          <button class="btn btn-icon play" @click="togglePlay" :aria-label="playing ? '暂停' : '播放'">
            <span v-if="playing">❚❚</span>
            <span v-else>▶</span>
          </button>
          <div class="time-rail">
            <input v-model.number="slider" type="range" min="0" max="1000" step="1" class="range timeline-range" :style="{ '--p': `${progress * 100}%` }" />
            <div class="timeline-marks">
              <span v-for="marker in markers" :key="marker.id" :style="{ left: `${marker.time * 100}%`, background: marker.color }" />
            </div>
          </div>
          <span class="mono time-label">{{ (progress * 100).toFixed(0) }}%</span>
          <div class="segmented speed">
            <button v-for="value in [0.5, 1, 2, 4]" :key="value" :class="{ active: speed === value }" @click="speed = value">{{ value }}x</button>
          </div>
        </div>
      </BaseCard>

      <div class="side-col">
        <BaseCard title="任务摘要" subtitle="当前选中飞行任务">
          <template #actions>
            <select v-model="selectedTaskId" class="select select-sm">
              <option v-for="task in tasks.items" :key="task.id" :value="task.id">{{ task.code }} · {{ task.name }}</option>
            </select>
          </template>
          <div class="mission">
            <RingGauge :value="progress * 100" :size="104" label="回放进度" sublabel="Flight Progress" />
            <div class="mission-meta">
              <div><span>任务编号</span><b class="mono">{{ selectedTask?.code ?? '—' }}</b></div>
              <div><span>覆盖面积</span><b class="mono">{{ selectedTask?.cover_km2 ?? 0 }} km²</b></div>
              <div><span>检出目标</span><b class="mono">{{ selectedTask?.detections ?? 0 }}</b></div>
              <div><span>飞行时长</span><b class="mono">{{ selectedTask?.duration_min ?? 0 }} min</b></div>
            </div>
          </div>
          <div class="progress"><span :style="{ width: `${selectedTask?.progress ?? 0}%` }" /></div>
          <div class="row-between mission-foot">
            <span class="tiny dim">数据库任务进度</span>
            <span class="tiny mono">{{ selectedTask?.progress ?? 0 }}%</span>
          </div>
        </BaseCard>

        <BaseCard title="相机与视角" subtitle="Three.js 相机模式">
          <div class="segmented camera">
            <button :class="{ active: cameraMode === 'free' }" @click="cameraMode = 'free'">自由环绕</button>
            <button :class="{ active: cameraMode === 'follow' }" @click="cameraMode = 'follow'">跟随飞行</button>
            <button :class="{ active: cameraMode === 'top' }" @click="cameraMode = 'top'">正俯视</button>
          </div>
          <div class="camera-hint muted-box">
            <p class="tiny dim">跟随模式会沿航线切线方向平滑追踪无人机；正俯视用于查看路网与目标分布。</p>
          </div>
        </BaseCard>

        <BaseCard title="目标落点" subtitle="点击定位到航迹时间点">
          <div class="marker-list">
            <button
              v-for="marker in markers"
              :key="marker.id"
              class="marker-row"
              type="button"
              @click="seekMarker(marker.time)"
            >
              <span class="marker-dot" :style="{ background: marker.color, boxShadow: `0 0 10px ${marker.color}` }" />
              <span class="marker-label">{{ marker.label }}</span>
              <span class="marker-count mono">{{ marker.count }}</span>
              <span class="tiny mono dim">{{ (marker.time * 100).toFixed(0) }}%</span>
            </button>
            <EmptyState v-if="!markers.length" title="暂无落点" description="完成检测后自动生成" />
          </div>
        </BaseCard>
      </div>
    </div>
  </div>
</template>

<style scoped>
.replay-grid { display: grid; grid-template-columns: minmax(0, 1fr) 350px; gap: 16px; align-items: start; }
.scene-card { overflow: hidden; }
.scene-head { width: 100%; }
.scene-wrap { position: relative; height: 540px; }
.hud {
  position: absolute; left: 14px; top: 14px;
  display: flex; gap: 8px;
  pointer-events: none;
}
.hud-item {
  display: flex; flex-direction: column; gap: 1px;
  padding: 6px 11px; border-radius: 8px;
  background: rgba(4, 11, 19, 0.78);
  border: 1px solid var(--line);
  backdrop-filter: blur(8px);
  min-width: 66px;
}
.hud-item b { font-size: 16px; font-weight: 600; color: var(--cyan); line-height: 1.2; }
.hud-item b small { font-size: 9px; color: var(--muted); margin-left: 2px; font-family: var(--font-ui); }
.hud-item .upper { font-size: 8px; }

.scene-corner { position: absolute; width: 22px; height: 22px; border-color: rgba(34, 211, 238, 0.4); border-style: solid; pointer-events: none; }
.scene-corner.top-left { top: 10px; left: 10px; border-width: 1px 0 0 1px; }
.scene-corner.top-right { top: 10px; right: 10px; border-width: 1px 1px 0 0; }
.scene-corner.bottom-left { bottom: 10px; left: 10px; border-width: 0 0 1px 1px; }
.scene-corner.bottom-right { bottom: 10px; right: 10px; border-width: 0 1px 1px 0; }

.scene-empty {
  position: absolute; left: 50%; bottom: 26px; transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 14px 18px; border-radius: 14px;
  background: rgba(4, 11, 19, 0.85); border: 1px solid rgba(34, 211, 238, 0.25);
  backdrop-filter: blur(10px);
}

.timeline {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px;
  border-top: 1px solid var(--line);
  background: rgba(4, 11, 19, 0.6);
}
.play { width: 34px; height: 34px; flex-shrink: 0; color: var(--cyan); font-size: 11px; }
.time-rail { position: relative; flex: 1; display: flex; align-items: center; }
.timeline-range { width: 100%; }
.timeline-marks { position: absolute; left: 0; right: 0; top: 12px; height: 8px; pointer-events: none; }
.timeline-marks span { position: absolute; top: 0; width: 2px; height: 8px; border-radius: 2px; transform: translateX(-50%); opacity: 0.9; }
.time-label { font-size: 12px; color: var(--text-dim); width: 38px; text-align: right; }
.speed { flex-shrink: 0; }
.speed button { padding: 4px 8px; font-family: var(--font-num); }

.side-col { display: flex; flex-direction: column; gap: 16px; }
.select-sm { height: 30px; font-size: 11px; max-width: 190px; }

.mission { display: flex; align-items: center; gap: 16px; }
.mission-meta { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.mission-meta div { display: flex; justify-content: space-between; gap: 10px; font-size: 11px; color: var(--muted); }
.mission-meta b { color: var(--text-dim); font-weight: 500; }
.mission-foot { margin-top: 6px; }

.camera { width: 100%; }
.camera button { flex: 1; }
.camera-hint { margin-top: 12px; padding: 10px 12px; }
.camera-hint p { line-height: 1.6; }

.marker-list { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
.marker-row {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--line); background: rgba(255, 255, 255, 0.02);
  font-size: 12px; color: var(--text-dim);
  transition: all 0.16s;
}
.marker-row:hover { border-color: var(--line-strong); background: rgba(34, 211, 238, 0.06); }
.marker-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.marker-label { flex: 1; text-align: left; }
.marker-count { color: var(--text); font-size: 12px; }

@media (max-width: 1200px) {
  .replay-grid { grid-template-columns: 1fr; }
  .scene-wrap { height: 460px; }
}
</style>
