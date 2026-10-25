<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import EChart from '@/components/ui/EChart.vue'
import ModalDialog from '@/components/ui/ModalDialog.vue'
import StatCard from '@/components/ui/StatCard.vue'
import { api } from '@/api/client'
import { useDatasetStore } from '@/stores/dataset'
import { useUiStore } from '@/stores/ui'
import type { GalleryItem, SampleDetail } from '@/types'

const dataset = useDatasetStore()
const ui = useUiStore()

const detail = ref<SampleDetail | null>(null)
const detailLoading = ref(false)

const summary = computed(() => dataset.summary)
const topClasses = computed(() => dataset.topClasses.slice(0, 8))

const barOption = computed(() => {
  const classes = [...dataset.topClasses].slice(0, 10).reverse()
  return {
    grid: { left: 78, right: 26, top: 10, bottom: 22 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(6,16,26,0.92)',
      borderColor: 'rgba(34,211,238,0.3)',
      textStyle: { color: '#e8f3ff', fontSize: 12 },
    },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#6c839c', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(120,190,235,0.08)' } },
    },
    yAxis: {
      type: 'category',
      data: classes.map((c) => c.name_cn),
      axisLabel: { color: '#a8bdd2', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar',
      barWidth: 11,
      data: classes.map((c) => ({
        value: c.count,
        itemStyle: {
          color: c.color,
          borderRadius: [0, 5, 5, 0],
          opacity: 0.85,
        },
      })),
      label: {
        show: true,
        position: 'right',
        color: '#a8bdd2',
        fontSize: 10,
        fontFamily: 'Consolas, monospace',
      },
    }],
  }
})

const pageList = computed(() => {
  const pages = dataset.pages
  const current = dataset.page
  const list: number[] = []
  for (let i = Math.max(1, current - 2); i <= Math.min(pages, current + 2); i += 1) list.push(i)
  return list
})

async function openSample(item: GalleryItem) {
  detail.value = { ...item, gt_count: item.objects, classes: item.classes, scene: '', gt: [] }
  detailLoading.value = true
  try {
    detail.value = await api.sample(item.id)
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '加载样本失败', 'error')
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detail.value = null
}

