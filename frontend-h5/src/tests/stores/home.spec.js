import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({
  coupleApi: { getCoupleInfo: vi.fn(), getLoveTimer: vi.fn() },
  recipeApi: { getCoupleRecipes: vi.fn() },
  anniversaryApi: { getNextAnniversary: vi.fn() },
  wishApi: { getWishList: vi.fn() },
  feedApi: { getReceivedFeeds: vi.fn(), getSentFeeds: vi.fn() },
  logUiEvent: vi.fn()
}))

vi.mock('@/api', () => ({
  coupleApi: mocks.coupleApi,
  recipeApi: mocks.recipeApi,
  anniversaryApi: mocks.anniversaryApi,
  wishApi: mocks.wishApi,
  feedApi: mocks.feedApi
}))
vi.mock('@/composables/useStructuredLog', () => ({
  logUiEvent: mocks.logUiEvent,
  normalizeUiErrorCode: error => String(error?.code ?? error?.response?.status ?? 'UNKNOWN_ERROR')
}))

import { useHomeStore } from '@/stores/home'
import { useUserStore } from '@/stores/user'

const ok = data => ({ code: 200, data })
const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

const primeSuccess = () => {
  mocks.coupleApi.getCoupleInfo.mockResolvedValue(ok({ partner: { nickName: '星河', avatarUrl: '/partner.webp' } }))
  mocks.coupleApi.getLoveTimer.mockResolvedValue(ok({ loveDays: 1314 }))
  mocks.recipeApi.getCoupleRecipes.mockResolvedValue(ok({ records: [{ id: 9, title: '星空汤' }], total: 12, current: 1, size: 1, pages: 12 }))
  mocks.anniversaryApi.getNextAnniversary.mockResolvedValue(ok({ id: 1, name: '相识日', daysUntil: 23 }))
  mocks.wishApi.getWishList.mockResolvedValue(ok([
    { id: 1, title: '旧心愿', createTime: '2026-07-01T10:00:00' },
    { id: 2, title: '新心愿', createTime: '2026-07-20T10:00:00' }
  ]))
  mocks.feedApi.getReceivedFeeds.mockResolvedValue(ok([{ id: 3, content: '较旧', createTime: '2026-07-10T10:00:00' }]))
  mocks.feedApi.getSentFeeds.mockResolvedValue(ok([{ id: 4, content: '最新', createTime: '2026-07-22T10:00:00' }]))
}

