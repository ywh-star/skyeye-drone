<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import EChart from '@/components/ui/EChart.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { useSystemStore } from '@/stores/system'
import { useTrainingStore } from '@/stores/training'
import { useUiStore } from '@/stores/ui'

const training = useTrainingStore()
const system = useSystemStore()
const ui = useUiStore()

const form = ref({
  epochs: 3,
  imgsz: 320,
  batch: 4,
  base_model: 'coco-yolov8n',
  note: 'VisDrone 小目标快速微调',
})

const terminal = ref<HTMLDivElement | null>(null)
const starting = ref(false)
const busy = ref(false)

const job = computed(() => training.selected)
const checkpoints = computed(() => job.value?.checkpoints ?? [])
const last = computed(() => job.value?.last_metrics ?? null)
const active = computed(() => job.value?.status === 'running' || job.value?.status === 'queued' || job.value?.status === 'stopping')
const canResume = computed(() =>
  !!job.value
  && ['stopped', 'failed'].includes(job.value.status)
  && job.value.current_epoch < (job.value.total_epochs || 1),
)
const resumeHint = computed(() => {
  if (!job.value) return '请先在右侧选择一个训练任务'
  if (canResume.value) {
    return checkpoints.value.some((c) => c.resumable)
      ? '从 last.pt 检查点继续训练'
      : '该任务无检查点，将按原配置从头重启训练'
  }
  if (active.value) return '任务进行中，请先停止再续训'
  return '任务已完成全部轮次，无需续训'
})

const latest = computed(() => training.metrics[training.metrics.length - 1] ?? null)
const epochsDone = computed(() => training.metrics.length)

const lossOption = computed(() => {
  const items = training.metrics
  const labels = items.map((m) => `E${m.epoch}`)
  const axis = {
    axisLabel: { color: '#6c839c', fontSize: 10 },
    axisLine: { lineStyle: { color: 'rgba(120,190,235,0.16)' } },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: 'rgba(120,190,235,0.07)' } },
  }
  return {
    grid: { left: 44, right: 46, top: 34, bottom: 26 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6,16,26,0.92)',
      borderColor: 'rgba(34,211,238,0.3)',
      textStyle: { color: '#e8f3ff', fontSize: 12 },
    },
    legend: {
      top: 4,
      textStyle: { color: '#a8bdd2', fontSize: 11 },
      itemWidth: 12,
      itemHeight: 4,
      icon: 'roundRect',
    },
    xAxis: { type: 'category', data: labels, ...axis, splitLine: { show: false } },
    yAxis: [
      { type: 'value', name: 'Loss', nameTextStyle: { color: '#6c839c', fontSize: 10 }, ...axis },
      { type: 'value', name: 'mAP', min: 0, max: 1, nameTextStyle: { color: '#6c839c', fontSize: 10 }, ...axis },
    ],
    series: [
      {
        name: 'box_loss', type: 'line', smooth: true, symbol: 'none',
        data: items.map((m) => m.box_loss),
        lineStyle: { width: 2, color: '#22d3ee' },
        itemStyle: { color: '#22d3ee' },
      },
      {
        name: 'cls_loss', type: 'line', smooth: true, symbol: 'none',
        data: items.map((m) => m.cls_loss),
        lineStyle: { width: 2, color: '#f59e0b' },
        itemStyle: { color: '#f59e0b' },
      },
      {
        name: 'dfl_loss', type: 'line', smooth: true, symbol: 'none',
        data: items.map((m) => m.dfl_loss),
        lineStyle: { width: 2, color: '#818cf8' },
        itemStyle: { color: '#818cf8' },
      },
      {
        name: 'mAP50', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, yAxisIndex: 1,
        data: items.map((m) => m.mAP50),
        lineStyle: { width: 2, color: '#a3e635' },
        itemStyle: { color: '#a3e635' },
        areaStyle: { color: 'rgba(163,230,53,0.08)' },
      },
      {
        name: 'mAP50-95', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1,
        data: items.map((m) => m.mAP50_95),
        lineStyle: { width: 1.4, color: '#f472b6', type: 'dashed' },
        itemStyle: { color: '#f472b6' },
      },
    ],
  }
})

const modelOptions = computed(() => system.models)

function scrollLog() {
  nextTick(() => {
    if (terminal.value) terminal.value.scrollTop = terminal.value.scrollHeight
  })
}

watch(() => training.logs.length, scrollLog)

