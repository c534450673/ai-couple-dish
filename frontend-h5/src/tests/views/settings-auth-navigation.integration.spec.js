import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

const transport = vi.hoisted(() => {
  const handlers = { request: null, response: null, responseError: null }
  const api = vi.fn()
  api.interceptors = {
    request: { use: vi.fn(handler => { handlers.request = handler }) },
    response: {
      use: vi.fn((handler, errorHandler) => {
        handlers.response = handler
        handlers.responseError = errorHandler
      })
    }
  }
  class CancelToken {
    constructor(executor) {
      executor(vi.fn())
    }
  }
  return {
    handlers,
    axios: {
      create: vi.fn(() => api),
      CancelToken,
      isCancel: vi.fn(() => false)
    }
  }
})

const session = vi.hoisted(() => ({
  router: {
    currentRoute: { value: { path: '/settings' } },
    replace: vi.fn(() => Promise.resolve()),
    push: vi.fn()
  },
  userStore: {
    token: 'local-session',
    userInfo: null,
    coupleInfo: { id: 17 },
    fetchUserInfo: vi.fn(),
    updateUserInfo: vi.fn(),
    getCoupleInfo: vi.fn(),
    logout: vi.fn(),
    clearLocalSession: vi.fn()
  },
  confirm: vi.fn(),
  toast: vi.fn(),
  logUiEvent: vi.fn()
}))

vi.mock('axios', () => ({ default: transport.axios }))
vi.mock('@/router', () => ({ default: session.router }))
vi.mock('@/stores/user', () => ({ useUserStore: () => session.userStore }))
vi.mock('vue-router', () => ({ useRouter: () => session.router }))
vi.mock('@/api', () => ({
  coupleApi: { applyUnbind: vi.fn() },
  uploadApi: { uploadImage: vi.fn() }
}))
vi.mock('vant', () => ({
  showConfirmDialog: session.confirm,
  showToast: session.toast
}))
vi.mock('@/composables/useStructuredLog', () => ({
  logUiEvent: session.logUiEvent,
  normalizeUiErrorCode: (error, fallback = 'UNKNOWN_ERROR') => String(error?.code ?? fallback)
}))

import SettingsView from '@/views/settings/index.vue'
import { isUnauthorizedNavigationStarted } from '@/api/request'

const mountSettings = () => mount(SettingsView, {
  global: {
    stubs: {
      RouterLink: { template: '<a><slot /></a>' },
      AsyncState: false
    }
  }
})

const triggerHttp401 = async () => {
  const config = { headers: {}, method: 'get', url: '/user/info', cache: false }
  transport.handlers.request(config)
  await expect(transport.handlers.response({
    config,
    data: { code: 401, message: 'expired' }
  })).rejects.toEqual({ code: 401, message: 'expired' })
  expect(isUnauthorizedNavigationStarted()).toBe(true)
}

describe('设置页与请求层未授权导航组合', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    localStorage.setItem('token', 'local-session')
    vi.clearAllMocks()
    session.router.currentRoute.value.path = '/settings'
    session.userStore.token = 'local-session'
    session.userStore.userInfo = null
    session.userStore.coupleInfo = { id: 17 }
    session.userStore.fetchUserInfo.mockResolvedValue({ data: { id: 42, nickName: '星河', avatarUrl: '/avatar.webp', memberLevel: 1 } })
    session.userStore.logout.mockResolvedValue(undefined)
    session.confirm.mockResolvedValue(undefined)

    const resetConfig = { headers: {}, method: 'get', url: '/reset', cache: false }
    transport.handlers.request(resetConfig)
    await transport.handlers.response({ config: resetConfig, data: { code: 200, data: null } })
  })

  it('真实 HTTP 401 后资料页不会二次 replace', async () => {
    session.userStore.fetchUserInfo.mockRejectedValue({ code: 401 })
    await triggerHttp401()

    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.find('[data-test="settings-unauthorized"]').exists()).toBe(true)
    expect(session.router.replace).toHaveBeenCalledOnce()
    expect(session.router.replace).toHaveBeenCalledWith('/login')
  })

  it('真实登出 HTTP 401 后设置页不会二次 replace，正常登出仍跳转一次', async () => {
    const wrapper = mountSettings()
    await flushPromises()
    await triggerHttp401()

    await wrapper.find('[data-test="logout-action"]').trigger('click')
    await flushPromises()

    expect(session.userStore.logout).toHaveBeenCalledOnce()
    expect(session.router.replace).toHaveBeenCalledOnce()
  })

  it('真实正常登出仍由设置页跳转一次', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    await wrapper.find('[data-test="logout-action"]').trigger('click')
    await flushPromises()

    expect(session.userStore.logout).toHaveBeenCalledOnce()
    expect(session.router.replace).toHaveBeenCalledOnce()
  })
})
