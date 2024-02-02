import './assets/main.css'

import { createApp } from 'vue'

import App from './App.vue'
const app = createApp(App)

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// import router from '@/router' // 引入路由
app.use(router)

import { createRouter, createWebHashHistory } from "vue-router"

app.use(ElementPlus);

import Login from '@/views/login.vue'
import regist from '@/views/regist.vue'

const routes = [
  { path: '/', component: regist },
  { path: '/login', component: Login }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})
// 5. 创建并挂载根实例
// const app = Vue.createApp({})
// export default router;
app.mount('#app')