async function startJob() {
  if (active.value) {
    ui.push('当前有训练任务进行中，请先停止或等待结束', 'error')
    return
  }
  starting.value = true
  try {
    const created = await training.start({ ...form.value })
    ui.push(`训练任务 ${created.id} 已启动（CPU 演示模式）`, 'success')
    scrollLog()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '启动训练失败', 'error')
  } finally {
    starting.value = false
  }
}

async function stopJob() {
  busy.value = true
  try {
    await training.stop()
    ui.push('已请求停止训练，检查点将保留用于续训', 'info')
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '停止失败', 'error')
  } finally {
    busy.value = false
  }
}

async function resumeJob() {
  busy.value = true
  try {
    const resumed = await training.resume()
    ui.push(
      resumed?.resumed_from === 'fresh' ? '该任务无检查点，已按原配置从头重启训练' : '已从 last.pt 断点续训',
      resumed?.resumed_from === 'fresh' ? 'info' : 'success',
    )
    scrollLog()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '续训失败', 'error')
  } finally {
    busy.value = false
  }
}

function selectJob(id: string) {
  training.selectJob(id)
}

function statusText(status: string) {
  const map: Record<string, string> = {
    queued: '排队中', running: '训练中', stopping: '停止中',
    stopped: '已停止', finished: '已完成', failed: '失败',
  }
  return map[status] ?? status
}

onMounted(async () => {
  await Promise.all([
    system.models.length ? Promise.resolve() : system.refresh(),
    training.loadJobs(),
  ])
  scrollLog()
})

