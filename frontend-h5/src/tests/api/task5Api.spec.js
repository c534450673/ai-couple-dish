import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()
}))
vi.mock('@/api/request', () => ({ default: request }))

import { menuApi, recipeApi } from '@/api'

describe('Task 5 API 合同', () => {
  beforeEach(() => vi.clearAllMocks())

  it('菜单提供成对点赞与收藏端点', () => {
    menuApi.unlikeMenu(4)
    menuApi.unfavoriteMenu(4)

    expect(request.delete).toHaveBeenNthCalledWith(1, '/menu/unlike/4')
    expect(request.delete).toHaveBeenNthCalledWith(2, '/menu/unfavorite/4')
  })

  it('菜单 API 最后一层防线也不会发送 isFavorite 伪筛选', () => {
    menuApi.getMenuList({ status: 0, page: 1, pageSize: 10, isFavorite: 1 })

    expect(request.get).toHaveBeenCalledWith('/menu/list', {
      params: { status: 0, page: 1, pageSize: 10 }
    })
  })

  it('菜谱列表端点保留各自真实数据域', () => {
    const params = { pageNum: 1, pageSize: 10 }
    recipeApi.getMyRecipes(params)
    recipeApi.getCoupleRecipes(params)
    recipeApi.getRecommendedRecipes(params)
    recipeApi.searchRecipes({ ...params, keyword: '汤' })
    recipeApi.getCollectedRecipes(params)

    expect(request.get.mock.calls).toEqual([
      ['/recipe/my', { params }],
      ['/recipe/couple', { params }],
      ['/recipe/recommended', { params }],
      ['/recipe/search', { params: { ...params, keyword: '汤' } }],
      ['/recipe/collected', { params }]
    ])
  })

  it('菜谱详情和 mutation 使用合同路径且原样保留结构化数组', () => {
    const body = { title: '汤', ingredients: [], steps: [], publish: false }
    recipeApi.createRecipe(body)
    recipeApi.updateRecipe(6, body)
    recipeApi.getRecipeDetail(6)
    recipeApi.publishRecipe(6)
    recipeApi.deleteRecipe(6)
    recipeApi.likeRecipe(6)
    recipeApi.unlikeRecipe(6)
    recipeApi.collectRecipe(6)
    recipeApi.uncollectRecipe(6)

    expect(request.post).toHaveBeenCalledWith('/recipe/create', body)
    expect(request.put).toHaveBeenCalledWith('/recipe/update/6', body)
    expect(request.get).toHaveBeenCalledWith('/recipe/detail/6')
    expect(request.post).toHaveBeenCalledWith('/recipe/publish/6')
    expect(request.delete).toHaveBeenCalledWith('/recipe/delete/6')
    expect(request.post).toHaveBeenCalledWith('/recipe/like/6')
    expect(request.delete).toHaveBeenCalledWith('/recipe/like/6')
    expect(request.post).toHaveBeenCalledWith('/recipe/collect/6')
    expect(request.delete).toHaveBeenCalledWith('/recipe/collect/6')
  })
})
