import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  request: { get: vi.fn(), put: vi.fn() },
  logUiEvent: vi.fn()
}))

vi.mock('@/api/request', () => ({ default: mocks.request }))
vi.mock('@/composables/useStructuredLog', async () => {
  const actual = await vi.importActual('@/composables/useStructuredLog')
  return { ...actual, logUiEvent: mocks.logUiEvent }
})

import NotificationView from '@/views/notification/index.vue'
import { useNotificationStore } from '@/stores/notification'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

const item = (id, type = 2, isRead = 0) => ({
  id,
  type,
  title: `标题${id}`,
  content: `通知正文${id}`,
  isRead,
  readTime: null,
  createTime: '2026-07-23T10:00:00'
})

describe('通知 Store 与页面', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.request.get.mockResolvedValue({ data: [] })
    mocks.request.put.mockResolvedValue({ data: null })
  })

  it('分页从 1 开始并精确映射 all、interaction、system 筛选', async () => {
    const store = useNotificationStore()
    mocks.request.get.mockResolvedValue({ data: [item(1)] })

    await store.loadPage({ reset: true })
    await store.setFilter('interaction')
    await store.setFilter('system')

    expect(mocks.request.get.mock.calls).toEqual([
      ['/notification/list', { params: { page: 1, pageSize: 20 } }],
      ['/notification/list', { params: { type: 2, page: 1, pageSize: 20 } }],
      ['/notification/list', { params: { type: 1, page: 1, pageSize: 20 } }]
    ])
  })

  it('AI 筛选没有服务端能力时零网络并进入明确 unavailable', async () => {
    const store = useNotificationStore()

    await store.setFilter('ai')

    expect(mocks.request.get).not.toHaveBeenCalled()
    expect(store.status).toBe('empty')
    expect(store.isFilterUnavailable).toBe(true)
  })

  it('裸数组满 20 条才允许下一页，短页推断分页结束', async () => {
    const store = useNotificationStore()
    mocks.request.get
      .mockResolvedValueOnce({ data: Array.from({ length: 20 }, (_, index) => item(index + 1)) })
      .mockResolvedValueOnce({ data: [item(21)] })

    await store.loadPage({ reset: true })
    expect(store.hasMore).toBe(true)
    await store.loadMore()

    expect(store.items).toHaveLength(21)
    expect(store.hasMore).toBe(false)
    expect(mocks.request.get).toHaveBeenLastCalledWith('/notification/list', {
      params: { page: 2, pageSize: 20 }
    })
  })

  it('非数组响应进入 error，不伪装为空数据', async () => {
    const store = useNotificationStore()
    mocks.request.get.mockResolvedValue({ data: { list: [] } })

    await store.loadPage({ reset: true })

    expect(store.status).toBe('error')
    expect(store.errorCode).toBe('INVALID_NOTIFICATION_LIST')
  })

  it('切换筛选后旧 requestId 的迟到结果不能覆盖当前数据', async () => {
    const store = useNotificationStore()
    const interaction = deferred()
    const system = deferred()
    mocks.request.get
      .mockReturnValueOnce(interaction.promise)
      .mockReturnValueOnce(system.promise)

    const oldRequest = store.setFilter('interaction')
    const currentRequest = store.setFilter('system')
    system.resolve({ data: [item(2, 1)] })
    await currentRequest
    interaction.resolve({ data: [item(1, 2)] })
    await oldRequest

    expect(store.filter).toBe('system')
    expect(store.items.map(entry => entry.id)).toEqual([2])
  })

  it('未读数失败保留上次可信值，不伪装为 0', async () => {
    const store = useNotificationStore()
    store.unreadCount = 7
    mocks.request.get.mockRejectedValue(new Error('network'))

    await store.loadUnreadCount()

    expect(store.unreadCount).toBe(7)
    expect(store.unreadStatus).toBe('error')
  })

  it('单条已读先乐观更新，失败时完整回滚条目与全局计数，并防重复', async () => {
    const store = useNotificationStore()
    const pending = deferred()
    store.items = [item(8, 2, 0)]
    store.unreadCount = 1
    mocks.request.put.mockReturnValueOnce(pending.promise)

    const first = store.markAsRead(8)
    const duplicate = store.markAsRead(8)
    expect(store.items[0].isRead).toBe(1)
    expect(store.unreadCount).toBe(0)
    pending.reject({ code: 500 })
    await first
    await duplicate

    expect(mocks.request.put).toHaveBeenCalledOnce()
    expect(mocks.request.put).toHaveBeenCalledWith('/notification/read/8', null, {
      retryConfig: { retries: 0 }
    })
    expect(store.items[0]).toEqual(item(8, 2, 0))
    expect(store.unreadCount).toBe(1)
  })

  it('全部已读只在服务端确认后更新已加载记录，失败保持原状', async () => {
    const store = useNotificationStore()
    const pending = deferred()
    store.items = [item(1), item(2, 1, 1)]
    store.unreadCount = 4
    mocks.request.put.mockReturnValueOnce(pending.promise)

    const request = store.markAllAsRead()
    expect(store.items[0].isRead).toBe(0)
    expect(store.unreadCount).toBe(4)
    pending.resolve({ data: null })
    await request
    expect(mocks.request.put).toHaveBeenCalledWith('/notification/readAll', null, {
      retryConfig: { retries: 0 }
    })
    expect(store.items.every(entry => entry.isRead === 1)).toBe(true)
    expect(store.unreadCount).toBe(0)

    store.items = [item(3)]
    store.unreadCount = 1
    mocks.request.put.mockRejectedValueOnce({ code: 500 })
    await store.markAllAsRead()
    expect(store.items[0].isRead).toBe(0)
    expect(store.unreadCount).toBe(1)
  })

  it('单条已读在途时拒绝启动全部已读，完成后才允许下一写入', async () => {
    const store = useNotificationStore()
    const pending = deferred()
    store.items = [item(1), item(2)]
    store.unreadCount = 2
    mocks.request.put.mockReturnValueOnce(pending.promise)

    const single = store.markAsRead(1)
    await store.markAllAsRead()

    expect(mocks.request.put).toHaveBeenCalledOnce()
    expect(mocks.request.put).toHaveBeenCalledWith('/notification/read/1', null, {
      retryConfig: { retries: 0 }
    })
    pending.resolve({ data: null })
    await single

    mocks.request.put.mockResolvedValueOnce({ data: null })
    await store.markAllAsRead()
    expect(mocks.request.put).toHaveBeenCalledTimes(2)
    expect(store.items.every(entry => entry.isRead === 1)).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('全部已读在途时拒绝单条已读，失败后仍保留可信快照', async () => {
    const store = useNotificationStore()
    const pending = deferred()
    store.items = [item(1), item(2)]
    store.unreadCount = 2
    mocks.request.put.mockReturnValueOnce(pending.promise)

    const readAll = store.markAllAsRead()
    await store.markAsRead(1)

    expect(mocks.request.put).toHaveBeenCalledOnce()
    expect(store.items).toEqual([item(1), item(2)])
    expect(store.unreadCount).toBe(2)
    pending.reject({ code: 500 })
    await readAll
    expect(store.items).toEqual([item(1), item(2)])
    expect(store.unreadCount).toBe(2)
  })

  it('页面任一已读写入 pending 时禁用全部其他已读控件', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(NotificationView, { global: { plugins: [pinia] } })
    await flushPromises()
    const store = useNotificationStore()
    store.items = [item(1), item(2)]
    store.unreadCount = 2
    const pending = deferred()
    mocks.request.put.mockReturnValueOnce(pending.promise)

    const write = store.markAsRead(1)
    await flushPromises()

    expect(wrapper.find('[data-test="read-all"]').attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('.notification-card').every(card => card.attributes('disabled') !== undefined)).toBe(true)
    pending.resolve({ data: null })
    await write
  })

  it('关闭本机通知显示后页面真实消费偏好且不读取通知数据', async () => {
    localStorage.setItem('couple-cosmos:notification-display', 'disabled')
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(NotificationView, { global: { plugins: [pinia] } })
    await flushPromises()

    expect(wrapper.find('[data-test="notification-display-disabled"]').text()).toContain('本机通知显示已关闭')
    expect(wrapper.find('[data-test="read-all"]').exists()).toBe(false)
    expect(wrapper.findAll('.notification-card')).toHaveLength(0)
    expect(mocks.request.get).not.toHaveBeenCalled()
    expect(mocks.logUiEvent).toHaveBeenCalledWith(
      'notification.preference.apply',
      expect.objectContaining({ result: 'disabled', enabled: false, errorCode: 'NONE' })
    )
  })

  it('页面显示 AI unavailable 且不创建轮询定时器', async () => {
    vi.useFakeTimers()
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(NotificationView, { global: { plugins: [pinia] } })
    await vi.runAllTicks()
    const callsBeforeAi = mocks.request.get.mock.calls.length
    await wrapper.find('[data-test="filter-ai"]').trigger('click')
    await vi.runAllTicks()

    expect(wrapper.find('[data-test="ai-unavailable"]').text()).toContain('暂不支持 AI 通知筛选')
    expect(mocks.request.get).toHaveBeenCalledTimes(callsBeforeAi)
    expect(vi.getTimerCount()).toBe(0)
    vi.useRealTimers()
  })

  it('结构化日志不包含通知正文或完整响应', async () => {
    const store = useNotificationStore()
    mocks.request.get.mockResolvedValue({ data: [item(91)] })

    await store.loadPage({ reset: true })

    const serializedLogs = JSON.stringify(mocks.logUiEvent.mock.calls)
    expect(serializedLogs).not.toContain('通知正文91')
    expect(serializedLogs).not.toContain('标题91')
    expect(serializedLogs).toContain('notification.list.load')
  })
})
