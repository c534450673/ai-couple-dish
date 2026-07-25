import { defineStore } from 'pinia'
import { anniversaryApi, coupleApi, feedApi, recipeApi, wishApi } from '@/api'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'
import { useUserStore } from '@/stores/user'

const REQUESTABLE_RESOURCES = ['couple', 'timer', 'anniversary', 'wish', 'feed', 'recipe']
const ALL_RESOURCES = [...REQUESTABLE_RESOURCES, 'footprint']
const FOOTPRINT_ERROR_CODE = 'FOOTPRINT_NOT_SUPPORTED'

const createResource = (status = 'idle') => ({
  status,
  requestId: 0,
  startedAt: null,
  data: null,
  errorCode: status === 'unavailable' ? FOOTPRINT_ERROR_CODE : null,
  retryCount: 0,
  flow: null,
  degradedSides: []
})

const createResources = () => Object.fromEntries(ALL_RESOURCES.map(resource => [
  resource,
  createResource(resource === 'footprint' ? 'unavailable' : 'idle')
]))

const resourceLog = (resource, state, requestId, startedAt, fields = {}) => {
  logUiEvent('home.resource', {
    resource,
    state,
    requestId,
    durationMs: Math.max(0, Date.now() - startedAt),
    ...fields
  })
}

const businessError = (response) => {
  const error = new Error('HOME_RESOURCE_BUSINESS_ERROR')
  error.code = response?.code ?? 'BUSINESS_ERROR'
  error.isUnbound = String(response?.message || '').includes('未绑定')
  return error
}

const unwrapResponse = (response) => {
  if (Number(response?.code) !== 200) throw businessError(response)
  return response.data
}

const flowForError = (error) => {
  const code = normalizeUiErrorCode(error)
  if (code === '401') return 'login'
  if (code === '2006' || error?.isUnbound) return 'bind'
  return null
}

const stableLatest = (items) => items
  .map((item, index) => ({ item, index, timestamp: Date.parse(item?.createTime || '') }))
  .sort((left, right) => {
    const leftValid = Number.isFinite(left.timestamp)
    const rightValid = Number.isFinite(right.timestamp)
    if (leftValid && rightValid && left.timestamp !== right.timestamp) return right.timestamp - left.timestamp
    if (leftValid !== rightValid) return leftValid ? -1 : 1
    return left.index - right.index
  })
  .map(entry => entry.item)

const resourceRequests = {
  couple: async () => {
    const cachedCouple = useUserStore().coupleInfo
    if (cachedCouple && typeof cachedCouple === 'object') {
      return { data: cachedCouple, itemCount: 1 }
    }
    const data = unwrapResponse(await coupleApi.getCoupleInfo())
    return { data: data && typeof data === 'object' ? data : null, itemCount: data ? 1 : 0 }
  },
  timer: async () => {
    const data = unwrapResponse(await coupleApi.getLoveTimer())
    const loveDays = Number(data?.loveDays)
    const normalized = data && Number.isFinite(loveDays) && loveDays >= 0 ? { loveDays } : null
    return { data: normalized, itemCount: normalized ? 1 : 0 }
  },
  anniversary: async () => {
    const data = unwrapResponse(await anniversaryApi.getNextAnniversary())
    return { data: data && typeof data === 'object' ? data : null, itemCount: data ? 1 : 0 }
  },
  wish: async () => {
    const data = unwrapResponse(await wishApi.getWishList())
    const items = Array.isArray(data) ? data : []
    return { data: stableLatest(items)[0] || null, itemCount: items.length }
  },
  recipe: async () => {
    const page = unwrapResponse(await recipeApi.getCoupleRecipes({ pageNum: 1, pageSize: 1 }))
    const records = Array.isArray(page?.records) ? page.records : []
    const data = records.length
      ? {
        item: records[0],
        total: Number(page?.total) || 0,
        current: Number(page?.current) || 1,
        size: Number(page?.size) || 1,
        pages: Number(page?.pages) || 0
      }
      : null
    return { data, itemCount: records.length }
  }
}

