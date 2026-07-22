import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  recipeApi: {
    getMyRecipes: vi.fn(),
    getCoupleRecipes: vi.fn(),
    getRecommendedRecipes: vi.fn(),
    searchRecipes: vi.fn(),
    getCollectedRecipes: vi.fn(),
    getRecipeDetail: vi.fn(),
    createRecipe: vi.fn(),
    updateRecipe: vi.fn(),
    deleteRecipe: vi.fn(),
    publishRecipe: vi.fn(),
    likeRecipe: vi.fn(),
    unlikeRecipe: vi.fn(),
    collectRecipe: vi.fn(),
    uncollectRecipe: vi.fn()
  }
}))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { recipeApi } from '@/api'
import { useRecipeStore } from '@/stores/recipe'

describe('useRecipeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('按我的草稿、情侣已发布、全局推荐选择真实端点并归一 MyBatis Page', async () => {
    const page = { records: [{ id: 5 }], total: 11, current: 2, size: 5, pages: 3 }
    recipeApi.getMyRecipes.mockResolvedValue({ data: page })
    recipeApi.getCoupleRecipes.mockResolvedValue({ data: page })
    recipeApi.getRecommendedRecipes.mockResolvedValue({ data: page })
    const store = useRecipeStore()

    await store.fetchList({ source: 'my', pageNum: 2, pageSize: 5 })
    expect(recipeApi.getMyRecipes).toHaveBeenCalledWith({ pageNum: 2, pageSize: 5 })
    expect(store.pagination).toEqual({ pageNum: 2, pageSize: 5, total: 11, totalPages: 3, hasMore: true })
    await store.fetchList({ source: 'couple', pageNum: 1, pageSize: 5, difficulty: 3 })
    expect(recipeApi.getCoupleRecipes).toHaveBeenCalledWith({ pageNum: 1, pageSize: 5 })
    await store.fetchList({ source: 'recommended', pageNum: 1, pageSize: 5, sortBy: 'likes' })
    expect(recipeApi.getRecommendedRecipes).toHaveBeenCalledWith({ pageNum: 1, pageSize: 5 })
  })

  it('搜索只发送 keyword/pageNum/pageSize，不伪装为情侣私域', async () => {
    recipeApi.searchRecipes.mockResolvedValue({ data: { records: [], total: 0, current: 1, size: 10, pages: 0 } })
    const store = useRecipeStore()

    await store.fetchList({ source: 'search', keyword: '面', pageNum: 1, pageSize: 10, collected: true })

    expect(recipeApi.searchRecipes).toHaveBeenCalledWith({ keyword: '面', pageNum: 1, pageSize: 10 })
    expect(store.activeSource).toBe('search')
    expect(store.listStatus).toBe('empty')
  })

  it('旧详情请求不会覆盖当前详情', async () => {
    let resolveFirst
    recipeApi.getRecipeDetail
      .mockReturnValueOnce(new Promise(resolve => { resolveFirst = resolve }))
      .mockResolvedValueOnce({ data: { id: 9, title: '当前菜谱' } })
    const store = useRecipeStore()

    const first = store.fetchDetail(8)
    await store.fetchDetail(9)
    resolveFirst({ data: { id: 8, title: '旧菜谱' } })
    await first

    expect(store.detail.id).toBe(9)
  })

  it('重复点赞业务错误不会乐观切换，成功只更新目标菜谱', async () => {
    const store = useRecipeStore()
    store.items = [{ id: 1, liked: false, likeCount: 2 }, { id: 2, liked: false, likeCount: 4 }]
    store.detail = { id: 1, liked: false, likeCount: 2 }
    recipeApi.likeRecipe.mockRejectedValueOnce({ code: 4001 }).mockResolvedValueOnce({ data: null })

    await expect(store.setLiked(1, true)).rejects.toEqual({ code: 4001 })
    expect(store.detail).toMatchObject({ liked: false, likeCount: 2 })
    await store.setLiked(1, true)
    expect(store.detail).toMatchObject({ liked: true, likeCount: 3 })
    expect(store.items[1]).toEqual({ id: 2, liked: false, likeCount: 4 })
  })

  it('更新时保留结构化空数组，成功后只刷新当前实体', async () => {
    const store = useRecipeStore()
    store.items = [{ id: 3, title: '旧标题' }, { id: 4, title: '其他' }]
    recipeApi.updateRecipe.mockResolvedValue({ data: { id: 3, title: '新标题', ingredients: [], steps: [] } })

    await store.update(3, { title: '新标题', ingredients: [], steps: [] })

    expect(recipeApi.updateRecipe).toHaveBeenCalledWith(3, { title: '新标题', ingredients: [], steps: [] })
    expect(store.items).toEqual([{ id: 3, title: '新标题', ingredients: [], steps: [] }, { id: 4, title: '其他' }])
  })

  it('追加页失败保留已有菜谱，并以 append 精确重试失败页', async () => {
    recipeApi.getMyRecipes
      .mockResolvedValueOnce({
        data: { records: [{ id: 1 }], total: 2, current: 1, size: 1, pages: 2 }
      })
      .mockRejectedValueOnce({ code: 'NETWORK_ERROR' })
      .mockResolvedValueOnce({
        data: { records: [{ id: 2 }], total: 2, current: 2, size: 1, pages: 2 }
      })
    const store = useRecipeStore()
    await store.fetchList({ source: 'my', pageNum: 1, pageSize: 1 })

    await expect(store.fetchList({ source: 'my', pageNum: 2, pageSize: 1 }, { append: true }))
      .rejects.toEqual({ code: 'NETWORK_ERROR' })

    expect(store.items).toEqual([{ id: 1 }])
    expect(store.listStatus).toBe('success')
    expect(store.loadMoreError).toEqual({ code: 'NETWORK_ERROR' })
    expect(store.failedPage).toBe(2)

    await store.retryList()

    expect(recipeApi.getMyRecipes).toHaveBeenLastCalledWith({ pageNum: 2, pageSize: 1 })
    expect(store.items).toEqual([{ id: 1 }, { id: 2 }])
    expect(store.loadMoreError).toBeNull()
    expect(store.failedPage).toBeNull()
  })
})
