import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock uni.request
vi.mock('uni', () => ({
  showLoading: vi.fn(),
  hideLoading: vi.fn(),
  showToast: vi.fn(),
  getStorageSync: vi.fn(() => 'mock_token'),
  request: vi.fn()
}))

describe('API Endpoints', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('User API', () => {
    it('should define loginByPhone endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.loginByPhone).toBeDefined()
      expect(typeof userApi.loginByPhone).toBe('function')
    })

    it('should define sendVerifyCode endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.sendVerifyCode).toBeDefined()
      expect(typeof userApi.sendVerifyCode).toBe('function')
    })

    it('should define getUserInfo endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.getUserInfo).toBeDefined()
      expect(typeof userApi.getUserInfo).toBe('function')
    })

    it('should define updateUserInfo endpoint', async () => {
      const { userApi } = await import('@/api')
      expect(userApi.updateUserInfo).toBeDefined()
      expect(typeof userApi.updateUserInfo).toBe('function')
    })
  })

  describe('Couple API', () => {
    it('should define getCoupleInfo endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.getCoupleInfo).toBeDefined()
      expect(typeof coupleApi.getCoupleInfo).toBe('function')
    })

    it('should define getCoupleHome endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.getCoupleHome).toBeDefined()
      expect(typeof coupleApi.getCoupleHome).toBe('function')
    })

    it('should define generateCoupleCode endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.generateCoupleCode).toBeDefined()
      expect(typeof coupleApi.generateCoupleCode).toBe('function')
    })

    it('should define bindCouple endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.bindCouple).toBeDefined()
      expect(typeof coupleApi.bindCouple).toBe('function')
    })

    it('should define validateCoupleCode endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.validateCoupleCode).toBeDefined()
      expect(typeof coupleApi.validateCoupleCode).toBe('function')
    })

    it('should define applyUnbind endpoint', async () => {
      const { coupleApi } = await import('@/api')
      expect(coupleApi.applyUnbind).toBeDefined()
      expect(typeof coupleApi.applyUnbind).toBe('function')
    })
  })

  describe('Menu API', () => {
    it('should define getMenuList endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.getMenuList).toBeDefined()
      expect(typeof menuApi.getMenuList).toBe('function')
    })

    it('should define getMenuDetail endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.getMenuDetail).toBeDefined()
      expect(typeof menuApi.getMenuDetail).toBe('function')
    })

    it('should define addMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.addMenu).toBeDefined()
      expect(typeof menuApi.addMenu).toBe('function')
    })

    it('should define updateMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.updateMenu).toBeDefined()
      expect(typeof menuApi.updateMenu).toBe('function')
    })

    it('should define deleteMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.deleteMenu).toBeDefined()
      expect(typeof menuApi.deleteMenu).toBe('function')
    })

    it('should define likeMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.likeMenu).toBeDefined()
      expect(typeof menuApi.likeMenu).toBe('function')
    })

    it('should define favoriteMenu endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.favoriteMenu).toBeDefined()
      expect(typeof menuApi.favoriteMenu).toBe('function')
    })

    it('should define getMenuStats endpoint', async () => {
      const { menuApi } = await import('@/api')
      expect(menuApi.getMenuStats).toBeDefined()
      expect(typeof menuApi.getMenuStats).toBe('function')
    })
  })

  describe('Anniversary API', () => {
    it('should define getAnniversaryList endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.getAnniversaryList).toBeDefined()
      expect(typeof anniversaryApi.getAnniversaryList).toBe('function')
    })

    it('should define getUpcomingAnniversaries endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.getUpcomingAnniversaries).toBeDefined()
      expect(typeof anniversaryApi.getUpcomingAnniversaries).toBe('function')
    })

    it('should define getNextAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.getNextAnniversary).toBeDefined()
      expect(typeof anniversaryApi.getNextAnniversary).toBe('function')
    })

    it('should define addAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.addAnniversary).toBeDefined()
      expect(typeof anniversaryApi.addAnniversary).toBe('function')
    })

    it('should define updateAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.updateAnniversary).toBeDefined()
      expect(typeof anniversaryApi.updateAnniversary).toBe('function')
    })

    it('should define deleteAnniversary endpoint', async () => {
      const { anniversaryApi } = await import('@/api')
      expect(anniversaryApi.deleteAnniversary).toBeDefined()
      expect(typeof anniversaryApi.deleteAnniversary).toBe('function')
    })
  })

  describe('Feed API', () => {
    it('should define getTodayFeedStatus endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.getTodayFeedStatus).toBeDefined()
      expect(typeof feedApi.getTodayFeedStatus).toBe('function')
    })

    it('should define sendFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.sendFeed).toBeDefined()
      expect(typeof feedApi.sendFeed).toBe('function')
    })

    it('should define getReceivedFeeds endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.getReceivedFeeds).toBeDefined()
      expect(typeof feedApi.getReceivedFeeds).toBe('function')
    })

    it('should define getSentFeeds endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.getSentFeeds).toBeDefined()
      expect(typeof feedApi.getSentFeeds).toBe('function')
    })

    it('should define acceptFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.acceptFeed).toBeDefined()
      expect(typeof feedApi.acceptFeed).toBe('function')
    })

    it('should define rejectFeed endpoint', async () => {
      const { feedApi } = await import('@/api')
      expect(feedApi.rejectFeed).toBeDefined()
      expect(typeof feedApi.rejectFeed).toBe('function')
    })
  })

  describe('Note API', () => {
    it('should define getNoteList endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.getNoteList).toBeDefined()
      expect(typeof noteApi.getNoteList).toBe('function')
    })

    it('should define getNoteDetail endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.getNoteDetail).toBeDefined()
      expect(typeof noteApi.getNoteDetail).toBe('function')
    })

    it('should define addNote endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.addNote).toBeDefined()
      expect(typeof noteApi.addNote).toBe('function')
    })

    it('should define updateNote endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.updateNote).toBeDefined()
      expect(typeof noteApi.updateNote).toBe('function')
    })

    it('should define deleteNote endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.deleteNote).toBeDefined()
      expect(typeof noteApi.deleteNote).toBe('function')
    })

    it('should define likeNote endpoint', async () => {
      const { noteApi } = await import('@/api')
      expect(noteApi.likeNote).toBeDefined()
      expect(typeof noteApi.likeNote).toBe('function')
    })
  })

  describe('Wish API', () => {
    it('should define getWishList endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.getWishList).toBeDefined()
      expect(typeof wishApi.getWishList).toBe('function')
    })

    it('should define addWish endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.addWish).toBeDefined()
      expect(typeof wishApi.addWish).toBe('function')
    })

    it('should define fulfillWish endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.fulfillWish).toBeDefined()
      expect(typeof wishApi.fulfillWish).toBe('function')
    })

    it('should define deleteWish endpoint', async () => {
      const { wishApi } = await import('@/api')
      expect(wishApi.deleteWish).toBeDefined()
      expect(typeof wishApi.deleteWish).toBe('function')
    })
  })

  describe('Notification API', () => {
    it('should define getNotificationList endpoint', async () => {
      const { notificationApi } = await import('@/api')
      expect(notificationApi.getNotificationList).toBeDefined()
      expect(typeof notificationApi.getNotificationList).toBe('function')
    })

    it('should define getUnreadCount endpoint', async () => {
      const { notificationApi } = await import('@/api')
      expect(notificationApi.getUnreadCount).toBeDefined()
      expect(typeof notificationApi.getUnreadCount).toBe('function')
    })

    it('should define markAsRead endpoint', async () => {
      const { notificationApi } = await import('@/api')
      expect(notificationApi.markAsRead).toBeDefined()
      expect(typeof notificationApi.markAsRead).toBe('function')
    })
  })

  describe('Upload API', () => {
    it('should define uploadImage endpoint', async () => {
      const { uploadApi } = await import('@/api')
      expect(uploadApi.uploadImage).toBeDefined()
      expect(typeof uploadApi.uploadImage).toBe('function')
    })
  })
})