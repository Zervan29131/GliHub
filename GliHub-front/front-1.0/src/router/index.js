// // 此文件专门负责项目的路由
//导入vue-router
import { createRouter, createWebHashHistory, } from 'vue-router'
//导入组件
import Login from '@/views/login.vue'
// import regist from '@/views/regist.vue'
import Home from '@/views/home.vue'

// import ArticleCategoryVue from '@/views/article/ArticleCategory.vue'
// import UserAvatarVue from '@/views/user/UserAvatar.vue'
// import UserResetPasswordVue from '@/views/user/UserResetPassword.vue'
//用户管理
import UserInfoVue from '@/views/user/UserInfo.vue'
import UserAreaVue from '@/views/user/UserArea.vue'
import UserEquipmentVue from '@/views/user/UserEquipment.vue'
//安全评价
import Evaluate from '@/views//evaluate/Evaluate.vue'


import ArticleManageVue from '@/views/user/UserInfo.vue'


const routes = [
  // { path: '/regist', component: regist },
  { path: '/login', component: Login },
  {
    path: '/', component: Home,
    //重定向
    redirect: '/article/manage',
    //子路由
    children: [
      // { path: '/article/category', component: ArticleCategoryVue },
      { path: '/article/manage', component: ArticleManageVue },
      //用户管理
      { path: '/user/info', component: UserInfoVue },
      { path: '/user/area', component: UserAreaVue },
      { path: '/user/equipment', component: UserEquipmentVue },
      //安全评价
      { path: '/evaluate/Evaluate', component: Evaluate },
      {
        path: '/views/user',
        name: 'user',
        meta: {
            title: '个人中心',
        },
        component: () => import(/* webpackChunkName: "user" */ '../views/user.vue'),
    },


      // { path: '/user/avatar', component: UserAvatarVue },
      // { path: '/user/password', component: UserResetPasswordVue },
    ]
  }

]

//创建路由实例并传递 `routes` 配置
const router = createRouter({
  history: createWebHashHistory(),
  routes, // `routes: routes` 的缩写
})
export default router;
//导出router
