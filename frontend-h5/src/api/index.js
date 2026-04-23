/**
 * API 接口定义
 */
import api from './request'

export const userApi = {
  // 手机号注册
  registerByPhone(data) {
    return api.post('/user/register', data)
  },
  // 手机号登录
  loginByPhone(data) {
    return api.post('/user/phoneLogin', data)
  },
  // 发送验证码
  sendVerifyCode(phone) {
    return api.post('/user/sendCode', null, { params: { phone } })
  },
  // 获取用户信息
  getUserInfo() {
    return api.get('/user/info')
  },
  // 更新用户信息
  updateUserInfo(data) {
    return api.put('/user/update', null, { params: data })
  },
  // 登出
  logout() {
    return api.post('/user/logout')
  }
}

export const coupleApi = {
  // 获取情侣信息
  getCoupleInfo() {
    return api.get('/couple/info')
  },
  // 获取情侣首页数据
  getCoupleHome() {
    return api.get('/couple/home')
  },
  // 生成情侣码
  generateCoupleCode() {
    return api.post('/couple/generateCode')
  },
  // 绑定情侣
  bindCouple(data) {
    return api.post('/couple/bind', data)
  },
  // 验证情侣码
  validateCoupleCode(coupleCode) {
    return api.get('/couple/validateCode', { params: { coupleCode } })
  },
  // 获取恋爱计时
  getLoveTimer() {
    return api.get('/couple/loveTimer')
  },
  // 申请解绑
  applyUnbind(data) {
    return api.post('/couple/unbind/apply', data)
  },
  // 确认解绑
  confirmUnbind(coupleId) {
    return api.post('/couple/unbind/confirm', null, { params: { coupleId } })
  }
}

export const menuApi = {
  // 获取菜单列表
  getMenuList(params) {
    return api.get('/menu/list', { params })
  },
  // 获取菜单详情
  getMenuDetail(id) {
    return api.get(`/menu/detail/${id}`)
  },
  // 添加菜单
  addMenu(data) {
    return api.post('/menu/add', data)
  },
  // 更新菜单
  updateMenu(data) {
    return api.put(`/menu/update/${data.id}`, data)
  },
  // 删除菜单
  deleteMenu(id) {
    return api.delete(`/menu/delete/${id}`)
  },
  // 点赞菜单
  likeMenu(id) {
    return api.post(`/menu/like/${id}`)
  },
  // 收藏菜单
  favoriteMenu(id) {
    return api.post(`/menu/favorite/${id}`)
  },
  // 获取菜单统计
  getMenuStats() {
    return api.get('/menu/stats')
  }
}

export const anniversaryApi = {
  // 获取纪念日列表
  getAnniversaryList() {
    return api.get('/anniversary/list')
  },
  // 获取即将到来的纪念日
  getUpcomingAnniversaries() {
    return api.get('/anniversary/upcoming')
  },
  // 获取下一个纪念日
  getNextAnniversary() {
    return api.get('/anniversary/next')
  },
  // 添加纪念日
  addAnniversary(data) {
    return api.post('/anniversary/add', data)
  },
  // 更新纪念日
  updateAnniversary(id, data) {
    return api.put(`/anniversary/update/${id}`, data)
  },
  // 删除纪念日
  deleteAnniversary(id) {
    return api.delete(`/anniversary/delete/${id}`)
  }
}

export const feedApi = {
  // 获取今日投喂状态
  getTodayFeedStatus() {
    return api.get('/feed/today')
  },
  // 发送投喂
  sendFeed(data) {
    return api.post('/feed/send', data)
  },
  // 获取收到的投喂
  getReceivedFeeds() {
    return api.get('/feed/received')
  },
  // 获取发出的投喂
  getSentFeeds() {
    return api.get('/feed/sent')
  },
  // 接受投喂
  acceptFeed(id) {
    return api.post(`/feed/accept/${id}`)
  },
  // 拒绝投喂
  rejectFeed(id, reason) {
    return api.post(`/feed/reject/${id}`, null, { params: { reason } })
  }
}

export const noteApi = {
  // 获取笔记列表
  getNoteList(params) {
    return api.get('/note/list', { params })
  },
  // 获取笔记详情
  getNoteDetail(id) {
    return api.get(`/note/detail/${id}`)
  },
  // 添加笔记
  addNote(data) {
    return api.post('/note/add', data)
  },
  // 更新笔记
  updateNote(id, data) {
    return api.put(`/note/update/${id}`, data)
  },
  // 删除笔记
  deleteNote(id) {
    return api.delete(`/note/delete/${id}`)
  },
  // 点赞笔记
  likeNote(id) {
    return api.post(`/note/like/${id}`)
  }
}

export const wishApi = {
  // 获取心愿单
  getWishList() {
    return api.get('/wish/list')
  },
  // 获取心愿详情
  getWishDetail(id) {
    return api.get(`/wish/detail/${id}`)
  },
  // 添加心愿
  addWish(data) {
    return api.post('/wish/add', data)
  },
  // 更新心愿
  updateWish(id, data) {
    return api.put(`/wish/update/${id}`, data)
  },
  // 实现心愿
  fulfillWish(id) {
    return api.post(`/wish/fulfill/${id}`)
  },
  // 撤销实现心愿
  unfulfillWish(id) {
    return api.post(`/wish/unfulfill/${id}`)
  },
  // 删除心愿
  deleteWish(id) {
    return api.delete(`/wish/delete/${id}`)
  }
}

export const notificationApi = {
  // 获取通知列表
  getNotificationList(params) {
    return api.get('/notification/list', { params })
  },
  // 获取未读数量
  getUnreadCount() {
    return api.get('/notification/unreadCount')
  },
  // 标记已读
  markAsRead(id) {
    return api.put(`/notification/read/${id}`)
  },
  // 全部已读
  markAllAsRead() {
    return api.put('/notification/readAll')
  }
}

export const uploadApi = {
  // 上传图片
  uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export const mapApi = {
  // 获取附近的餐厅
  getNearbyRestaurants(params) {
    return api.get('/menu/nearby', { params })
  },
  // 获取地图视图的餐厅数据
  getMapRestaurants(params) {
    return api.get('/menu/map', { params })
  }
}
