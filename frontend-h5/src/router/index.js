/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/bind',
    name: 'Bind',
    component: () => import('@/views/bind/index.vue'),
    meta: { title: '绑定TA', requiresAuth: true }
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '首页', requiresAuth: true, hasCouple: true }
  },
  {
    path: '/menu',
    name: 'Menu',
    component: () => import('@/views/menu/index.vue'),
    meta: { title: '私密菜单', requiresAuth: true }
  },
  {
    path: '/menu/add',
    name: 'MenuAdd',
    component: () => import('@/views/menu/add.vue'),
    meta: { title: '添加菜单', requiresAuth: true }
  },
  {
    path: '/menu/:id',
    name: 'MenuDetail',
    component: () => import('@/views/menu/detail.vue'),
    meta: { title: '菜单详情', requiresAuth: true }
  },
  {
    path: '/anniversary',
    name: 'Anniversary',
    component: () => import('@/views/anniversary/index.vue'),
    meta: { title: '纪念日', requiresAuth: true }
  },
  {
    path: '/feed',
    name: 'Feed',
    component: () => import('@/views/feed/index.vue'),
    meta: { title: '投喂', requiresAuth: true }
  },
  {
    path: '/note',
    name: 'Note',
    component: () => import('@/views/note/index.vue'),
    meta: { title: '美食笔记', requiresAuth: true }
  },
  {
    path: '/wish',
    name: 'Wish',
    component: () => import('@/views/wish/index.vue'),
    meta: { title: '心愿单', requiresAuth: true }
  },
  {
    path: '/map',
    name: 'Map',
    component: () => import('@/views/map/index.vue'),
    meta: { title: '餐厅地图', requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/index.vue'),
    meta: { title: '设置', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 情侣私密菜单` : '情侣私密菜单'

  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && token) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
