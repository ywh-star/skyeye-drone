<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DetectionCanvas from '@/components/detect/DetectionCanvas.vue'
import UploadDropzone from '@/components/detect/UploadDropzone.vue'
import { useDetectionStore } from '@/stores/detection'
import { useSystemStore } from '@/stores/system'
import { useUiStore } from '@/stores/ui'

// 异步组件：Three.js 三维复核场景按需加载
const SceneDetect3D = defineAsyncComponent(() => import('@/components/detect/SceneDetect3D.vue'))

const detection = useDetectionStore()
const system = useSystemStore()
const ui = useUiStore()

const hoveredId = ref<string | null>(null)
const viewerMode = ref<'overlay' | 'annotated'>('overlay')
const paramsOpen = ref(true)
const lastFile = ref<File | null>(null)

const activeModel = computed(() =>
  system.models.find((m) => m.id === detection.params.modelId) ?? system.models[0] ?? null,
)

const imageUrl = computed(() => {
  if (detection.result) {
    return viewerMode.value === 'annotated' ? detection.result.output_url : detection.result.image_url
  }
  return detection.currentSample?.url ?? ''
})

const gtDetections = computed(() => detection.currentSample?.gt ?? [])

const viewerTitle = computed(() => {
  if (detection.lastUploadName) return `上传影像 · ${detection.lastUploadName}`
  if (detection.currentSample) return `VisDrone · ${detection.currentSample.id}`
  return '航拍影像'
})

const hasResult = computed(() => Boolean(detection.result))

const confidenceStyle = (conf: number) => ({
  width: `${Math.round(conf * 100)}%`,
  background: conf > 0.7 ? 'linear-gradient(90deg,#22d3ee,#a3e635)' : conf > 0.4 ? 'linear-gradient(90deg,#22d3ee,#f59e0b)' : 'rgba(251,113,133,0.7)',
})

async function run() {
  if (detection.loading) return
  if (lastFile.value && !detection.selectedId) {
    await detection.runFile(lastFile.value)
  } else if (detection.selectedId) {
    await detection.runSample()
  } else {
    return
  }
  if (detection.result) {
    ui.push(`检测完成：${detection.result.total} 个目标 · ${detection.result.inference_ms}ms`)
    detection.showGroundTruth = false
  } else if (detection.error) {
    ui.push(detection.error, 'error')
  }
}

async function onUpload(file: File) {
  lastFile.value = file
  detection.reset()
  detection.selectedId = ''
  await detection.runFile(file)
  if (detection.result) ui.push(`上传影像检测完成：${detection.result.total} 个目标`)
  else if (detection.error) ui.push(detection.error, 'error')
}

async function pickSample(id: string) {
  if (detection.loading) return
  lastFile.value = null
  detection.reset()
  detection.lastUploadName = ''
  await detection.selectSample(id)
}

