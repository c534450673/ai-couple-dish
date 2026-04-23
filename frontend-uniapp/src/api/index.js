/**
 * API 接口定义
 */
import request from './request'
import { BASE_URL } from './config'

export const userApi = {
  loginByPhone(phone) {
    return request({ url: `/user/phoneLogin?phone=${phone}`, method: 'POST' })
  },
  sendVerifyCode(phone) {
    return request({ url: `/user/sendCode?phone=${phone}`, method: 'POST' })
  },
  getUserInfo() {
    return request({ url: '/user/info' })
  },
  updateUserInfo(data) {
    // 后端使用 @RequestParam，需要拼接到URL
    const params = new URLSearchParams(data).toString()
    return request({ url: `/user/update?${params}`, method: 'PUT' })
  }
}

export const coupleApi = {
  getCoupleInfo() {
    return request({ url: '/couple/info' })
  },
  getCoupleHome() {
    return request({ url: '/couple/home' })
  },
  generateCoupleCode() {
    return request({ url: '/couple/generateCode', method: 'POST' })
  },
  bindCouple(data) {
    return request({ url: '/couple/bind', method: 'POST', data })
  },
  validateCoupleCode(coupleCode) {
    return request({ url: '/couple/validateCode', data: { coupleCode } })
  },
  getLoveTimer() {
    return request({ url: '/couple/loveTimer' })
  },
  applyUnbind(data) {
    return request({ url: '/couple/unbind/apply', method: 'POST', data })
  }
}

export const menuApi = {
  getMenuList(params) {
    return request({ url: '/menu/list', data: params })
  },
  getMenuDetail(id) {
    return request({ url: `/menu/detail/${id}` })
  },
  addMenu(data) {
    return request({ url: '/menu/add', method: 'POST', data })
  },
  updateMenu(data) {
    return request({ url: `/menu/update/${data.id}`, method: 'PUT', data })
  },
  deleteMenu(id) {
    return request({ url: `/menu/delete/${id}`, method: 'DELETE' })
  },
  likeMenu(id) {
    return request({ url: `/menu/like/${id}`, method: 'POST' })
  },
  favoriteMenu(id) {
    return request({ url: `/menu/favorite/${id}`, method: 'POST' })
  },
  getMenuStats() {
    return request({ url: '/menu/stats' })
  }
}

export const anniversaryApi = {
  getAnniversaryList() {
    return request({ url: '/anniversary/list' })
  },
  getUpcomingAnniversaries() {
    return request({ url: '/anniversary/upcoming' })
  },
  getNextAnniversary() {
    return request({ url: '/anniversary/next' })
  },
  addAnniversary(data) {
    return request({ url: '/anniversary/add', method: 'POST', data })
  },
  updateAnniversary(id, data) {
    return request({ url: `/anniversary/update/${id}`, method: 'PUT', data })
  },
  deleteAnniversary(id) {
    return request({ url: `/anniversary/delete/${id}`, method: 'DELETE' })
  }
}

export const feedApi = {
  getTodayFeedStatus() {
    return request({ url: '/feed/today' })
  },
  sendFeed(data) {
    return request({ url: '/feed/send', method: 'POST', data })
  },
  getReceivedFeeds() {
    return request({ url: '/feed/received' })
  },
  getSentFeeds() {
    return request({ url: '/feed/sent' })
  },
  acceptFeed(id) {
    return request({ url: `/feed/accept/${id}`, method: 'POST' })
  },
  rejectFeed(id, reason) {
    return request({ url: `/feed/reject/${id}?reason=${encodeURIComponent(reason || '')}`, method: 'POST' })
  }
}

export const noteApi = {
  getNoteList(params) {
    return request({ url: '/note/list', data: params })
  },
  getNoteDetail(id) {
    return request({ url: `/note/detail/${id}` })
  },
  addNote(data) {
    return request({ url: '/note/add', method: 'POST', data })
  },
  updateNote(id, data) {
    return request({ url: `/note/update/${id}`, method: 'PUT', data })
  },
  deleteNote(id) {
    return request({ url: `/note/delete/${id}`, method: 'DELETE' })
  },
  likeNote(id) {
    return request({ url: `/note/like/${id}`, method: 'POST' })
  }
}

export const wishApi = {
  getWishList() {
    return request({ url: '/wish/list' })
  },
  getWishDetail(id) {
    return request({ url: `/wish/detail/${id}` })
  },
  addWish(data) {
    return request({ url: '/wish/add', method: 'POST', data })
  },
  updateWish(id, data) {
    return request({ url: `/wish/update/${id}`, method: 'PUT', data })
  },
  fulfillWish(id) {
    return request({ url: `/wish/fulfill/${id}`, method: 'POST' })
  },
  deleteWish(id) {
    return request({ url: `/wish/delete/${id}`, method: 'DELETE' })
  }
}

export const notificationApi = {
  getNotificationList(params) {
    const query = params ? new URLSearchParams(params).toString() : ''
    return request({ url: `/notification/list${query ? '?' + query : ''}` })
  },
  getUnreadCount() {
    return request({ url: '/notification/unreadCount' })
  },
  markAsRead(id) {
    return request({ url: `/notification/read/${id}`, method: 'PUT' })
  },
  markAllAsRead() {
    return request({ url: '/notification/readAll', method: 'PUT' })
  }
}

export const uploadApi = {
  uploadImage(filePath) {
    const token = uni.getStorageSync('token')
    return new Promise((resolve, reject) => {
      uni.uploadFile({
        url: BASE_URL + '/upload/image',
        filePath,
        name: 'file',
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          const data = JSON.parse(res.data)
          if (data.code === 200) {
            resolve(data)
          } else {
            reject(data)
          }
        },
        fail: reject
      })
    })
  }
}