onUnmounted(() => training.disconnect())
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1 class="page-title">模型训练中心</h1>
        <p class="page-sub">YOLOv8 微调 · 实时指标 · 断点续训 · CPU 演示模式</p>
      </div>
      <div class="row">
        <span class="chip" :class="training.streaming ? 'lime' : ''">
          <span class="dot" :class="training.streaming ? 'lime pulse' : 'cyan'" />
          {{ training.streaming ? 'SSE 实时通道已连接' : '实时通道待连接' }}
        </span>
        <span class="chip mono">{{ training.jobs.length }} 个训练任务</span>
      </div>
    </div>

    <div class="grid grid-4">
      <StatCard
        label="最佳 mAP50"
        :value="last ? (last.mAP50 * 100).toFixed(1) : '—'"
        unit="%"
        accent="lime"
        :hint="job ? `任务 ${job.id}` : '尚未选择任务'"
        :trend="training.metrics.map((m) => Math.round(m.mAP50 * 100))"
      />
      <StatCard
        label="已完成轮次"
        :value="job?.current_epoch ?? 0"
        :unit="`/ ${job?.total_epochs ?? form.epochs}`"
        accent="cyan"
        hint="断点续训会从 last.pt 恢复"
        :trend="training.metrics.map((m) => m.epoch)"
      />
      <StatCard
        label="断点续训次数"
        :value="job?.resume_count ?? 0"
        unit="次"
        accent="amber"
        hint="每轮训练自动保存检查点"
        :trend="[0, 1, 1, 2, 2, 3, 3, 4]"
      />
      <StatCard
        label="检查点"
        :value="checkpoints.length"
        unit="个"
        accent="violet"
        hint="best.pt / last.pt 自动归档"
        :trend="[1, 2, 2, 3, 3, 4, 4, 5]"
      />
    </div>

    <div class="train-grid section-gap">
      <BaseCard title="训练配置" subtitle="基于 VisDrone 子集的检测微调">
        <template #actions>
          <span class="chip amber">CPU</span>
        </template>
        <div class="form-grid">
          <div class="field">
            <label class="field-label">训练轮次 Epochs <span class="value">{{ form.epochs }}</span></label>
            <input v-model.number="form.epochs" class="range" type="range" min="1" max="30" step="1" :style="{ '--p': `${(form.epochs / 30) * 100}%` }" />
          </div>
          <div class="field">
            <label class="field-label">输入尺寸 imgsz <span class="value">{{ form.imgsz }}</span></label>
            <input v-model.number="form.imgsz" class="range" type="range" min="256" max="640" step="32" :style="{ '--p': `${((form.imgsz - 256) / 384) * 100}%` }" />
          </div>
          <div class="field">
            <label class="field-label">批大小 Batch</label>
            <select v-model.number="form.batch" class="select">
              <option v-for="size in [2, 4, 8, 16]" :key="size" :value="size">{{ size }}</option>
            </select>
          </div>
          <div class="field">
            <label class="field-label">基础权重</label>
            <select v-model="form.base_model" class="select">
              <option v-for="model in modelOptions" :key="model.id" :value="model.id">{{ model.name }}（{{ model.size_mb }} MB）</option>
              <option v-if="!modelOptions.length" value="coco-yolov8n">YOLOv8n COCO 预训练</option>
            </select>
          </div>
        </div>
        <div class="field">
          <label class="field-label">任务备注</label>
          <input v-model="form.note" class="input" placeholder="例如：小目标检测课程实验" />
        </div>
        <div class="train-actions">
          <button class="btn btn-primary" :disabled="starting || active" @click="startJob">
            <span v-if="starting" class="spinner" />
            {{ starting ? '正在创建任务…' : '启动训练' }}
          </button>
          <button class="btn btn-danger" :disabled="!active || busy" @click="stopJob">停止训练</button>
          <button class="btn btn-lime" :disabled="!canResume || busy" :title="resumeHint" @click="resumeJob">断点续训</button>
        </div>
        <p class="tiny dim train-note">
          CPU 训练速度较慢，建议先用 1–3 个 epoch 验证链路；每次 epoch 结束自动写入 best.pt / last.pt，
          任务被停止后可从 last.pt 继续，已完成轮次不会丢失。
        </p>
      </BaseCard>

      <BaseCard title="训练任务" subtitle="点击切换实时日志与指标">
        <template #actions>
          <button class="btn btn-sm" :disabled="training.loading" @click="training.loadJobs()">刷新</button>
        </template>
        <div class="job-list">
          <button
            v-for="item in training.jobs"
            :key="item.id"
            class="job-row"
            :class="{ active: item.id === training.selectedId }"
            type="button"
            @click="selectJob(item.id)"
          >
            <div class="job-main">
              <span class="job-id mono">{{ item.id }}</span>
              <StatusPill :status="item.status" />
            </div>
            <div class="job-meta">
              <span class="mono">{{ item.current_epoch }} / {{ item.total_epochs }} epoch</span>
              <span class="mono">mAP50 {{ (item.best_map50 * 100).toFixed(1) }}%</span>
              <span class="tiny dim">{{ item.created_at.slice(5, 16) }}</span>
            </div>
            <div class="progress job-progress">
              <span :style="{ width: `${Math.min(100, (item.current_epoch / Math.max(1, item.total_epochs)) * 100)}%` }" />
            </div>
          </button>
          <EmptyState v-if="!training.jobs.length && !training.loading" title="还没有训练任务" description="在上方配置参数并启动第一次训练" />
        </div>
      </BaseCard>
    </div>

    <div class="train-grid section-gap">
      <BaseCard title="损失与精度曲线" :subtitle="job ? `${job.id} · ${statusText(job.status)}` : '选择任务后展示'">
        <template #actions>
          <span class="chip mono">{{ epochsDone }} 条指标</span>
        </template>
        <div v-if="training.metrics.length" class="chart-wrap">
          <EChart :option="lossOption" :height="300" />
          <div v-if="latest" class="metric-strip">
            <div><span class="upper">box_loss</span><b class="mono">{{ latest.box_loss.toFixed(3) }}</b></div>
            <div><span class="upper">cls_loss</span><b class="mono">{{ latest.cls_loss.toFixed(3) }}</b></div>
            <div><span class="upper">dfl_loss</span><b class="mono">{{ latest.dfl_loss.toFixed(3) }}</b></div>
            <div><span class="upper">mAP50</span><b class="mono lime">{{ (latest.mAP50 * 100).toFixed(1) }}%</b></div>
            <div><span class="upper">mAP50-95</span><b class="mono">{{ (latest.mAP50_95 * 100).toFixed(1) }}%</b></div>
            <div><span class="upper">lr</span><b class="mono">{{ latest.lr.toExponential(1) }}</b></div>
          </div>
        </div>
        <EmptyState v-else title="暂无训练指标" description="训练开始后会从子进程回传每个 epoch 的损失与 mAP" />
      </BaseCard>

      <BaseCard title="检查点归档" subtitle="runs/<job_id>/weights">
        <div class="ckpt-list">
          <div v-for="ckpt in checkpoints" :key="ckpt.name" class="ckpt-row">
            <div class="ckpt-icon" :class="{ best: ckpt.best }">{{ ckpt.best ? 'B' : 'L' }}</div>
            <div class="ckpt-main">
              <span class="mono">{{ ckpt.name }}</span>
              <span class="tiny dim">{{ ckpt.updated_at }}</span>
            </div>
            <div class="ckpt-meta">
              <span class="chip" :class="ckpt.best ? 'lime' : ckpt.resumable ? 'cyan' : ''">
                {{ ckpt.best ? '最佳' : ckpt.resumable ? '可续训' : '权重' }}
              </span>
              <span class="tiny mono dim">{{ ckpt.size_mb }} MB</span>
            </div>
          </div>
          <EmptyState v-if="!checkpoints.length" title="暂无检查点" description="训练进入第一个 epoch 后自动生成" />
        </div>
        <div class="ckpt-note muted-box">
          续训使用 <b class="mono">last.pt</b> 恢复优化器与学习率状态，训练结束或手动停止都不会丢失已完成的轮次。
        </div>
      </BaseCard>
    </div>

    <BaseCard class="section-gap" title="训练日志" subtitle="子进程 stdout 实时流（SSE）">
      <template #actions>
        <span class="chip" :class="active ? 'lime' : ''">
          <span class="dot" :class="active ? 'lime pulse' : 'cyan'" />
          {{ active ? '训练进行中' : '已结束' }}
        </span>
        <button class="btn btn-sm" @click="scrollLog">滚到底部</button>
      </template>
      <div ref="terminal" class="terminal">
        <p v-for="(line, index) in training.logs" :key="index" class="log-line" :class="{ metric: line.includes('mAP'), err: line.toLowerCase().includes('error') }">
          <span class="log-index mono">{{ String(index + 1).padStart(3, '0') }}</span>{{ line }}
        </p>
        <p v-if="!training.logs.length" class="log-empty">等待训练进程输出…</p>
      </div>
    </BaseCard>
  </div>
