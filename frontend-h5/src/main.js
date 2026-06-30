import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { Lazyload } from 'vant'
import router from './router'
import App from './App.vue'
import 'vant/lib/index.css'
import './assets/styles/main.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Lazyload)

app.mount('#app')
