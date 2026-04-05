import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the API
vi.mock('@/api', () => ({
  userApi: {
    loginByPhone: vi.fn(),
    sendVerifyCode: vi.fn(),
    getUserInfo: vi.fn(),
    updateUserInfo: vi.fn()
  },
  coupleApi: {
    getCoupleInfo: vi.fn()
  }
}))

// Mock uni
vi.mock('uni', () => ({
  getStorageSync: vi.fn((key) => {
    if (key === 'token') return 'test_token_123'
    if (key === 'userInfo') return JSON.stringify({ id: 1, nickName: 'Test User' })
    return null
  }),
  setStorageSync: vi.fn(),
  removeStorageSync: vi.fn()
}))

describe('User Store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('State', () => {
    it('should have correct initial state', async () => {
      const { useUserStore } = await import('@/store/user')
      const userStore = useUserStore()

      expect(userStore.token).toBeDefined()
      expect(userStore.userInfo).toBeDefined()
      expect(userStore.isLoggedIn).toBe(false)
    })
  })

  describe('Actions', () => {
    describe('loginByPhone', () => {
      it('should login successfully', async () => {
        const mockResponse = {
          data: {
            token: 'test_token_123',
            userInfo: { id: 1, nickName: 'Test User' }
          }
        }
        const { userApi } = await import('@/api')
        userApi.loginByPhone.mockResolvedValue(mockResponse)

        const { useUserStore } = await import('@/store/user')
        const userStore = useUserStore()
        const result = await userStore.loginByPhone('13800138000', '123456')

        expect(result.data.token).toBe('test_token_123')
      })
    })

    describe('sendVerifyCode', () => {
      it('should send verify code successfully', async () => {
        const { userApi } = await import('@/api')
        userApi.sendVerifyCode.mockResolvedValue({})

        const { useUserStore } = await import('@/store/user')
        const userStore = useUserStore()
        await userStore.sendVerifyCode('13800138000')

        expect(userApi.sendVerifyCode).toHaveBeenCalledWith('13800138000')
      })
    })

    describe('getCoupleInfo', () => {
      it('should fetch couple info successfully', async () => {
        const mockCoupleInfo = { id: 1, coupleCode: 'ABC123', partnerName: 'Partner' }
        const { coupleApi } = await import('@/api')
        coupleApi.getCoupleInfo.mockResolvedValue({ data: mockCoupleInfo })

        const { useUserStore } = await import('@/store/user')
        const userStore = useUserStore()
        userStore.token = 'test_token'
        await userStore.getCoupleInfo()

        expect(userStore.coupleInfo).toEqual(mockCoupleInfo)
      })
    })

    describe('updateUserInfo', () => {
      it('should update user info successfully', async () => {
        const mockResponse = {
          data: { id: 1, nickName: 'Updated User' }
        }
        const { userApi } = await import('@/api')
        userApi.updateUserInfo.mockResolvedValue(mockResponse)

        const { useUserStore } = await import('@/store/user')
        const userStore = useUserStore()
        const result = await userStore.updateUserInfo({ nickName: 'Updated User' })

        expect(result.data.nickName).toBe('Updated User')
      })
    })

    describe('logout', () => {
      it('should clear all state and storage', async () => {
        const { useUserStore } = await import('@/store/user')
        const userStore = useUserStore()

        userStore.token = 'test_token'
        userStore.userInfo = { id: 1 }
        userStore.coupleInfo = { id: 1 }
        userStore.isLoggedIn = true

        userStore.logout()

        expect(userStore.token).toBe('')
        expect(userStore.userInfo).toBeNull()
        expect(userStore.coupleInfo).toBeNull()
        expect(userStore.isLoggedIn).toBe(false)
      })
    })
  })
})