const loadFeed = async () => {
  const results = await Promise.allSettled([
    feedApi.getReceivedFeeds().then(unwrapResponse),
    feedApi.getSentFeeds().then(unwrapResponse)
  ])
  const sideNames = ['received', 'sent']
  const degradedSides = results
    .map((result, index) => result.status === 'rejected' ? sideNames[index] : null)
    .filter(Boolean)

  if (degradedSides.length === results.length) {
    const error = new Error('ALL_FEED_SIDES_FAILED')
    const reasons = results.map(result => result.reason)
    const errorCodes = reasons.map(reason => normalizeUiErrorCode(reason))
    error.code = errorCodes.includes('401')
      ? '401'
      : (errorCodes.includes('2006') ? '2006' : 'ALL_FEED_SIDES_FAILED')
    error.isUnbound = reasons.some(reason => reason?.isUnbound)
    error.degradedSides = degradedSides
    throw error
  }

  const items = results.flatMap(result => (
    result.status === 'fulfilled' && Array.isArray(result.value) ? result.value : []
  ))
  return { data: stableLatest(items)[0] || null, itemCount: items.length, degradedSides }
}

resourceRequests.feed = loadFeed

export const useHomeStore = defineStore('home', {
  state: () => ({
    resources: createResources()
  }),
  actions: {
    async loadResource(resource) {
      if (!REQUESTABLE_RESOURCES.includes(resource)) {
        const footprint = this.resources.footprint
        resourceLog('footprint', 'unavailable', footprint.requestId, Date.now(), {
          itemCount: 0,
          errorCode: FOOTPRINT_ERROR_CODE,
          retry: footprint.retryCount
        })
        return footprint
      }

      const current = this.resources[resource]
      const requestId = current.requestId + 1
      const startedAt = Date.now()
      Object.assign(current, {
        status: 'loading',
        requestId,
        startedAt,
        data: null,
        errorCode: null,
        flow: null,
        degradedSides: []
      })
      resourceLog(resource, 'loading', requestId, startedAt, {
        retry: current.retryCount
      })

      try {
        const result = await resourceRequests[resource]()
        if (requestId !== current.requestId) {
          resourceLog(resource, 'stale_ignored', requestId, startedAt, {
            itemCount: result.itemCount,
            retry: current.retryCount
          })
          return current
        }

        current.data = result.data
        current.status = result.data ? 'success' : 'empty'
        current.startedAt = startedAt
        current.degradedSides = result.degradedSides || []
        resourceLog(resource, current.status, requestId, startedAt, {
          itemCount: result.itemCount,
          retry: current.retryCount,
          ...(current.degradedSides.length ? { errorCode: `PARTIAL_${current.degradedSides.join('_').toUpperCase()}` } : {})
        })
        return current
      } catch (error) {
        if (requestId !== current.requestId) {
          resourceLog(resource, 'stale_ignored', requestId, startedAt, {
            itemCount: 0,
            retry: current.retryCount
          })
          return current
        }

        const errorCode = normalizeUiErrorCode(error)
        current.status = 'error'
        current.data = null
        current.errorCode = errorCode
        current.flow = flowForError(error)
        current.degradedSides = error?.degradedSides || []
        resourceLog(resource, 'error', requestId, startedAt, {
          itemCount: 0,
          errorCode,
          retry: current.retryCount
        })
        return current
      }
    },
    loadAll() {
      const footprint = this.resources.footprint
      resourceLog('footprint', 'unavailable', footprint.requestId, Date.now(), {
        itemCount: 0,
        errorCode: FOOTPRINT_ERROR_CODE,
        retry: footprint.retryCount
      })
      return Promise.allSettled(REQUESTABLE_RESOURCES.map(resource => this.loadResource(resource)))
    },
    retryResource(resource) {
      if (!REQUESTABLE_RESOURCES.includes(resource)) return this.loadResource('footprint')
      const current = this.resources[resource]
      current.retryCount += 1
      resourceLog(resource, 'retry', current.requestId, Date.now(), {
        itemCount: current.data ? 1 : 0,
        retry: current.retryCount
      })
      return this.loadResource(resource)
    },
    invalidatePending() {
      REQUESTABLE_RESOURCES.forEach((resource) => {
        const current = this.resources[resource]
        if (current.status !== 'loading') return
        const staleRequestId = current.requestId
        const startedAt = current.startedAt || Date.now()
        current.requestId += 1
        current.status = 'idle'
        current.startedAt = null
        current.data = null
        current.errorCode = null
        current.flow = null
        current.degradedSides = []
        resourceLog(resource, 'invalidated', staleRequestId, startedAt, {
          itemCount: 0,
          retry: current.retryCount
        })
      })
    }
  }
})
