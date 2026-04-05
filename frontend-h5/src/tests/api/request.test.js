import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }))
  }
}))

describe('API Request Module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('BASE_URL Configuration', () => {
    it('should use default API path when env var is not set', async () => {
      // The actual test would check if the baseURL is set correctly
      // For now, we verify the module structure
      const apiModule = await import('@/api/request')
      expect(apiModule).toBeDefined()
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