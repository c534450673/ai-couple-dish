import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() }
const route = { params: {}, query: {} }
const menuStore = vi.hoisted(() => ({
  items: [], detail: null, stats: {}, pagination: { hasMore: false },
  listStatus: 'empty', detailStatus: 'idle', mutationStatus: 'idle', error: null,
  fetchList: vi.fn(), retryList: vi.fn(), fetchStats: vi.fn(), fetchDetail: vi.fn(),
  setLiked: vi.fn(), setFavorite: vi.fn(), remove: vi.fn(), create: vi.fn(), update: vi.fn()
}))
const menuDraft = vi.hoisted(() => ({
  draft: { value: null }, hasDraft: { value: false }, save: vi.fn(), restore: vi.fn(), clear: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => router,
  useRoute: () => route,
  onBeforeRouteLeave: vi.fn()
}))
vi.mock('@/stores/menu', () => ({ useMenuStore: () => menuStore }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ userInfo: { id: 42 } }) }))
vi.mock('@/composables/useDraft', () => ({
  useDraft: vi.fn(() => menuDraft)
}))
vi.mock('@/api', () => ({ uploadApi: { uploadImage: vi.fn() } }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))
vi.mock('vant', () => ({ showToast: vi.fn(), showConfirmDialog: vi.fn(() => Promise.resolve()) }))

import MenuIndex from '@/views/menu/index.vue'
import MenuDetail from '@/views/menu/detail.vue'
import MenuEditor from '@/views/menu/add.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))

describe('菜单页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.params = {}
    route.query = {}
    Object.assign(menuStore, {
      items: [], detail: null, stats: {}, pagination: { hasMore: false },
      listStatus: 'empty', detailStatus: 'idle', mutationStatus: 'idle', error: null
    })
  })

  it('列表不提供伪收藏筛选，并明确图片合同降级', async () => {
    menuStore.items = [{ id: 1, restaurantName: '星港餐厅', status: 0 }]
    menuStore.listStatus = 'success'
    const wrapper = mount(MenuIndex)
    await flush()

    expect(wrapper.text()).toContain('后端图片合同缺失')
    expect(wrapper.text()).toContain('收藏筛选暂不可用')
    expect(wrapper.find('[data-test="menu-placeholder-1"]').exists()).toBe(true)
    expect(JSON.stringify(menuStore.fetchList.mock.calls)).not.toContain('isFavorite')
  })

  it('列表错误只暴露一次显式重试入口，空态可新建', async () => {
    menuStore.listStatus = 'error'
    const wrapper = mount(MenuIndex)
    await wrapper.find('[data-test="menu-retry"]').trigger('click')
    expect(menuStore.retryList).toHaveBeenCalledOnce()

    menuStore.listStatus = 'empty'
    wrapper.unmount()
    const emptyWrapper = mount(MenuIndex)
    expect(emptyWrapper.find('[data-test="menu-empty-add"]').exists()).toBe(true)
  })

  it('详情始终使用本地占位，提供真实编辑路由和 pending 操作', async () => {
    route.params = { id: '7' }
    menuStore.detail = { id: 7, restaurantName: '星港餐厅', likeCount: 2, isFavorite: false }
    menuStore.detailStatus = 'success'
    const wrapper = mount(MenuDetail)
    await flush()

    expect(wrapper.find('[data-test="menu-detail-placeholder"]').attributes('data-contract')).toBe('backend-image-missing')
    await wrapper.find('[data-test="menu-edit"]').trigger('click')
    expect(router.push).toHaveBeenCalledWith('/menu/7/edit')
    expect(wrapper.find('[data-test="menu-like"]').attributes('disabled')).toBeUndefined()
  })

  it('编辑器限制图片并在提交 pending 时禁用，成功清当前草稿', async () => {
    const draft = await import('@/composables/useDraft')
    const clear = vi.fn()
    draft.useDraft.mockReturnValueOnce({ draft: { value: null }, hasDraft: { value: false }, save: vi.fn(), restore: vi.fn(), clear })
    menuStore.create.mockResolvedValue({ id: 8 })
    const wrapper = mount(MenuEditor)

    await wrapper.find('[data-test="restaurant-name"]').setValue('星港餐厅')
    await wrapper.find('form').trigger('submit')
    await flush()

    expect(menuStore.create).toHaveBeenCalledWith(expect.objectContaining({ restaurantName: '星港餐厅', photoUrls: [] }))
    expect(clear).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('图片仅保留在本地草稿与本次预览')
  })
})
