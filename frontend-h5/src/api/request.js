/**
 * API 请求封装
 */
import axios from 'axios'
import { showToast } from 'vant'
import router from '@/router'
import { useUserStore } from '@/stores/user'

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
  if (config.method !== 'get') return null
  const cacheKey = generateRequestKey(config)
  const cached = memoryCache.get(cacheKey)
  if (cached && Date.now() - cached.timestamp < (config.cacheTime || DEFAULT_CACHE_TIME)) {
    return cached.data
  }
  return null
}

// 设置缓存
const setCache = (config, data) => {
  if (config.method !== 'get') return
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

// 定时清理过期缓存
setInterval(clearExpiredCache, DEFAULT_CACHE_TIME)

// 请求拦截器
api.interceptors.request.use(
  (config) => {
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
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
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
    const retryConfig = {
      ...DEFAULT_RETRY_CONFIG,
      ...config.retryConfig
    }

    // 检查是否应该重试
    if (config && !config.__retryCount) {
      config.__retryCount = 0
    }

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
      await new Promise(resolve => setTimeout(resolve, delay))

      console.log(`请求重试 ${config.__retryCount}/${retryConfig.retries}: ${config.url}`)
      return api(config)
    }

    if (error.response) {
      if (error.response.status === 401) {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
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

// 导出清除特定缓存的方法
export const clearCacheByKey = (key) => {
  memoryCache.delete(key)
}

export default api
