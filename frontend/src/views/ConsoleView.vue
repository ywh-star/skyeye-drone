<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { EChartsCoreOption } from 'echarts/core'
import BaseCard from '@/components/ui/BaseCard.vue'
import EChart from '@/components/ui/EChart.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ModalDialog from '@/components/ui/ModalDialog.vue'
import RingGauge from '@/components/ui/RingGauge.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { useDetectionStore } from '@/stores/detection'
import { useSystemStore } from '@/stores/system'
import { useTaskStore } from '@/stores/tasks'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import type { TaskItem, TaskStatus } from '@/types'

const router = useRouter()
const system = useSystemStore()
const tasks = useTaskStore()
const detection = useDetectionStore()
const ui = useUiStore()
const auth = useAuthStore()

const range = ref(7)
const showCreate = ref(false)
const saving = ref(false)
const lastSync = computed(() => system.lastSync || '尚未同步')

const summary = computed(() => system.overview)
const dataset = computed(() => summary.value?.dataset)
const timeline = computed(() => summary.value?.timeline ?? [])

const trendOption = computed<EChartsCoreOption>(() => {
  const data = timeline.value.slice(-range.value)
  const dates = data.length ? data.map((d) => d.date.slice(5)) : ['—', '—', '—', '—', '—', '—', '—']
  const counts = data.length ? data.map((d) => d.count) : [0, 0, 0, 0, 0, 0, 0]
  return {
    backgroundColor: 'transparent',
    grid: { left: 6, right: 10, top: 22, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(8,18,30,0.96)',
      borderColor: 'rgba(34,211,238,0.35)',
      textStyle: { color: '#e8f3ff', fontSize: 11 },
      axisPointer: { lineStyle: { color: 'rgba(34,211,238,0.35)' } },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(120,190,235,0.16)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6c839c', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(120,190,235,0.07)' } },
      axisLabel: { color: '#6c839c', fontSize: 10 },
    },
    series: [
      {
        name: '识别目标',
        type: 'line',
        smooth: 0.4,
        data: counts,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#22d3ee', width: 2 },
        itemStyle: { color: '#22d3ee' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(34,211,238,0.32)' },
              { offset: 1, color: 'rgba(34,211,238,0.01)' },
            ],
          },
        },
      },
    ],
  }
})

const classSource = computed(() => {
  const detected = summary.value?.class_top ?? []
  if (detected.length) return detected.map((d) => ({ label: d.label, count: d.count }))
  return (dataset.value?.classes ?? []).filter((c) => c.count > 0).map((c) => ({ label: c.name_cn, count: c.count }))
})

const pieOption = computed<EChartsCoreOption>(() => {
  const colors = ['#22d3ee', '#a3e635', '#f59e0b', '#f472b6', '#818cf8', '#34d399', '#fb7185', '#facc15']
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(8,18,30,0.96)',
      borderColor: 'rgba(34,211,238,0.35)',
      textStyle: { color: '#e8f3ff', fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '82%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#07111d', borderWidth: 2 },
        label: { show: false },
        data: classSource.value.slice(0, 6).map((item, index) => ({
          name: item.label,
          value: item.count,
          itemStyle: { color: colors[index % colors.length] },
        })),
      },
    ],
  }
})

const classTotal = computed(() => classSource.value.slice(0, 6).reduce((sum, item) => sum + item.count, 0))

const taskStats = computed(() => tasks.counts)

const form = reactive({ name: '', area: '', drone: 'Mavic 3E', altitude: 150, cover_km2: 2.4, assignee: '', priority: 'normal' })
const formValid = computed(() => form.name.trim().length >= 2 && form.area.trim().length >= 2)

function openCreate() {
  form.name = ''
  form.area = ''
  form.altitude = 150
  form.cover_km2 = 2.4
  form.assignee = ''
  form.priority = 'normal'
  showCreate.value = true
}

async function createTask() {
  if (!formValid.value || saving.value) return
  saving.value = true
  try {
    await tasks.create({
      ...form,
      assignee: auth.role === 'pilot' ? auth.callsign : (form.assignee || ''),
      priority: form.priority || 'normal',
    })
    ui.push(`任务「${form.name}」已加入调度队列`)
    showCreate.value = false
    await system.loadOverview()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '创建任务失败', 'error')
  } finally {
    saving.value = false
  }
}

