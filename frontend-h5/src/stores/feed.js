import { defineStore } from 'pinia'
import { feedApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const emptyDraft = () => ({ feedType: 'meal', content: '', imageUrls: [], message: '' })
const errorCode = error => String(error?.code || error?.response?.status || 'UNKNOWN')

const logFeed = (operation, result, startedAt, fields = {}) => logUiEvent(`feed.${operation}`, {
  module: 'feed_store',
  operation,
  result,
  durationMs: Date.now() - startedAt,
  ...fields
})

export const mapFeedState = (feed, perspective = 'receiver') => {
  if (!feed) return { state: 'draft', terminalReason: null }
  const status = Number(feed.status)
  if (status === 0) return { state: perspective === 'sender' ? 'sent' : 'received', terminalReason: null }
  if (status === 1) return { state: 'accepted', terminalReason: null }
  if (status === 2) return { state: 'rejected', terminalReason: 'rejected' }
  if (status === 3) return { state: 'rejected', terminalReason: 'expired' }
  return { state: 'rejected', terminalReason: 'unknown' }
}

export const useFeedStore = defineStore('feed', {
  state: () => ({
    draft: emptyDraft(),
    today: null,
    received: [],
    sent: [],
    loadStatus: 'idle',
    mutationStatus: 'idle',
    mutationKey: '',
    error: null,
    loadRequestId: 0,
    mutationRequestId: 0
  }),
  getters: {
    isMutationPending: state => state.mutationStatus === 'loading'
  },
  actions: {
    updateDraft(patch) {
      this.draft = { ...this.draft, ...patch }
    },
    unavailable(operation, reason) {
      const startedAt = Date.now()
      const requestId = ++this.mutationRequestId
      logFeed(operation, 'unavailable', startedAt, { requestId, errorCode: reason })
      return { status: 'unavailable', reason, draft: { ...this.draft } }
    },
    requestCounter() {
      return this.unavailable('counter', 'COUNTER_NOT_SUPPORTED')
    },
    requestCompletion() {
      return this.unavailable('completion', 'COMPLETION_NOT_SUPPORTED')
    },
    requestWithdraw() {
      return this.unavailable('withdraw', 'WITHDRAW_NOT_SUPPORTED')
    },
    async fetchAll() {
      const startedAt = Date.now()
      const requestId = ++this.loadRequestId
      this.loadStatus = 'loading'
      this.error = null
      logFeed('resources', 'loading', startedAt, { requestId })
      const results = await Promise.allSettled([
        feedApi.getTodayFeedStatus(),
        feedApi.getReceivedFeeds(),
        feedApi.getSentFeeds()
      ])
      if (requestId !== this.loadRequestId) {
        logFeed('resources', 'stale_ignored', startedAt, { requestId })
        return results
      }
      if (results[0].status === 'fulfilled') this.today = results[0].value?.data || null
      if (results[1].status === 'fulfilled') this.received = Array.isArray(results[1].value?.data) ? results[1].value.data : []
      if (results[2].status === 'fulfilled') this.sent = Array.isArray(results[2].value?.data) ? results[2].value.data : []
      const failures = results.filter(result => result.status === 'rejected')
      this.loadStatus = failures.length === results.length
        ? 'error'
        : (this.received.length || this.sent.length || this.today ? 'success' : 'empty')
      this.error = failures[0]?.reason || null
      logFeed('resources', this.loadStatus, startedAt, {
        requestId,
        itemCount: this.received.length + this.sent.length,
        ...(failures.length ? { errorCode: errorCode(failures[0].reason) } : {})
      })
      return results
    },
    async sendDraft() {
      if (this.isMutationPending) {
        logFeed('send', 'unavailable', Date.now(), {
          requestId: this.mutationRequestId,
          errorCode: 'REQUEST_PENDING'
        })
        return { status: 'unavailable', reason: 'REQUEST_PENDING' }
      }
      if (Number(this.today?.remainingCount) === 0) return this.unavailable('send', 'DAILY_LIMIT_REACHED')
      const startedAt = Date.now()
      const requestId = ++this.mutationRequestId
      const payload = {
        feedType: this.draft.feedType,
        content: this.draft.content,
        imageUrls: Array.isArray(this.draft.imageUrls) ? [...this.draft.imageUrls] : [],
        message: this.draft.message
      }
      this.mutationStatus = 'loading'
      this.mutationKey = 'send'
      this.error = null
      logFeed('send', 'loading', startedAt, { requestId })
      try {
        const response = await feedApi.sendFeed(payload)
        const id = response?.data
        this.draft = emptyDraft()
        await this.fetchAll()
        this.mutationStatus = 'success'
        logFeed('send', 'success', startedAt, { requestId, itemCount: id == null ? 0 : 1 })
        return { status: 'success', id }
      } catch (error) {
        this.mutationStatus = 'error'
        this.error = error
        logFeed('send', 'error', startedAt, { requestId, errorCode: errorCode(error) })
        throw error
      } finally {
        this.mutationKey = ''
      }
    },
    async mutatePending(operation, feed, request) {
      if (this.isMutationPending) {
        logFeed(operation, 'unavailable', Date.now(), {
          requestId: this.mutationRequestId,
          errorCode: 'REQUEST_PENDING'
        })
        return { status: 'unavailable', reason: 'REQUEST_PENDING' }
      }
      if (Number(feed?.status) !== 0) {
        const requestId = ++this.mutationRequestId
        logFeed(operation, 'unavailable', Date.now(), { requestId, errorCode: 'FEED_NOT_PENDING' })
        return { status: 'unavailable', reason: 'FEED_NOT_PENDING' }
      }
      const startedAt = Date.now()
      const requestId = ++this.mutationRequestId
      this.mutationStatus = 'loading'
      this.mutationKey = `${operation}:${feed.id}`
      this.error = null
      logFeed(operation, 'loading', startedAt, { requestId })
      try {
        await request()
        await this.fetchAll()
        this.mutationStatus = 'success'
        logFeed(operation, 'success', startedAt, { requestId, itemCount: 1 })
        return { status: 'success' }
      } catch (error) {
        this.mutationStatus = 'error'
        this.error = error
        logFeed(operation, 'error', startedAt, { requestId, errorCode: errorCode(error) })
        await this.fetchAll()
        throw error
      } finally {
        this.mutationKey = ''
      }
    },
    accept(feed) {
      return this.mutatePending('accept', feed, () => feedApi.acceptFeed(feed.id))
    },
    reject(feed, reason = '') {
      return this.mutatePending('reject', feed, () => feedApi.rejectFeed(feed.id, reason))
    }
  }
})