onMounted(async () => {
  try {
    await dataset.init()
  } catch (err) {
    ui.push(err instanceof Error ? err.message : '数据集加载失败', 'error')
  }
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1 class="page-title">VisDrone 数据集</h1>
        <p class="page-sub">真实无人机航拍影像 · YOLO 格式标注 · 10 类地面目标</p>
      </div>
      <div class="row wrap">
        <span class="chip cyan">VisDrone2019-DET</span>
        <span class="chip mono">{{ summary?.images ?? 0 }} 张影像</span>
        <span class="chip mono">{{ summary?.objects ?? 0 }} 个标注框</span>
      </div>
    </div>

    <div class="grid grid-4">
      <StatCard
        label="影像总数"
        :value="summary?.images ?? 0"
        unit="张"
        accent="cyan"
        hint="已入库航拍帧"
        :trend="[6, 8, 7, 9, 11, 10, 13, 12]"
      />
      <StatCard
        label="标注目标"
        :value="summary?.objects ?? 0"
        unit="个"
        accent="lime"
        hint="YOLO 归一化标注"
        :trend="[9, 7, 11, 10, 13, 12, 15, 14]"
      />
      <StatCard
        label="平均目标数"
        :value="summary?.avg_objects ?? 0"
        unit="/ 张"
        accent="amber"
        hint="单帧目标密度"
        :trend="[4, 6, 5, 7, 6, 8, 7, 9]"
      />
      <StatCard
        label="类别数"
        :value="summary?.classes.length ?? 0"
        unit="类"
        accent="violet"
        hint="行人 / 车辆 / 三轮车等"
        :trend="[3, 5, 4, 6, 5, 7, 8, 10]"
      />
    </div>

    <div class="dataset-grid section-gap">
      <BaseCard title="类别分布" subtitle="按标注框数量降序">
        <template #actions>
          <span class="chip mono">{{ summary?.size_mb ?? 0 }} MB</span>
        </template>
        <div v-if="topClasses.length" class="class-body">
          <EChart :option="barOption" :height="292" />
          <div class="class-list">
            <button
              class="class-row"
              :class="{ active: dataset.classId === undefined }"
              type="button"
              @click="dataset.setFilter(undefined)"
            >
              <span class="class-swatch all" />
              <span class="class-name">全部类别</span>
              <span class="class-count mono">{{ summary?.objects ?? 0 }}</span>
            </button>
            <button
              v-for="item in summary?.classes ?? []"
              :key="item.id"
              class="class-row"
              :class="{ active: dataset.classId === item.id }"
              type="button"
              @click="dataset.setFilter(item.id)"
            >
              <span class="class-swatch" :style="{ background: item.color, boxShadow: `0 0 8px ${item.color}` }" />
              <span class="class-name">{{ item.name_cn }}<small>{{ item.name }}</small></span>
              <span class="class-count mono">{{ item.count }}</span>
            </button>
          </div>
        </div>
        <EmptyState v-else title="暂无类别统计" description="数据集尚未准备完成" />
      </BaseCard>

      <BaseCard title="数据说明" subtitle="来源与使用许可">
        <div class="info-list">
          <div class="info-row">
            <span class="upper">数据来源</span>
            <b>{{ summary?.source ?? 'VisDrone2019-DET' }}</b>
          </div>
          <div class="info-row">
            <span class="upper">数据划分</span>
            <b>{{ summary?.split ?? 'val' }}（验证子集）</b>
          </div>
          <div class="info-row">
            <span class="upper">标注格式</span>
            <b class="mono">class cx cy w h（归一化）</b>
          </div>
          <div class="info-row">
            <span class="upper">许可协议</span>
            <b>{{ summary?.license ?? 'CC BY-SA 3.0' }}</b>
          </div>
          <div class="info-row">
            <span class="upper">标签文件</span>
            <b class="mono">{{ summary?.labels ?? 0 }} 个 .txt</b>
          </div>
        </div>
        <div class="source-note muted-box">
          <p class="tiny dim">
            数据来自天津大学 VisDrone 团队公开的无人机视觉数据集，覆盖城市道路、广场、公园等场景，
            包含行人、自行车、轿车、货车、公交车等 10 类目标，适合作为航拍小目标检测的训练与验证数据。
          </p>
        </div>
        <template #footer>
          <div class="row-between">
            <span class="tiny dim">浏览模式：点击缩略图查看标注框</span>
            <span class="chip lime">YOLO 兼容</span>
          </div>
        </template>
      </BaseCard>
    </div>

    <BaseCard class="section-gap" title="样本画廊" :subtitle="`共 ${dataset.total} 张${dataset.classId !== undefined ? ' · 已按类别筛选' : ''}`">
      <template #actions>
        <button v-if="dataset.classId !== undefined" class="btn btn-sm" @click="dataset.setFilter(undefined)">清除筛选</button>
        <button class="btn btn-sm" :disabled="dataset.loading" @click="dataset.loadGallery()">
          {{ dataset.loading ? '加载中…' : '刷新' }}
        </button>
      </template>

      <div v-if="dataset.loading" class="gallery-state">
        <span class="spinner" />
        <span class="tiny dim">正在读取航拍样本…</span>
      </div>
      <div v-else-if="dataset.items.length" class="gallery">
        <button
          v-for="item in dataset.items"
          :key="item.id"
          class="shot"
          type="button"
          @click="openSample(item)"
        >
          <div class="shot-media">
            <img :src="item.url" :alt="item.name" loading="lazy" />
            <span class="shot-count mono">{{ item.objects }} 目标</span>
            <span class="shot-reticle" />
          </div>
          <div class="shot-meta">
            <span class="shot-name mono">{{ item.name.replace('.jpg', '') }}</span>
            <div class="shot-tags">
              <span v-for="label in item.classes.slice(0, 3)" :key="label" class="mini-tag">{{ label }}</span>
              <span v-if="item.classes.length > 3" class="mini-tag">+{{ item.classes.length - 3 }}</span>
            </div>
          </div>
        </button>
      </div>
      <EmptyState v-else title="没有匹配的样本" description="换一个类别筛选条件再试试" />

      <template v-if="dataset.pages > 1" #footer>
        <div class="pager">
          <button class="btn btn-sm" :disabled="dataset.page <= 1" @click="dataset.setPage(dataset.page - 1)">上一页</button>
          <button
            v-for="page in pageList"
            :key="page"
            class="page-btn"
            :class="{ active: page === dataset.page }"
            type="button"
            @click="dataset.setPage(page)"
          >{{ page }}</button>
          <span class="tiny dim mono">/ {{ dataset.pages }}</span>
          <button class="btn btn-sm" :disabled="dataset.page >= dataset.pages" @click="dataset.setPage(dataset.page + 1)">下一页</button>
        </div>
      </template>
    </BaseCard>

    <ModalDialog :open="detail !== null" :title="detail ? `样本标注 · ${detail.name}` : '样本标注'" width="820px" @close="closeDetail">
      <div v-if="detail" class="detail">
        <div class="detail-canvas">
          <img :src="detail.url" :alt="detail.name" />
          <span
            v-for="(box, index) in detail.gt"
            :key="index"
            class="gt-box"
            :style="{
              left: `${box.x * 100}%`,
              top: `${box.y * 100}%`,
              width: `${box.w * 100}%`,
              height: `${box.h * 100}%`,
              borderColor: box.color,
              color: box.color,
              '--gt-color': box.color,
            }"
          >
            <span class="gt-label">{{ box.label_cn }}</span>
          </span>
          <div v-if="detailLoading" class="detail-loading">
            <span class="spinner" />
          </div>
        </div>
        <div class="detail-side">
          <div class="detail-kv">
            <div><span class="upper">尺寸</span><b class="mono">{{ detail.width }} × {{ detail.height }}</b></div>
            <div><span class="upper">标注数</span><b class="mono">{{ detail.gt.length || detail.gt_count }}</b></div>
            <div><span class="upper">场景</span><b>{{ detail.scene || '航拍城市场景' }}</b></div>
          </div>
          <div class="detail-classes">
            <span v-for="label in detail.classes" :key="label" class="chip lime">{{ label }}</span>
          </div>
          <div class="detail-list">
            <div v-for="(box, index) in detail.gt.slice(0, 30)" :key="index" class="detail-row">
              <span class="gt-dot" :style="{ background: box.color }" />
              <span>{{ box.label_cn }}</span>
              <span class="mono dim">{{ (box.area_ratio * 100).toFixed(2) }}%</span>
            </div>
            <p v-if="!detail.gt.length && !detailLoading" class="tiny dim">该样本暂无标注框</p>
          </div>
        </div>
      </div>
    </ModalDialog>
  </div>
</template>

<style scoped>
.dataset-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 16px; align-items: start; }

