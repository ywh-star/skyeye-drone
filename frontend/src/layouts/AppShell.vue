<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import { useUiStore } from '@/stores/ui'
import { useAuthStore, type RoleId } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const system = useSystemStore()
const ui = useUiStore()
const auth = useAuthStore()

// 消费 skyeyePlugin 插件 provide 的全局配置（教程知识点：provide / inject）
const appName = inject<string>('appName', 'SkyEye 天穹')
const appVersion = inject<string>('appVersion', '1.0.0')

const searchInput = ref<HTMLInputElement | null>(null)
const now = ref(new Date())
let timer = 0

const icons: Record<string, string> = {
  console: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  detect: 'M12 3v3m0 12v3M3 12h3m12 0h3M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
  replay: 'M4 12a8 8 0 1 0 2.5-5.8M4 4v4h4M10 9l5 3-5 3z',
  dataset: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Zm0 0v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
  training: 'M4 18V9m5 9V5m5 13v-6m5 6V7M3 21h18',
}

interface NavItem {
  name: string
  label: string
  icon: string
  tag: string
  roles: RoleId[]
}

const nav: NavItem[] = [
  { name: 'console', label: '任务控制台', icon: 'console', tag: '总览', roles: ['pilot', 'analyst', 'admin'] },
  { name: 'detect', label: '检测工作台', icon: 'detect', tag: 'YOLO', roles: ['pilot', 'analyst', 'admin'] },
  { name: 'replay', label: '三维航迹回放', icon: 'replay', tag: '3D', roles: ['pilot', 'analyst'] },
  { name: 'dataset', label: 'VisDrone 数据集', icon: 'dataset', tag: '数据', roles: ['analyst', 'admin'] },
  { name: 'training', label: '模型训练中心', icon: 'training', tag: '训练', roles: ['admin'] },
]

const roleNav = computed(() => nav.filter((item) => item.roles.includes(auth.role)))

const filteredNav = computed(() => {
  const keyword = ui.search.trim().toLowerCase()
  if (!keyword) return roleNav.value
  return roleNav.value.filter((item) => item.label.toLowerCase().includes(keyword) || item.tag.toLowerCase().includes(keyword))
})

const title = computed(() => (route.meta.title as string) ?? '任务控制台')
const subtitle = computed(() => (route.meta.subtitle as string) ?? '')
const roleAccent = computed(() => auth.meta.accent)
const avatarText = computed(() => auth.callsign.slice(0, 2).toUpperCase() || auth.meta.label.slice(0, 1))
const operatorTitle = computed(() => `${auth.meta.label} · ${auth.callsign || '未登录'}`)
const operatorSub = computed(() => auth.meta.desc)

