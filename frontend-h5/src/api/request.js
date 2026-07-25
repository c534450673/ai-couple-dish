/**
 * API 请求封装
 */
import axios from 'axios'
import { showToast } from 'vant'
import router from '@/router'
import { useUserStore } from '@/stores/user'
import { logUiEvent } from '@/composables/useStructuredLog'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// 重试配置
const DEFAULT_RETRY_CONFIG = {
  retries: 3,
  retryDelay: 1000,
  retryableStatuses: [408, 429, 500, 502, 503, 504]
}

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求去重 Map
const pendingRequestMap = new Map()

// 重试状态；重置后使用新代际，旧请求不得再次发起网络调用。
let requestStateVersion = 0
const retryTimerCancels = new Map()
const retryConfigs = new Set()
let unauthorizedNavigationStarted = false

export const isUnauthorizedNavigationStarted = () => unauthorizedNavigationStarted

// 简单内存缓存 (用于 GET 请求)
const memoryCache = new Map()
const DEFAULT_CACHE_TIME = 5 * 60 * 1000 // 5分钟缓存

// 生成请求唯一标识
const generateRequestKey = (config) => {
  const { method, url, params, data } = config
  return `${method}_${url}_${JSON.stringify(params)}_${JSON.stringify(data)}`
}

// 添加请求到去重队列
const addPendingRequest = (config) => {
  const requestKey = generateRequestKey(config)
  if (pendingRequestMap.has(requestKey)) {
    const cancel = pendingRequestMap.get(requestKey)
    cancel('请求取消：重复请求')
  }
  config.cancelToken = new axios.CancelToken((cancel) => {
    pendingRequestMap.set(requestKey, cancel)
  })
}

// 从去重队列移除请求
const removePendingRequest = (config) => {
  const requestKey = generateRequestKey(config)
  if (pendingRequestMap.has(requestKey)) {
    pendingRequestMap.delete(requestKey)
  }
}

// 获取缓存
const getCache = (config) => {
  if (config.method !== 'get' || config.cache === false) return null
  const cacheKey = generateRequestKey(config)
  const cached = memoryCache.get(cacheKey)
  if (cached && Date.now() - cached.timestamp < (config.cacheTime || DEFAULT_CACHE_TIME)) {
    return cached.data
  }
  return null
}

// 设置缓存
const setCache = (config, data) => {
  if (config.method !== 'get' || config.cache === false) return
  const cacheKey = generateRequestKey(config)
  memoryCache.set(cacheKey, { data, timestamp: Date.now() })
}

// 清理过期缓存
const clearExpiredCache = () => {
  const now = Date.now()
  for (const [key, value] of memoryCache.entries()) {
    if (now - value.timestamp > (value.cacheTime || DEFAULT_CACHE_TIME)) {
      memoryCache.delete(key)
    }
  }
}

const handleUnauthorized = () => {
  const startedAt = Date.now()
  const userStore = useUserStore()
  const sessionCleared = userStore.clearLocalSession({ reason: 'unauthorized' })
  const alreadyAtLogin = router.currentRoute.value?.path === '/login'
  const shouldRedirect = !alreadyAtLogin && !unauthorizedNavigationStarted

  logUiEvent('request.auth.unauthorized', {
    module: 'request', operation: 'local_session_clear',
    result: sessionCleared === false ? 'skipped' : 'success',
    durationMs: Date.now() - startedAt, errorCode: 'NONE',
    cleanupApplied: sessionCleared !== false, redirectStarted: shouldRedirect
  })
  if (!shouldRedirect) return

  unauthorizedNavigationStarted = true
  Promise.resolve(router.replace('/login')).catch(() => {
    logUiEvent('request.auth.redirect', {
      module: 'request', operation: 'login_redirect', result: 'error',
      durationMs: Date.now() - startedAt, errorCode: 'LOGIN_REDIRECT_FAILED'
    })
  })
}

const clearRetryConfig = (config) => {
  if (!config) return
  retryConfigs.delete(config)
  delete config.__retryCount
  delete config.__requestStateVersion
}

const waitForRetry = (delay) => new Promise((resolve) => {
  const timerId = setTimeout(() => {
    retryTimerCancels.delete(timerId)
    resolve(true)
  }, delay)
  retryTimerCancels.set(timerId, () => {
    clearTimeout(timerId)
    retryTimerCancels.delete(timerId)
    resolve(false)
  })
})