.class-body { display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 14px; align-items: start; }
.class-list { display: flex; flex-direction: column; gap: 5px; }
.class-row {
  display: flex; align-items: center; gap: 9px;
  padding: 7px 10px; border-radius: 8px;
  border: 1px solid transparent; background: rgba(255, 255, 255, 0.02);
  font-size: 12px; color: var(--text-dim); text-align: left;
  transition: all 0.16s;
}
.class-row:hover { border-color: var(--line); background: rgba(34, 211, 238, 0.05); }
.class-row.active { border-color: rgba(34, 211, 238, 0.42); background: rgba(34, 211, 238, 0.1); color: var(--text); }
.class-swatch { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
.class-swatch.all { background: linear-gradient(135deg, var(--cyan), var(--lime)); }
.class-name { flex: 1; display: flex; flex-direction: column; line-height: 1.25; }
.class-name small { font-size: 9px; color: var(--muted); letter-spacing: 0.04em; }
.class-count { font-size: 11px; color: var(--muted); }

.info-list { display: flex; flex-direction: column; gap: 10px; }
.info-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 12px; }
.info-row b { color: var(--text-dim); font-weight: 500; text-align: right; }
.source-note { margin-top: 14px; padding: 12px 14px; }
.source-note p { line-height: 1.7; }

