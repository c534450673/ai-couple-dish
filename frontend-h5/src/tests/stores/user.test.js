/**
 * 用户 Store 补充场景：避免与 user.spec.js 重复覆盖。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'

vi.mock('@/api', () => ({
  userApi: {
    logout: vi.fn()
  },
  coupleApi: {
    getCoupleInfo: vi.fn()
  }
}))

vi.mock('@/api/request', () => ({
  resetRequestState: vi.fn()
}))

import { userApi } from '@/api'
import { resetRequestState } from '@/api/request'

const deferred = () => {
  let resolve
  const promise = new Promise((yes) => {
    resolve = yes
  })
  return { promise, resolve }
}

describe('用户 Store 补充测试', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('登出接口失败时仍应清除本地登录状态', async () => {
    const userStore = useUserStore()
    userStore.token = 'test-token'
    userStore.userInfo = { id: 1 }
    userStore.coupleInfo = { id: 1 }
    userStore.isLoggedIn = true
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('userInfo', JSON.stringify({ id: 1 }))
    localStorage.setItem('coupleInfo', JSON.stringify({ id: 1 }))
    userApi.logout.mockRejectedValue(new Error('服务暂不可用'))

    await userStore.logout()

    expect(userApi.logout).toHaveBeenCalledOnce()
    expect(resetRequestState).toHaveBeenCalledOnce()
    expect(userStore.token).toBe('')
    expect(userStore.userInfo).toBeNull()
    expect(userStore.coupleInfo).toBeNull()
    expect(userStore.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('userInfo')).toBeNull()
    expect(localStorage.getItem('coupleInfo')).toBeNull()
  })

  it('本机会话清理幂等且绝不调用远程登出接口', () => {
    const userStore = useUserStore()
    userStore.token = 'test-token'
    userStore.userInfo = { id: 1 }
    userStore.coupleInfo = { id: 1 }
    userStore.isLoggedIn = true
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('userInfo', JSON.stringify({ id: 1 }))
    localStorage.setItem('coupleInfo', JSON.stringify({ id: 1 }))

    const first = userStore.clearLocalSession({ reason: 'unauthorized' })
    const second = userStore.clearLocalSession({ reason: 'unauthorized' })

    expect(first).toBe(true)
    expect(second).toBe(false)
    expect(resetRequestState).toHaveBeenCalledOnce()
    expect(userApi.logout).not.toHaveBeenCalled()
    expect(userStore.token).toBe('')
    expect(userStore.userInfo).toBeNull()
    expect(userStore.coupleInfo).toBeNull()
  })

  it('并发远程登出复用同一个在途操作并只请求一次', async () => {
    const pending = deferred()
    const userStore = useUserStore()
    userStore.token = 'test-token'
    localStorage.setItem('token', 'test-token')
    userApi.logout.mockReturnValueOnce(pending.promise)

    const first = userStore.logout()
    const second = userStore.logout()
    expect(userApi.logout).toHaveBeenCalledOnce()

    pending.resolve({ data: null })
    await Promise.all([first, second])

    expect(userApi.logout).toHaveBeenCalledOnce()
    expect(resetRequestState).toHaveBeenCalledOnce()
    expect(userStore.token).toBe('')
  })
})