// 定时清理过期缓存；测试环境由 afterEach 显式重置状态，避免遗留计时器。
let cacheCleanupTimer = null
if (import.meta.env.MODE !== 'test') {
  cacheCleanupTimer = setInterval(clearExpiredCache, DEFAULT_CACHE_TIME)
  console.info('[request.cache.scheduler.started]', {
    cleanupIntervalMs: DEFAULT_CACHE_TIME,
    environment: import.meta.env.MODE
  })
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    config.__requestStateVersion = requestStateVersion

    // 检查缓存
    const cachedData = getCache(config)
    if (cachedData) {
      // 返回缓存数据，使用特殊的 promise 标志
      config.adapter = () => Promise.resolve({ data: cachedData, cached: true })
      return config
    }

    // 添加请求去重
    addPendingRequest(config)

    const token = localStorage.getItem('token')
    if (token) {
      unauthorizedNavigationStarted = false
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 移除已完成请求
    removePendingRequest(response.config)
    clearRetryConfig(response.config)

    // 如果是缓存的响应，直接返回
    if (response.cached) {
      return response.data
    }

    const res = response.data
    if (res.code === 200) {
      // 缓存 GET 请求响应
      setCache(response.config, res)
      return res
    } else if (res.code === 401) {
      // Token过期
      handleUnauthorized()
      return Promise.reject(res)
    } else {
      showToast(res.message || '请求失败')
      return Promise.reject(res)
    }
  },
  async (error) => {
    // 移除失败请求
    if (error.config) {
      removePendingRequest(error.config)
    }

    if (axios.isCancel(error)) {
      // 请求被取消，不显示错误
      return Promise.reject(error)
    }

    const config = error.config
    if (!config || config.__requestStateVersion !== requestStateVersion) {
      if (config) clearRetryConfig(config)
      return Promise.reject(error)
    }
    const retryConfig = {
      ...DEFAULT_RETRY_CONFIG,
      ...config.retryConfig
    }

    // 检查是否应该重试
    if (config && !config.__retryCount) {
      config.__retryCount = 0
    }
    retryConfigs.add(config)

    if (
      config &&
      retryConfig.retries > 0 &&
      config.__retryCount < retryConfig.retries &&
      (retryConfig.retryableStatuses.includes(error.response?.status) ||
        !error.response) // 网络错误也没有 response
    ) {
      config.__retryCount++

      // 延迟重试
      const delay = retryConfig.retryDelay * config.__retryCount
      const shouldRetry = await waitForRetry(delay)
      if (!shouldRetry || config.__requestStateVersion !== requestStateVersion) {
        clearRetryConfig(config)
        return Promise.reject(error)
      }

      console.info('[request.retry.scheduled]', {
        attempt: config.__retryCount,
        delayMs: delay,
        reason: error.response ? 'retryable_http_status' : 'network_error'
      })
      return api(config)
    }

    clearRetryConfig(config)

    if (error.response) {
      if (error.response.status === 401) {
        handleUnauthorized()
      } else {
        showToast('网络错误')
      }
    } else {
      showToast('网络错误')
    }
    return Promise.reject(error)
  }
)

// 导出清除缓存的方法
export const clearCache = () => {
  memoryCache.clear()
}

// 重置请求去重和缓存状态，供测试隔离及登出清理流程复用。
export const resetRequestState = () => {
  const state = {
    cacheCleanupScheduled: cacheCleanupTimer !== null,
    memoryCacheEntries: memoryCache.size,
    pendingRequests: pendingRequestMap.size,
    pendingRetries: retryTimerCancels.size
  }
  for (const cancelPendingRequest of pendingRequestMap.values()) {
    cancelPendingRequest('请求取消：请求状态已重置')
  }
  for (const cancelRetryTimer of retryTimerCancels.values()) {
    cancelRetryTimer()
  }
  for (const config of retryConfigs) {
    clearRetryConfig(config)
  }
  requestStateVersion++
  pendingRequestMap.clear()
  memoryCache.clear()

  if (import.meta.env.MODE !== 'test') {
    console.info('[request.state.reset]', state)
  }
}

// 导出清除特定缓存的方法
export const clearCacheByKey = (key) => {
  memoryCache.delete(key)
}

export default api
