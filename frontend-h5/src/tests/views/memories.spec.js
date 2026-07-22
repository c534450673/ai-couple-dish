import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() }
const route = { params: {}, query: {} }
const memoriesStore = vi.hoisted(() => ({
  timeline: [], filteredTimeline: [], sourceStatus: { anniversary: 'empty', wish: 'error', note: 'success', map: 'unavailable' },
  sourceErrors: { anniversary: null, wish: new Error('offline'), note: null, map: null }, activeType: 'all',
  fetchAll: vi.fn(), retrySource: vi.fn(), setActiveType: vi.fn(), fetchNoteDetail: vi.fn(), saveNote: vi.fn()
}))
const feedStore = vi.hoisted(() => ({
  draft: { feedType: 'meal', content: '一起吃饭', imageUrls: [], message: '' },
  today: { remainingCount: 1 }, received: [], sent: [], loadStatus: 'success', mutationStatus: 'idle',
  isMutationPending: false, updateDraft: vi.fn(), fetchAll: vi.fn(), sendDraft: vi.fn(),
  accept: vi.fn(), reject: vi.fn(), requestCounter: vi.fn(), requestCompletion: vi.fn(), requestWithdraw: vi.fn()
}))
const draftState = vi.hoisted(() => ({ draft: { value: null }, hasDraft: { value: false }, save: vi.fn(), restore: vi.fn(), clear: vi.fn() }))

vi.mock('vue-router', () => ({ useRouter: () => router, useRoute: () => route, onBeforeRouteLeave: vi.fn() }))
vi.mock('@/stores/memories', () => ({ useMemoriesStore: () => memoriesStore }))
vi.mock('@/stores/feed', () => ({ useFeedStore: () => feedStore }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ userInfo: { id: 42 } }) }))
vi.mock('@/composables/useDraft', () => ({ useDraft: vi.fn(() => draftState) }))
vi.mock('@/composables/useReducedMotion', async () => {
  const { ref } = await import('vue')
  return { useReducedMotion: () => ref(true) }
})
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))
vi.mock('vant', () => ({ showToast: vi.fn(), showConfirmDialog: vi.fn(() => Promise.resolve()) }))

import MemoriesIndex from '@/views/memories/index.vue'
import NoteEditor from '@/views/memories/note-editor.vue'
import NoteDetail from '@/views/memories/note-detail.vue'
import FeedIndex from '@/views/feed/index.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))

describe('回忆与笔记页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.params = {}
    route.query = {}
    Object.assign(memoriesStore, {
      timeline: [], filteredTimeline: [],
      sourceStatus: { anniversary: 'empty', wish: 'error', note: 'success', map: 'unavailable' },
      sourceErrors: { anniversary: null, wish: new Error('offline'), note: null, map: null }, activeType: 'all'
    })
    Object.assign(feedStore, {
      draft: { feedType: 'meal', content: '一起吃饭', imageUrls: [], message: '' },
      today: { remainingCount: 1 }, received: [], sent: [], loadStatus: 'success', mutationStatus: 'idle', isMutationPending: false
    })
    feedStore.fetchAll.mockResolvedValue([])
  })

  it('地图 chip 明确不可用，单源错误提供局部重试且不清空其他时间线', async () => {
    memoriesStore.filteredTimeline = [{ id: 'note:7', type: 'note', title: '晚餐', summary: '<img src=x onerror=alert(1)>', media: [], occurredAt: '2026-07-01' }]
    const wrapper = mount(MemoriesIndex)
    await flush()

    expect(wrapper.find('[data-test="filter-map"]').text()).toContain('暂不可用')
    expect(wrapper.find('[data-test="source-error-wish"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
    expect(wrapper.find('img[src="x"]').exists()).toBe(false)
    await wrapper.find('[data-test="retry-wish"]').trigger('click')
    expect(memoriesStore.retrySource).toHaveBeenCalledWith('wish')
  })

  it('笔记新增只提交真实字段，并以 note/new 草稿 key 隔离', async () => {
    const { useDraft } = await import('@/composables/useDraft')
    memoriesStore.saveNote.mockResolvedValue({ id: 11 })
    const wrapper = mount(NoteEditor)

    await wrapper.find('[data-test="note-title"]').setValue('星空晚餐')
    await wrapper.find('[data-test="note-content"]').setValue('属于我们的味觉故事')
    await wrapper.find('[data-test="note-location"]').setValue('云端餐厅')
    await wrapper.find('form').trigger('submit')
    await flush()

    expect(useDraft).toHaveBeenCalledWith({ userId: 42, resource: 'note', resourceId: null })
    expect(memoriesStore.saveNote).toHaveBeenCalledWith(null, {
      title: '星空晚餐', content: '属于我们的味觉故事', location: '云端餐厅',
      latitude: null, longitude: null, isAnniversaryLinked: 0, anniversaryId: null, photoUrls: []
    })
    expect(JSON.stringify(memoriesStore.saveNote.mock.calls)).not.toContain('recipe')
    expect(draftState.clear).toHaveBeenCalledOnce()
  })

  it('详情展示真实图片、正文、位置和创建人，明确菜谱关联 unavailable，作者可进入内嵌编辑', async () => {
    route.params = { id: '7' }
    memoriesStore.fetchNoteDetail.mockResolvedValue({
      id: 7, title: '晚餐', content: '很好吃', location: '星港', photoUrls: ['photo.webp'], authorName: '小星', isAuthor: true
    })
    const wrapper = mount(NoteDetail)
    await flush()

    expect(wrapper.text()).toContain('很好吃')
    expect(wrapper.text()).toContain('星港')
    expect(wrapper.text()).toContain('小星')
    expect(wrapper.text()).toContain('菜谱关联暂不可用')
    expect(wrapper.find('[data-test="note-photo-0"]').attributes('src')).toBe('photo.webp')
    await wrapper.find('[data-test="note-edit"]').trigger('click')
    expect(wrapper.findComponent(NoteEditor).exists()).toBe(true)
  })

  it('无效笔记 ID 不发详情请求并返回回忆页', async () => {
    route.params = { id: '../bad' }
    const wrapper = mount(NoteDetail)
    await flush()

    expect(memoriesStore.fetchNoteDetail).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="invalid-note-id"]').exists()).toBe(true)
    await wrapper.find('[data-test="back-memories"]').trigger('click')
    expect(router.replace).toHaveBeenCalledWith('/memories?type=note')
  })

  it('投喂提交 pending 时禁用，reduced-motion 成功后使用静态反馈', async () => {
    feedStore.sendDraft.mockResolvedValue({ status: 'success', id: 9 })
    const wrapper = mount(FeedIndex)
    await flush()

    await wrapper.find('[data-test="feed-send"]').trigger('click')
    await flush()
    expect(wrapper.find('[data-test="feed-success"]').attributes('data-motion')).toBe('static')

    feedStore.isMutationPending = true
    wrapper.unmount()
    const pendingWrapper = mount(FeedIndex)
    expect(pendingWrapper.find('[data-test="feed-send"]').attributes('disabled')).toBeDefined()
  })
})
