import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

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

describe('User Store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  describe('State', () => {
    it('should have correct initial state', () => {
      const userStore = useUserStore()

      expect(userStore.token).toBe('')
      expect(userStore.userInfo).toBeNull()
      expect(userStore.coupleInfo).toBeNull()
      expect(userStore.isLoggedIn).toBe(false)
    })

    it('should load state from localStorage', () => {
      const mockUserInfo = { id: 1, nickName: 'Test User' }
      localStorage.setItem('token', 'test_token_123')
      localStorage.setItem('userInfo', JSON.stringify(mockUserInfo))

      const userStore = useUserStore()

      expect(userStore.token).toBe('test_token_123')
      expect(userStore.userInfo).toEqual(mockUserInfo)
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

        const userStore = useUserStore()
        const result = await userStore.loginByPhone('13800138000', '123456')

        expect(userStore.token).toBe('test_token_123')
        expect(userStore.isLoggedIn).toBe(true)
        expect(userStore.userInfo).toEqual(mockResponse.data.userInfo)
      })

      it('should throw error on login failure', async () => {
        const { userApi } = await import('@/api')
        userApi.loginByPhone.mockRejectedValue(new Error('登录失败'))

        const userStore = useUserStore()

        await expect(userStore.loginByPhone('13800138000', '123456')).rejects.toThrow('登录失败')
      })
    })

    describe('sendVerifyCode', () => {
      it('should send verify code successfully', async () => {
        const { userApi } = await import('@/api')
        userApi.sendVerifyCode.mockResolvedValue({})

        const userStore = useUserStore()
        const result = await userStore.sendVerifyCode('13800138000')

        expect(userApi.sendVerifyCode).toHaveBeenCalledWith('13800138000')
      })
    })

    describe('setLoginInfo', () => {
      it('should set login info correctly', () => {
        const userStore = useUserStore()
        const token = 'test_token_456'
        const userInfo = { id: 2, nickName: 'New User' }

        userStore.setLoginInfo(token, userInfo)

        expect(userStore.token).toBe(token)
        expect(userStore.userInfo).toEqual(userInfo)
        expect(userStore.isLoggedIn).toBe(true)
        expect(localStorage.getItem('token')).toBe(token)
        expect(localStorage.getItem('userInfo')).toBe(JSON.stringify(userInfo))
      })
    })

    describe('getCoupleInfo', () => {
      it('should fetch couple info successfully', async () => {
        const mockCoupleInfo = { id: 1, coupleCode: 'ABC123', partnerName: 'Partner' }
        const { coupleApi } = await import('@/api')
        coupleApi.getCoupleInfo.mockResolvedValue({ data: mockCoupleInfo })

        const userStore = useUserStore()
        userStore.token = 'test_token'
        await userStore.getCoupleInfo()

        expect(userStore.coupleInfo).toEqual(mockCoupleInfo)
      })

      it('should not fetch when token is empty', async () => {
        const userStore = useUserStore()
        userStore.token = ''

        await userStore.getCoupleInfo()

        expect(userStore.coupleInfo).toBeNull()
      })
    })

    describe('logout', () => {
      it('should clear all state and localStorage', () => {
        const userStore = useUserStore()

        // Set some state
        userStore.token = 'test_token'
        userStore.userInfo = { id: 1 }
        userStore.coupleInfo = { id: 1 }
        userStore.isLoggedIn = true

        userStore.logout()

        expect(userStore.token).toBe('')
        expect(userStore.userInfo).toBeNull()
        expect(userStore.coupleInfo).toBeNull()
        expect(userStore.isLoggedIn).toBe(false)
        expect(localStorage.getItem('token')).toBeNull()
        expect(localStorage.getItem('userInfo')).toBeNull()
        expect(localStorage.getItem('coupleInfo')).toBeNull()
      })
    })
  })
})