function exportJson() {
  if (!detection.result) return
  const blob = new Blob([JSON.stringify(detection.result, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `detection-${detection.result.id}.json`
  link.click()
  URL.revokeObjectURL(url)
  ui.push('检测结果 JSON 已导出')
}

function setParam(key: 'conf' | 'iou', event: Event) {
  detection.params[key] = Number((event.target as HTMLInputElement).value)
}

watch(() => detection.result, () => { hoveredId.value = null })

onMounted(async () => {
  if (!system.info) await system.refresh()
  await detection.loadSamples()
  await detection.loadHistory()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1 class="page-title">检测工作台</h1>
        <p class="page-sub">VisDrone 真实航拍样本 or 自选影像 · YOLOv8 推理 · 三维复核</p>
      </div>
      <div class="row">
        <span class="chip cyan mono">{{ activeModel?.name ?? 'YOLOv8n' }}</span>
        <span class="chip">设备 {{ system.info?.device ?? 'CPU' }}</span>
        <button class="btn btn-sm" :disabled="!hasResult" @click="exportJson">导出 JSON</button>
      </div>
    </div>

    <div class="workbench">
      <BaseCard class="samples-panel" title="影像来源" subtitle="真实无人机航拍样本" :padded="false">
        <div class="samples-body">
          <UploadDropzone :busy="detection.loading" compact @file="onUpload" @error="(m) => ui.push(m, 'error')" />
          <div class="samples-title">
            <span class="upper">VisDrone val · 抽样</span>
            <span class="tiny mono dim">{{ detection.samples.length }} 张</span>
          </div>
          <div class="samples-grid">
            <button
              v-for="sample in detection.samples"
              :key="sample.id"
              type="button"
              class="sample-card"
              :class="{ active: sample.id === detection.selectedId && !detection.result }"
              @click="pickSample(sample.id)"
            >
              <img :src="sample.url" :alt="sample.id" loading="lazy" />
              <span class="sample-meta">
                <b class="mono">{{ sample.gt_count }}</b>
                <i>{{ sample.scene }}</i>
              </span>
            </button>
          </div>
        </div>
        <template #footer>
          <div class="row-between">
            <span class="tiny dim">点击样本切换检测对象</span>
            <span class="tiny mono">{{ system.info?.dataset.images ?? 0 }} 张可用</span>
          </div>
        </template>
      </BaseCard>

      <BaseCard class="viewer-panel" :padded="false">
        <template #header>
          <div class="viewer-head">
            <div>
              <h3 class="panel-title">{{ viewerTitle }}</h3>
              <p class="tiny dim">{{ detection.currentSample ? `${detection.currentSample.width} × ${detection.currentSample.height} · 真值 ${detection.currentSample.gt_count} 个目标` : '用户上传影像' }}</p>
            </div>
            <div class="row">
              <div class="segmented">
                <button :class="{ active: detection.viewMode === '2d' }" @click="detection.viewMode = '2d'">2D</button>
                <button :class="{ active: detection.viewMode === '3d' }" @click="detection.viewMode = '3d'">3D</button>
              </div>
              <div v-if="detection.viewMode === '2d'" class="segmented">
                <button :class="{ active: viewerMode === 'overlay' }" @click="viewerMode = 'overlay'">交互框</button>
                <button :class="{ active: viewerMode === 'annotated' }" @click="viewerMode = 'annotated'" :disabled="!hasResult">标注图</button>
              </div>
              <label class="gt-toggle" v-if="detection.currentSample">
                <button type="button" class="switch" :class="{ on: detection.showGroundTruth }" @click="detection.showGroundTruth = !detection.showGroundTruth" />
                GT
              </label>
            </div>
          </div>
        </template>

        <div class="viewer-body">
          <DetectionCanvas
            v-if="detection.viewMode === '2d' && imageUrl"
            :image-url="imageUrl"
            :detections="viewerMode === 'overlay' ? detection.filteredDetections : []"
            :ground-truth="gtDetections"
            :show-ground-truth="detection.showGroundTruth"
            :loading="detection.loading"
            @hover="hoveredId = $event"
          />
          <SceneDetect3D
            v-else-if="detection.viewMode === '3d' && hasResult"
            :image-url="detection.result!.image_url"
            :detections="detection.filteredDetections"
            :image-w="detection.result!.width"
            :image-h="detection.result!.height"
          />
          <EmptyState
            v-else-if="detection.viewMode === '3d'"
            title="先运行一次检测"
            description="三维立体框会将 2D 检测结果拉伸到空间坐标系中"
          />
          <EmptyState v-else title="尚未选择影像" description="从左侧选择 VisDrone 样本或上传航拍图" />

          <div v-if="!hasResult && imageUrl && detection.viewMode === '2d'" class="viewer-cta">
            <button class="btn btn-primary" :disabled="detection.loading" @click="run">
              <span v-if="detection.loading" class="spinner" />
              {{ detection.loading ? '推理中…' : '运行 YOLOv8 检测' }}
            </button>
            <span class="tiny dim">当前参数：conf {{ detection.params.conf }} · iou {{ detection.params.iou }} · {{ detection.params.imgsz }}px</span>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="params-panel" title="推理参数" subtitle="实时调整并重新推理">
        <template #actions>
          <button class="btn btn-sm" @click="paramsOpen = !paramsOpen">{{ paramsOpen ? '收起' : '展开' }}</button>
        </template>

        <div v-show="paramsOpen">
          <div class="field">
            <span class="field-label">推理权重</span>
            <select v-model="detection.params.modelId" class="select">
              <option v-for="model in system.models" :key="model.id" :value="model.id">
                {{ model.name }}
              </option>
            </select>
            <span class="tiny dim">{{ activeModel?.note }}</span>
          </div>

          <div class="field">
            <span class="field-label">置信度阈值 <span class="value mono">{{ detection.params.conf.toFixed(2) }}</span></span>
            <input class="range" type="range" min="0.05" max="0.9" step="0.01" :value="detection.params.conf" :style="{ '--p': `${(detection.params.conf / 0.9) * 100}%` }" @input="setParam('conf', $event)" />
          </div>

          <div class="field">
            <span class="field-label">NMS IoU <span class="value mono">{{ detection.params.iou.toFixed(2) }}</span></span>
            <input class="range" type="range" min="0.1" max="0.9" step="0.01" :value="detection.params.iou" :style="{ '--p': `${(detection.params.iou / 0.9) * 100}%` }" @input="setParam('iou', $event)" />
          </div>

          <div class="field">
            <span class="field-label">推理分辨率</span>
            <div class="segmented imgsz">
              <button v-for="size in [640, 960, 1280]" :key="size" :class="{ active: detection.params.imgsz === size }" @click="detection.params.imgsz = size">{{ size }}</button>
            </div>
            <span class="tiny dim">分辨率越高小目标召回越好，CPU 耗时增加</span>
          </div>

          <button class="btn btn-primary btn-block" :disabled="detection.loading || !detection.selectedId && !detection.lastUploadName" @click="run">
            <span v-if="detection.loading" class="spinner" />
            {{ detection.loading ? '正在推理…' : '运行检测' }}
          </button>
          <button class="btn btn-block btn-sm reset" @click="detection.reset(); detection.showGroundTruth = false">清空结果</button>
        </div>

        <div v-if="hasResult" class="result-summary">
          <div class="summary-row">
            <span class="stat-label">检出目标</span>
            <b class="mono">{{ detection.result!.total }}</b>
          </div>
          <div class="summary-row">
            <span class="stat-label">平均置信度</span>
            <b class="mono">{{ (detection.result!.avg_conf * 100).toFixed(1) }}%</b>
          </div>
          <div class="summary-row">
            <span class="stat-label">推理耗时</span>
            <b class="mono">{{ detection.result!.inference_ms }} ms</b>
          </div>
          <div class="summary-row">
            <span class="stat-label">源 / 模型</span>
            <b class="small">{{ detection.result!.source }}</b>
          </div>
        </div>

        <div v-if="hasResult && detection.classOptions.length" class="class-filter">
          <p class="upper">类别筛选</p>
          <div class="row wrap">
            <button
              v-for="item in detection.classOptions"
              :key="item.label"
              class="chip clickable"
              :class="{ active: detection.activeLabels.includes(item.label) }"
              @click="detection.toggleLabel(item.label)"
            >
              <span class="dot" :style="{ background: item.color, boxShadow: `0 0 8px ${item.color}` }" />
              {{ item.label }} {{ item.count }}
            </button>
          </div>
        </div>
      </BaseCard>
    </div>

    <div class="grid grid-3 section-gap">
      <BaseCard class="span-2" title="目标明细" subtitle="置信度降序，悬停联动画面">
        <template #actions>
          <span class="chip">{{ detection.filteredTotal }} / {{ detection.result?.total ?? 0 }}</span>
        </template>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>类别</th>
                <th>置信度</th>
                <th>像素框 (x,y,w,h)</th>
                <th>画面占比</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="det in detection.filteredDetections.slice(0, 12)"
                :key="det.id"
                :class="{ highlight: hoveredId === det.id }"
                @mouseenter="hoveredId = det.id"
                @mouseleave="hoveredId = null"
              >
                <td>
                  <span class="dot" :style="{ background: det.color, boxShadow: `0 0 8px ${det.color}` }" />
                  <span class="strong">{{ det.label_cn }}</span>
                  <span class="tiny dim"> {{ det.label }}</span>
                </td>
                <td>
                  <div class="conf-bar"><span :style="confidenceStyle(det.conf)" /></div>
                  <span class="mono tiny">{{ (det.conf * 100).toFixed(1) }}%</span>
                </td>
                <td class="mono tiny">{{ det.px.join(' , ') }}</td>
                <td class="mono tiny">{{ (det.area_ratio * 100).toFixed(2) }}%</td>
              </tr>
              <tr v-if="!detection.filteredDetections.length">
                <td colspan="4"><EmptyState title="暂无检测结果" description="运行一次检测后可查看目标明细" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>

      <BaseCard title="检测记录" subtitle="最近落库批次">
        <div class="mini-history">
          <div v-for="item in detection.history.slice(0, 6)" :key="item.id" class="mini-row">
            <img :src="item.output_url" :alt="item.name" loading="lazy" />
            <div class="mini-meta">
              <strong class="mono">{{ item.total }} 目标</strong>
              <span class="tiny dim">{{ item.created_at.slice(5, 16) }}</span>
            </div>
            <span class="tiny mono">{{ item.latency_ms }}ms</span>
          </div>
          <EmptyState v-if="!detection.history.length" title="暂无记录" />
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<style scoped>
.workbench { display: grid; grid-template-columns: 280px minmax(0, 1fr) 310px; gap: 16px; align-items: start; }
.samples-panel { position: sticky; top: 82px; }
.samples-body { padding: 12px; display: flex; flex-direction: column; gap: 12px; }
.samples-title { display: flex; align-items: center; justify-content: space-between; }
.samples-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; max-height: 520px; overflow-y: auto; padding-right: 2px; }
.sample-card {
  position: relative; padding: 0; border: 1px solid var(--line); border-radius: 8px;
  overflow: hidden; background: #07131f; transition: all 0.18s;
}
.sample-card img { width: 100%; aspect-ratio: 16 / 10; object-fit: cover; opacity: 0.82; }
.sample-card:hover { border-color: var(--line-strong); transform: translateY(-1px); }
.sample-card.active { border-color: var(--cyan); box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.4), 0 0 16px rgba(34, 211, 238, 0.2); }
.sample-card.active img { opacity: 1; }
.sample-meta {
  position: absolute; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 3px 6px; background: rgba(3, 9, 16, 0.82); font-size: 9px; color: var(--text-dim);
}
.sample-meta b { color: var(--lime); font-weight: 600; }
.sample-meta i { font-style: normal; color: var(--muted); }

.viewer-panel { min-width: 0; }
.viewer-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; width: 100%; }
.viewer-body { position: relative; padding: 12px; }
.gt-toggle { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--muted); }

.viewer-cta {
  position: absolute; left: 50%; bottom: 28px; transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 14px 18px; border-radius: 14px;
  background: rgba(4, 11, 19, 0.86); border: 1px solid rgba(34, 211, 238, 0.3);
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
}

.params-panel :deep(.panel-body) { padding-bottom: 12px; }
.params-panel .reset { margin-top: 8px; }
.imgsz { width: 100%; }
.imgsz button { flex: 1; }

.result-summary { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 8px; }
.summary-row { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.summary-row b { color: var(--text); font-size: 14px; }
.summary-row b.small { font-size: 11px; color: var(--text-dim); }
.summary-row .stat-label { text-transform: none; letter-spacing: 0.02em; font-size: 11px; }

.class-filter { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 8px; }
.class-filter p { margin: 0; }

.span-2 { grid-column: span 2; }
.table-wrap { overflow-x: auto; }
.conf-bar { width: 74px; height: 3px; border-radius: 99px; background: rgba(120, 180, 220, 0.12); overflow: hidden; margin-bottom: 4px; }
.conf-bar span { display: block; height: 100%; border-radius: inherit; }
tr.highlight { background: rgba(34, 211, 238, 0.06); }

.mini-history { display: flex; flex-direction: column; gap: 8px; }
.mini-row { display: flex; align-items: center; gap: 9px; padding: 6px; border-radius: 8px; border: 1px solid var(--line); }
.mini-row img { width: 54px; height: 34px; object-fit: cover; border-radius: 5px; opacity: 0.85; }
.mini-meta { display: flex; flex-direction: column; flex: 1; line-height: 1.3; }
.mini-meta strong { font-size: 11px; color: var(--text-dim); }

@media (max-width: 1400px) {
  .workbench { grid-template-columns: 240px minmax(0, 1fr) 280px; }
}
@media (max-width: 1200px) {
  .workbench { grid-template-columns: 1fr; }
  .samples-panel { position: static; }
  .samples-grid { grid-template-columns: repeat(4, 1fr); max-height: none; }
  .span-2 { grid-column: span 1; }
}
@media (max-width: 700px) {
  .samples-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
