// // 此文件专门负责项目的路由

import {
    createRouter,
    createWebHashHistory,
} from 'vue-router'
import Login from '@/views/login.vue'
import regist from '@/views/regist.vue'
import Home from '@/views/Home.vue'

const routes = [
  { path: '/regist', component: regist },
  { path: '/login', component: Login },
  { path: '/', component: Home }
]

//3. 创建路由实例并传递 `routes` 配置
const router = createRouter({
    history: createWebHashHistory(),
    routes, // `routes: routes` 的缩写
})
export default router;
//导出router