function logout() {
  auth.logout()
  ui.push('已安全退出天穹系统')
  router.push('/')
}
const online = computed(() => Boolean(system.info))
const activeTasks = computed(() => system.overview?.active_tasks ?? 0)
const clock = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))
const dateText = computed(() =>
  now.value.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', weekday: 'short' }),
)

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (event.key === '/' && target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
    event.preventDefault()
    searchInput.value?.focus()
  }
  if (event.key === 'Escape' && document.activeElement === searchInput.value) {
    ui.search = ''
    searchInput.value?.blur()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  timer = window.setInterval(() => { now.value = new Date() }, 1000)
  if (!system.info) void system.refresh()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.clearInterval(timer)
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink to="/" class="brand">
        <span class="brand-mark">
          <svg viewBox="0 0 40 40" width="26" height="26" aria-hidden="true">
            <path d="M20 7 8 14v12l12 7 12-7V14L20 7Z" fill="none" stroke="currentColor" stroke-width="1.6" opacity=".55" />
            <circle cx="20" cy="20" r="3.2" fill="currentColor" />
            <path d="M20 16.8V8m0 24v-8.8M16.8 20H8m24 0h-8.8" stroke="currentColor" stroke-width="1.2" opacity=".8" />
            <path d="M10 12 6 8m24 4 4-4M10 28l-4 4m24-4 4 4" stroke="currentColor" stroke-width="1.1" opacity=".4" />
          </svg>
        </span>
        <span class="brand-text">
          <strong>SKYEYE</strong>
          <em>天穹 · 航拍智能</em>
        </span>
      </RouterLink>

      <p class="nav-label">作战域 / OPS</p>
      <nav class="nav">
        <RouterLink
          v-for="item in filteredNav"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-item"
          :class="{ active: route.name === item.name }"
        >
          <span class="nav-icon">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path :d="icons[item.icon]" />
            </svg>
          </span>
          <span class="nav-text">{{ item.label }}</span>
          <span class="nav-tag">{{ item.tag }}</span>
        </RouterLink>
        <p v-if="!filteredNav.length" class="nav-empty">没有匹配的模块</p>
      </nav>

      <div class="side-panel">
        <div class="side-row">
          <span class="dot" :class="online ? 'lime pulse' : 'amber pulse'" />
          <span>{{ online ? '后端在线' : '连接中…' }}</span>
          <span class="side-val mono">{{ activeTasks }} 任务</span>
        </div>
        <div class="side-row">
          <span class="dot cyan" />
          <span>推理设备</span>
          <span class="side-val mono">{{ system.info?.device ?? 'CPU' }}</span>
        </div>
        <div class="side-row">
          <span class="dot pink" />
          <span>VisDrone 样本</span>
          <span class="side-val mono">{{ system.info?.dataset.images ?? 0 }}</span>
        </div>
        <div class="side-bar"><span :style="{ width: online ? '100%' : '36%' }" /></div>
      </div>

      <div class="side-foot">
        <span class="tiny dim">Vue 3.5 · TS 5 · Three r172</span>
        <span class="tiny dim">{{ appName }} · v{{ appVersion }}</span>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="crumbs">
          <span class="upper">Mission</span>
          <span class="crumb-sep">/</span>
          <span class="crumb-current">{{ title }}</span>
          <span v-if="subtitle" class="crumb-sub">{{ subtitle }}</span>
        </div>

        <div class="top-actions">
          <label class="search">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
              <circle cx="11" cy="11" r="6.5" />
              <path d="m16 16 4 4" stroke-linecap="round" />
            </svg>
            <input
              ref="searchInput"
              v-model="ui.search"
              type="search"
              placeholder="搜索模块…"
              aria-label="搜索模块"
            />
            <kbd class="kbd">/</kbd>
          </label>

          <div class="clock">
            <span class="mono clock-time">{{ clock }}</span>
            <span class="tiny dim">{{ dateText }}</span>
          </div>

          <div class="divider-v" />

          <div class="operator">
            <span class="avatar" :class="`avatar-${roleAccent}`">{{ avatarText }}</span>
            <span class="operator-text">
              <strong>{{ operatorTitle }}</strong>
              <em>{{ operatorSub }}</em>
            </span>
            <button class="logout-btn" title="退出登录" @click="logout">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="M16 17l5-5-5-5" />
                <path d="M21 12H9" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main class="page">
        <RouterView v-slot="{ Component, route: current }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" :key="current.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px 14px 16px;
  border-right: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(7, 17, 29, 0.82), rgba(4, 9, 16, 0.9));
  backdrop-filter: blur(20px);
  z-index: 20;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 4px 8px 18px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--cyan);
  border: 1px solid rgba(34, 211, 238, 0.35);
  background: radial-gradient(circle at 30% 20%, rgba(34, 211, 238, 0.28), rgba(8, 20, 32, 0.9));
  box-shadow: 0 0 26px rgba(34, 211, 238, 0.22), inset 0 0 18px rgba(34, 211, 238, 0.08);
  flex-shrink: 0;
}

.brand-text { display: flex; flex-direction: column; line-height: 1.25; overflow: hidden; }
.brand-text strong { font-family: var(--font-num); font-size: 17px; letter-spacing: 0.26em; font-weight: 700; }
.brand-text em { font-style: normal; font-size: 10px; color: var(--muted); letter-spacing: 0.14em; white-space: nowrap; }

.nav-label { padding: 0 10px 8px; font-size: 9px; letter-spacing: 0.22em; color: #556b82; }

.nav { display: flex; flex-direction: column; gap: 3px; }

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 43px;
  padding: 0 10px;
  border-radius: 11px;
  color: var(--text-dim);
  font-size: 13px;
  transition: all 0.18s ease;
}

