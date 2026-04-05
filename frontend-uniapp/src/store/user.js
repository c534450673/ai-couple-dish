/**
 * 用户 Store
 */
import { defineStore } from 'pinia'
import { userApi, coupleApi } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: uni.getStorageSync('token') || '',
    userInfo: JSON.parse(uni.getStorageSync('userInfo') || 'null'),
    coupleInfo: JSON.parse(uni.getStorageSync('coupleInfo') || 'null'),
    isLoggedIn: false
  }),

  actions: {
    checkLoginStatus() {
      const token = uni.getStorageSync('token')
      const userInfo = uni.getStorageSync('userInfo')
      if (token && userInfo) {
        this.token = token
        this.userInfo = JSON.parse(userInfo)
        this.isLoggedIn = true
        this.getCoupleInfo()
      }
    },

    async loginByPhone(phone, verifyCode) {
      try {
        const res = await userApi.loginByPhone({ phone, verifyCode })
        this.setLoginInfo(res.data.token, res.data.userInfo)
        return res
      } catch (error) {
        throw error
      }
    },

    async sendVerifyCode(phone) {
      return await userApi.sendVerifyCode(phone)
    },

    setLoginInfo(token, userInfo) {
      this.token = token
      this.userInfo = userInfo
      this.isLoggedIn = true
      uni.setStorageSync('token', token)
      uni.setStorageSync('userInfo', JSON.stringify(userInfo))
      this.getCoupleInfo()
    },

    async getCoupleInfo() {
      if (!this.token) return
      try {
        const res = await coupleApi.getCoupleInfo()
        this.coupleInfo = res.data
        uni.setStorageSync('coupleInfo', JSON.stringify(res.data))
      } catch (error) {
        this.coupleInfo = null
        uni.removeStorageSync('coupleInfo')
      }
    },

    async updateUserInfo(data) {
      try {
        const res = await userApi.updateUserInfo(data)
        if (res.data) {
          this.userInfo = { ...this.userInfo, ...res.data }
          uni.setStorageSync('userInfo', JSON.stringify(this.userInfo))
        }
        return res
      } catch (error) {
        throw error
      }
    },

    logout() {
      this.token = ''
      this.userInfo = null
      this.coupleInfo = null
      this.isLoggedIn = false
      uni.removeStorageSync('token')
      uni.removeStorageSync('userInfo')
      uni.removeStorageSync('coupleInfo')
    }
  }
})
