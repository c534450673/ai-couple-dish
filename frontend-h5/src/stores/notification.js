import { defineStore } from 'pinia'
import { notificationApi } from '@/api'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'

export const NOTIFICATION_FILTERS = ['all', 'interaction', 'system', 'ai']

const FILTER_TYPES = {
  interaction: 2,
  system: 1
}

const hashIdentifier = (value) => {
  let hash = 2166136261
  for (const character of String(value)) {
    hash ^= character.charCodeAt(0)
    hash = Math.imul(hash, 16777619)
  }
  return `n_${(hash >>> 0).toString(16)}`
}

const isUnauthorized = (error) => normalizeUiErrorCode(error) === '401'

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    items: [],
    filter: 'all',
    page: 1,
    pageSize: 20,
    hasMore: true,
    status: 'idle',
    errorCode: null,
    unreadCount: null,
    unreadStatus: 'idle',
    isFilterUnavailable: false,
    requestSequence: 0,
    pendingReadIds: {},
    readAllPending: false
  }),

  actions: {
    async loadPage({ reset = false } = {}) {
      const requestId = ++this.requestSequence
      const startedAt = Date.now()
      if (reset) {
        this.items = []
        this.page = 1
        this.hasMore = true
        this.errorCode = null
      }
      this.isFilterUnavailable = this.filter === 'ai'

      if (this.isFilterUnavailable) {
        this.status = 'empty'
        this.hasMore = false
        logUiEvent('notification.list.load', {
          module: 'notification', operation: 'list_load', result: 'unavailable', durationMs: 0,
          errorCode: 'AI_FILTER_UNAVAILABLE', requestId, page: 1, pageSize: this.pageSize,
          filter: this.filter, itemCount: 0, hasMore: false
        })
        return
      }

      const requestedPage = this.page
      this.status = this.items.length ? 'success' : 'loading'
      logUiEvent('notification.list.load', {
        module: 'notification', operation: 'list_load', result: 'started', durationMs: 0,
        errorCode: 'NONE', requestId, page: requestedPage, pageSize: this.pageSize,
        filter: this.filter, itemCount: this.items.length, hasMore: this.hasMore
      })

      const params = { page: requestedPage, pageSize: this.pageSize }
      if (FILTER_TYPES[this.filter]) params.type = FILTER_TYPES[this.filter]

      try {
        const res = await notificationApi.getNotificationList(params)
        if (requestId !== this.requestSequence) {
          logUiEvent('notification.list.load', {
            module: 'notification', operation: 'list_load', result: 'cancelled',
            durationMs: Date.now() - startedAt, errorCode: 'STALE_REQUEST', requestId,
            page: requestedPage, pageSize: this.pageSize, filter: this.filter,
            itemCount: 0, hasMore: this.hasMore
          })
          return
        }

        if (!Array.isArray(res.data)) {
          const shapeError = new Error('Invalid notification list response')
          shapeError.code = 'INVALID_NOTIFICATION_LIST'
          throw shapeError
        }
        const pageItems = res.data
        this.items = reset ? pageItems : [...this.items, ...pageItems]
        this.hasMore = pageItems.length === this.pageSize
        this.page = requestedPage + 1
        this.status = this.items.length ? 'success' : 'empty'
        this.errorCode = null
        logUiEvent('notification.list.load', {
          module: 'notification', operation: 'list_load',
          result: this.items.length ? 'success' : 'empty', durationMs: Date.now() - startedAt,
          errorCode: 'NONE', requestId, page: requestedPage, pageSize: this.pageSize,
          filter: this.filter, itemCount: pageItems.length, hasMore: this.hasMore
        })
      } catch (error) {
        if (requestId !== this.requestSequence) return
        this.errorCode = normalizeUiErrorCode(error)
        this.status = isUnauthorized(error) ? 'unauthorized' : (this.items.length ? 'success' : 'error')
        logUiEvent('notification.list.load', {
          module: 'notification', operation: 'list_load',
          result: isUnauthorized(error) ? 'unauthorized' : 'error', durationMs: Date.now() - startedAt,
          errorCode: this.errorCode, requestId, page: requestedPage, pageSize: this.pageSize,
          filter: this.filter, itemCount: this.items.length, hasMore: this.hasMore
        })
      }
    },

    async setFilter(filter) {
      this.filter = NOTIFICATION_FILTERS.includes(filter) ? filter : 'all'
      return this.loadPage({ reset: true })
    },

    async loadMore() {
      if (!this.hasMore || this.status === 'loading') return
      return this.loadPage({ reset: false })
    },

    async retry() {
      return this.loadPage({ reset: this.items.length === 0 })
    },

    async loadUnreadCount() {
      const startedAt = Date.now()
      this.unreadStatus = 'loading'
      try {
        const res = await notificationApi.getUnreadCount()
        if (!Number.isInteger(res.data) || res.data < 0) {
          const shapeError = new Error('Invalid unread count response')
          shapeError.code = 'INVALID_UNREAD_COUNT'
          throw shapeError
        }
        this.unreadCount = res.data
        this.unreadStatus = 'success'
        logUiEvent('notification.unread.load', {
          module: 'notification', operation: 'unread_load', result: 'success',
          durationMs: Date.now() - startedAt, errorCode: 'NONE', itemCount: res.data
        })
      } catch (error) {
        this.unreadStatus = isUnauthorized(error) ? 'unauthorized' : 'error'
        logUiEvent('notification.unread.load', {
          module: 'notification', operation: 'unread_load',
          result: isUnauthorized(error) ? 'unauthorized' : 'error',
          durationMs: Date.now() - startedAt, errorCode: normalizeUiErrorCode(error),
          itemCount: this.unreadCount
        })
      }
    },

    async markAsRead(id) {
      const index = this.items.findIndex(entry => entry.id === id)
      if (index < 0 || this.items[index].isRead || this.pendingReadIds[id]) return

      const startedAt = Date.now()
      const previousItem = { ...this.items[index] }
      const previousUnreadCount = this.unreadCount
      this.pendingReadIds[id] = true
      this.items[index] = { ...this.items[index], isRead: 1 }
      if (Number.isInteger(this.unreadCount)) this.unreadCount = Math.max(0, this.unreadCount - 1)
      logUiEvent('notification.read.one', {
        module: 'notification', operation: 'read_one', result: 'started', durationMs: 0,
        errorCode: 'NONE', notificationIdHash: hashIdentifier(id),
        itemCount: 1, unreadCountBefore: previousUnreadCount, unreadCountAfter: this.unreadCount
      })

      try {
        await notificationApi.markAsRead(id)
        logUiEvent('notification.read.one', {
          module: 'notification', operation: 'read_one', result: 'success',
          durationMs: Date.now() - startedAt, errorCode: 'NONE',
          notificationIdHash: hashIdentifier(id), itemCount: 1,
          unreadCountBefore: previousUnreadCount, unreadCountAfter: this.unreadCount
        })
      } catch (error) {
        const currentIndex = this.items.findIndex(entry => entry.id === id)
        if (currentIndex >= 0) this.items[currentIndex] = previousItem
        this.unreadCount = previousUnreadCount
        logUiEvent('notification.read.one', {
          module: 'notification', operation: 'read_one', result: 'error',
          durationMs: Date.now() - startedAt, errorCode: normalizeUiErrorCode(error),
          notificationIdHash: hashIdentifier(id), itemCount: 1,
          unreadCountBefore: previousUnreadCount, unreadCountAfter: this.unreadCount
        })
      } finally {
        delete this.pendingReadIds[id]
      }
    },

    async markAllAsRead() {
      if (this.readAllPending) return
      const startedAt = Date.now()
      const unreadLoadedCount = this.items.filter(entry => !entry.isRead).length
      this.readAllPending = true
      logUiEvent('notification.read.all', {
        module: 'notification', operation: 'read_all', result: 'started', durationMs: 0,
        errorCode: 'NONE', itemCount: unreadLoadedCount
      })
      try {
        await notificationApi.markAllAsRead()
        this.items = this.items.map(entry => ({ ...entry, isRead: 1 }))
        this.unreadCount = 0
        logUiEvent('notification.read.all', {
          module: 'notification', operation: 'read_all', result: 'success',
          durationMs: Date.now() - startedAt, errorCode: 'NONE', itemCount: unreadLoadedCount
        })
      } catch (error) {
        logUiEvent('notification.read.all', {
          module: 'notification', operation: 'read_all', result: 'error',
          durationMs: Date.now() - startedAt, errorCode: normalizeUiErrorCode(error),
          itemCount: unreadLoadedCount
        })
      } finally {
        this.readAllPending = false
      }
    }
  }
})
