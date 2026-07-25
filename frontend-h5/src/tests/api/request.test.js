import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const transport = vi.hoisted(() => {
  const state = {
    requestHandler: null,
    responseHandler: null,
    responseErrorHandler: null
  }
  const api = vi.fn()
  api.interceptors = {
    request: {
      use: vi.fn((handler) => {
        state.requestHandler = handler
      })
    },
    response: {
      use: vi.fn((handler, errorHandler) => {
        state.responseHandler = handler
        state.responseErrorHandler = errorHandler
      })
    }
  }
  api.get = vi.fn()
  api.post = vi.fn()
  api.put = vi.fn()
  api.delete = vi.fn()

  class CancelToken {
    constructor(executor) {
      executor(vi.fn())
    }
  }

  return {
    api,
    axios: {
      CancelToken,
      create: vi.fn(() => api),
      isCancel: vi.fn(() => false)
    },
    state
  }
})

const session = vi.hoisted(() => ({
  router: {
    currentRoute: { value: { path: '/settings' } },
    push: vi.fn(() => Promise.resolve()),
    replace: vi.fn(() => Promise.resolve())
  },
  userStore: {
    clearLocalSession: vi.fn(),
    logout: vi.fn()
  },
  logUiEvent: vi.fn()
}))

vi.mock('axios', () => ({ default: transport.axios }))
vi.mock('@/router', () => ({ default: session.router }))
vi.mock('@/stores/user', () => ({ useUserStore: () => session.userStore }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: session.logUiEvent }))

import { resetRequestState } from '@/api/request'

describe('API Request Module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    localStorage.clear()
    session.router.currentRoute.value.path = '/settings'
    session.router.replace.mockResolvedValue(undefined)
    resetRequestState()
  })

  afterEach(() => {
    resetRequestState()
    vi.useRealTimers()
  })

  describe('BASE_URL Configuration', () => {
    it('should use default API path when env var is not set', async () => {
      // The actual test would check if the baseURL is set correctly
      // For now, we verify the module structure
      const apiModule = await import('@/api/request')
      expect(apiModule).toBeDefined()
    })
  })

  describe('retry state reset', () => {
    it('should cancel pending retry and prevent the old request from running', async () => {
      const config = { headers: {}, method: 'get', url: '/test' }
      transport.state.requestHandler(config)
      const error = { config, response: { status: 503 } }

      const retryResult = transport.state.responseErrorHandler(error).catch((caughtError) => caughtError)
      expect(config.__retryCount).toBe(1)

      resetRequestState()
      await vi.advanceTimersByTimeAsync(1000)

      await expect(retryResult).resolves.toBe(error)
      expect(transport.api).not.toHaveBeenCalled()
      expect(config.__retryCount).toBeUndefined()
    })

    it('should log retry metadata without the request path', async () => {
      const logSpy = vi.spyOn(console, 'info').mockImplementation(() => {})
      const config = { headers: {}, method: 'get', url: '/private-path' }
      transport.state.requestHandler(config)

      const retryPromise = transport.state.responseErrorHandler({ config, response: { status: 503 } })
      await vi.advanceTimersByTimeAsync(1000)
      await retryPromise

      expect(logSpy).toHaveBeenCalledWith('[request.retry.scheduled]', {
        attempt: 1,
        delayMs: 1000,
        reason: 'retryable_http_status'
      })
      expect(JSON.stringify(logSpy.mock.calls)).not.toContain('/private-path')
      logSpy.mockRestore()
    })
  })

  describe('cache opt-out', () => {
    it('cache:false 的 GET 不读取或写入内存缓存', () => {
      const config = { headers: {}, method: 'get', url: '/couple/codeInfo', cache: false }
      transport.state.requestHandler(config)
      transport.state.responseHandler({ config, data: { code: 200, data: { coupleCode: 'A1B2C3D4' } } })

      const repeatedConfig = { headers: {}, method: 'get', url: '/couple/codeInfo', cache: false }
      transport.state.requestHandler(repeatedConfig)

      expect(repeatedConfig.adapter).toBeUndefined()
    })
  })

  describe('unauthorized session cleanup', () => {
    it('业务码 401 只清理本机会话，不调用远程 logout', async () => {
      localStorage.setItem('token', 'expired-session')
      const config = { headers: {}, method: 'get', url: '/profile' }
      transport.state.requestHandler(config)

      await expect(transport.state.responseHandler({
        config,
        data: { code: 401, message: 'expired' }
      })).rejects.toEqual({ code: 401, message: 'expired' })

      expect(session.userStore.clearLocalSession).toHaveBeenCalledOnce()
      expect(session.userStore.logout).not.toHaveBeenCalled()
      expect(session.router.replace).toHaveBeenCalledOnce()
      expect(session.router.replace).toHaveBeenCalledWith('/login')
      expect(session.logUiEvent).toHaveBeenCalledWith(
        'request.auth.unauthorized',
        expect.objectContaining({
          module: 'request', operation: 'local_session_clear', result: 'success',
          durationMs: expect.any(Number), errorCode: 'NONE', redirectStarted: true
        })
      )
      expect(JSON.stringify(session.logUiEvent.mock.calls)).not.toContain('expired-session')
    })

    it('并发 HTTP 401 只触发一次登录页跳转且不递归调用远程 logout', async () => {
      localStorage.setItem('token', 'expired-session')
      const firstConfig = { headers: {}, method: 'get', url: '/first' }
      const secondConfig = { headers: {}, method: 'get', url: '/second' }
      transport.state.requestHandler(firstConfig)
      transport.state.requestHandler(secondConfig)

      await Promise.all([
        transport.state.responseErrorHandler({
          config: firstConfig,
          response: { status: 401 }
        }).catch(() => undefined),
        transport.state.responseErrorHandler({
          config: secondConfig,
          response: { status: 401 }
        }).catch(() => undefined)
      ])

      expect(session.userStore.clearLocalSession).toHaveBeenCalledTimes(2)
      expect(session.userStore.logout).not.toHaveBeenCalled()
      expect(session.router.replace).toHaveBeenCalledOnce()
      expect(session.router.replace).toHaveBeenCalledWith('/login')
    })
  })
})

