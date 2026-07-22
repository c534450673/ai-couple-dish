import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  menuApi: {
    getMenuList: vi.fn(),
    getMenuDetail: vi.fn(),
    getMenuStats: vi.fn(),
    addMenu: vi.fn(),
    updateMenu: vi.fn(),
    deleteMenu: vi.fn(),
    likeMenu: vi.fn(),
    unlikeMenu: vi.fn(),
    favoriteMenu: vi.fn(),
    unfavoriteMenu: vi.fn()
  }
}))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { menuApi } from '@/api'
import { useMenuStore } from '@/stores/menu'

describe('useMenuStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('归一菜单 PageDTO，过滤不存在的 isFavorite 参数并去重追加页', async () => {
    menuApi.getMenuList
      .mockResolvedValueOnce({ data: { page: 1, pageSize: 2, total: 3, totalPages: 2, hasMore: true, list: [{ id: 1 }, { id: 2 }] } })
      .mockResolvedValueOnce({ data: { page: 2, pageSize: 2, total: 3, totalPages: 2, hasMore: false, list: [{ id: 2 }, { id: 3 }] } })
    const store = useMenuStore()

    await store.fetchList({ status: 0, isFavorite: 1, page: 1, pageSize: 2 })
    await store.fetchList({ status: 0, page: 2, pageSize: 2 }, { append: true })

    expect(menuApi.getMenuList.mock.calls[0][0]).toEqual({ status: 0, page: 1, pageSize: 2 })
    expect(store.items.map(item => item.id)).toEqual([1, 2, 3])
    expect(store.pagination).toEqual({ page: 2, pageSize: 2, total: 3, totalPages: 2, hasMore: false })
    expect(store.listStatus).toBe('success')
  })

  it('旧详情请求晚返回时不覆盖新路由实体', async () => {
    let resolveFirst
    menuApi.getMenuDetail
      .mockReturnValueOnce(new Promise(resolve => { resolveFirst = resolve }))
      .mockResolvedValueOnce({ data: { id: 2, restaurantName: '新餐厅' } })
    const store = useMenuStore()

    const first = store.fetchDetail(1)
    await store.fetchDetail(2)
    resolveFirst({ data: { id: 1, restaurantName: '旧餐厅' } })
    await first

    expect(store.detail.id).toBe(2)
  })

  it('mutation 成功只更新相关实体，失败时不做乐观累计', async () => {
    const store = useMenuStore()
    store.items = [{ id: 1, likeCount: 2 }, { id: 2, likeCount: 8 }]
    store.detail = { id: 1, likeCount: 2 }
    menuApi.likeMenu.mockResolvedValue({ data: null })

    await store.setLiked(1, true)

    expect(store.items).toEqual([{ id: 1, likeCount: 3, liked: true }, { id: 2, likeCount: 8 }])
    expect(store.detail.likeCount).toBe(3)
    menuApi.unlikeMenu.mockRejectedValueOnce({ code: 2010 })
    await expect(store.setLiked(1, false)).rejects.toEqual({ code: 2010 })
    expect(store.detail.likeCount).toBe(3)
  })

  it('列表失败进入可重试错误态', async () => {
    menuApi.getMenuList.mockRejectedValueOnce({ code: 2006 }).mockResolvedValueOnce({
      data: { page: 1, pageSize: 10, total: 0, totalPages: 0, hasMore: false, list: [] }
    })
    const store = useMenuStore()

    await expect(store.fetchList({ page: 1, pageSize: 10 })).rejects.toEqual({ code: 2006 })
    expect(store.listStatus).toBe('error')
    await store.retryList()
    expect(menuApi.getMenuList).toHaveBeenCalledTimes(2)
    expect(store.listStatus).toBe('empty')
  })

  it('追加页失败保留已有列表，并以 append 精确重试失败页', async () => {
    menuApi.getMenuList
      .mockResolvedValueOnce({
        data: { page: 1, pageSize: 2, total: 3, totalPages: 2, hasMore: true, list: [{ id: 1 }] }
      })
      .mockRejectedValueOnce({ code: 'NETWORK_ERROR' })
      .mockResolvedValueOnce({
        data: { page: 2, pageSize: 2, total: 3, totalPages: 2, hasMore: false, list: [{ id: 2 }] }
      })
    const store = useMenuStore()
    await store.fetchList({ page: 1, pageSize: 2 })

    await expect(store.fetchList({ page: 2, pageSize: 2 }, { append: true }))
      .rejects.toEqual({ code: 'NETWORK_ERROR' })

    expect(store.items).toEqual([{ id: 1 }])
    expect(store.listStatus).toBe('success')
    expect(store.loadMoreError).toEqual({ code: 'NETWORK_ERROR' })
    expect(store.failedPage).toBe(2)

    await store.retryList()

    expect(menuApi.getMenuList).toHaveBeenLastCalledWith({ page: 2, pageSize: 2 })
    expect(store.items).toEqual([{ id: 1 }, { id: 2 }])
    expect(store.loadMoreError).toBeNull()
    expect(store.failedPage).toBeNull()
  })
})
