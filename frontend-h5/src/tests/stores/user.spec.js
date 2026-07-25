/**
 * 用户 Store 单元测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

// Mock the API modules
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

import { userApi, coupleApi } from '@/api'

describe('用户 Store', () => {
  let userStore

  beforeEach(() => {
    setActivePinia(createPinia())
    userStore = useUserStore()
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('状态初始化', () => {
    it('应该正确初始化状态', () => {
      expect(userStore.token).toBe('')
      expect(userStore.userInfo).toBeNull()
      expect(userStore.coupleInfo).toBeNull()
      expect(userStore.isLoggedIn).toBe(false)
    })

    it('应该从 localStorage 恢复 token', () => {
      localStorage.setItem('token', 'test_token_123')
      const pinia = createPinia()
      setActivePinia(pinia)
      const store = useUserStore()
      expect(store.token).toBe('test_token_123')
    })

    it('应该从 localStorage 恢复并迁移白名单 userInfo', () => {
      const userInfo = {
        id: 1,
        nickName: '测试用户',
        avatarUrl: '/avatar.webp',
        memberLevel: 1,
        openid: 'wx-sensitive-openid',
        phone: '13800138000'
      }
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      const pinia = createPinia()
      setActivePinia(pinia)
      const store = useUserStore()
      const expectedProfile = {
        id: 1,
        nickName: '测试用户',
        avatarUrl: '/avatar.webp',
        memberLevel: 1
      }
      expect(store.userInfo).toEqual(expectedProfile)
      expect(JSON.parse(localStorage.getItem('userInfo'))).toEqual(expectedProfile)
    })
  })

  describe('Getters', () => {
    it('isAuthenticated 应该正确反映登录状态', () => {
      expect(userStore.isAuthenticated).toBe(false)
      userStore.token = 'valid_token'
      expect(userStore.isAuthenticated).toBe(true)
    })

    it('hasCouple 应该正确反映情侣状态', () => {
      expect(userStore.hasCouple).toBe(false)
      userStore.coupleInfo = { id: 1, coupleCode: 'ABC123' }
      expect(userStore.hasCouple).toBe(true)
    })
  })

  describe('checkLoginStatus', () => {
    it('有有效 token 和 userInfo 时应该设置登录状态', () => {
      localStorage.setItem('token', 'valid_token')
      localStorage.setItem('userInfo', JSON.stringify({ id: 1, nickName: '测试' }))
      coupleApi.getCoupleInfo.mockResolvedValue({ data: { id: 1 } })

      userStore.checkLoginStatus()

      expect(userStore.token).toBe('valid_token')
      expect(userStore.isLoggedIn).toBe(true)
    })

    it('没有 token 时不应该设置登录状态', () => {
      localStorage.removeItem('token')
      userStore.checkLoginStatus()
      expect(userStore.isLoggedIn).toBe(false)
    })
  })

  describe('loginByPhone', () => {
    it('应该成功登录并设置登录信息', async () => {
      const mockResponse = {
        data: {
          token: 'new_token_123',
          userInfo: { id: 1, nickName: '手机用户' }
        }
      }
      userApi.loginByPhone.mockResolvedValue(mockResponse)
      coupleApi.getCoupleInfo.mockResolvedValue({ data: null })

      const result = await userStore.loginByPhone('13800138000')

      expect(result).toEqual(mockResponse)
      expect(userStore.token).toBe('new_token_123')
      expect(userStore.userInfo.nickName).toBe('手机用户')
      expect(userStore.isLoggedIn).toBe(true)
    })

    it('登录失败时应该抛出错误', async () => {
      const error = new Error('登录失败')
      userApi.loginByPhone.mockRejectedValue(error)

      await expect(userStore.loginByPhone('13800138000')).rejects.toThrow('登录失败')
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
    it('应该正确设置登录信息且只持久化用户白名单字段', () => {
      const token = 'test_token'
      const userInfo = {
        id: 1,
        nickName: '新用户',
        avatarUrl: '/avatar.webp',
        memberLevel: 0,
        openid: 'wx-sensitive-openid',
        phone: '13800138000'
      }
      const expectedProfile = {
        id: 1,
        nickName: '新用户',
        avatarUrl: '/avatar.webp',
        memberLevel: 0
      }

      userStore.setLoginInfo(token, userInfo)

      expect(userStore.token).toBe(token)
      expect(userStore.userInfo).toEqual(expectedProfile)
      expect(userStore.isLoggedIn).toBe(true)
      expect(localStorage.getItem('token')).toBe(token)
      expect(JSON.parse(localStorage.getItem('userInfo'))).toEqual(expectedProfile)
      expect(localStorage.getItem('userInfo')).not.toContain('openid')
      expect(localStorage.getItem('userInfo')).not.toContain('13800138000')
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

    it('获取失败时应该保留旧情侣快照并返回可判定结果', async () => {
      userStore.token = 'valid_token'
      const snapshot = { id: 7, coupleCode: 'OLD123' }
      userStore.coupleInfo = snapshot
      localStorage.setItem('coupleInfo', JSON.stringify(snapshot))
      coupleApi.getCoupleInfo.mockRejectedValue({ code: 503 })

      const result = await userStore.getCoupleInfo()

      expect(result).toEqual({ status: 'error', errorCode: '503' })
      expect(userStore.coupleInfo).toEqual(snapshot)
      expect(JSON.parse(localStorage.getItem('coupleInfo'))).toEqual(snapshot)
    })
  })

  describe('fetchUserInfo', () => {
    it('只将消费者需要的资料白名单写入 Store 和 localStorage', async () => {
      userApi.getUserInfo.mockResolvedValue({
        data: {
          id: 42,
          openid: 'wx-sensitive-openid',
          nickName: '星河',
          avatarUrl: '/avatar.webp',
          phone: '13800138000',
          memberLevel: 1,
          createTime: '2026-07-23T10:00:00',
          unexpectedServerField: 'must-not-persist'
        }
      })

      const result = await userStore.fetchUserInfo()
      const expectedProfile = {
        id: 42,
        nickName: '星河',
        avatarUrl: '/avatar.webp',
        memberLevel: 1
      }

      expect(result.data).toEqual(expectedProfile)
      expect(userStore.userInfo).toEqual(expectedProfile)
      expect(JSON.parse(localStorage.getItem('userInfo'))).toEqual(expectedProfile)
      expect(localStorage.getItem('userInfo')).not.toContain('openid')
      expect(localStorage.getItem('userInfo')).not.toContain('13800138000')
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
      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('userInfo')).toBeNull()
      expect(localStorage.getItem('coupleInfo')).toBeNull()
    })
  })

  describe('updateUserInfo', () => {
    it('应该成功更新用户信息', async () => {
      userStore.userInfo = { id: 1, nickName: '旧昵称', avatarUrl: '/old.webp' }
      const updateData = { nickName: '新昵称', avatarUrl: '/new.webp' }
      const response = { data: null }
      userApi.updateUserInfo.mockResolvedValue(response)

      const result = await userStore.updateUserInfo(updateData)

      expect(result).toEqual(response)
      expect(userStore.userInfo.nickName).toBe('新昵称')
      expect(userStore.userInfo.avatarUrl).toBe('/new.webp')
      expect(userStore.userInfo.id).toBe(1)
      expect(localStorage.getItem('userInfo')).toBe(JSON.stringify(userStore.userInfo))
    })

    it('更新失败时应该抛出错误', async () => {
      userStore.userInfo = { id: 1, nickName: '旧昵称' }
      userApi.updateUserInfo.mockRejectedValue(new Error('更新失败'))

      await expect(userStore.updateUserInfo({ nickName: '新' })).rejects.toThrow('更新失败')
    })
  })
})
