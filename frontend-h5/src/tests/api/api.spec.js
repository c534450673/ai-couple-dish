/**
 * API 单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'

// Import API after setting up mocks
vi.mock('@/api/request', async () => {
  const actual = await vi.importActual('@/api/request')
  return {
    ...actual,
    default: axios.create({
      baseURL: 'http://localhost:8080/api',
      timeout: 10000
    })
  }
})

import api, { userApi, coupleApi, menuApi, anniversaryApi, feedApi, noteApi, wishApi, notificationApi, uploadApi } from '@/api/index'

describe('API 模块测试', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(axios)
  })

  afterEach(() => {
    mock.restore()
  })

  describe('userApi', () => {
    it('loginByPhone 应该发送正确的请求', async () => {
      const mockResponse = { data: { token: 'test', userInfo: {} } }
      mock.onPost('/api/user/phoneLogin').reply(200, mockResponse)

      const result = await userApi.loginByPhone('13800138000')
      expect(result.data.token).toBe('test')
    })

    it('sendVerifyCode 应该发送正确的请求', async () => {
      mock.onPost('/api/user/sendCode').reply(200, { data: { success: true } })

      const result = await userApi.sendVerifyCode('13800138000')
      expect(result.data.success).toBe(true)
    })

    it('getUserInfo 应该发送 GET 请求', async () => {
      const mockResponse = { data: { id: 1, nickName: '测试' } }
      mock.onGet('/api/user/info').reply(200, mockResponse)

      const result = await userApi.getUserInfo()
      expect(result.data.nickName).toBe('测试')
    })

    it('updateUserInfo 应该发送 PUT 请求', async () => {
      const updateData = { nickName: '新昵称' }
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/user/update').reply(200, mockResponse)

      const result = await userApi.updateUserInfo(updateData)
      expect(result.data.success).toBe(true)
    })
  })

  describe('coupleApi', () => {
    it('getCoupleInfo 应该发送 GET 请求', async () => {
      const mockResponse = { data: { id: 1, coupleCode: 'ABC123' } }
      mock.onGet('/api/couple/info').reply(200, mockResponse)

      const result = await coupleApi.getCoupleInfo()
      expect(result.data.coupleCode).toBe('ABC123')
    })

    it('getCoupleHome 应该发送 GET 请求', async () => {
      const mockResponse = { data: { myInfo: {}, partnerInfo: {} } }
      mock.onGet('/api/couple/home').reply(200, mockResponse)

      const result = await coupleApi.getCoupleHome()
      expect(result.data).toHaveProperty('myInfo')
    })

    it('generateCoupleCode 应该发送 POST 请求', async () => {
      const mockResponse = { data: 'XYZ98765' }
      mock.onPost('/api/couple/generateCode').reply(200, mockResponse)

      const result = await coupleApi.generateCoupleCode()
      expect(result.data).toBe('XYZ98765')
    })

    it('bindCouple 应该发送 POST 请求', async () => {
      const bindData = { coupleCode: 'ABC123' }
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/couple/bind').reply(200, mockResponse)

      const result = await coupleApi.bindCouple(bindData)
      expect(result.data.success).toBe(true)
    })

    it('validateCoupleCode 应该发送带参数的 GET 请求', async () => {
      const mockResponse = { data: true }
      mock.onGet('/api/couple/validateCode', { params: { coupleCode: 'ABC123' } }).reply(200, mockResponse)

      const result = await coupleApi.validateCoupleCode('ABC123')
      expect(result.data).toBe(true)
    })

    it('getLoveTimer 应该发送 GET 请求', async () => {
      const mockResponse = { data: { loveDays: 100 } }
      mock.onGet('/api/couple/loveTimer').reply(200, mockResponse)

      const result = await coupleApi.getLoveTimer()
      expect(result.data.loveDays).toBe(100)
    })

    it('applyUnbind 应该发送 POST 请求', async () => {
      const unbindData = { reason: '不合适' }
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/couple/unbind/apply').reply(200, mockResponse)

      const result = await coupleApi.applyUnbind(unbindData)
      expect(result.data.success).toBe(true)
    })

    it('confirmUnbind 应该发送带参数的 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/couple/unbind/confirm', { coupleId: 1 }).reply(200, mockResponse)

      const result = await coupleApi.confirmUnbind(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('menuApi', () => {
    it('getMenuList 应该发送带参数的 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, restaurantName: '测试餐厅' }] }
      mock.onGet('/api/menu/list', { params: { status: 0 } }).reply(200, mockResponse)

      const result = await menuApi.getMenuList({ status: 0 })
      expect(result.data[0].restaurantName).toBe('测试餐厅')
    })

    it('getMenuDetail 应该发送带 ID 的 GET 请求', async () => {
      const mockResponse = { data: { id: 1, restaurantName: '详情餐厅' } }
      mock.onGet('/api/menu/detail/1').reply(200, mockResponse)

      const result = await menuApi.getMenuDetail(1)
      expect(result.data.restaurantName).toBe('详情餐厅')
    })

    it('addMenu 应该发送 POST 请求', async () => {
      const menuData = { restaurantName: '新餐厅', dishName: '新菜品' }
      const mockResponse = { data: { id: 1 } }
      mock.onPost('/api/menu/add').reply(200, mockResponse)

      const result = await menuApi.addMenu(menuData)
      expect(result.data.id).toBe(1)
    })

    it('updateMenu 应该发送 PUT 请求', async () => {
      const updateData = { id: 1, restaurantName: '更新餐厅' }
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/menu/update/1').reply(200, mockResponse)

      const result = await menuApi.updateMenu(updateData)
      expect(result.data.success).toBe(true)
    })

    it('deleteMenu 应该发送 DELETE 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onDelete('/api/menu/delete/1').reply(200, mockResponse)

      const result = await menuApi.deleteMenu(1)
      expect(result.data.success).toBe(true)
    })

    it('likeMenu 应该发送 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/menu/like/1').reply(200, mockResponse)

      const result = await menuApi.likeMenu(1)
      expect(result.data.success).toBe(true)
    })

    it('favoriteMenu 应该发送 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/menu/favorite/1').reply(200, mockResponse)

      const result = await menuApi.favoriteMenu(1)
      expect(result.data.success).toBe(true)
    })

    it('getMenuStats 应该发送 GET 请求', async () => {
      const mockResponse = { data: { wantToGo: 5, beenTo: 3, recommended: 2 } }
      mock.onGet('/api/menu/stats').reply(200, mockResponse)

      const result = await menuApi.getMenuStats()
      expect(result.data.wantToGo).toBe(5)
    })
  })

  describe('anniversaryApi', () => {
    it('getAnniversaryList 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, name: '相识纪念' }] }
      mock.onGet('/api/anniversary/list').reply(200, mockResponse)

      const result = await anniversaryApi.getAnniversaryList()
      expect(result.data[0].name).toBe('相识纪念')
    })

    it('getUpcomingAnniversaries 应该发送 GET 请求', async () => {
      const mockResponse = { data: [] }
      mock.onGet('/api/anniversary/upcoming').reply(200, mockResponse)

      const result = await anniversaryApi.getUpcomingAnniversaries()
      expect(result.data).toEqual([])
    })

    it('getNextAnniversary 应该发送 GET 请求', async () => {
      const mockResponse = { data: { name: '恋爱一周年' } }
      mock.onGet('/api/anniversary/next').reply(200, mockResponse)

      const result = await anniversaryApi.getNextAnniversary()
      expect(result.data.name).toBe('恋爱一周年')
    })

    it('addAnniversary 应该发送 POST 请求', async () => {
      const anniversaryData = { name: '新纪念日', anniversaryDate: '2024-01-01' }
      const mockResponse = { data: { id: 1 } }
      mock.onPost('/api/anniversary/add').reply(200, mockResponse)

      const result = await anniversaryApi.addAnniversary(anniversaryData)
      expect(result.data.id).toBe(1)
    })

    it('updateAnniversary 应该发送 PUT 请求', async () => {
      const updateData = { name: '更新纪念日' }
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/anniversary/update/1').reply(200, mockResponse)

      const result = await anniversaryApi.updateAnniversary(1, updateData)
      expect(result.data.success).toBe(true)
    })

    it('deleteAnniversary 应该发送 DELETE 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onDelete('/api/anniversary/delete/1').reply(200, mockResponse)

      const result = await anniversaryApi.deleteAnniversary(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('feedApi', () => {
    it('getTodayFeedStatus 应该发送 GET 请求', async () => {
      const mockResponse = { data: { status: 'pending' } }
      mock.onGet('/api/feed/today').reply(200, mockResponse)

      const result = await feedApi.getTodayFeedStatus()
      expect(result.data.status).toBe('pending')
    })

    it('sendFeed 应该发送 POST 请求', async () => {
      const feedData = { dishName: '美食', restaurant: '餐厅' }
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/feed/send').reply(200, mockResponse)

      const result = await feedApi.sendFeed(feedData)
      expect(result.data.success).toBe(true)
    })

    it('getReceivedFeeds 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, dishName: '收到的投喂' }] }
      mock.onGet('/api/feed/received').reply(200, mockResponse)

      const result = await feedApi.getReceivedFeeds()
      expect(result.data[0].dishName).toBe('收到的投喂')
    })

    it('getSentFeeds 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, dishName: '发出的投喂' }] }
      mock.onGet('/api/feed/sent').reply(200, mockResponse)

      const result = await feedApi.getSentFeeds()
      expect(result.data[0].dishName).toBe('发出的投喂')
    })

    it('acceptFeed 应该发送 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/feed/accept/1').reply(200, mockResponse)

      const result = await feedApi.acceptFeed(1)
      expect(result.data.success).toBe(true)
    })

    it('rejectFeed 应该发送带原因的 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/feed/reject/1', { reason: '不想吃' }).reply(200, mockResponse)

      const result = await feedApi.rejectFeed(1, '不想吃')
      expect(result.data.success).toBe(true)
    })
  })

  describe('noteApi', () => {
    it('getNoteList 应该发送带参数的 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, title: '测试笔记' }] }
      mock.onGet('/api/note/list', { params: { page: 1 } }).reply(200, mockResponse)

      const result = await noteApi.getNoteList({ page: 1 })
      expect(result.data[0].title).toBe('测试笔记')
    })

    it('getNoteDetail 应该发送带 ID 的 GET 请求', async () => {
      const mockResponse = { data: { id: 1, content: '笔记内容' } }
      mock.onGet('/api/note/detail/1').reply(200, mockResponse)

      const result = await noteApi.getNoteDetail(1)
      expect(result.data.content).toBe('笔记内容')
    })

    it('addNote 应该发送 POST 请求', async () => {
      const noteData = { title: '新笔记', content: '内容' }
      const mockResponse = { data: { id: 1 } }
      mock.onPost('/api/note/add').reply(200, mockResponse)

      const result = await noteApi.addNote(noteData)
      expect(result.data.id).toBe(1)
    })

    it('updateNote 应该发送 PUT 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/note/update/1').reply(200, mockResponse)

      const result = await noteApi.updateNote(1, { title: '更新' })
      expect(result.data.success).toBe(true)
    })

    it('deleteNote 应该发送 DELETE 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onDelete('/api/note/delete/1').reply(200, mockResponse)

      const result = await noteApi.deleteNote(1)
      expect(result.data.success).toBe(true)
    })

    it('likeNote 应该发送 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/note/like/1').reply(200, mockResponse)

      const result = await noteApi.likeNote(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('wishApi', () => {
    it('getWishList 应该发送 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, content: '想吃的美食' }] }
      mock.onGet('/api/wish/list').reply(200, mockResponse)

      const result = await wishApi.getWishList()
      expect(result.data[0].content).toBe('想吃的美食')
    })

    it('addWish 应该发送 POST 请求', async () => {
      const wishData = { content: '新心愿' }
      const mockResponse = { data: { id: 1 } }
      mock.onPost('/api/wish/add').reply(200, mockResponse)

      const result = await wishApi.addWish(wishData)
      expect(result.data.id).toBe(1)
    })

    it('fulfillWish 应该发送 POST 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPost('/api/wish/fulfill/1').reply(200, mockResponse)

      const result = await wishApi.fulfillWish(1)
      expect(result.data.success).toBe(true)
    })

    it('deleteWish 应该发送 DELETE 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onDelete('/api/wish/delete/1').reply(200, mockResponse)

      const result = await wishApi.deleteWish(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('notificationApi', () => {
    it('getNotificationList 应该发送带参数的 GET 请求', async () => {
      const mockResponse = { data: [{ id: 1, title: '通知' }] }
      mock.onGet('/api/notification/list', { params: { page: 1 } }).reply(200, mockResponse)

      const result = await notificationApi.getNotificationList({ page: 1 })
      expect(result.data[0].title).toBe('通知')
    })

    it('getUnreadCount 应该发送 GET 请求', async () => {
      const mockResponse = { data: { count: 5 } }
      mock.onGet('/api/notification/unreadCount').reply(200, mockResponse)

      const result = await notificationApi.getUnreadCount()
      expect(result.data.count).toBe(5)
    })

    it('markAsRead 应该发送 PUT 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/notification/read/1').reply(200, mockResponse)

      const result = await notificationApi.markAsRead(1)
      expect(result.data.success).toBe(true)
    })

    it('markAllAsRead 应该发送 PUT 请求', async () => {
      const mockResponse = { data: { success: true } }
      mock.onPut('/api/notification/readAll').reply(200, mockResponse)

      const result = await notificationApi.markAllAsRead()
      expect(result.data.success).toBe(true)
    })
  })

  describe('uploadApi', () => {
    it('uploadImage 应该发送 multipart/form-data 请求', async () => {
      const mockResponse = { data: { url: 'https://example.com/image.jpg' } }
      mock.onPost('/api/upload/image').reply(200, mockResponse)

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      const result = await uploadApi.uploadImage(file)
      expect(result.data.url).toBe('https://example.com/image.jpg')
    })
  })
})