async function advance(taskId: string, next: string, name: string) {
  try {
    await tasks.setStatus(taskId, next)
    ui.push(`任务「${name}」状态已更新`)
    await system.loadOverview()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '状态更新失败', 'error')
  }
}

function nextAction(status: string) {
  if (status === 'running') return { label: '完成复核', next: 'review' }
  if (status === 'review') return { label: '归档', next: 'done' }
  if (status === 'queued') return { label: '启动', next: 'running' }
  return { label: '重新执行', next: 'running' }
}

const modelCount = computed(() => system.info?.models.length ?? 0)

const taskBoardTitle = computed(() => {
  if (auth.role === 'pilot') return '我的飞行任务'
  if (auth.role === 'analyst') return '任务态势总览'
  return '飞行任务编排'
})
const taskBoardSub = computed(() => {
  if (auth.role === 'pilot') return '我负责的巡检任务 · 支持状态流转'
  if (auth.role === 'analyst') return '全局任务态势 · 仅复核不可编辑'
  return '按状态自动排序，支持状态流转'
})
const canManageTasks = computed(() => auth.role !== 'analyst')

// ── 角色化任务管理 ──────────────────────────────────────────────
const priorityOptions = [
  { value: 'low', label: '低', color: '#6c839c' },
  { value: 'normal', label: '普通', color: '#22d3ee' },
  { value: 'high', label: '高', color: '#f59e0b' },
  { value: 'urgent', label: '紧急', color: '#fb7185' },
]
const priorityColor = (p: string) => priorityOptions.find((o) => o.value === p)?.color ?? '#6c839c'
const priorityLabel = (p: string) => priorityOptions.find((o) => o.value === p)?.label ?? p

// 飞手：创建任务表单扩展（优先级）
form.priority = 'normal'

// 分析师：复核弹窗
const reviewTarget = ref<TaskItem | null>(null)
const reviewNote = ref('')
const reviewDecision = ref<'pass' | 'reject'>('pass')

function openReview(task: TaskItem) {
  reviewTarget.value = task
  reviewNote.value = task.review_note || ''
  reviewDecision.value = 'pass'
}

async function submitReview() {
  if (!reviewTarget.value) return
  const next = reviewDecision.value === 'pass' ? 'done' : 'running'
  const label = reviewDecision.value === 'pass' ? '复核通过' : '驳回重飞'
  try {
    await tasks.setStatus(
      reviewTarget.value.id,
      next,
      auth.callsign,
      reviewNote.value.trim(),
    )
    ui.push(`任务「${reviewTarget.value.name}」${label}`)
    reviewTarget.value = null
    await system.loadOverview()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '复核失败', 'error')
  }
}

// 管理员：状态筛选 + 强制流转 + 删除
const adminFilter = ref<'all' | TaskStatus>('all')
const filteredTasks = computed(() => {
  if (adminFilter.value === 'all') return tasks.items
  return tasks.items.filter((t) => t.status === adminFilter.value)
})

async function forceStatus(task: TaskItem, status: TaskStatus) {
  try {
    await tasks.setStatus(task.id, status)
    ui.push(`任务「${task.name}」已强制流转为 ${status}`)
    await system.loadOverview()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '操作失败', 'error')
  }
}

async function removeTask(task: TaskItem) {
  if (!window.confirm(`确认删除任务「${task.name}」？此操作不可撤销。`)) return
  try {
    await tasks.remove(task.id)
    ui.push(`任务「${task.name}」已删除`)
    await system.loadOverview()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '删除失败', 'error')
  }
}

// 飞手视角：我的任务（按负责人过滤，若无负责人则显示全部）
const myTasks = computed(() => {
  if (!auth.callsign) return tasks.items
  const owned = tasks.items.filter((t) => t.assignee === auth.callsign)
  return owned.length ? owned : tasks.items
})

// 分析师视角：待复核任务
const reviewTasks = computed(() => tasks.items.filter((t) => t.status === 'review'))

async function refreshAll(manual = false) {
  try {
    await Promise.all([system.refresh(), tasks.load(), detection.loadHistory()])
    if (manual) {
      if (system.error) ui.push(`刷新完成，但后端异常：${system.error}`, 'error')
      else ui.push('态势数据已刷新')
    }
  } catch (err) {
    if (manual) ui.push(err instanceof Error ? err.message : '刷新失败', 'error')
  }
}