describe('useHomeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    primeSuccess()
  })

  it('独立归一七项资源并只按真实接口形状取值', async () => {
    const store = useHomeStore()
    await store.loadAll()

    expect(store.resources.couple.status).toBe('success')
    expect(store.resources.timer.data).toEqual({ loveDays: 1314 })
    expect(store.resources.recipe.data).toEqual({
      item: { id: 9, title: '星空汤' }, total: 12, current: 1, size: 1, pages: 12
    })
    expect(store.resources.wish.data.title).toBe('新心愿')
    expect(store.resources.feed.data.content).toBe('最新')
    expect(store.resources.footprint.status).toBe('unavailable')
    expect(mocks.recipeApi.getCoupleRecipes).toHaveBeenCalledWith({ pageNum: 1, pageSize: 1 })
    expect(mocks.wishApi.getWishList).toHaveBeenCalledWith()
  })

  it('优先复用全局 store 的真实情侣快照，避免重复请求被去重器取消', async () => {
    const userStore = useUserStore()
    userStore.coupleInfo = { partner: { nickName: '星河', avatarUrl: '/partner.webp' } }
    const store = useHomeStore()

    await store.loadResource('couple')

    expect(store.resources.couple).toMatchObject({
      status: 'success',
      data: { partner: { nickName: '星河', avatarUrl: '/partner.webp' } }
    })
    expect(mocks.coupleApi.getCoupleInfo).not.toHaveBeenCalled()
  })

  it('成功空数据进入 empty 且不生成 0 或兜底内容', async () => {
    mocks.coupleApi.getCoupleInfo.mockResolvedValue(ok(null))
    mocks.coupleApi.getLoveTimer.mockResolvedValue(ok(null))
    mocks.recipeApi.getCoupleRecipes.mockResolvedValue(ok({ records: [], total: 0, current: 1, size: 1, pages: 0 }))
    mocks.anniversaryApi.getNextAnniversary.mockResolvedValue(ok(null))
    mocks.wishApi.getWishList.mockResolvedValue(ok([]))
    mocks.feedApi.getReceivedFeeds.mockResolvedValue(ok([]))
    mocks.feedApi.getSentFeeds.mockResolvedValue(ok([]))
    const store = useHomeStore()

    await store.loadAll()

    for (const key of ['couple', 'timer', 'recipe', 'anniversary', 'wish', 'feed']) {
      expect(store.resources[key].status).toBe('empty')
      expect(store.resources[key].data).toBeNull()
    }
  })

  it('业务码与网络错误互不清空，并将 401/2006 映射到登录和绑定', async () => {
    mocks.coupleApi.getCoupleInfo.mockResolvedValue({ code: 401, message: 'expired' })
    mocks.coupleApi.getLoveTimer.mockRejectedValue({ code: 'NETWORK_ERROR' })
    mocks.anniversaryApi.getNextAnniversary.mockResolvedValue({ code: 2006, message: '未绑定情侣关系' })
    const store = useHomeStore()

    await store.loadAll()

    expect(store.resources.couple).toMatchObject({ status: 'error', errorCode: '401', flow: 'login' })
    expect(store.resources.timer).toMatchObject({ status: 'error', errorCode: 'NETWORK_ERROR', flow: null })
    expect(store.resources.anniversary).toMatchObject({ status: 'error', errorCode: '2006', flow: 'bind' })
    expect(store.resources.recipe.status).toBe('success')
    expect(store.resources.wish.status).toBe('success')
  })

  it('Feed 用 allSettled 保留成功侧、按 createTime 降序并标记局部降级', async () => {
    mocks.feedApi.getReceivedFeeds.mockRejectedValue({ code: 503 })
    mocks.feedApi.getSentFeeds.mockResolvedValue(ok([
      { id: 2, content: '旧动态', createTime: '2026-07-01T10:00:00' },
      { id: 3, content: '真实最新动态', createTime: '2026-07-22T10:00:00' }
    ]))
    const store = useHomeStore()

    await store.loadResource('feed')

    expect(store.resources.feed.status).toBe('success')
    expect(store.resources.feed.data.content).toBe('真实最新动态')
    expect(store.resources.feed.degradedSides).toEqual(['received'])
  })

  it('Feed 双侧失败才进入整体 error', async () => {
    mocks.feedApi.getReceivedFeeds.mockRejectedValue({ code: 502 })
    mocks.feedApi.getSentFeeds.mockRejectedValue({ code: 503 })
    const store = useHomeStore()

    await store.loadResource('feed')

    expect(store.resources.feed).toMatchObject({ status: 'error', errorCode: 'ALL_FEED_SIDES_FAILED' })
  })

  it('Feed 将业务码失败视为 reject，并保留另一侧成功数据', async () => {
    mocks.feedApi.getReceivedFeeds.mockResolvedValue({ code: 503, message: 'busy' })
    mocks.feedApi.getSentFeeds.mockResolvedValue(ok([
      { id: 5, message: '成功侧消息', createTime: '2026-07-23T10:00:00' }
    ]))
    const store = useHomeStore()

    await store.loadResource('feed')

    expect(store.resources.feed).toMatchObject({
      status: 'success',
      data: { id: 5, message: '成功侧消息', createTime: '2026-07-23T10:00:00' },
      degradedSides: ['received']
    })
  })

  it('Feed 双侧鉴权或未绑定时仍映射到正确访问流程', async () => {
    mocks.feedApi.getReceivedFeeds.mockResolvedValue({ code: 401, message: 'expired' })
    mocks.feedApi.getSentFeeds.mockResolvedValue({ code: 2006, message: '未绑定情侣关系' })
    const store = useHomeStore()

    await store.loadResource('feed')

    expect(store.resources.feed).toMatchObject({ status: 'error', errorCode: '401', flow: 'login' })
  })

  it('心愿排序对无效时间和相同时间保持稳定，不自行添加请求参数', async () => {
    mocks.wishApi.getWishList.mockResolvedValue(ok([
      { id: 1, title: '同时间第一项', createTime: '2026-07-22T10:00:00' },
      { id: 2, title: '同时间第二项', createTime: '2026-07-22T10:00:00' },
      { id: 3, title: '无效时间', createTime: 'invalid' }
    ]))
    const store = useHomeStore()

    await store.loadResource('wish')

    expect(store.resources.wish.data.id).toBe(1)
    expect(mocks.wishApi.getWishList).toHaveBeenCalledWith()
  })

  it('服务端真实返回 loveDays 为 0 时保留为成功数据', async () => {
    mocks.coupleApi.getLoveTimer.mockResolvedValue(ok({ loveDays: 0 }))
    const store = useHomeStore()

    await store.loadResource('timer')

    expect(store.resources.timer).toMatchObject({ status: 'success', data: { loveDays: 0 } })
  })

  it('footprint 固定 unavailable，不调用任何首页 API', async () => {
    const store = useHomeStore()

    await store.loadResource('footprint')

    expect(store.resources.footprint).toMatchObject({
      status: 'unavailable', errorCode: 'FOOTPRINT_NOT_SUPPORTED', requestId: 0
    })
    expect(mocks.coupleApi.getCoupleInfo).not.toHaveBeenCalled()
    expect(mocks.recipeApi.getCoupleRecipes).not.toHaveBeenCalled()
    expect(mocks.feedApi.getReceivedFeeds).not.toHaveBeenCalled()
  })

  it('各资源 requestId 独立递增，加载一项不改变其他项', async () => {
    const store = useHomeStore()

    await store.loadResource('recipe')
    await store.loadResource('recipe')

    expect(store.resources.recipe.requestId).toBe(2)
    expect(store.resources.couple.requestId).toBe(0)
    expect(store.resources.wish.requestId).toBe(0)
    expect(store.resources.footprint.requestId).toBe(0)
  })

  it('retry 只更新并重发目标资源，重试计数和其他成功数据保持独立', async () => {
    const store = useHomeStore()
    await store.loadAll()
    vi.clearAllMocks()
    mocks.anniversaryApi.getNextAnniversary.mockResolvedValue(ok({ id: 2, name: '生日', daysUntil: 8 }))

    await store.retryResource('anniversary')

    expect(mocks.anniversaryApi.getNextAnniversary).toHaveBeenCalledOnce()
    expect(mocks.coupleApi.getCoupleInfo).not.toHaveBeenCalled()
    expect(mocks.wishApi.getWishList).not.toHaveBeenCalled()
    expect(store.resources.anniversary.retryCount).toBe(1)
    expect(store.resources.recipe.data.total).toBe(12)
  })

  it('旧 requestId 的迟到响应不会覆盖新状态并产生脱敏诊断日志', async () => {
    const oldRequest = deferred()
    const newRequest = deferred()
    mocks.coupleApi.getLoveTimer
      .mockReturnValueOnce(oldRequest.promise)
      .mockReturnValueOnce(newRequest.promise)
    const store = useHomeStore()

    const oldLoad = store.loadResource('timer')
    const currentLoad = store.retryResource('timer')
    newRequest.resolve(ok({ loveDays: 88 }))
    await currentLoad
    oldRequest.resolve(ok({ loveDays: 3 }))
    await oldLoad

    expect(store.resources.timer.data).toEqual({ loveDays: 88 })
    expect(mocks.logUiEvent).toHaveBeenCalledWith('home.resource', expect.objectContaining({
      resource: 'timer', state: 'stale_ignored'
    }))
    expect(JSON.stringify(mocks.logUiEvent.mock.calls)).not.toMatch(/星河|partner\.webp|真实最新动态|Authorization|token/i)
  })

  it('页面失效只取消 loading 资源的提交资格', async () => {
    const pending = deferred()
    mocks.coupleApi.getCoupleInfo.mockReturnValue(pending.promise)
    const store = useHomeStore()
    const loading = store.loadResource('couple')

    store.invalidatePending()
    pending.resolve(ok({ partner: { nickName: '迟到数据' } }))
    await loading

    expect(store.resources.couple.status).toBe('idle')
    expect(store.resources.couple.data).toBeNull()
  })
})
