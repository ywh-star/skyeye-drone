<script setup lang="ts">
import { computed, defineAsyncComponent, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import { useUiStore } from '@/stores/ui'
import { useAuthStore, ROLES, type RoleId } from '@/stores/auth'

// 异步组件（教程知识点）：Three.js 场景体积较大，按需加载以缩短首屏时间
const HeroScene = defineAsyncComponent(() => import('@/components/three/HeroScene.vue'))

const router = useRouter()
const system = useSystemStore()
const ui = useUiStore()
const auth = useAuthStore()

const roles = [
  { id: 'pilot', label: ROLES.pilot.label, desc: ROLES.pilot.desc },
  { id: 'analyst', label: ROLES.analyst.label, desc: ROLES.analyst.desc },
  { id: 'admin', label: ROLES.admin.label, desc: ROLES.admin.desc },
]

const form = reactive({
  role: 'pilot',
  callsign: 'SKY-071',
  code: 'skyeye',
  remember: true,
})

const showCode = ref(false)
const submitting = ref(false)
const touched = ref(false)

const errors = computed(() => ({
  callsign: form.callsign.trim().length < 2 ? '呼号至少 2 个字符' : '',
  code: form.code.trim().length < 4 ? '口令至少 4 位' : '',
}))
const valid = computed(() => !errors.value.callsign && !errors.value.code)
const roleLabel = computed(() => roles.find((r) => r.id === form.role)?.label ?? '')

const fieldLabel = computed(() => {
  if (form.role === 'analyst') return '分析师工号'
  if (form.role === 'admin') return '管理员账号'
  return '飞手呼号'
})
const fieldHint = computed(() => {
  if (form.role === 'analyst') return 'ANALYST ID'
  if (form.role === 'admin') return 'ADMIN ACCOUNT'
  return 'CALLSIGN'
})

async function submit() {
  touched.value = true
  if (!valid.value || submitting.value) return
  submitting.value = true
  await new Promise((resolve) => window.setTimeout(resolve, 760))
  auth.login(form.role as RoleId, form.callsign.trim())
  ui.push(`身份校验通过，${roleLabel.value} ${form.callsign} 已接入天穹`)
  await router.push('/console')
  submitting.value = false
}
</script>

<template>
  <div class="landing">
    <HeroScene />

    <header class="land-top">
      <div class="land-brand">
        <span class="mark">
          <svg viewBox="0 0 40 40" width="24" height="24">
            <path d="M20 7 8 14v12l12 7 12-7V14L20 7Z" fill="none" stroke="currentColor" stroke-width="1.6" opacity=".6" />
            <circle cx="20" cy="20" r="3" fill="currentColor" />
            <path d="M20 17V9m0 22v-8M17 20H9m22 0h-8" stroke="currentColor" stroke-width="1.2" opacity=".85" />
          </svg>
        </span>
        <span class="land-brand-text">
          <strong>SKYEYE</strong>
          <em>天穹 · 无人机航拍智能检测</em>
        </span>
      </div>

      <nav class="land-nav">
        <RouterLink to="/detect">检测工作台</RouterLink>
        <RouterLink to="/dataset">VisDrone 数据</RouterLink>
        <RouterLink to="/training">模型训练</RouterLink>
      </nav>

      <div class="land-status">
        <span class="dot" :class="system.info ? 'lime pulse' : 'amber pulse'" />
        <span class="tiny">{{ system.info ? '系统在线' : '正在连接' }}</span>
        <span class="chip cyan mono">v1.0</span>
      </div>
    </header>

    <main class="land-main">
      <section v-reveal class="land-copy">
        <p class="eyebrow">
          <span class="line" />
          UAV AERIAL INTELLIGENCE · 2026
        </p>

        <h1 class="land-title">
          让每一帧航拍<br />
          都被<span class="grad">理解</span>
        </h1>

        <p class="land-desc">
          基于 YOLOv8 的无人机航拍目标检测与三维任务回放平台。融合
          Vue 3 响应式系统、TypeScript 类型约束与 Three.js 空间渲染，
          把城市上空的车流、人群与道路设施，转译为可研判的数字态势。
        </p>

        <ul class="land-tags">
          <li><i class="dot lime" />YOLOv8 实时推理</li>
          <li><i class="dot cyan" />VisDrone 真实航拍数据</li>
          <li><i class="dot pink" />Three.js 三维重建</li>
          <li><i class="dot amber" />断点续训</li>
        </ul>

        <div class="land-stats">
          <div class="land-stat">
            <span class="mono">{{ system.info?.dataset.images ?? 60 }}</span>
            <em>航拍样本</em>
          </div>
          <div class="land-stat">
            <span class="mono">10</span>
            <em>VisDrone 类别</em>
          </div>
          <div class="land-stat">
            <span class="mono">{{ system.info?.ultralytics ?? '8.4' }}</span>
            <em>Ultralytics</em>
          </div>
          <div class="land-stat">
            <span class="mono">3</span>
            <em>核心前端技术</em>
          </div>
        </div>

        <div class="land-cta">
          <RouterLink to="/console" class="btn btn-primary btn-lg">
            进入任务控制台
            <span class="arrow">→</span>
          </RouterLink>
          <RouterLink to="/detect" class="btn btn-lg">查看检测成果</RouterLink>
        </div>
      </section>

      <section v-reveal="140" class="login-wrap">
        <div class="login-card">
          <div class="login-head">
            <div>
              <p class="upper">Mission Access</p>
              <h2>任务接入</h2>
            </div>
            <span class="chip cyan mono">SECURE</span>
          </div>

          <div class="role-tabs">
            <button
              v-for="role in roles"
              :key="role.id"
              type="button"
              class="role-tab"
              :class="{ active: form.role === role.id }"
              @click="form.role = role.id"
            >
              <strong>{{ role.label }}</strong>
              <em>{{ role.desc }}</em>
            </button>
          </div>

          <form class="login-form" @submit.prevent="submit">
            <label class="field">
              <span class="field-label">{{ fieldLabel }} <span class="tiny dim">{{ fieldHint }}</span></span>
              <input v-model="form.callsign" class="input" placeholder="输入 2 位以上标识" autocomplete="username" />
              <span v-if="touched && errors.callsign" class="err">{{ errors.callsign }}</span>
            </label>

            <label class="field">
              <span class="field-label">接入口令 <span class="tiny dim">ACCESS CODE</span></span>
              <div class="code-row">
                <input
                  v-model="form.code"
                  class="input"
                  :type="showCode ? 'text' : 'password'"
                  placeholder="演示口令：skyeye"
                  autocomplete="current-password"
                />
                <button type="button" class="btn btn-sm code-toggle" @click="showCode = !showCode">
                  {{ showCode ? '隐藏' : '显示' }}
                </button>
              </div>
              <span v-if="touched && errors.code" class="err">{{ errors.code }}</span>
            </label>

            <div class="login-row">
              <label class="remember">
                <button type="button" class="switch" :class="{ on: form.remember }" @click="form.remember = !form.remember" aria-label="保持会话" />
                保持本机会话
              </label>
              <span class="tiny dim">演示环境 · 任意 4 位口令</span>
            </div>

            <button class="btn btn-primary btn-block btn-lg" type="submit" :disabled="submitting">
              <span v-if="submitting" class="spinner" />
              {{ submitting ? '正在建立链路…' : '接入天穹系统' }}
            </button>
          </form>

          <div class="login-foot">
            <span class="tiny dim">数据源：VisDrone2019-DET · CC BY-NC-SA 3.0</span>
            <span class="tiny dim mono">Vue 3.5 / TS 5 / Three r172</span>
          </div>
        </div>

        <div class="login-deco">
          <span /><span /><span /><span />
        </div>
      </section>
    </main>

    <footer class="land-foot">
      <div class="ticker">
        <span class="ticker-label">LIVE</span>
        <span class="ticker-item mono">{{ system.info?.device ?? 'CPU' }} INFERENCE</span>
        <span class="ticker-sep">•</span>
        <span class="ticker-item mono">{{ system.info?.torch ? `TORCH ${system.info.torch}` : 'TORCH 2.5' }}</span>
        <span class="ticker-sep">•</span>
        <span class="ticker-item">YOLOv8 · FastAPI · Pinia · Vue Router</span>
      </div>
      <div class="land-meta">
        <span>© 2026 SKYEYE LAB</span>
        <span>课程实验 · 计算机视觉 × Web 前端</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #040810;
}