onMounted(() => refreshAll())

</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ auth.meta.title }}</h1>
        <p class="page-sub">{{ auth.meta.subtitle }} · 最后同步 {{ lastSync }}</p>
      </div>
      <div class="row">
        <span class="chip" :class="system.error ? 'amber' : 'lime'">
          <span class="dot" :class="system.error ? 'amber' : 'lime pulse'" />
          {{ system.error ? '后端未连接' : '数据链路正常' }}
        </span>
        <button class="btn btn-sm" :disabled="system.loading" @click="refreshAll(true)">
          <span v-if="system.loading" class="spinner" />
          刷新态势
        </button>
        <button v-if="auth.role !== 'analyst'" class="btn btn-primary btn-sm" @click="openCreate">新建巡检任务</button>
        <span v-else class="chip cyan"><span class="dot cyan" />分析师 · 只读复核</span>
      </div>
    </div>

    <div v-if="system.error" class="alert-panel">
      <span class="dot amber pulse" />
      <div>
        <strong>无法连接 FastAPI 后端</strong>
        <p class="tiny dim">请在 backend 目录运行 uvicorn app.main:app --port 8000，并确认 agri_drone 环境已安装 ultralytics。</p>
      </div>
    </div>

    <div class="grid grid-4">
      <StatCard
        label="累计检测影像"
        :value="summary?.images_processed ?? 0"
        unit="帧"
        accent="cyan"
        :trend="timeline.map((d) => d.count)"
        hint="YOLOv8 推理记录"
        @select="router.push('/detect')"
      />
      <StatCard
        label="识别目标总数"
        :value="summary?.objects_found ?? 0"
        unit="个"
        accent="lime"
        :trend="classSource.map((c) => c.count)"
        hint="车辆 / 行人 / 非机动车"
        @select="router.push('/dataset')"
      />
      <StatCard
        label="平均推理时延"
        :value="summary?.avg_latency ?? 0"
        unit="ms"
        accent="amber"
        hint="CPU 单帧 · imgsz 可变"
        @select="router.push('/training')"
      />
      <StatCard
        label="活跃飞行任务"
        :value="summary?.active_tasks ?? 0"
        unit="条"
        accent="pink"
        :hint="`共 ${summary?.total_tasks ?? 0} 条任务`"
        @select="router.push('/replay')"
      />
    </div>

    <div class="grid grid-3 section-gap">
      <BaseCard class="span-2" title="目标识别趋势" subtitle="按检测批次聚合，切换时间窗口查看">
        <template #actions>
          <div class="segmented">
            <button v-for="d in [7, 14, 30]" :key="d" :class="{ active: range === d }" @click="range = d">{{ d }}D</button>
          </div>
        </template>
        <EChart :option="trendOption" :height="246" />
        <template #footer>
          <div class="row-between">
            <span class="tiny dim">数据来自检测工作台落库记录</span>
            <span class="tiny mono">{{ timeline.length }} 个采样日</span>
          </div>
        </template>
      </BaseCard>

      <BaseCard title="类别构成" subtitle="Top 6 目标类别占比">
        <EChart v-if="classSource.length" :option="pieOption" :height="190" />
        <EmptyState v-else title="暂无类别数据" description="完成一次检测后自动生成" />
        <div class="class-legend">
          <span v-for="(item, index) in classSource.slice(0, 6)" :key="item.label">
            <i :style="{ background: ['#22d3ee','#a3e635','#f59e0b','#f472b6','#818cf8','#34d399'][index] }" />
            {{ item.label }}
            <b class="mono">{{ classTotal ? Math.round((item.count / classTotal) * 100) : 0 }}%</b>
          </span>
        </div>
      </BaseCard>
    </div>

    <div class="grid grid-3 section-gap">
      <BaseCard class="span-2" :title="taskBoardTitle" :subtitle="taskBoardSub">
        <template #actions>
          <span class="chip lime"><span class="dot lime" />{{ taskStats.running }} 执行中</span>
          <span class="chip amber">{{ taskStats.review }} 待复核</span>
          <select v-if="auth.role === 'admin'" v-model="adminFilter" class="select select-sm">
            <option value="all">全部状态</option>
            <option value="queued">排队</option>
            <option value="running">执行中</option>
            <option value="review">待复核</option>
            <option value="done">已完成</option>
          </select>
        </template>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>任务</th>
                <th>区域 / 机型</th>
                <th>优先级</th>
                <th>进度</th>
                <th>目标</th>
                <th>状态</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in (auth.role === 'pilot' ? myTasks : auth.role === 'analyst' ? reviewTasks : filteredTasks)" :key="task.id">
                <td>
                  <div class="task-name">{{ task.name }}</div>
                  <span class="tiny mono dim">{{ task.code }} · {{ task.duration_min }}min · {{ task.cover_km2 }}km²</span>
                  <div v-if="task.assignee" class="tiny dim">负责人：{{ task.assignee }}</div>
                  <div v-if="task.reviewer" class="tiny dim">复核人：{{ task.reviewer }}<span v-if="task.review_note"> · {{ task.review_note }}</span></div>
                </td>
                <td>
                  <div>{{ task.area }}</div>
                  <span class="tiny dim">{{ task.drone }} · {{ task.altitude }}m</span>
                </td>
                <td>
                  <span class="pri-dot" :style="{ background: priorityColor(task.priority) }" />
                  <span class="tiny">{{ priorityLabel(task.priority) }}</span>
                </td>
                <td>
                  <div class="progress"><span :style="{ width: `${task.progress}%` }" /></div>
                  <span class="tiny mono dim">{{ task.progress }}%</span>
                </td>
                <td class="mono strong">{{ task.detections }}</td>
                <td><StatusPill :status="task.status" /></td>
                <td class="ta-r">
                  <!-- 飞手：启动 / 提交复核 -->
                  <template v-if="auth.role === 'pilot'">
                    <button
                      v-if="task.status === 'queued'"
                      class="btn btn-sm"
                      :disabled="tasks.loading"
                      @click="advance(task.id, 'running', task.name)"
                    >启动飞行</button>
                    <button
                      v-else-if="task.status === 'running'"
                      class="btn btn-sm btn-primary"
                      :disabled="tasks.loading"
                      @click="advance(task.id, 'review', task.name)"
                    >提交复核</button>
                    <span v-else class="tiny dim">{{ task.status === 'review' ? '待复核' : '已完成' }}</span>
                  </template>
                  <!-- 分析师：复核 -->
                  <template v-else-if="auth.role === 'analyst'">
                    <button class="btn btn-sm btn-primary" @click="openReview(task)">复核</button>
                  </template>
                  <!-- 管理员：强制流转 + 删除 -->
                  <template v-else>
                    <select
                      class="select select-sm"
                      :value="task.status"
                      @change="forceStatus(task, ($event.target as HTMLSelectElement).value as TaskStatus)"
                    >
                      <option value="queued">排队</option>
                      <option value="running">执行中</option>
                      <option value="review">待复核</option>
                      <option value="done">已完成</option>
                    </select>
                    <button class="btn btn-sm btn-danger" @click="removeTask(task)">删除</button>
                  </template>
                </td>
              </tr>
              <tr v-if="!(auth.role === 'pilot' ? myTasks : auth.role === 'analyst' ? reviewTasks : filteredTasks).length">
                <td colspan="7">
                  <EmptyState
                    :title="auth.role === 'analyst' ? '暂无待复核任务' : '暂无飞行任务'"
                    :description="auth.role === 'analyst' ? '飞手提交复核后将在此显示' : '点击右上角新建巡检任务'"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>

      <BaseCard title="系统与数据" subtitle="运行环境与数据就绪度">
        <div class="sys-gauge">
          <RingGauge :value="100" :size="116" label="标注覆盖率" sublabel="VisDrone 子集" />
          <div class="sys-gauge-info">
            <div><span class="tiny dim">样本</span><b class="mono">{{ dataset?.images ?? 0 }}</b></div>
            <div><span class="tiny dim">标注目标</span><b class="mono">{{ dataset?.objects ?? 0 }}</b></div>
            <div><span class="tiny dim">权重</span><b class="mono">{{ modelCount }}</b></div>
          </div>
        </div>
        <div class="kv">
          <div><span>后端框架</span><b>FastAPI</b></div>
          <div><span>推理框架</span><b>Ultralytics {{ system.info?.ultralytics ?? '—' }}</b></div>
          <div><span>PyTorch</span><b>{{ system.info?.torch ?? '—' }} · {{ system.info?.device ?? 'CPU' }}</b></div>
          <div><span>前端</span><b>Vue {{ system.info?.frontend.vue ?? '3.5' }} · TS</b></div>
          <div><span>三维渲染</span><b>Three.js {{ system.info?.frontend.three ?? 'r172' }}</b></div>
        </div>
        <template #footer>
          <RouterLink to="/training" class="btn btn-sm btn-block">打开训练中心 →</RouterLink>
        </template>
      </BaseCard>
    </div>

    <BaseCard class="section-gap" title="最近检测批次" subtitle="点击任意批次进入检测工作台复核">
      <template #actions>
        <button class="btn btn-sm" @click="router.push('/detect')">检测工作台 →</button>
      </template>
      <div v-if="detection.history.length" class="history-strip">
        <button
          v-for="item in detection.history.slice(0, 8)"
          :key="item.id"
          class="history-card"
          type="button"
          @click="router.push('/detect')"
        >
          <div class="history-thumb">
            <img :src="item.output_url" :alt="item.name" loading="lazy" />
            <span class="history-total mono">{{ item.total }} 目标</span>
          </div>
          <div class="history-meta">
            <strong>{{ item.model }}</strong>
            <span class="tiny dim">{{ item.created_at.slice(5, 16) }} · {{ item.latency_ms }}ms</span>
          </div>
        </button>
      </div>
      <EmptyState v-else title="暂无检测记录" description="前往检测工作台选择 VisDrone 样本或上传航拍图" />
    </BaseCard>

    <ModalDialog :open="showCreate" title="新建巡检任务" @close="showCreate = false">
      <div class="field">
        <span class="field-label">任务名称</span>
        <input v-model="form.name" class="input" placeholder="如：滨江路网晚高峰巡检" maxlength="40" />
      </div>
      <div class="field">
        <span class="field-label">空域 / 区域</span>
        <input v-model="form.area" class="input" placeholder="如：滨江区 · 江南大道" maxlength="60" />
      </div>
      <div class="form-grid">
        <div class="field">
          <span class="field-label">执行机型</span>
          <select v-model="form.drone" class="select">
            <option>Mavic 3E</option>
            <option>Matrice 350 RTK</option>
            <option>Matrice 30T</option>
            <option>Mavic 3 Pro</option>
          </select>
        </div>
        <div class="field">
          <span class="field-label">规划覆盖 <span class="value">{{ form.cover_km2 }} km²</span></span>
          <input v-model.number="form.cover_km2" class="range" type="range" min="0.5" max="10" step="0.1" :style="{ '--p': `${(form.cover_km2 / 10) * 100}%` }" />
        </div>
      </div>
      <div class="field">
        <span class="field-label">飞行高度 <span class="value">{{ form.altitude }} m</span></span>
        <input v-model.number="form.altitude" class="range" type="range" min="30" max="500" step="10" :style="{ '--p': `${((form.altitude - 30) / 470) * 100}%` }" />
      </div>
      <div class="form-grid">
        <div class="field">
          <span class="field-label">任务优先级</span>
          <select v-model="form.priority" class="select">
            <option v-for="p in priorityOptions" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </div>
        <div v-if="auth.role === 'admin'" class="field">
          <span class="field-label">指派负责人</span>
          <input v-model="form.assignee" class="input" placeholder="飞手呼号（可留空）" />
        </div>
      </div>
      <p class="tiny dim">任务创建后将进入排队状态，飞手可启动执行，采集完成后提交分析师复核。</p>
      <template #footer>
        <button class="btn" @click="showCreate = false">取消</button>
        <button class="btn btn-primary" :disabled="!formValid || saving" @click="createTask">
          {{ saving ? '创建中…' : '加入调度队列' }}
        </button>
      </template>
    </ModalDialog>

    <!-- 分析师复核弹窗 -->
    <ModalDialog :open="!!reviewTarget" :title="`复核任务 · ${reviewTarget?.name ?? ''}`" @close="reviewTarget = null">
      <div v-if="reviewTarget" class="review-info">
        <div class="kv">
          <div><span>任务编号</span><b class="mono">{{ reviewTarget.code }}</b></div>
          <div><span>区域</span><b>{{ reviewTarget.area }}</b></div>
          <div><span>机型 / 高度</span><b>{{ reviewTarget.drone }} · {{ reviewTarget.altitude }}m</b></div>
          <div><span>检测目标</span><b class="mono">{{ reviewTarget.detections }} 个</b></div>
        </div>
      </div>
      <div class="field">
        <span class="field-label">复核决定</span>
        <div class="review-decision">
          <button
            type="button"
            class="decision-btn"
            :class="{ active: reviewDecision === 'pass' }"
            @click="reviewDecision = 'pass'"
          >
            <span class="dot lime" />复核通过
          </button>
          <button
            type="button"
            class="decision-btn"
            :class="{ active: reviewDecision === 'reject' }"
            @click="reviewDecision = 'reject'"
          >
            <span class="dot amber" />驳回重飞
          </button>
        </div>
      </div>
      <div class="field">
        <span class="field-label">复核意见</span>
        <textarea
          v-model="reviewNote"
          class="input"
          rows="3"
          :placeholder="reviewDecision === 'pass' ? '可填写通过说明（选填）' : '请说明驳回原因，便于飞手调整'"
        />
      </div>
      <template #footer>
        <button class="btn" @click="reviewTarget = null">取消</button>
        <button
          class="btn"
          :class="reviewDecision === 'pass' ? 'btn-primary' : 'btn-danger'"
          @click="submitReview"
        >
          {{ reviewDecision === 'pass' ? '确认通过' : '确认驳回' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>

<style scoped>
.span-2 { grid-column: span 2; }
.alert-panel {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.07);
}
.alert-panel strong { font-size: 13px; }
.ta-r { text-align: right; }

.task-name { color: var(--text); font-size: 13px; font-weight: 550; }
.table-wrap { overflow-x: auto; }

.class-legend { display: grid; grid-template-columns: repeat(2, 1fr); gap: 7px 12px; margin-top: 6px; }
.class-legend span { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-dim); }
.class-legend i { width: 7px; height: 7px; border-radius: 2px; }
.class-legend b { margin-left: auto; font-size: 11px; color: var(--muted); }

