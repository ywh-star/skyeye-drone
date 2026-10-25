import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore, type RoleId } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'welcome',
    component: () => import('@/views/LandingView.vue'),
    meta: { title: '接入天穹', layout: 'blank' },
  },
  {
    path: '/console',
    name: 'console',
    component: () => import('@/views/ConsoleView.vue'),
    meta: {
      title: '任务控制台',
      layout: 'app',
      subtitle: '航拍任务、模型态势与检测成果总览',
      roles: ['pilot', 'analyst', 'admin'] as RoleId[],
    },
  },
  {
    path: '/detect',
    name: 'detect',
    component: () => import('@/views/DetectView.vue'),
    meta: {
      title: '检测工作台',
      layout: 'app',
      subtitle: '上传或选择航拍影像，YOLOv8 实时推理与三维复核',
      roles: ['pilot', 'analyst', 'admin'] as RoleId[],
    },
  },
  {
    path: '/replay',
    name: 'replay',
    component: () => import('@/views/ReplayView.vue'),
    meta: {
      title: '三维航迹回放',
      layout: 'app',
      subtitle: '基于 Three.js 的飞行航迹与目标落点重建',
      roles: ['pilot', 'analyst'] as RoleId[],
    },
  },
  {
    path: '/dataset',
    name: 'dataset',
    component: () => import('@/views/DatasetView.vue'),
    meta: {
      title: 'VisDrone 数据集',
      layout: 'app',
      subtitle: '真实无人机航拍样本、类别分布与标注浏览',
      roles: ['analyst', 'admin'] as RoleId[],
    },
  },
  {
    path: '/training',
    name: 'training',
    component: () => import('@/views/TrainingView.vue'),
    meta: {
      title: '模型训练中心',
      layout: 'app',
      subtitle: 'YOLOv8 微调、实时日志与断点续训',
      roles: ['admin'] as RoleId[],
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '信号丢失', layout: 'blank' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved ?? { top: 0, behavior: 'smooth' },
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const isApp = to.meta.layout === 'app'

  if (to.name === 'welcome' && auth.loggedIn) {
    return { name: 'console' }
  }

  if (isApp && !auth.loggedIn) {
    return { name: 'welcome' }
  }

  const allowed = to.meta.roles as RoleId[] | undefined
  if (isApp && allowed && !allowed.includes(auth.role)) {
    return { name: 'console' }
  }

  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '无人机航拍智能检测'
  document.title = `${title} · SkyEye 天穹`
})

export default router