.land-top {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 44px;
}

.land-brand { display: flex; align-items: center; gap: 12px; }
.mark {
  width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  color: var(--cyan);
  border: 1px solid rgba(34, 211, 238, 0.38);
  background: radial-gradient(circle at 30% 20%, rgba(34, 211, 238, 0.25), rgba(6, 16, 26, 0.9));
  box-shadow: 0 0 24px rgba(34, 211, 238, 0.24);
}
.land-brand-text { display: flex; flex-direction: column; line-height: 1.25; }
.land-brand-text strong { font-family: var(--font-num); font-size: 17px; letter-spacing: 0.3em; font-weight: 700; }
.land-brand-text em { font-style: normal; font-size: 10px; color: var(--muted); letter-spacing: 0.1em; }

.land-nav { display: flex; gap: 26px; font-size: 12px; color: var(--text-dim); }
.land-nav a { position: relative; transition: color 0.2s; }
.land-nav a:hover { color: var(--cyan); }
.land-nav a::after {
  content: ""; position: absolute; left: 0; bottom: -5px; height: 1px; width: 0;
  background: var(--cyan); transition: width 0.24s ease;
}
.land-nav a:hover::after { width: 100%; }

.land-status { display: flex; align-items: center; gap: 9px; }

.land-main {
  position: relative;
  z-index: 3;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 430px);
  align-items: center;
  gap: 60px;
  padding: 10px 60px 40px 64px;
}

