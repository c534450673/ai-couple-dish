/**
 * 用户 Store
 */
import { defineStore } from 'pinia'
import { userApi, coupleApi } from '@/api'
import { resetRequestState } from '@/api/request'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'

let remoteLogoutPromise = null

const USER_PROFILE_FIELDS = ['id', 'nickName', 'avatarUrl', 'memberLevel']

const projectUserProfile = (data) => {
  if (!data || typeof data !== 'object') return null
  return Object.fromEntries(
    USER_PROFILE_FIELDS
      .filter(field => Object.prototype.hasOwnProperty.call(data, field))
      .map(field => [field, data[field]])
  )
}

const readStoredUserProfile = () => {
  const storedProfile = localStorage.getItem('userInfo')
  if (!storedProfile) return null
  const profile = projectUserProfile(JSON.parse(storedProfile))
  const projectedProfile = JSON.stringify(profile)
  if (projectedProfile !== storedProfile) {
    localStorage.setItem('userInfo', projectedProfile)
    logUiEvent('settings.profile.storage', {
      module: 'settings', operation: 'profile_storage_migrate', result: 'success',
      durationMs: 0, errorCode: 'NONE', keptFields: Object.keys(profile),
      keptFieldCount: Object.keys(profile).length
    })
  }
  return profile
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: readStoredUserProfile(),
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
      const profile = readStoredUserProfile()
      if (token && profile) {
        this.token = token
        this.userInfo = profile
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
      const startedAt = Date.now()
      const profile = projectUserProfile(userInfo)
      this.token = token
      this.userInfo = profile
      this.isLoggedIn = true
      localStorage.setItem('token', token)
      localStorage.setItem('userInfo', JSON.stringify(profile))
      logUiEvent('settings.profile.storage', {
        module: 'settings', operation: 'profile_storage_write', result: 'success',
        durationMs: Date.now() - startedAt, errorCode: 'NONE',
        keptFields: Object.keys(profile), keptFieldCount: Object.keys(profile).length
      })
      this.getCoupleInfo()
    },

    // 绑定接口已返回情侣快照时，先持久化它再允许路由继续。
    setCoupleInfo(coupleInfo) {
      this.coupleInfo = coupleInfo
      localStorage.setItem('coupleInfo', JSON.stringify(coupleInfo))
    },

    // 获取情侣信息
    async getCoupleInfo() {
      if (!this.token) {
        logUiEvent('user.couple.load', {
          module: 'user', operation: 'couple_load', result: 'skipped',
          durationMs: 0, errorCode: 'AUTH_REQUIRED'
        })
        return { status: 'skipped', errorCode: 'AUTH_REQUIRED' }
      }
      const startedAt = Date.now()
      logUiEvent('user.couple.load', {
        module: 'user', operation: 'couple_load', result: 'started',
        durationMs: 0, errorCode: 'NONE'
      })
      try {
        const res = await coupleApi.getCoupleInfo()
        this.coupleInfo = res.data
        localStorage.setItem('coupleInfo', JSON.stringify(res.data))
        logUiEvent('user.couple.load', {
          module: 'user', operation: 'couple_load', result: 'success',
          durationMs: Date.now() - startedAt, errorCode: 'NONE'
        })
        return { status: 'success', data: res.data }
      } catch (error) {
        const errorCode = normalizeUiErrorCode(error)
        logUiEvent('user.couple.load', {
          module: 'user', operation: 'couple_load', result: 'error',
          durationMs: Date.now() - startedAt, errorCode
        })
        return { status: 'error', errorCode }
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
        const profile = projectUserProfile(res.data)
        this.userInfo = profile
        localStorage.setItem('userInfo', JSON.stringify(profile))
        logUiEvent('settings.profile.load', {
          module: 'settings',
          operation: 'profile_load',
          result: 'success',
          durationMs: Date.now() - startedAt,
          errorCode: 'NONE'
        })
        return { ...res, data: profile }
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

    clearLocalSession({ reason = 'explicit_logout', errorCode = 'NONE' } = {}) {
      const hasSession = Boolean(
        this.token || this.userInfo || this.coupleInfo || this.isLoggedIn ||
        localStorage.getItem('token') || localStorage.getItem('userInfo') || localStorage.getItem('coupleInfo')
      )
      if (!hasSession) {
        logUiEvent('settings.session.clear', {
          module: 'settings', operation: 'local_session_clear', result: 'skipped',
          durationMs: 0, errorCode: 'SESSION_ALREADY_CLEAR', cleanupItemCount: 0, reason
        })
        return false
      }

      const startedAt = Date.now()
      resetRequestState()
      this.token = ''
      this.userInfo = null
      this.coupleInfo = null
      this.isLoggedIn = false
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      localStorage.removeItem('coupleInfo')
      logUiEvent('settings.session.clear', {
        module: 'settings', operation: 'local_session_clear', result: 'success',
        durationMs: Date.now() - startedAt, errorCode, cleanupItemCount: 3, reason
      })
      return true
    },

    // 显式登出会请求服务端一次；401 清理只调用 clearLocalSession。
    async logout() {
      if (remoteLogoutPromise) {
        logUiEvent('settings.logout', {
          module: 'settings', operation: 'remote_logout_request', result: 'coalesced',
          durationMs: 0, errorCode: 'NONE', cleanupItemCount: 0
        })
        return remoteLogoutPromise
      }

      const startedAt = Date.now()
      logUiEvent('settings.logout', {
        module: 'settings',
        operation: 'remote_logout_request',
        result: 'started',
        durationMs: 0,
        errorCode: 'NONE',
        cleanupItemCount: 0
      })

      remoteLogoutPromise = (async () => {
        let remoteErrorCode = 'NONE'
        try {
          await userApi.logout()
          logUiEvent('settings.logout', {
            module: 'settings', operation: 'remote_logout_request', result: 'success',
            durationMs: Date.now() - startedAt, errorCode: 'NONE', cleanupItemCount: 0
          })
        } catch (error) {
          remoteErrorCode = normalizeUiErrorCode(error, 'REMOTE_LOGOUT_FAILED')
          logUiEvent('settings.logout', {
            module: 'settings', operation: 'remote_logout_request', result: 'error',
            durationMs: Date.now() - startedAt, errorCode: remoteErrorCode, cleanupItemCount: 0
          })
        }
        this.clearLocalSession({ reason: 'explicit_logout', errorCode: remoteErrorCode })
      })()

      try {
        return await remoteLogoutPromise
      } finally {
        remoteLogoutPromise = null
      }
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