describe('API Endpoints', () => {
  describe('User API', () => {
    it('should define loginByPhone endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.loginByPhone).toBeDefined()
      expect(typeof userApi.loginByPhone).toBe('function')
    })

    it('should define sendVerifyCode endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.sendVerifyCode).toBeDefined()
      expect(typeof userApi.sendVerifyCode).toBe('function')
    })

    it('should define getUserInfo endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.getUserInfo).toBeDefined()
      expect(typeof userApi.getUserInfo).toBe('function')
    })

    it('should define updateUserInfo endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.updateUserInfo).toBeDefined()
      expect(typeof userApi.updateUserInfo).toBe('function')
    })
  })

  describe('Couple API', () => {
    it('should define getCoupleInfo endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.getCoupleInfo).toBeDefined()
      expect(typeof coupleApi.getCoupleInfo).toBe('function')
    })

    it('should define getCoupleHome endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.getCoupleHome).toBeDefined()
      expect(typeof coupleApi.getCoupleHome).toBe('function')
    })

    it('should define generateCoupleCode endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.generateCoupleCode).toBeDefined()
      expect(typeof coupleApi.generateCoupleCode).toBe('function')
    })

    it('should define bindCouple endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.bindCouple).toBeDefined()
      expect(typeof coupleApi.bindCouple).toBe('function')
    })

    it('should define validateCoupleCode endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.validateCoupleCode).toBeDefined()
      expect(typeof coupleApi.validateCoupleCode).toBe('function')
    })
  })

  describe('Menu API', () => {
    it('should define getMenuList endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.getMenuList).toBeDefined()
      expect(typeof menuApi.getMenuList).toBe('function')
    })

    it('should define getMenuDetail endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.getMenuDetail).toBeDefined()
      expect(typeof menuApi.getMenuDetail).toBe('function')
    })

    it('should define addMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.addMenu).toBeDefined()
      expect(typeof menuApi.addMenu).toBe('function')
    })

    it('should define deleteMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.deleteMenu).toBeDefined()
      expect(typeof menuApi.deleteMenu).toBe('function')
    })
  })

  describe('Anniversary API', () => {
    it('should define getAnniversaryList endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.getAnniversaryList).toBeDefined()
      expect(typeof anniversaryApi.getAnniversaryList).toBe('function')
    })

    it('should define addAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.addAnniversary).toBeDefined()
      expect(typeof anniversaryApi.addAnniversary).toBe('function')
    })

    it('should define deleteAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.deleteAnniversary).toBeDefined()
      expect(typeof anniversaryApi.deleteAnniversary).toBe('function')
    })
  })

  describe('Feed API', () => {
    it('should define getTodayFeedStatus endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.getTodayFeedStatus).toBeDefined()
      expect(typeof feedApi.getTodayFeedStatus).toBe('function')
    })

    it('should define sendFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.sendFeed).toBeDefined()
      expect(typeof feedApi.sendFeed).toBe('function')
    })

    it('should define acceptFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.acceptFeed).toBeDefined()
      expect(typeof feedApi.acceptFeed).toBe('function')
    })

    it('should define rejectFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.rejectFeed).toBeDefined()
      expect(typeof feedApi.rejectFeed).toBe('function')
    })
  })

  describe('Wish API', () => {
    it('should define getWishList endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.getWishList).toBeDefined()
      expect(typeof wishApi.getWishList).toBe('function')
    })

    it('should define addWish endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.addWish).toBeDefined()
      expect(typeof wishApi.addWish).toBe('function')
    })

    it('should define fulfillWish endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.fulfillWish).toBeDefined()
      expect(typeof wishApi.fulfillWish).toBe('function')
    })
  })
})