.land-copy { max-width: 620px; }

.eyebrow { display: flex; align-items: center; gap: 12px; font-family: var(--font-num); font-size: 11px; letter-spacing: 0.22em; color: var(--cyan); }
.eyebrow .line { width: 34px; height: 1px; background: linear-gradient(90deg, var(--cyan), transparent); }

.land-title {
  margin-top: 18px;
  font-size: clamp(40px, 5vw, 68px);
  line-height: 1.08;
  font-weight: 680;
  letter-spacing: -0.01em;
}
.grad {
  background: linear-gradient(100deg, #22d3ee 10%, #a3e635 55%, #f472b6 95%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  position: relative;
}
.grad::after {
  content: "";
  position: absolute; left: 0; right: 0; bottom: 6px; height: 10px;
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.28), transparent);
  filter: blur(6px);
}

.land-desc { margin-top: 22px; max-width: 540px; color: var(--text-dim); font-size: 14px; line-height: 1.9; }

.land-tags { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 24px; font-size: 12px; color: var(--text-dim); }
.land-tags li { display: flex; align-items: center; gap: 8px; }

.land-stats { display: flex; gap: 38px; margin-top: 34px; }
.land-stat { display: flex; flex-direction: column; gap: 2px; }
.land-stat span { font-size: 27px; font-weight: 600; color: var(--text); letter-spacing: 0.03em; }
.land-stat em { font-style: normal; font-size: 11px; color: var(--muted); letter-spacing: 0.06em; }

.land-cta { display: flex; gap: 12px; margin-top: 34px; }
.btn-lg { height: 46px; padding: 0 22px; border-radius: 12px; font-size: 14px; }
.arrow { font-family: var(--font-num); transition: transform 0.22s; }
.btn:hover .arrow { transform: translateX(4px); }

.login-wrap { position: relative; }

