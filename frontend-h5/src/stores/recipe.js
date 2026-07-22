import { defineStore } from 'pinia'
import { recipeApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const SOURCE_API = {
  my: 'getMyRecipes',
  couple: 'getCoupleRecipes',
  recommended: 'getRecommendedRecipes',
  search: 'searchRecipes',
  collected: 'getCollectedRecipes'
}

const errorCode = (error) => String(error?.code || error?.response?.status || 'UNKNOWN')
const logResult = (operation, result, startedAt, fields = {}) => logUiEvent(`recipe.${operation}`, {
  module: 'recipe_store', operation, result, durationMs: Date.now() - startedAt, ...fields
})
const initialPagination = () => ({ pageNum: 1, pageSize: 10, total: 0, totalPages: 0, hasMore: false })

export const useRecipeStore = defineStore('recipe', {
  state: () => ({
    items: [],
    detail: null,
    pagination: initialPagination(),
    activeSource: 'my',
    listStatus: 'idle',
    loadMoreError: null,
    failedPage: null,
    isLoadingMore: false,
    detailStatus: 'idle',
    mutationStatus: 'idle',
    mutationKey: '',
    error: null,
    lastListParams: { source: 'my', pageNum: 1, pageSize: 10 },
    listRequestId: 0,
    detailRequestId: 0
  }),
  actions: {
    async fetchList(params = {}, { append = false } = {}) {
      const startedAt = Date.now()
      const requestId = ++this.listRequestId
      const source = SOURCE_API[params.source] ? params.source : 'my'
      const requestParams = {
        ...(source === 'search' && params.keyword ? { keyword: params.keyword } : {}),
        pageNum: Number(params.pageNum || 1),
        pageSize: Number(params.pageSize || 10)
      }
      this.activeSource = source
      this.lastListParams = { source, ...requestParams }
      if (append) {
        this.isLoadingMore = true
        this.loadMoreError = null
        this.failedPage = null
      } else {
        this.listStatus = 'loading'
        this.error = null
        this.loadMoreError = null
        this.failedPage = null
        this.isLoadingMore = false
      }
      logResult('list', 'started', startedAt, { source, page: requestParams.pageNum, append })
      try {
        const response = await recipeApi[SOURCE_API[source]](requestParams)
        if (requestId !== this.listRequestId) {
          logResult('list', 'stale_ignored', startedAt, { source })
          return response
        }
        const data = response?.data || {}
        const incoming = Array.isArray(data.records) ? data.records : []
        if (append) {
          const byId = new Map(this.items.map(item => [String(item.id), item]))
          incoming.forEach(item => byId.set(String(item.id), item))
          this.items = [...byId.values()]
        } else {
          this.items = incoming
        }
        const pageNum = Number(data.current || requestParams.pageNum)
        const pageSize = Number(data.size || requestParams.pageSize)
        const totalPages = Number(data.pages || 0)
        this.pagination = {
          pageNum,
          pageSize,
          total: Number(data.total || 0),
          totalPages,
          hasMore: pageNum < totalPages
        }
        this.listStatus = this.items.length ? 'success' : 'empty'
        this.loadMoreError = null
        this.failedPage = null
        logResult('list', this.listStatus, startedAt, {
          source, itemCount: this.items.length, page: pageNum, hasMore: this.pagination.hasMore
        })
        return response
      } catch (error) {
        if (requestId === this.listRequestId) {
          if (append) {
            this.loadMoreError = error
            this.failedPage = requestParams.pageNum
          } else {
            this.listStatus = 'error'
            this.error = error
          }
        }
        logResult('list', 'failed', startedAt, {
          source,
          errorCode: errorCode(error),
          page: requestParams.pageNum,
          append
        })
        throw error
      } finally {
        if (append && requestId === this.listRequestId) this.isLoadingMore = false
      }
    },
    retryList() {
      if (this.failedPage !== null) {
        const retryParams = { ...this.lastListParams, pageNum: this.failedPage }
        return this.fetchList(retryParams, { append: true })
      }
      return this.fetchList({ ...this.lastListParams, pageNum: 1 })
    },
    async fetchDetail(id) {
      const startedAt = Date.now()
      const requestId = ++this.detailRequestId
      this.detail = null
      this.detailStatus = 'loading'
      this.error = null
      logResult('detail', 'started', startedAt)
      try {
        const response = await recipeApi.getRecipeDetail(id)
        if (requestId !== this.detailRequestId) {
          logResult('detail', 'stale_ignored', startedAt)
          return response
        }
        this.detail = response?.data || null
        this.detailStatus = this.detail ? 'success' : 'empty'
        logResult('detail', this.detailStatus, startedAt)
        return response
      } catch (error) {
        if (requestId === this.detailRequestId) {
          this.detailStatus = 'error'
          this.error = error
        }
        logResult('detail', 'failed', startedAt, { errorCode: errorCode(error) })
        throw error
      }
    },
    async runMutation(operation, id, request, apply) {
      const startedAt = Date.now()
      this.mutationStatus = 'loading'
      this.mutationKey = `${operation}:${id || 'new'}`
      logResult(operation, 'started', startedAt)
      try {
        const response = await request()
        apply?.(response?.data)
        this.mutationStatus = 'success'
        logResult(operation, 'success', startedAt)
        return response?.data ?? response
      } catch (error) {
        this.mutationStatus = 'error'
        this.error = error
        logResult(operation, 'failed', startedAt, { errorCode: errorCode(error) })
        throw error
      } finally {
        this.mutationKey = ''
      }
    },
    create(payload) {
      return this.runMutation('create', null, () => recipeApi.createRecipe(payload))
    },
    update(id, payload) {
      return this.runMutation('update', id, () => recipeApi.updateRecipe(id, payload), (data) => {
        const updated = data && typeof data === 'object' ? data : { ...payload, id }
        this.patchEntity(id, updated)
      })
    },
    remove(id) {
      return this.runMutation('delete', id, () => recipeApi.deleteRecipe(id), () => {
        this.items = this.items.filter(item => String(item.id) !== String(id))
        if (String(this.detail?.id) === String(id)) this.detail = null
      })
    },
    publish(id) {
      return this.runMutation('publish', id, () => recipeApi.publishRecipe(id), () => {
        this.patchEntity(id, { status: 1 })
      })
    },
    setLiked(id, liked) {
      const request = liked ? recipeApi.likeRecipe : recipeApi.unlikeRecipe
      return this.runMutation(liked ? 'like' : 'unlike', id, () => request(id), () => {
        this.patchEntity(id, item => ({
          ...item, liked,
          likeCount: Math.max(0, Number(item.likeCount || 0) + (liked ? 1 : -1))
        }))
      })
    },
    setCollected(id, collected) {
      const request = collected ? recipeApi.collectRecipe : recipeApi.uncollectRecipe
      return this.runMutation(collected ? 'collect' : 'uncollect', id, () => request(id), () => {
        this.patchEntity(id, item => ({
          ...item, collected,
          collectCount: Math.max(0, Number(item.collectCount || 0) + (collected ? 1 : -1))
        }))
      })
    },
    patchEntity(id, patch) {
      const applyPatch = item => typeof patch === 'function' ? patch(item) : { ...item, ...patch }
      this.items = this.items.map(item => String(item.id) === String(id) ? applyPatch(item) : item)
      if (String(this.detail?.id) === String(id)) this.detail = applyPatch(this.detail)
    }
  }
})
