/**
 * API 模块请求合同测试
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn()
}))

vi.mock('@/api/request', () => ({ default: requestMock }))

import {
  anniversaryApi,
  coupleApi,
  feedApi,
  menuApi,
  noteApi,
  notificationApi,
  uploadApi,
  userApi,
  wishApi
} from '@/api/index'

const phone = '13800138000'
const cases = [
  ['userApi.loginByPhone', 'post', () => userApi.loginByPhone({ phone }), ['/user/phoneLogin', { phone }], { token: 'test-token' }],
  ['userApi.sendVerifyCode', 'post', () => userApi.sendVerifyCode(phone), ['/user/sendCode', null, { params: { phone } }], { sent: true }],
  ['userApi.getUserInfo', 'get', () => userApi.getUserInfo(), ['/user/info'], { id: 1 }],
  ['userApi.updateUserInfo', 'put', () => userApi.updateUserInfo({ nickName: '新昵称' }), ['/user/update', { nickName: '新昵称' }, { retryConfig: { retries: 0 } }], null],
  ['coupleApi.getCoupleInfo', 'get', () => coupleApi.getCoupleInfo(), ['/couple/info'], { id: 1 }],
  ['coupleApi.getCoupleHome', 'get', () => coupleApi.getCoupleHome(), ['/couple/home'], { myInfo: {} }],
  ['coupleApi.generateCoupleCode', 'post', () => coupleApi.generateCoupleCode(), ['/couple/generateCode'], 'ABC123'],
  ['coupleApi.getCodeInfo', 'get', () => coupleApi.getCodeInfo(), ['/couple/codeInfo', { cache: false }], { coupleCode: 'A1B2C3D4', remainingSeconds: 604800 }],
  ['coupleApi.refreshCode', 'post', () => coupleApi.refreshCode(), ['/couple/refreshCode'], 'D4C3B2A1'],
  ['coupleApi.bindCouple', 'post', () => coupleApi.bindCouple({ coupleCode: 'ABC123' }), ['/couple/bind', { coupleCode: 'ABC123' }], { bound: true }],
  ['coupleApi.validateCoupleCode', 'get', () => coupleApi.validateCoupleCode('ABC123'), ['/couple/validateCode', { params: { coupleCode: 'ABC123' } }], true],
  ['coupleApi.getLoveTimer', 'get', () => coupleApi.getLoveTimer(), ['/couple/loveTimer'], { loveDays: 100 }],
  ['coupleApi.applyUnbind', 'post', () => coupleApi.applyUnbind({ reason: '测试' }), ['/couple/unbind/apply', { reason: '测试' }], { applied: true }],
  ['coupleApi.confirmUnbind', 'post', () => coupleApi.confirmUnbind(1), ['/couple/unbind/confirm', null, { params: { coupleId: 1 } }], { confirmed: true }],
  ['menuApi.getMenuList', 'get', () => menuApi.getMenuList({ status: 0 }), ['/menu/list', { params: { status: 0 } }], [{ id: 1 }]],
  ['menuApi.getMenuDetail', 'get', () => menuApi.getMenuDetail(1), ['/menu/detail/1'], { id: 1 }],
  ['menuApi.addMenu', 'post', () => menuApi.addMenu({ dishName: '菜品' }), ['/menu/add', { dishName: '菜品' }], { id: 1 }],
  ['menuApi.updateMenu', 'put', () => menuApi.updateMenu({ id: 1, dishName: '新菜品' }), ['/menu/update/1', { id: 1, dishName: '新菜品' }], { updated: true }],
  ['menuApi.deleteMenu', 'delete', () => menuApi.deleteMenu(1), ['/menu/delete/1'], { deleted: true }],
  ['menuApi.likeMenu', 'post', () => menuApi.likeMenu(1), ['/menu/like/1'], { liked: true }],
  ['menuApi.favoriteMenu', 'post', () => menuApi.favoriteMenu(1), ['/menu/favorite/1'], { favorited: true }],
  ['menuApi.getMenuStats', 'get', () => menuApi.getMenuStats(), ['/menu/stats'], { total: 1 }],
  ['anniversaryApi.getAnniversaryList', 'get', () => anniversaryApi.getAnniversaryList(), ['/anniversary/list'], []],
  ['anniversaryApi.getUpcomingAnniversaries', 'get', () => anniversaryApi.getUpcomingAnniversaries(), ['/anniversary/upcoming'], []],
  ['anniversaryApi.getNextAnniversary', 'get', () => anniversaryApi.getNextAnniversary(), ['/anniversary/next'], { id: 1 }],
  ['anniversaryApi.addAnniversary', 'post', () => anniversaryApi.addAnniversary({ name: '纪念日' }), ['/anniversary/add', { name: '纪念日' }], { id: 1 }],
  ['anniversaryApi.updateAnniversary', 'put', () => anniversaryApi.updateAnniversary(1, { name: '更新' }), ['/anniversary/update/1', { name: '更新' }], { updated: true }],
  ['anniversaryApi.deleteAnniversary', 'delete', () => anniversaryApi.deleteAnniversary(1), ['/anniversary/delete/1'], { deleted: true }],
  ['feedApi.getTodayFeedStatus', 'get', () => feedApi.getTodayFeedStatus(), ['/feed/today', { cache: false }], { status: 'pending' }],
  ['feedApi.sendFeed', 'post', () => feedApi.sendFeed({ dishName: '菜品' }), ['/feed/send', { dishName: '菜品' }], { sent: true }],
  ['feedApi.getReceivedFeeds', 'get', () => feedApi.getReceivedFeeds(), ['/feed/received', { cache: false }], []],
  ['feedApi.getSentFeeds', 'get', () => feedApi.getSentFeeds(), ['/feed/sent', { cache: false }], []],
  ['feedApi.acceptFeed', 'post', () => feedApi.acceptFeed(1), ['/feed/accept/1'], { accepted: true }],
  ['feedApi.rejectFeed', 'post', () => feedApi.rejectFeed(1, '不想吃'), ['/feed/reject/1', null, { params: { reason: '不想吃' } }], { rejected: true }],
  ['noteApi.getNoteList', 'get', () => noteApi.getNoteList({ page: 1 }), ['/note/list', { params: { page: 1 } }], []],
  ['noteApi.getNoteDetail', 'get', () => noteApi.getNoteDetail(1), ['/note/detail/1'], { id: 1 }],
  ['noteApi.addNote', 'post', () => noteApi.addNote({ title: '笔记' }), ['/note/add', { title: '笔记' }], { id: 1 }],
  ['noteApi.updateNote', 'put', () => noteApi.updateNote(1, { title: '更新' }), ['/note/update/1', { title: '更新' }], { updated: true }],
  ['noteApi.deleteNote', 'delete', () => noteApi.deleteNote(1), ['/note/delete/1'], { deleted: true }],
  ['noteApi.likeNote', 'post', () => noteApi.likeNote(1), ['/note/like/1'], { liked: true }],
  ['wishApi.getWishList', 'get', () => wishApi.getWishList(), ['/wish/list'], []],
  ['wishApi.getWishDetail', 'get', () => wishApi.getWishDetail(1), ['/wish/detail/1'], { id: 1 }],
  ['wishApi.addWish', 'post', () => wishApi.addWish({ content: '心愿' }), ['/wish/add', { content: '心愿' }], { id: 1 }],
  ['wishApi.updateWish', 'put', () => wishApi.updateWish(1, { content: '更新' }), ['/wish/update/1', { content: '更新' }], { updated: true }],
  ['wishApi.fulfillWish', 'post', () => wishApi.fulfillWish(1), ['/wish/fulfill/1'], { fulfilled: true }],
  ['wishApi.unfulfillWish', 'post', () => wishApi.unfulfillWish(1), ['/wish/unfulfill/1'], { fulfilled: false }],
  ['wishApi.deleteWish', 'delete', () => wishApi.deleteWish(1), ['/wish/delete/1'], { deleted: true }],
  ['notificationApi.getNotificationList', 'get', () => notificationApi.getNotificationList({ page: 1 }), ['/notification/list', { params: { page: 1 } }], []],
  ['notificationApi.getUnreadCount', 'get', () => notificationApi.getUnreadCount(), ['/notification/unreadCount'], { count: 1 }],
  ['notificationApi.markAsRead', 'put', () => notificationApi.markAsRead(1), ['/notification/read/1', null, { retryConfig: { retries: 0 } }], { read: true }],
  ['notificationApi.markAllAsRead', 'put', () => notificationApi.markAllAsRead(), ['/notification/readAll', null, { retryConfig: { retries: 0 } }], { read: true }],
  ['uploadApi.uploadImage', 'post', () => uploadApi.uploadImage(new File(['test'], 'test.jpg', { type: 'image/jpeg' })), ['/upload/image', expect.any(FormData), { headers: { 'Content-Type': 'multipart/form-data' } }], { url: 'https://example.com/image.jpg' }]
]

describe('API 模块请求合同', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it.each(cases)('%s 应传递准确参数并返回成功合同', async (_, method, invoke, args, data) => {
    const response = { code: 200, message: 'ok', data }
    requestMock[method].mockResolvedValue(response)

    await expect(invoke()).resolves.toEqual(response)
    expect(requestMock[method]).toHaveBeenCalledWith(...args)
  })
})