.login-card {
  position: relative;
  border-radius: 20px;
  padding: 24px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  background: linear-gradient(160deg, rgba(10, 24, 38, 0.92), rgba(5, 12, 20, 0.88));
  backdrop-filter: blur(22px);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.login-card::before {
  content: "";
  position: absolute; inset: -1px;
  border-radius: 20px;
  background: linear-gradient(140deg, rgba(34, 211, 238, 0.45), transparent 35%, transparent 70%, rgba(163, 230, 53, 0.25));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  padding: 1px;
  pointer-events: none;
}

.login-head { display: flex; align-items: flex-start; justify-content: space-between; }
.login-head h2 { font-size: 22px; font-weight: 620; margin-top: 4px; }

.role-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 20px; }
.role-tab {
  text-align: left;
  padding: 10px 11px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.025);
  transition: all 0.2s;
}
.role-tab strong { display: block; font-size: 12px; font-weight: 600; color: var(--text-dim); }
.role-tab em { font-style: normal; display: block; font-size: 9px; color: var(--muted); margin-top: 3px; line-height: 1.4; }
.role-tab:hover { border-color: var(--line-strong); }
.role-tab.active {
  border-color: rgba(34, 211, 238, 0.45);
  background: rgba(34, 211, 238, 0.1);
  box-shadow: inset 0 0 16px rgba(34, 211, 238, 0.08);
}
.role-tab.active strong { color: var(--cyan); }

.login-form { margin-top: 20px; }
.field { margin-bottom: 14px; }
.code-row { display: flex; gap: 8px; align-items: center; }
.code-row .input { flex: 1; }
.code-toggle { flex-shrink: 0; min-width: 52px; color: var(--cyan); border-color: rgba(34, 211, 238, 0.3); }
.err { font-size: 11px; color: var(--danger); }

.login-row { display: flex; align-items: center; justify-content: space-between; margin: 4px 0 16px; }
.remember { display: flex; align-items: center; gap: 9px; font-size: 12px; color: var(--text-dim); cursor: pointer; }

.login-foot { display: flex; justify-content: space-between; gap: 10px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line); }

.login-deco { position: absolute; inset: -14px; pointer-events: none; }
.login-deco span { position: absolute; width: 20px; height: 20px; border-color: rgba(34, 211, 238, 0.5); border-style: solid; }
.login-deco span:nth-child(1) { top: 0; left: 0; border-width: 1px 0 0 1px; }
.login-deco span:nth-child(2) { top: 0; right: 0; border-width: 1px 1px 0 0; }
.login-deco span:nth-child(3) { bottom: 0; left: 0; border-width: 0 0 1px 1px; }
.login-deco span:nth-child(4) { bottom: 0; right: 0; border-width: 0 1px 1px 0; }

.land-foot {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 44px 20px;
  border-top: 1px solid rgba(120, 190, 235, 0.1);
  background: linear-gradient(180deg, transparent, rgba(3, 7, 12, 0.65));
}
.ticker { display: flex; align-items: center; gap: 12px; font-size: 10px; color: var(--muted); letter-spacing: 0.08em; }
.ticker-label { color: var(--lime); border: 1px solid rgba(163, 230, 53, 0.35); padding: 2px 6px; border-radius: 4px; font-size: 9px; letter-spacing: 0.16em; }
.ticker-sep { color: #2f4559; }
.land-meta { display: flex; gap: 22px; font-size: 10px; color: #4d6379; }

@media (max-width: 1180px) {
  .land-main { grid-template-columns: 1fr; gap: 40px; padding: 20px 44px 40px; }
  .login-wrap { max-width: 440px; }
  .land-foot { flex-direction: column; align-items: flex-start; gap: 8px; }
}

@media (max-width: 720px) {
  .land-top { padding: 16px 20px; }
  .land-nav { display: none; }
  .land-main { padding: 8px 20px 30px; }
  .land-title { font-size: 40px; }
  .land-stats { gap: 22px; flex-wrap: wrap; }
  .land-foot { padding: 14px 20px 18px; }
  .ticker { flex-wrap: wrap; }
  .land-meta { flex-direction: column; gap: 2px; }
}
</style>
