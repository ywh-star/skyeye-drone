import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type RoleId = 'pilot' | 'analyst' | 'admin'

export interface RoleMeta {
  id: RoleId
  label: string
  desc: string
  title: string
  subtitle: string
  accent: string
}

export const ROLES: Record<RoleId, RoleMeta> = {
  pilot: {
    id: 'pilot',
    label: '飞手',
    desc: '航线执行 · 影像采集',
    title: '任务控制台',
    subtitle: '我的飞行任务、影像采集与航迹回放',
    accent: 'cyan',
  },
  analyst: {
    id: 'analyst',
    label: '分析师',
    desc: '目标复核 · 态势研判',
    title: '态势研判中心',
    subtitle: '检测成果复核、类别洞察与趋势研判',
    accent: 'lime',
  },
  admin: {
    id: 'admin',
    label: '管理员',
    desc: '模型训练 · 系统治理',
    title: '系统治理台',
    subtitle: '模型训练、数据集管理与全局态势总览',
    accent: 'amber',
  },
}

const STORAGE_KEY = 'skyeye.auth'

interface AuthState {
  role: RoleId
  callsign: string
}

function load(): AuthState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as AuthState
    if (parsed.role && ROLES[parsed.role]) return parsed
    return null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const persisted = load()
  const role = ref<RoleId>(persisted?.role ?? 'pilot')
  const callsign = ref<string>(persisted?.callsign ?? '')

  const loggedIn = computed(() => Boolean(callsign.value))
  const meta = computed(() => ROLES[role.value])

  function login(nextRole: RoleId, nextCallsign: string) {
    role.value = nextRole
    callsign.value = nextCallsign
    persist()
  }

  function logout() {
    role.value = 'pilot'
    callsign.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  function persist() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ role: role.value, callsign: callsign.value }),
    )
  }

  return { role, callsign, loggedIn, meta, login, logout }
})
