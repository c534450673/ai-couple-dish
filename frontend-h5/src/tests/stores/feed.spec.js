import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  feedApi: {
    getTodayFeedStatus: vi.fn(),
    getReceivedFeeds: vi.fn(),
    getSentFeeds: vi.fn(),
    sendFeed: vi.fn(),
    acceptFeed: vi.fn(),
    rejectFeed: vi.fn()
  }
}))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { feedApi } from '@/api'
import { mapFeedState, useFeedStore } from '@/stores/feed'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useFeedStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    feedApi.getTodayFeedStatus.mockResolvedValue({ data: { remainingCount: 2 } })
    feedApi.getReceivedFeeds.mockResolvedValue({ data: [] })
    feedApi.getSentFeeds.mockResolvedValue({ data: [] })
  })

  it('按真实后端状态和视角映射状态机，并把过期保留为明确终态原因', () => {
    expect(mapFeedState(null, 'sender')).toEqual({ state: 'draft', terminalReason: null })
    expect(mapFeedState({ status: 0 }, 'sender')).toEqual({ state: 'sent', terminalReason: null })
    expect(mapFeedState({ status: 0 }, 'receiver')).toEqual({ state: 'received', terminalReason: null })
    expect(mapFeedState({ status: 1 }, 'receiver')).toEqual({ state: 'accepted', terminalReason: null })
    expect(mapFeedState({ status: 2 }, 'receiver')).toEqual({ state: 'rejected', terminalReason: 'rejected' })
    expect(mapFeedState({ status: 3 }, 'receiver')).toEqual({ state: 'rejected', terminalReason: 'expired' })
  })

  it('替代、完成确认和撤回均 unavailable，不发伪请求且保留草稿', async () => {
    const store = useFeedStore()
    store.updateDraft({ feedType: 'dessert', content: '保留的草稿', message: '悄悄话' })

    expect(await store.requestCounter()).toEqual(expect.objectContaining({ status: 'unavailable', reason: 'COUNTER_NOT_SUPPORTED' }))
    expect(await store.requestCompletion()).toEqual(expect.objectContaining({ status: 'unavailable', reason: 'COMPLETION_NOT_SUPPORTED' }))
    expect(await store.requestWithdraw()).toEqual(expect.objectContaining({ status: 'unavailable', reason: 'WITHDRAW_NOT_SUPPORTED' }))
    expect(store.draft).toEqual(expect.objectContaining({ content: '保留的草稿', message: '悄悄话' }))
    expect(feedApi.sendFeed).not.toHaveBeenCalled()
    expect(feedApi.acceptFeed).not.toHaveBeenCalled()
    expect(feedApi.rejectFeed).not.toHaveBeenCalled()
  })

  it('发送期间禁用重复提交，按数组发送图片且成功后只刷新 feed 资源', async () => {
    const pending = deferred()
    feedApi.sendFeed.mockReturnValue(pending.promise)
    const store = useFeedStore()
    store.today = { remainingCount: 1 }
    store.updateDraft({ feedType: 'meal', content: '一起吃饭', imageUrls: ['https://image.invalid/a.webp'] })

    const first = store.sendDraft()
    const second = await store.sendDraft()

    expect(second).toEqual({ status: 'unavailable', reason: 'REQUEST_PENDING' })
    expect(store.isMutationPending).toBe(true)
    expect(feedApi.sendFeed).toHaveBeenCalledOnce()
    expect(feedApi.sendFeed).toHaveBeenCalledWith(expect.objectContaining({ imageUrls: ['https://image.invalid/a.webp'] }))
    pending.resolve({ data: 81 })
    await first

    expect(feedApi.getTodayFeedStatus).toHaveBeenCalledOnce()
    expect(feedApi.getReceivedFeeds).toHaveBeenCalledOnce()
    expect(feedApi.getSentFeeds).toHaveBeenCalledOnce()
    expect(store.draft.content).toBe('')
  })

  it('写入成功后的资源刷新完成前仍保持 pending，避免一致性窗口内重复提交', async () => {
    const refreshing = deferred()
    feedApi.sendFeed.mockResolvedValue({ data: 82 })
    feedApi.getTodayFeedStatus.mockReturnValue(refreshing.promise)
    const store = useFeedStore()
    store.today = { remainingCount: 1 }
    store.updateDraft({ content: '刷新期间保持禁用' })

    const sending = store.sendDraft()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(feedApi.getTodayFeedStatus).toHaveBeenCalledOnce()
    expect(store.isMutationPending).toBe(true)
    refreshing.resolve({ data: { remainingCount: 0 } })
    await sending
    expect(store.isMutationPending).toBe(false)
  })

  it('次数用尽和网络失败都不伪成功，网络失败保留全部输入', async () => {
    const store = useFeedStore()
    store.today = { remainingCount: 0 }
    store.updateDraft({ feedType: 'drink', content: '一杯饮料', imageUrls: ['local-preview'], message: '给你' })

    expect(await store.sendDraft()).toEqual(expect.objectContaining({ status: 'unavailable', reason: 'DAILY_LIMIT_REACHED' }))
    expect(feedApi.sendFeed).not.toHaveBeenCalled()

    store.today = { remainingCount: 1 }
    feedApi.sendFeed.mockRejectedValue({ code: 500, message: 'network' })
    await expect(store.sendDraft()).rejects.toMatchObject({ code: 500 })
    expect(store.draft).toEqual({ feedType: 'drink', content: '一杯饮料', imageUrls: ['local-preview'], message: '给你' })
    expect(store.mutationStatus).toBe('error')
  })

  it('缺少投喂类型时不发请求并保留草稿', async () => {
    const store = useFeedStore()
    store.today = { remainingCount: 1 }
    store.updateDraft({ feedType: '  ', content: '一起吃饭', message: '等你' })

    expect(await store.sendDraft()).toEqual(expect.objectContaining({
      status: 'unavailable', reason: 'FEED_TYPE_REQUIRED'
    }))
    expect(feedApi.sendFeed).not.toHaveBeenCalled()
    expect(store.draft).toEqual(expect.objectContaining({
      feedType: '  ', content: '一起吃饭', message: '等你'
    }))
  })

  it('只允许待领取投喂被接受或拒绝，并对过期竞态刷新真实状态', async () => {
    const store = useFeedStore()
    expect(await store.accept({ id: 1, status: 1 })).toEqual({ status: 'unavailable', reason: 'FEED_NOT_PENDING' })
    expect(await store.reject({ id: 2, status: 3 }, '不记录此原因')).toEqual({ status: 'unavailable', reason: 'FEED_NOT_PENDING' })

    feedApi.acceptFeed.mockRejectedValue({ code: 4008, message: '投喂已过期' })
    await expect(store.accept({ id: 3, status: 0 })).rejects.toMatchObject({ code: 4008 })
    expect(feedApi.getTodayFeedStatus).toHaveBeenCalledOnce()
    expect(feedApi.getReceivedFeeds).toHaveBeenCalledOnce()
    expect(feedApi.getSentFeeds).toHaveBeenCalledOnce()
  })

  it('send、accept、reject 成功后都重新读取三项 feed 资源', async () => {
    feedApi.sendFeed.mockResolvedValue({ data: 9 })
    feedApi.acceptFeed.mockResolvedValue({ data: null })
    feedApi.rejectFeed.mockResolvedValue({ data: null })
    const store = useFeedStore()
    store.today = { remainingCount: 2 }
    store.updateDraft({ feedType: 'meal', content: '' })

    await store.sendDraft()
    await store.accept({ id: 1, status: 0 })
    await store.reject({ id: 2, status: 0 }, '')

    expect(feedApi.getTodayFeedStatus).toHaveBeenCalledTimes(3)
    expect(feedApi.getReceivedFeeds).toHaveBeenCalledTimes(3)
    expect(feedApi.getSentFeeds).toHaveBeenCalledTimes(3)
  })
})
