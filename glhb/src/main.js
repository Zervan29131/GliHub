
import './assets/main.scss'

import { createApp } from 'vue'
const app = createApp(App)

import App from "./App.vue"

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import router from '@/router'
app.use(router)
app.use(ElementPlus)
app.mount('#app')