</template>

<style scoped>
.train-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.train-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.train-note { margin-top: 12px; line-height: 1.7; }

.job-list { display: flex; flex-direction: column; gap: 7px; max-height: 372px; overflow-y: auto; }
.job-row {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--line); background: rgba(255, 255, 255, 0.02);
  text-align: left; transition: all 0.16s;
}
.job-row:hover { border-color: var(--line-strong); background: rgba(34, 211, 238, 0.05); }
.job-row.active { border-color: rgba(34, 211, 238, 0.45); background: rgba(34, 211, 238, 0.09); }
.job-main { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.job-id { font-size: 12px; color: var(--text); }
.job-meta { display: flex; align-items: center; gap: 12px; font-size: 10px; color: var(--muted); }
.job-progress { height: 3px; }

.chart-wrap { display: flex; flex-direction: column; gap: 10px; }
.metric-strip {
  display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px;
  padding: 10px 12px; border-radius: 10px; background: rgba(5, 13, 22, 0.55);
  border: 1px solid var(--line);
}
.metric-strip div { display: flex; flex-direction: column; gap: 1px; }
.metric-strip b { font-size: 13px; color: var(--text); font-weight: 500; }
.metric-strip b.lime { color: var(--lime); }

.ckpt-list { display: flex; flex-direction: column; gap: 7px; }
.ckpt-row { display: flex; align-items: center; gap: 11px; padding: 9px 11px; border-radius: 10px; border: 1px solid var(--line); background: rgba(255, 255, 255, 0.02); }
.ckpt-icon {
  width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
  display: grid; place-items: center; font-size: 11px; font-family: var(--font-num);
  color: var(--cyan); background: rgba(34, 211, 238, 0.1); border: 1px solid rgba(34, 211, 238, 0.3);
}
.ckpt-icon.best { color: var(--lime); background: rgba(163, 230, 53, 0.12); border-color: rgba(163, 230, 53, 0.35); }
.ckpt-main { flex: 1; display: flex; flex-direction: column; gap: 1px; font-size: 12px; color: var(--text-dim); }
.ckpt-meta { display: flex; align-items: center; gap: 8px; }
.ckpt-note { margin-top: 12px; padding: 10px 12px; font-size: 11px; color: var(--muted); line-height: 1.7; }
.ckpt-note b { color: var(--cyan); }

.terminal {
  height: 260px; overflow-y: auto; padding: 12px 14px;
  border-radius: 10px; border: 1px solid var(--line);
  background: #040c14; font-family: var(--font-num); font-size: 11.5px; line-height: 1.75;
}
.log-line { color: #93aec5; white-space: pre-wrap; word-break: break-all; }
.log-line.metric { color: var(--lime); }
.log-line.err { color: var(--danger); }
.log-index { color: #3c556c; margin-right: 10px; font-size: 10px; }
.log-empty { color: var(--muted); font-size: 11px; }

@media (max-width: 1200px) {
  .train-grid { grid-template-columns: 1fr; }
  .metric-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .form-grid { grid-template-columns: 1fr; }
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
