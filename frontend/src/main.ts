import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './style.css'
import { useAuth } from './composables/useAuth'

async function bootstrap() {
  const { restoreSession } = useAuth()
  await restoreSession()

  const app = createApp(App)
  app.use(ElementPlus)
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void bootstrap()
