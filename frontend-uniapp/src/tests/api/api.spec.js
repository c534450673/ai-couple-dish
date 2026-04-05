/**
 * UniApp API 单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Create mock uni module
const mockUni = {
  request: vi.fn(),
  getStorageSync: vi.fn()
}

vi.mock('uni', () => mockUni)

// Mock request module
vi.mock('@/api/request', () => ({
  default: vi.fn((config) => mockUni.request(config))
}))

vi.mock('@/api/config', () => ({
  BASE_URL: 'http://localhost:8080/api'
}))

import { userApi, coupleApi, menuApi, anniversaryApi, feedApi, noteApi, wishApi, notificationApi, uploadApi } from '@/api/index'

describe('UniApp API 模块测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUni.getStorageSync.mockReturnValue('mock_token')
  })

  describe('userApi', () => {
    it('loginByPhone 应该发送 POST 请求', async () => {
      const mockResponse = { data: { token: 'test', userInfo: {} } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await userApi.loginByPhone({ phone: '13800138000', verifyCode: '123456' })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/user/login',
        method: 'POST',
        data: { phone: '13800138000', verifyCode: '123456' }
      })
      expect(result).toEqual(mockResponse)
    })

    it('sendVerifyCode 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await userApi.sendVerifyCode('13800138000')

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/user/sendCode',
        method: 'POST',
        data: { phone: '13800138000' }
      })
    })

    it('getUserInfo 应该发送 GET 请求', async () => {
      const mockResponse = { data: { id: 1, nickName: '测试' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await userApi.getUserInfo()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/user/info' })
      expect(result).toEqual(mockResponse)
    })

    it('updateUserInfo 应该发送 PUT 请求', async () => {
      const updateData = { nickName: '新昵称' }
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await userApi.updateUserInfo(updateData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/user/update',
        method: 'PUT',
        data: updateData
      })
    })
  })

  describe('coupleApi', () => {
    it('getCoupleInfo 应该发送 GET 请求', async () => {
      const mockResponse = { data: { id: 1, coupleCode: 'ABC123' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await coupleApi.getCoupleInfo()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/couple/info' })
      expect(result.data.coupleCode).toBe('ABC123')
    })

    it('getCoupleHome 应该发送 GET 请求', async () => {
      const mockResponse = { data: { myInfo: {}, partnerInfo: {} } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await coupleApi.getCoupleHome()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/couple/home' })
    })

    it('generateCoupleCode 应该发送 POST 请求', async () => {
      const mockResponse = { data: 'XYZ98765' }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await coupleApi.generateCoupleCode()

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/couple/generateCode',
        method: 'POST'
      })
    })

    it('bindCouple 应该发送 POST 请求', async () => {
      const bindData = { coupleCode: 'ABC123' }
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await coupleApi.bindCouple(bindData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/couple/bind',
        method: 'POST',
        data: bindData
      })
    })

    it('validateCoupleCode 应该发送带参数的请求', async () => {
      mockUni.request.mockResolvedValue({ data: true })

      await coupleApi.validateCoupleCode('ABC123')

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/couple/validateCode',
        data: { coupleCode: 'ABC123' }
      })
    })

    it('getLoveTimer 应该发送 GET 请求', async () => {
      const mockResponse = { data: { loveDays: 100 } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await coupleApi.getLoveTimer()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/couple/loveTimer' })
      expect(result.data.loveDays).toBe(100)
    })

    it('applyUnbind 应该发送 POST 请求', async () => {
      const unbindData = { reason: '不合适' }
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await coupleApi.applyUnbind(unbindData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/couple/unbind/apply',
        method: 'POST',
        data: unbindData
      })
    })
  })

  describe('menuApi', () => {
    it('getMenuList 应该发送带参数的请求', async () => {
      const mockResponse = { data: [{ id: 1, restaurantName: '测试餐厅' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await menuApi.getMenuList({ status: 0 })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/list',
        data: { status: 0 }
      })
    })

    it('getMenuDetail 应该发送带 ID 的请求', async () => {
      const mockResponse = { data: { id: 1, restaurantName: '详情餐厅' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await menuApi.getMenuDetail(1)

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/menu/detail/1' })
    })

    it('addMenu 应该发送 POST 请求', async () => {
      const menuData = { restaurantName: '新餐厅', dishName: '新菜品' }
      mockUni.request.mockResolvedValue({ data: { id: 1 } })

      await menuApi.addMenu(menuData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/add',
        method: 'POST',
        data: menuData
      })
    })

    it('updateMenu 应该发送 PUT 请求', async () => {
      const updateData = { id: 1, restaurantName: '更新餐厅' }
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await menuApi.updateMenu(updateData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/update/1',
        method: 'PUT',
        data: updateData
      })
    })

    it('deleteMenu 应该发送 DELETE 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await menuApi.deleteMenu(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/delete/1',
        method: 'DELETE'
      })
    })

    it('likeMenu 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await menuApi.likeMenu(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/like/1',
        method: 'POST'
      })
    })

    it('favoriteMenu 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await menuApi.favoriteMenu(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/menu/favorite/1',
        method: 'POST'
      })
    })

    it('getMenuStats 应该发送 GET 请求', async () => {
      const mockResponse = { data: { wantToGo: 5, beenTo: 3, recommended: 2 } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await menuApi.getMenuStats()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/menu/stats' })
    })
  })

  describe('anniversaryApi', () => {
    it('getAnniversaryList 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, name: '相识纪念' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await anniversaryApi.getAnniversaryList()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/anniversary/list' })
    })

    it('getUpcomingAnniversaries 应该发送 GET 请求', async () => {
      mockUni.request.mockResolvedValue({ data: [] })

      await anniversaryApi.getUpcomingAnniversaries()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/anniversary/upcoming' })
    })

    it('getNextAnniversary 应该发送 GET 请求', async () => {
      const mockResponse = { data: { name: '恋爱一周年' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await anniversaryApi.getNextAnniversary()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/anniversary/next' })
    })

    it('addAnniversary 应该发送 POST 请求', async () => {
      const anniversaryData = { name: '新纪念日', anniversaryDate: '2024-01-01' }
      mockUni.request.mockResolvedValue({ data: { id: 1 } })

      await anniversaryApi.addAnniversary(anniversaryData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/anniversary/add',
        method: 'POST',
        data: anniversaryData
      })
    })

    it('updateAnniversary 应该发送 PUT 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await anniversaryApi.updateAnniversary(1, { name: '更新纪念日' })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/anniversary/update/1',
        method: 'PUT',
        data: { name: '更新纪念日' }
      })
    })

    it('deleteAnniversary 应该发送 DELETE 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await anniversaryApi.deleteAnniversary(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/anniversary/delete/1',
        method: 'DELETE'
      })
    })
  })

  describe('feedApi', () => {
    it('getTodayFeedStatus 应该发送 GET 请求', async () => {
      const mockResponse = { data: { status: 'pending' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await feedApi.getTodayFeedStatus()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/feed/today' })
    })

    it('sendFeed 应该发送 POST 请求', async () => {
      const feedData = { dishName: '美食', restaurant: '餐厅' }
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await feedApi.sendFeed(feedData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/feed/send',
        method: 'POST',
        data: feedData
      })
    })

    it('getReceivedFeeds 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, dishName: '收到的投喂' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await feedApi.getReceivedFeeds()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/feed/received' })
    })

    it('getSentFeeds 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, dishName: '发出的投喂' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await feedApi.getSentFeeds()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/feed/sent' })
    })

    it('acceptFeed 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await feedApi.acceptFeed(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/feed/accept/1',
        method: 'POST'
      })
    })

    it('rejectFeed 应该发送带原因的 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await feedApi.rejectFeed(1, '不想吃')

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/feed/reject/1',
        method: 'POST',
        data: { reason: '不想吃' }
      })
    })
  })

  describe('noteApi', () => {
    it('getNoteList 应该发送带参数的请求', async () => {
      const mockResponse = { data: [{ id: 1, title: '测试笔记' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      await noteApi.getNoteList({ page: 1 })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/note/list',
        data: { page: 1 }
      })
    })

    it('getNoteDetail 应该发送带 ID 的请求', async () => {
      const mockResponse = { data: { id: 1, content: '笔记内容' } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await noteApi.getNoteDetail(1)

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/note/detail/1' })
    })

    it('addNote 应该发送 POST 请求', async () => {
      const noteData = { title: '新笔记', content: '内容' }
      mockUni.request.mockResolvedValue({ data: { id: 1 } })

      await noteApi.addNote(noteData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/note/add',
        method: 'POST',
        data: noteData
      })
    })

    it('updateNote 应该发送 PUT 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await noteApi.updateNote(1, { title: '更新' })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/note/update/1',
        method: 'PUT',
        data: { title: '更新' }
      })
    })

    it('deleteNote 应该发送 DELETE 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await noteApi.deleteNote(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/note/delete/1',
        method: 'DELETE'
      })
    })

    it('likeNote 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await noteApi.likeNote(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/note/like/1',
        method: 'POST'
      })
    })
  })

  describe('wishApi', () => {
    it('getWishList 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, content: '想吃的美食' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await wishApi.getWishList()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/wish/list' })
    })

    it('addWish 应该发送 POST 请求', async () => {
      const wishData = { content: '新心愿' }
      mockUni.request.mockResolvedValue({ data: { id: 1 } })

      await wishApi.addWish(wishData)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/wish/add',
        method: 'POST',
        data: wishData
      })
    })

    it('fulfillWish 应该发送 POST 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await wishApi.fulfillWish(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/wish/fulfill/1',
        method: 'POST'
      })
    })

    it('deleteWish 应该发送 DELETE 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await wishApi.deleteWish(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/wish/delete/1',
        method: 'DELETE'
      })
    })
  })

  describe('notificationApi', () => {
    it('getNotificationList 应该发送带参数的请求', async () => {
      const mockResponse = { data: [{ id: 1, title: '通知' }] }
      mockUni.request.mockResolvedValue(mockResponse)

      await notificationApi.getNotificationList({ page: 1 })

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/notification/list',
        data: { page: 1 }
      })
    })

    it('getUnreadCount 应该发送 GET 请求', async () => {
      const mockResponse = { data: { count: 5 } }
      mockUni.request.mockResolvedValue(mockResponse)

      const result = await notificationApi.getUnreadCount()

      expect(mockUni.request).toHaveBeenCalledWith({ url: '/notification/unreadCount' })
    })

    it('markAsRead 应该发送 PUT 请求', async () => {
      mockUni.request.mockResolvedValue({ data: { success: true } })

      await notificationApi.markAsRead(1)

      expect(mockUni.request).toHaveBeenCalledWith({
        url: '/notification/read/1',
        method: 'PUT'
      })
    })
  })
})