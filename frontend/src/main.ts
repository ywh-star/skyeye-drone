import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { skyeyePlugin } from './plugins/skyeye'
import './styles/theme.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(skyeyePlugin)

app.config.errorHandler = (err, _instance, info) => {
  console.error('[SkyEye] 未捕获异常:', err, info)
}

app.mount('#app')