.gallery-state { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 46px 0; }
.gallery { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.shot {
  border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
  background: rgba(5, 13, 22, 0.55); padding: 0; text-align: left;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}
.shot:hover { transform: translateY(-2px); border-color: var(--line-strong); box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4); }
.shot-media { position: relative; aspect-ratio: 16 / 10; overflow: hidden; background: #050d16; }
.shot-media img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
.shot:hover .shot-media img { transform: scale(1.06); }
.shot-count {
  position: absolute; right: 8px; bottom: 8px;
  padding: 2px 7px; border-radius: 6px; font-size: 10px;
  background: rgba(4, 11, 19, 0.82); border: 1px solid rgba(34, 211, 238, 0.35); color: var(--cyan);
}
.shot-reticle {
  position: absolute; inset: 8px; border: 1px solid rgba(34, 211, 238, 0.16);
  border-radius: 6px; pointer-events: none;
}
.shot-meta { padding: 9px 11px 11px; display: flex; flex-direction: column; gap: 6px; }
.shot-name { font-size: 11px; color: var(--text-dim); letter-spacing: 0.02em; }
.shot-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.mini-tag { font-size: 9px; padding: 1px 6px; border-radius: 4px; color: var(--muted); background: rgba(255, 255, 255, 0.04); border: 1px solid var(--line); }

.pager { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
.page-btn {
  width: 28px; height: 28px; border-radius: 7px; font-size: 11px;
  border: 1px solid var(--line); background: transparent; color: var(--muted);
  font-family: var(--font-num);
}
.page-btn:hover { color: var(--text); border-color: var(--line-strong); }
.page-btn.active { color: var(--cyan); border-color: rgba(34, 211, 238, 0.45); background: rgba(34, 211, 238, 0.12); }

.detail { display: grid; grid-template-columns: minmax(0, 1.6fr) 230px; gap: 16px; }
.detail-canvas { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--line); background: #050d16; }
.detail-canvas img { width: 100%; display: block; }
.gt-box { position: absolute; border: 1px solid; box-sizing: border-box; }
.gt-label {
  position: absolute; left: -1px; top: -16px;
  padding: 0 5px; border-radius: 3px 3px 3px 0;
  font-size: 9px; line-height: 15px; white-space: nowrap;
  background: var(--gt-color);
  color: #03131c;
}
.detail-loading { position: absolute; inset: 0; display: grid; place-items: center; background: rgba(4, 11, 19, 0.4); }
.detail-side { display: flex; flex-direction: column; gap: 12px; }
.detail-kv { display: flex; flex-direction: column; gap: 8px; }
.detail-kv div { display: flex; flex-direction: column; gap: 2px; }
.detail-kv b { font-size: 13px; color: var(--text); font-weight: 500; }
.detail-classes { display: flex; flex-wrap: wrap; gap: 5px; }
.detail-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.detail-row { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-dim); padding: 4px 0; border-bottom: 1px solid rgba(120, 190, 235, 0.05); }
.detail-row span:nth-child(2) { flex: 1; }
.gt-dot { width: 6px; height: 6px; border-radius: 2px; flex-shrink: 0; }

@media (max-width: 1400px) {
  .gallery { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 1200px) {
  .dataset-grid, .class-body, .detail { grid-template-columns: 1fr; }
  .gallery { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .gallery { grid-template-columns: 1fr; }
}
</style>
