import { defineStore } from 'pinia'
import { menuApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const LIST_PARAM_KEYS = [
  'status', 'keyword', 'dishCategory', 'minPrice', 'maxPrice', 'minRating',
  'sortBy', 'sortOrder', 'page', 'pageSize'
]

const selectParams = (params, keys) => Object.fromEntries(
  keys.filter(key => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map(key => [key, params[key]])
)

const errorCode = (error) => String(error?.code || error?.response?.status || 'UNKNOWN')

const logResult = (operation, result, startedAt, fields = {}) => {
  logUiEvent(`menu.${operation}`, {
    module: 'menu_store',
    operation,
    result,
    durationMs: Date.now() - startedAt,
    ...fields
  })
}

const initialPagination = () => ({ page: 1, pageSize: 10, total: 0, totalPages: 0, hasMore: false })

export const useMenuStore = defineStore('menu', {
  state: () => ({
    items: [],
    detail: null,
    stats: {},
    pagination: initialPagination(),
    listStatus: 'idle',
    loadMoreError: null,
    failedPage: null,
    isLoadingMore: false,
    detailStatus: 'idle',
    mutationStatus: 'idle',
    mutationKey: '',
    error: null,
    lastListParams: { page: 1, pageSize: 10 },
    listRequestId: 0,
    detailRequestId: 0
  }),
  actions: {
    async fetchList(params = {}, { append = false } = {}) {
      const startedAt = Date.now()
      const requestId = ++this.listRequestId
      const safeParams = selectParams(params, LIST_PARAM_KEYS)
      this.lastListParams = safeParams
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
      logResult('list', 'started', startedAt, { page: Number(safeParams.page || 1), append })
      try {
        const response = await menuApi.getMenuList(safeParams)
        if (requestId !== this.listRequestId) {
          logResult('list', 'stale_ignored', startedAt)
          return response
        }
        const data = response?.data || {}
        const incoming = Array.isArray(data.list) ? data.list : []
        if (append) {
          const byId = new Map(this.items.map(item => [String(item.id), item]))
          incoming.forEach(item => byId.set(String(item.id), item))
          this.items = [...byId.values()]
        } else {
          this.items = incoming
        }
        this.pagination = {
          page: Number(data.page || safeParams.page || 1),
          pageSize: Number(data.pageSize || safeParams.pageSize || 10),
          total: Number(data.total || 0),
          totalPages: Number(data.totalPages || 0),
          hasMore: Boolean(data.hasMore)
        }
        this.listStatus = this.items.length ? 'success' : 'empty'
        this.loadMoreError = null
        this.failedPage = null
        logResult('list', this.listStatus, startedAt, {
          itemCount: this.items.length,
          page: this.pagination.page,
          hasMore: this.pagination.hasMore
        })
        return response
      } catch (error) {
        if (requestId === this.listRequestId) {
          if (append) {
            this.loadMoreError = error
            this.failedPage = Number(safeParams.page || 1)
          } else {
            this.listStatus = 'error'
            this.error = error
          }
        }
        logResult('list', 'failed', startedAt, {
          errorCode: errorCode(error),
          page: Number(safeParams.page || 1),
          append
        })
        throw error
      } finally {
        if (append && requestId === this.listRequestId) this.isLoadingMore = false
      }
    },
    retryList() {
      if (this.failedPage !== null) {
        const retryParams = { ...this.lastListParams, page: this.failedPage }
        return this.fetchList(retryParams, { append: true })
      }
      const retryParams = { ...this.lastListParams, page: 1 }
      return this.fetchList(retryParams)
    },
    async fetchStats() {
      const startedAt = Date.now()
      logResult('stats', 'started', startedAt)
      try {
        const response = await menuApi.getMenuStats()
        this.stats = response?.data || {}
        logResult('stats', 'success', startedAt)
        return response
      } catch (error) {
        logResult('stats', 'failed', startedAt, { errorCode: errorCode(error) })
        throw error
      }
    },
    async fetchDetail(id) {
      const startedAt = Date.now()
      const requestId = ++this.detailRequestId
      this.detailStatus = 'loading'
      this.detail = null
      this.error = null
      logResult('detail', 'started', startedAt)
      try {
        const response = await menuApi.getMenuDetail(id)
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
      return this.runMutation('create', null, () => menuApi.addMenu(payload))
    },
    update(id, payload) {
      return this.runMutation('update', id, () => menuApi.updateMenu({ ...payload, id }), (data) => {
        const updated = data && typeof data === 'object' ? data : { ...payload, id }
        this.patchEntity(id, updated)
      })
    },
    remove(id) {
      return this.runMutation('delete', id, () => menuApi.deleteMenu(id), () => {
        this.items = this.items.filter(item => String(item.id) !== String(id))
        if (String(this.detail?.id) === String(id)) this.detail = null
        this.pagination.total = Math.max(0, this.pagination.total - 1)
      })
    },
    setLiked(id, liked) {
      const request = liked ? menuApi.likeMenu : menuApi.unlikeMenu
      return this.runMutation(liked ? 'like' : 'unlike', id, () => request(id), () => {
        this.patchEntity(id, item => ({
          ...item,
          liked,
          likeCount: Math.max(0, Number(item.likeCount || 0) + (liked ? 1 : -1))
        }))
      })
    },
    setFavorite(id, favorite) {
      const request = favorite ? menuApi.favoriteMenu : menuApi.unfavoriteMenu
      return this.runMutation(favorite ? 'favorite' : 'unfavorite', id, () => request(id), () => {
        this.patchEntity(id, item => ({ ...item, isFavorite: favorite }))
      })
    },
    patchEntity(id, patch) {
      const applyPatch = item => typeof patch === 'function' ? patch(item) : { ...item, ...patch }
      this.items = this.items.map(item => String(item.id) === String(id) ? applyPatch(item) : item)
      if (String(this.detail?.id) === String(id)) this.detail = applyPatch(this.detail)
    }
  }
})
