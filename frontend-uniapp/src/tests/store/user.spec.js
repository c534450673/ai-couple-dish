/**
 * UniApp 用户 Store 单元测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Create mock uni module
const mockUni = {
  getStorageSync: vi.fn(),
  setStorageSync: vi.fn(),
  removeStorageSync: vi.fn(),
  showToast: vi.fn(),
  showLoadingToast: vi.fn(),
  hideLoading: vi.fn(),
  navigateTo: vi.fn(),
  redirectTo: vi.fn(),
  reLaunch: vi.fn(),
  switchTab: vi.fn(),
  navigateBack: vi.fn(),
  login: vi.fn(),
  getUserProfile: vi.fn(),
  getProvider: vi.fn(),
  chooseImage: vi.fn(),
  previewImage: vi.fn(),
  uploadFile: vi.fn(),
  request: vi.fn()
}

vi.mock('uni', () => mockUni)

// Mock API modules
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

import { useUserStore } from '@/store/user'
import { userApi, coupleApi } from '@/api'

describe('UniApp 用户 Store 测试', () => {
  let userStore

  beforeEach(() => {
    setActivePinia(createPinia())
    userStore = useUserStore()
    vi.clearAllMocks()
    mockUni.getStorageSync.mockReturnValue('')
    mockUni.removeStorageSync.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('状态初始化', () => {
    it('应该正确初始化状态', () => {
      expect(userStore.token).toBe('')
      expect(userStore.userInfo).toBeNull()
      expect(userStore.coupleInfo).toBeNull()
      expect(userStore.isLoggedIn).toBe(false)
    })

    it('应该从 Storage 恢复 token', () => {
      mockUni.getStorageSync.mockImplementation((key) => {
        if (key === 'token') return 'test_token_123'
        if (key === 'userInfo') return JSON.stringify({ id: 1, nickName: '测试' })
        return ''
      })

      const pinia = createPinia()
      setActivePinia(pinia)
      const store = useUserStore()
      expect(store.token).toBe('test_token_123')
    })

    it('应该从 Storage 恢复 userInfo', () => {
      const userInfo = { id: 1, nickName: '测试用户' }
      mockUni.getStorageSync.mockImplementation((key) => {
        if (key === 'token') return 'valid_token'
        if (key === 'userInfo') return JSON.stringify(userInfo)
        return ''
      })

      const pinia = createPinia()
      setActivePinia(pinia)
      const store = useUserStore()
      expect(store.userInfo).toEqual(userInfo)
    })
  })

  describe('checkLoginStatus', () => {
    it('有有效 token 和 userInfo 时应该设置登录状态', () => {
      mockUni.getStorageSync.mockImplementation((key) => {
        if (key === 'token') return 'valid_token'
        if (key === 'userInfo') return JSON.stringify({ id: 1, nickName: '测试' })
        return ''
      })
      coupleApi.getCoupleInfo.mockResolvedValue({ data: { id: 1 } })

      userStore.checkLoginStatus()

      expect(userStore.token).toBe('valid_token')
      expect(userStore.isLoggedIn).toBe(true)
    })

    it('没有 token 时不应该设置登录状态', () => {
      mockUni.getStorageSync.mockReturnValue('')

      userStore.checkLoginStatus()

      expect(userStore.isLoggedIn).toBe(false)
    })
  })

  describe('loginByPhone', () => {
    it('应该成功登录并设置登录信息', async () => {
      const mockResponse = {
        data: {
          token: 'new_token_456',
          userInfo: { id: 1, nickName: '手机用户' }
        }
      }
      userApi.loginByPhone.mockResolvedValue(mockResponse)
      coupleApi.getCoupleInfo.mockResolvedValue({ data: null })

      const result = await userStore.loginByPhone('13800138000', '123456')

      expect(result).toEqual(mockResponse)
      expect(userStore.token).toBe('new_token_456')
      expect(userStore.userInfo.nickName).toBe('手机用户')
      expect(userStore.isLoggedIn).toBe(true)
    })

    it('登录失败时应该抛出错误', async () => {
      const error = new Error('登录失败')
      userApi.loginByPhone.mockRejectedValue(error)

      await expect(userStore.loginByPhone('13800138000', '123456')).rejects.toThrow('登录失败')
    })
  })

  describe('sendVerifyCode', () => {
    it('应该调用发送验证码 API', async () => {
      userApi.sendVerifyCode.mockResolvedValue({ data: { success: true } })

      await userStore.sendVerifyCode('13800138000')

      expect(userApi.sendVerifyCode).toHaveBeenCalledWith('13800138000')
    })
  })

  describe('setLoginInfo', () => {
    it('应该正确设置登录信息', () => {
      const token = 'test_token'
      const userInfo = { id: 1, nickName: '新用户' }

      userStore.setLoginInfo(token, userInfo)

      expect(userStore.token).toBe(token)
      expect(userStore.userInfo).toEqual(userInfo)
      expect(userStore.isLoggedIn).toBe(true)
      expect(mockUni.setStorageSync).toHaveBeenCalledWith('token', token)
      expect(mockUni.setStorageSync).toHaveBeenCalledWith('userInfo', JSON.stringify(userInfo))
    })
  })

  describe('getCoupleInfo', () => {
    it('没有 token 时不应该请求', async () => {
      userStore.token = ''

      await userStore.getCoupleInfo()

      expect(coupleApi.getCoupleInfo).not.toHaveBeenCalled()
    })

    it('成功获取情侣信息时应该更新状态', async () => {
      userStore.token = 'valid_token'
      const coupleInfo = { id: 1, coupleCode: 'ABC123' }
      coupleApi.getCoupleInfo.mockResolvedValue({ data: coupleInfo })

      await userStore.getCoupleInfo()

      expect(userStore.coupleInfo).toEqual(coupleInfo)
    })

    it('获取失败时应该清除情侣信息', async () => {
      userStore.token = 'valid_token'
      coupleApi.getCoupleInfo.mockRejectedValue(new Error('获取失败'))

      await userStore.getCoupleInfo()

      expect(userStore.coupleInfo).toBeNull()
    })
  })

  describe('logout', () => {
    it('应该清除所有登录信息', () => {
      userStore.token = 'test_token'
      userStore.userInfo = { id: 1 }
      userStore.coupleInfo = { id: 1 }
      userStore.isLoggedIn = true

      userStore.logout()

      expect(userStore.token).toBe('')
      expect(userStore.userInfo).toBeNull()
      expect(userStore.coupleInfo).toBeNull()
      expect(userStore.isLoggedIn).toBe(false)
      expect(mockUni.removeStorageSync).toHaveBeenCalledWith('token')
      expect(mockUni.removeStorageSync).toHaveBeenCalledWith('userInfo')
      expect(mockUni.removeStorageSync).toHaveBeenCalledWith('coupleInfo')
    })
  })

  describe('updateUserInfo', () => {
    it('应该成功更新用户信息', async () => {
      userStore.userInfo = { id: 1, nickName: '旧昵称' }
      const updateData = { nickName: '新昵称' }
      const response = { data: { id: 1, nickName: '新昵称' } }
      userApi.updateUserInfo.mockResolvedValue(response)

      const result = await userStore.updateUserInfo(updateData)

      expect(result).toEqual(response)
      expect(userStore.userInfo.nickName).toBe('新昵称')
    })

    it('更新失败时应该抛出错误', async () => {
      userStore.userInfo = { id: 1, nickName: '旧昵称' }
      userApi.updateUserInfo.mockRejectedValue(new Error('更新失败'))

      await expect(userStore.updateUserInfo({ nickName: '新' })).rejects.toThrow('更新失败')
    })
  })
})