.sys-gauge { display: flex; align-items: center; gap: 18px; }
.sys-gauge-info { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.sys-gauge-info div { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.sys-gauge-info b { font-size: 15px; color: var(--text); }

.kv { display: flex; flex-direction: column; gap: 7px; margin-top: 16px; }
.kv div { display: flex; justify-content: space-between; gap: 12px; font-size: 12px; color: var(--muted); }
.kv b { color: var(--text-dim); font-weight: 500; }

.history-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.history-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(6, 15, 26, 0.55);
  overflow: hidden;
  text-align: left;
  padding: 0;
  transition: all 0.2s;
}
.history-card:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.history-thumb { position: relative; aspect-ratio: 16 / 9; overflow: hidden; }
.history-thumb img { width: 100%; height: 100%; object-fit: cover; opacity: 0.86; }
.history-total {
  position: absolute; right: 8px; bottom: 8px;
  font-size: 10px; padding: 2px 7px; border-radius: 5px;
  background: rgba(4, 10, 17, 0.8); border: 1px solid rgba(34, 211, 238, 0.35); color: var(--cyan);
}
.history-meta { padding: 9px 11px 10px; display: flex; flex-direction: column; }
.history-meta strong { font-size: 11px; font-weight: 500; color: var(--text-dim); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.pri-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }

.select-sm { height: 30px; font-size: 11px; padding: 0 8px; min-width: 90px; }

.btn-danger {
  color: #fca5a5;
  border-color: rgba(251, 113, 133, 0.35);
  background: rgba(251, 113, 133, 0.08);
}
.btn-danger:hover { background: rgba(251, 113, 133, 0.16); color: #fecaca; }

.review-info { margin-bottom: 12px; }
.review-info .kv { margin-top: 0; }

.review-decision { display: flex; gap: 10px; }
.decision-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-dim);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s;
}
.decision-btn:hover { border-color: var(--line-strong); }
.decision-btn.active {
  border-color: rgba(34, 211, 238, 0.45);
  background: rgba(34, 211, 238, 0.1);
  color: var(--cyan);
}
.decision-btn:has(.amber).active {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.1);
  color: var(--amber);
}

textarea.input { resize: vertical; min-height: 72px; font-family: inherit; }

.ta-r { text-align: right; }

@media (max-width: 1200px) {
  .span-2 { grid-column: span 1; }
  .history-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
