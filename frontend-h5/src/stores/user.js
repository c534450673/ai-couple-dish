/**
 * 用户 Store
 */
import { defineStore } from 'pinia'
import { userApi, coupleApi } from '@/api'

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
      try {
        const res = await userApi.loginByPhone({ phone, verifyCode })
        this.setLoginInfo(res.data.token, res.data.userInfo)
        return res
      } catch (error) {
        throw error
      }
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

    // 登出
    async logout() {
      try {
        await userApi.logout()
      } catch (error) {
        // 忽略退出接口错误，继续清除本地状态
      }
      this.token = ''
      this.userInfo = null
      this.coupleInfo = null
      this.isLoggedIn = false
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      localStorage.removeItem('coupleInfo')
    },

    // 更新用户信息
    async updateUserInfo(data) {
      try {
        const res = await userApi.updateUserInfo(data)
        this.userInfo = { ...this.userInfo, ...res.data }
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        return res
      } catch (error) {
        throw error
      }
    }
  }
})
