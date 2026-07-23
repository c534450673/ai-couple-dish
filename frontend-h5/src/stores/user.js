/**
 * 用户 Store
 */
import { defineStore } from 'pinia'
import { userApi, coupleApi } from '@/api'
import { resetRequestState } from '@/api/request'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
    coupleInfo: JSON.parse(localStorage.getItem('coupleInfo') || 'null'),
    isLoggedIn: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    hasCouple: (state) => !!state.coupleInfo
  },

  actions: {
    // 当前服务端没有密码认证合同，必须在发起请求前明确拒绝。
    async login() {
      return { status: 'unavailable', reason: 'PASSWORD_AUTH_NOT_SUPPORTED' }
    },

    async register() {
      return { status: 'unavailable', reason: 'PASSWORD_AUTH_NOT_SUPPORTED' }
    },

    // 检查登录状态
    checkLoginStatus() {
      const token = localStorage.getItem('token')
      const userInfo = localStorage.getItem('userInfo')
      if (token && userInfo) {
        this.token = token
        this.userInfo = JSON.parse(userInfo)
        this.isLoggedIn = true
        this.getCoupleInfo()
      }
    },

    // 手机号登录
    async loginByPhone(phone, verifyCode) {
      const res = await userApi.loginByPhone({ phone, verifyCode })
      this.setLoginInfo(res.data.token, res.data.userInfo)
      return res
    },

    // 发送验证码
    async sendVerifyCode(phone) {
      return await userApi.sendVerifyCode(phone)
    },

    // 手机号注册（自动登录如果已注册）
    async registerByPhone(phone, verifyCode) {
      try {
        const res = await userApi.registerByPhone({ phone, verifyCode })
        this.setLoginInfo(res.data.token, res.data.userInfo)
        return res
      } catch (error) {
        // 如果手机号已注册，尝试登录
        if (error.code === 1005 || error.message?.includes('已注册')) {
          return this.loginByPhone(phone, verifyCode)
        }
        throw error
      }
    },

    // 设置登录信息
    setLoginInfo(token, userInfo) {
      this.token = token
      this.userInfo = userInfo
      this.isLoggedIn = true
      localStorage.setItem('token', token)
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      this.getCoupleInfo()
    },

    // 绑定接口已返回情侣快照时，先持久化它再允许路由继续。
    setCoupleInfo(coupleInfo) {
      this.coupleInfo = coupleInfo
      localStorage.setItem('coupleInfo', JSON.stringify(coupleInfo))
    },

    // 获取情侣信息
    async getCoupleInfo() {
      if (!this.token) return
      try {
        const res = await coupleApi.getCoupleInfo()
        this.coupleInfo = res.data
        localStorage.setItem('coupleInfo', JSON.stringify(res.data))
      } catch (error) {
        this.coupleInfo = null
        localStorage.removeItem('coupleInfo')
      }
    },

    async fetchUserInfo() {
      const startedAt = Date.now()
      logUiEvent('settings.profile.load', {
        module: 'settings',
        operation: 'profile_load',
        result: 'started',
        durationMs: 0,
        errorCode: 'NONE'
      })
      try {
        const res = await userApi.getUserInfo()
        this.userInfo = res.data
        localStorage.setItem('userInfo', JSON.stringify(res.data))
        logUiEvent('settings.profile.load', {
          module: 'settings',
          operation: 'profile_load',
          result: 'success',
          durationMs: Date.now() - startedAt,
          errorCode: 'NONE'
        })
        return res
      } catch (error) {
        logUiEvent('settings.profile.load', {
          module: 'settings',
          operation: 'profile_load',
          result: normalizeUiErrorCode(error) === '401' ? 'unauthorized' : 'error',
          durationMs: Date.now() - startedAt,
          errorCode: normalizeUiErrorCode(error)
        })
        throw error
      }
    },

    // 登出
    async logout() {
      const startedAt = Date.now()
      resetRequestState()
      logUiEvent('settings.logout', {
        module: 'settings',
        operation: 'local_session_logout',
        result: 'started',
        durationMs: 0,
        errorCode: 'NONE',
        cleanupItemCount: 3
      })
      let remoteErrorCode = 'NONE'
      try {
        await userApi.logout()
      } catch (error) {
        remoteErrorCode = normalizeUiErrorCode(error, 'REMOTE_LOGOUT_FAILED')
        logUiEvent('settings.logout', {
          module: 'settings',
          operation: 'remote_logout_request',
          result: 'error',
          durationMs: Date.now() - startedAt,
          errorCode: remoteErrorCode,
          cleanupItemCount: 0
        })
      }
      this.token = ''
      this.userInfo = null
      this.coupleInfo = null
      this.isLoggedIn = false
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      localStorage.removeItem('coupleInfo')
      logUiEvent('settings.logout', {
        module: 'settings',
        operation: 'local_session_logout',
        result: 'success',
        durationMs: Date.now() - startedAt,
        errorCode: remoteErrorCode,
        cleanupItemCount: 3
      })
    },

    // 更新用户信息
    async updateUserInfo(data) {
      const startedAt = Date.now()
      const payload = {
        nickName: data.nickName,
        avatarUrl: data.avatarUrl
      }
      logUiEvent('settings.profile.update', {
        module: 'settings',
        operation: 'profile_update',
        result: 'started',
        durationMs: 0,
        errorCode: 'NONE',
        changedFields: ['nickName', 'avatarUrl']
      })
      try {
        const res = await userApi.updateUserInfo(payload)
        this.userInfo = { ...this.userInfo, ...payload }
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        logUiEvent('settings.profile.update', {
          module: 'settings',
          operation: 'profile_update',
          result: 'success',
          durationMs: Date.now() - startedAt,
          errorCode: 'NONE',
          changedFields: ['nickName', 'avatarUrl']
        })
        return res
      } catch (error) {
        logUiEvent('settings.profile.update', {
          module: 'settings',
          operation: 'profile_update',
          result: 'error',
          durationMs: Date.now() - startedAt,
          errorCode: normalizeUiErrorCode(error),
          changedFields: ['nickName', 'avatarUrl']
        })
        throw error
      }
    }
  }
})
