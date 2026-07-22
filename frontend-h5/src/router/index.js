/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import { logUiEvent } from '@/composables/useStructuredLog'

const unavailableView = () => import('@/views/states/UnavailableView.vue')

export const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', guest: true, requiresAuth: false, requiresCouple: false, shell: false }
  },
  {
    path: '/bind',
    name: 'Bind',
    component: () => import('@/views/bind/index.vue'),
    meta: { title: '绑定TA', requiresAuth: true, requiresCouple: false, shell: false }
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '首页', requiresAuth: true, requiresCouple: true, hasCouple: true, shell: true, tab: '星球' }
  },
  {
    path: '/menu',
    name: 'Menu',
    component: () => import('@/views/menu/index.vue'),
    meta: { title: '私密菜单', requiresAuth: true, requiresCouple: true, shell: true, tab: '菜单' }
  },
  {
    path: '/feed',
    name: 'Feed',
    component: () => import('@/views/feed/index.vue'),
    meta: { title: '投喂', requiresAuth: true, requiresCouple: true, shell: true, tab: '投喂' }
  },
  {
    path: '/memories',
    name: 'Memories',
    component: unavailableView,
    meta: { title: '回忆', requiresAuth: true, requiresCouple: true, shell: true, tab: '回忆' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/index.vue'),
    meta: { title: '设置', requiresAuth: true, requiresCouple: false, shell: true, tab: '我们' }
  },
  {
    path: '/menu/add',
    name: 'MenuAdd',
    component: () => import('@/views/menu/add.vue'),
    meta: { title: '添加菜单', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/menu/:id/edit',
    name: 'MenuEdit',
    component: () => import('@/views/menu/add.vue'),
    meta: { title: '编辑菜单', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/menu/:id',
    name: 'MenuDetail',
    component: () => import('@/views/menu/detail.vue'),
    meta: { title: '菜单详情', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/recipe/add',
    redirect: '/recipes/new'
  },
  {
    path: '/anniversary',
    name: 'Anniversary',
    component: () => import('@/views/anniversary/index.vue'),
    meta: { title: '纪念日', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/note',
    name: 'Note',
    component: () => import('@/views/note/index.vue'),
    meta: { title: '美食笔记', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/wish',
    name: 'Wish',
    component: () => import('@/views/wish/index.vue'),
    meta: { title: '心愿单', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/map',
    name: 'Map',
    component: () => import('@/views/map/index.vue'),
    meta: { title: '餐厅地图', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/recipes',
    name: 'Recipes',
    component: () => import('@/views/recipe/index.vue'),
    meta: { title: '菜谱', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/recipes/new',
    name: 'RecipeNew',
    component: () => import('@/views/recipe/add.vue'),
    meta: { title: '新建菜谱', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/recipes/:id/edit',
    name: 'RecipeEdit',
    component: () => import('@/views/recipe/add.vue'),
    meta: { title: '编辑菜谱', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/recipes/:id',
    name: 'RecipeDetail',
    component: () => import('@/views/recipe/detail.vue'),
    meta: { title: '菜谱详情', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/memories/notes/new',
    name: 'MemoryNoteNew',
    component: unavailableView,
    meta: { title: '新建回忆', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/memories/notes/:id',
    name: 'MemoryNoteDetail',
    component: unavailableView,
    meta: { title: '回忆详情', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/ai',
    name: 'Ai',
    component: unavailableView,
    meta: { title: 'AI 助手', requiresAuth: true, requiresCouple: true, shell: true }
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: unavailableView,
    meta: { title: '通知', requiresAuth: true, requiresCouple: false, shell: true }
  },
  {
    path: '/legal',
    name: 'Legal',
    component: unavailableView,
    meta: { title: '协议与隐私', requiresAuth: false, requiresCouple: false, shell: false }
  },
  {
    path: '/states',
    name: 'States',
    component: unavailableView,
    meta: { title: '状态', requiresAuth: true, requiresCouple: false, shell: true }
  }
]

const hasCoupleSnapshot = (storage) => {
  const rawCoupleInfo = storage?.getItem('coupleInfo')
  if (!rawCoupleInfo) return false

  try {
    return Boolean(JSON.parse(rawCoupleInfo))
  } catch (error) {
    logUiEvent('route_couple_snapshot_invalid', {
      module: 'router',
      operation: 'read_couple_snapshot',
      result: 'invalid_json',
      durationMs: 0,
      errorCode: 'INVALID_COUPLE_SNAPSHOT'
    })
    return false
  }
}

export const createCosmosRouter = ({
  history = createWebHistory(),
  storage = globalThis.localStorage
} = {}) => {
  const router = createRouter({ history, routes })

  router.beforeEach((to) => {
    if (typeof document !== 'undefined') {
      document.title = to.meta.title ? `${to.meta.title} - 情侣私密菜单` : '情侣私密菜单'
    }

    const token = storage?.getItem('token')

    if (to.meta.requiresAuth && !token) {
      logUiEvent('route_guard_redirected', {
        module: 'router',
        operation: 'authorize',
        result: 'login_required',
        targetRoute: to.name || 'unknown',
        durationMs: 0
      })
      return { name: 'Login', query: { redirect: to.fullPath } }
    }

    if (to.meta.requiresCouple && !hasCoupleSnapshot(storage)) {
      logUiEvent('route_guard_redirected', {
        module: 'router',
        operation: 'authorize_couple',
        result: 'couple_required',
        targetRoute: to.name || 'unknown',
        durationMs: 0
      })
      return { name: 'Bind', query: { redirect: to.fullPath } }
    }

    if (to.meta.guest && token) {
      logUiEvent('route_guard_redirected', {
        module: 'router',
        operation: 'authorize_guest',
        result: 'authenticated_home',
        targetRoute: to.name || 'unknown',
        durationMs: 0
      })
      return { name: 'Home' }
    }

    logUiEvent('route_guard_allowed', {
      module: 'router',
      operation: 'authorize',
      result: 'allowed',
      targetRoute: to.name || 'unknown',
      durationMs: 0
    })
    return true
  })

  return router
}

const router = createCosmosRouter()

export default router
