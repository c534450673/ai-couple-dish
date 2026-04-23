/**
 * UniApp API 请求封装
 */
import { BASE_URL } from './config'

const request = (options) => {
  const token = uni.getStorageSync('token')

  return new Promise((resolve, reject) => {
    uni.showLoading({ title: '加载中...', mask: true })

    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      success: (res) => {
        uni.hideLoading()

        if (res.statusCode === 200) {
          if (res.data.code === 200) {
            resolve(res.data)
          } else if (res.data.code === 401 || res.data.code === 9001) {
            // Token过期或未登录，统一处理
            uni.removeStorageSync('token')
            uni.removeStorageSync('userInfo')
            uni.reLaunch({ url: '/pages/index/index' })
            reject(res.data)
          } else {
            uni.showToast({ title: res.data.message || '请求失败', icon: 'none' })
            reject(res.data)
          }
        } else {
          uni.showToast({ title: '网络错误', icon: 'none' })
          reject(res)
        }
      },
      fail: (err) => {
        uni.hideLoading()
        uni.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

export default request