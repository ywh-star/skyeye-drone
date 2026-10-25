import type { App } from 'vue'
import { vReveal } from '@/directives/reveal'

/**
 * 应用级插件：注册全局自定义指令、注入全局配置与埋点方法。
 */
export const skyeyePlugin = {
  install(app: App) {
    app.directive('reveal', vReveal)
    app.provide('appName', 'SkyEye 天穹')
    app.provide('appVersion', '1.0.0')
    app.config.globalProperties.$track = (event: string) => {
      if (import.meta.env.DEV) console.debug('[telemetry]', event)
    }
  },
}