.nav-item:hover { background: rgba(34, 211, 238, 0.06); color: var(--text); }
.nav-item.active {
  color: var(--cyan);
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.15), rgba(34, 211, 238, 0.02));
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.18);
}
.nav-item.active::before {
  content: "";
  position: absolute;
  left: -14px;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 4px 4px 0;
  background: var(--cyan);
  box-shadow: 0 0 14px var(--cyan);
}

.nav-icon { display: grid; place-items: center; width: 22px; flex-shrink: 0; }
.nav-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nav-tag {
  font-family: var(--font-num);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--muted);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 1px 5px;
}
.nav-item.active .nav-tag { color: var(--cyan); border-color: rgba(34, 211, 238, 0.35); }
.nav-empty { padding: 12px 10px; font-size: 12px; color: var(--muted); }

.side-panel {
  margin-top: auto;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(6, 15, 26, 0.6);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.side-row { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-dim); }
.side-val { margin-left: auto; color: var(--text); font-size: 11px; }
.side-bar { height: 3px; border-radius: 99px; background: rgba(120, 180, 220, 0.14); overflow: hidden; margin-top: 4px; }
.side-bar span { display: block; height: 100%; background: linear-gradient(90deg, var(--cyan), var(--lime)); transition: width 1s ease; }

.side-foot { display: flex; flex-direction: column; gap: 2px; padding: 12px 8px 2px; }

.main { min-width: 0; display: flex; flex-direction: column; }

.topbar {
  position: sticky;
  top: 0;
  z-index: 15;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  height: 66px;
  padding: 0 28px;
  border-bottom: 1px solid var(--line);
  background: rgba(4, 10, 18, 0.72);
  backdrop-filter: blur(18px);
}

.crumbs { display: flex; align-items: center; gap: 9px; min-width: 0; }
.crumb-sep { color: #3d5368; }
.crumb-current { font-size: 14px; font-weight: 550; white-space: nowrap; }
.crumb-sub { font-size: 11px; color: var(--muted); padding-left: 10px; border-left: 1px solid var(--line); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.top-actions { display: flex; align-items: center; gap: 16px; }

.search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 9px;
  border-radius: 9px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.025);
  color: var(--muted);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search:focus-within { border-color: rgba(34, 211, 238, 0.4); box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.08); }
.search input { border: 0; background: transparent; outline: none; width: 108px; font-size: 12px; color: var(--text); }
.search input::placeholder { color: #52687e; }

.clock { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.2; }
.clock-time { font-size: 15px; color: var(--text); letter-spacing: 0.08em; }

.divider-v { width: 1px; height: 26px; background: var(--line); }

.operator { display: flex; align-items: center; gap: 9px; }
.avatar {
  width: 34px; height: 34px; border-radius: 10px;
  display: grid; place-items: center;
  font-family: var(--font-num); font-size: 12px; letter-spacing: 0.08em;
  color: var(--cyan);
  border: 1px solid rgba(34, 211, 238, 0.3);
  background: rgba(34, 211, 238, 0.1);
}
.avatar-lime { color: var(--lime); border-color: rgba(163, 230, 53, 0.35); background: rgba(163, 230, 53, 0.1); }
.avatar-amber { color: var(--amber); border-color: rgba(245, 158, 11, 0.35); background: rgba(245, 158, 11, 0.1); }

.logout-btn {
  width: 32px; height: 32px; border-radius: 9px;
  display: grid; place-items: center;
  color: var(--muted);
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  cursor: pointer;
  transition: all 0.18s;
}
.logout-btn:hover { color: var(--danger); border-color: rgba(251, 113, 133, 0.4); background: rgba(251, 113, 133, 0.08); }
.operator-text { display: flex; flex-direction: column; line-height: 1.3; }
.operator-text strong { font-size: 11px; font-weight: 550; }
.operator-text em { font-style: normal; font-size: 9px; color: var(--muted); letter-spacing: 0.1em; }

@media (max-width: 1100px) {
  .search, .operator-text, .crumb-sub { display: none; }
}

@media (max-width: 900px) {
  .brand-text, .nav-text, .nav-tag, .nav-label, .side-panel, .side-foot, .nav-empty { display: none; }
  .sidebar { padding: 16px 10px; align-items: center; }
  .brand { padding: 0 0 18px; }
  .nav-item { justify-content: center; padding: 0; width: 44px; }
  .nav-item.active::before { display: none; }
  .topbar { padding: 0 16px; height: 58px; }
  .clock { display: none; }
}
</style>
