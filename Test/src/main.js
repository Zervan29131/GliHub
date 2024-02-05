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
// import { createRouter, createWebHashHistory } from "vue-router"
// const VueRouter = createRouter()

// const Login = import('./views/login.vue');

// app.use(VueRouter);

// // const router = new VueRouter()
// app.mount('#app')
// new Vue({
//     render: h => h(App),  // render 函数将帮助解析模板，传入的参数 h 为一个函数，该函数可用来解析 App 这个组件
//     router // 路由 4
//   }).$mount('#app') // 将 App.vue 组件挂载到 index.html 中的 id 为 app 的 div 标签上

// import './assets/main.css'

// import { createApp } from 'vue'

// import App from './App.vue'
// const app = createApp(App)

// import ElementPlus from 'element-plus'
// import 'element-plus/dist/index.css'
// // import router from '@/router' // 引入路由
// app.use(router)

// import { createRouter, createWebHashHistory } from "vue-router"

// app.use(ElementPlus);

// import Login from '@/views/login.vue'
// import regist from '@/views/regist.vue'

// const routes = [
//   { path: '/', component: regist },
//   { path: '/login', component: Login }
// ]

// const router = createRouter({
//   history: createWebHashHistory(),
//   routes
// })
// // 5. 创建并挂载根实例
// // const app = Vue.createApp({})
// // export default router;
// app.mount('#app')