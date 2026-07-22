import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  anniversaryApi: { getAnniversaryList: vi.fn() },
  wishApi: { getWishList: vi.fn() },
  noteApi: { getNoteList: vi.fn(), getNoteDetail: vi.fn(), addNote: vi.fn(), updateNote: vi.fn(), deleteNote: vi.fn() }
}))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { anniversaryApi, noteApi, wishApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'
import { normalizeTimelineItem, useMemoriesStore } from '@/stores/memories'

const deferred = () => {
  let resolve
  const promise = new Promise(resolvePromise => { resolve = resolvePromise })
  return { promise, resolve }
}

describe('useMemoriesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    anniversaryApi.getAnniversaryList.mockResolvedValue({ data: [] })
    wishApi.getWishList.mockResolvedValue({ data: [] })
    noteApi.getNoteList.mockResolvedValue({ data: [] })
  })

  it('把三种真实 DTO 精确归一，并以 type 前缀避免同 ID 冲突', () => {
    expect(normalizeTimelineItem('anniversary', { id: 1, name: '相识日', anniversaryDate: '2026-08-20', typeName: '恋爱' })).toEqual({
      id: 'anniversary:1', type: 'anniversary', occurredAt: '2026-08-20', creatorId: null,
      title: '相识日', summary: '恋爱', media: []
    })
    expect(normalizeTimelineItem('wish', { id: 1, creatorId: 9, title: '看海', description: '去海边', imageUrl: 'wish.webp', achievedDate: '2026-07-01' })).toEqual({
      id: 'wish:1', type: 'wish', occurredAt: '2026-07-01', creatorId: 9,
      title: '看海', summary: '去海边', media: ['wish.webp']
    })
    expect(normalizeTimelineItem('note', { id: 1, authorId: 8, title: '晚餐', content: '<script>bad()</script>', photoUrls: ['note.webp'], createTime: '2026-07-02 20:00:00' })).toEqual({
      id: 'note:1', type: 'note', occurredAt: '2026-07-02 20:00:00', creatorId: 8,
      title: '晚餐', summary: '<script>bad()</script>', media: ['note.webp']
    })
  })

  it('使用 allSettled 保留成功来源，失败只标记对应 chip，地图明确 unavailable 且不生成事件', async () => {
    anniversaryApi.getAnniversaryList.mockResolvedValue({ data: [{ id: 1, name: '相识日', anniversaryDate: '2026-08-20' }] })
    wishApi.getWishList.mockRejectedValue({ code: 2006 })
    noteApi.getNoteList.mockResolvedValue({ data: [{ id: 2, title: '晚餐', content: '很好吃', createTime: '2026-07-02' }] })
    const store = useMemoriesStore()

    await store.fetchAll()

    expect(store.sourceStatus).toEqual({ anniversary: 'success', wish: 'error', note: 'success', map: 'unavailable' })
    expect(store.timeline.map(item => item.id)).toEqual(['anniversary:1', 'note:2'])
    expect(store.timeline.some(item => item.type === 'map')).toBe(false)
    expect(store.sourceErrors.wish).toMatchObject({ code: 2006 })
  })

  it('局部重试只重发失败 source，空数组与失败状态明确区分', async () => {
    wishApi.getWishList.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: [] })
    const store = useMemoriesStore()
    await store.fetchAll()

    await store.retrySource('wish')

    expect(wishApi.getWishList).toHaveBeenCalledTimes(2)
    expect(anniversaryApi.getAnniversaryList).toHaveBeenCalledOnce()
    expect(noteApi.getNoteList).toHaveBeenCalledOnce()
    expect(store.sourceStatus.wish).toBe('empty')
    expect(store.sourceErrors.wish).toBeNull()
  })

  it('后发请求完成后，旧聚合响应不会覆盖新路由请求的数据', async () => {
    const oldAnniversary = deferred()
    anniversaryApi.getAnniversaryList
      .mockReturnValueOnce(oldAnniversary.promise)
      .mockResolvedValueOnce({ data: [{ id: 2, name: '新数据', anniversaryDate: '2026-09-01' }] })
    const store = useMemoriesStore()

    const oldRequest = store.fetchAll()
    const newRequest = store.fetchAll()
    await newRequest
    oldAnniversary.resolve({ data: [{ id: 1, name: '旧数据', anniversaryDate: '2026-10-01' }] })
    await oldRequest

    expect(store.timeline.map(item => item.title)).toContain('新数据')
    expect(store.timeline.map(item => item.title)).not.toContain('旧数据')
  })

  it('较早的聚合响应不会覆盖较新的单来源重试结果', async () => {
    const oldWish = deferred()
    wishApi.getWishList
      .mockReturnValueOnce(oldWish.promise)
      .mockResolvedValueOnce({ data: [{ id: 2, title: '重试新数据', createTime: '2026-08-01' }] })
    const store = useMemoriesStore()

    const aggregate = store.fetchAll()
    await store.retrySource('wish')
    oldWish.resolve({ data: [{ id: 1, title: '聚合旧数据', createTime: '2026-09-01' }] })
    await aggregate

    expect(store.timeline.map(item => item.title)).toContain('重试新数据')
    expect(store.timeline.map(item => item.title)).not.toContain('聚合旧数据')
  })

  it('缺失或无效日期使用稳定顺序，不让排序抛错', async () => {
    noteApi.getNoteList.mockResolvedValue({ data: [
      { id: 1, title: '无日期 A', content: '', createTime: null },
      { id: 2, title: '无效日期', content: '', createTime: 'not-a-date' },
      { id: 3, title: '无日期 B', content: '', createTime: '' }
    ] })
    const store = useMemoriesStore()

    await store.fetchAll()

    expect(store.timeline.map(item => item.id)).toEqual(['note:1', 'note:2', 'note:3'])
  })

  it('三项真实来源全部失败时聚合日志为 error 而不是 empty', async () => {
    anniversaryApi.getAnniversaryList.mockRejectedValue({ code: 500 })
    wishApi.getWishList.mockRejectedValue({ code: 501 })
    noteApi.getNoteList.mockRejectedValue({ code: 502 })
    const store = useMemoriesStore()

    await store.fetchAll()

    const aggregateLog = logUiEvent.mock.calls.find(([event]) => event === 'memories.aggregate')
    expect(aggregateLog?.[1]).toEqual(expect.objectContaining({
      module: 'memories_store', operation: 'aggregate', result: 'error', itemCount: 0
    }))
  })

  it('解除纪念日关联的笔记更新结果清空本地关联 ID 和名称', async () => {
    noteApi.updateNote.mockResolvedValue({ data: null })
    const store = useMemoriesStore()

    const updated = await store.saveNote(7, {
      title: '晚餐', content: '记录', isAnniversaryLinked: 0,
      anniversaryId: 99, anniversaryName: '残留纪念日'
    })

    expect(noteApi.updateNote).toHaveBeenCalledWith(7, {
      title: '晚餐', content: '记录', isAnniversaryLinked: 0, anniversaryId: null
    })
    expect(updated).toEqual(expect.objectContaining({
      id: 7, isAnniversaryLinked: 0, anniversaryId: null, anniversaryName: null
    }))
  })
})
