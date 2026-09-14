import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = {
  get: vi.fn(),
  post: vi.fn()
}

vi.mock('@/api/request', () => ({ default: api }))

const { adminApi } = await import('@/api')

describe('adminApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('登录使用独立的管理员令牌，不覆盖用户会话', async () => {
    localStorage.setItem('token', 'user-token')
    api.post.mockResolvedValue({ data: { token: 'admin-token' } })

    await adminApi.login({ username: 'admin', password: 'secret' })

    expect(api.post).toHaveBeenCalledWith('/admin/login', { username: 'admin', password: 'secret' }, {
      retryConfig: { retries: 0 }, skipAuthErrorHandler: true
    })
    expect(localStorage.getItem('token')).toBe('user-token')
  })

  it('所有管理员读取请求使用 adminToken 且关闭缓存', async () => {
    localStorage.setItem('adminToken', 'admin-token')
    api.get.mockResolvedValue({ data: { code: 200 } })

    await adminApi.getAudit('catalog.review')
    await adminApi.getOrders('pending')
    await adminApi.getCatalogImports()
    await adminApi.getDailyReport('2026-09-14')
    await adminApi.getHourlyReport('2026-09-14')

    expect(api.get).toHaveBeenNthCalledWith(1, '/admin/audit', expect.objectContaining({
      params: { operation: 'catalog.review' },
      cache: false,
      headers: { Authorization: 'Bearer admin-token' }
    }))
    expect(api.get).toHaveBeenNthCalledWith(2, '/admin/orders', expect.objectContaining({
      params: { status: 'pending' },
      cache: false,
      headers: { Authorization: 'Bearer admin-token' }
    }))
    expect(api.get).toHaveBeenNthCalledWith(3, '/admin/catalog/imports', expect.objectContaining({
      cache: false,
      headers: { Authorization: 'Bearer admin-token' }
    }))
    expect(api.get).toHaveBeenNthCalledWith(4, '/analytics/reports/daily', expect.objectContaining({
      params: { date: '2026-09-14' },
      cache: false,
      headers: { Authorization: 'Bearer admin-token' }
    }))
  })

  it('审核与订单标记请求不自动重试', async () => {
    localStorage.setItem('adminToken', 'admin-token')
    api.post.mockResolvedValue({ data: { code: 200 } })

    await adminApi.reviewCatalog({ slug: 'mapo-tofu', approved: true, reason: 'verified' })
    await adminApi.publishCatalog('mapo-tofu')
    await adminApi.flagOrder('order-1', { flagged: true, reason: 'manual-check' })

    expect(api.post).toHaveBeenNthCalledWith(1, '/admin/catalog/review', expect.anything(), expect.objectContaining({
      retryConfig: { retries: 0 },
      headers: { Authorization: 'Bearer admin-token' }
    }))
    expect(api.post).toHaveBeenNthCalledWith(3, '/admin/orders/order-1/flag', expect.anything(), expect.objectContaining({
      retryConfig: { retries: 0 },
      headers: { Authorization: 'Bearer admin-token' }
    }))
  })
})
