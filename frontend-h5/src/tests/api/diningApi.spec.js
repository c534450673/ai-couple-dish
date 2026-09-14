import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn()
}))
vi.mock('@/api/request', () => ({ default: request }))

import { diningApi } from '@/api'

describe('点菜 API 合同', () => {
  beforeEach(() => vi.clearAllMocks())

  it('查询目录和购物车不使用可能过期的购物车缓存', () => {
    diningApi.getCuisines()
    diningApi.getDishes({ cuisine: 'chuan', page: 2 })
    diningApi.getCart()

    expect(request.get.mock.calls).toEqual([
      ['/dining/cuisines', { cache: false }],
      ['/dining/dishes', { params: { cuisine: 'chuan', page: 2 }, cache: false }],
      ['/dining/cart', { cache: false }]
    ])
  })

  it('购物车变更不自动重试，避免重复加购', () => {
    diningApi.addItem({ dishId: 7, quantity: 2 })
    diningApi.updateItem(3, 4)
    diningApi.removeItem(3)
    diningApi.clearCart()

    expect(request.post).toHaveBeenCalledWith(
      '/dining/cart/items', { dishId: 7, quantity: 2 }, { retryConfig: { retries: 0 } }
    )
    expect(request.patch).toHaveBeenCalledWith(
      '/dining/cart/items/3', { quantity: 4 }, { retryConfig: { retries: 0 } }
    )
    expect(request.delete.mock.calls).toEqual([
      ['/dining/cart/items/3', { retryConfig: { retries: 0 } }],
      ['/dining/cart', { retryConfig: { retries: 0 } }]
    ])
  })

  it('建单携带幂等键，订单读取不缓存', () => {
    diningApi.createOrder({ remark: '少辣' }, 'submit-once-123')
    diningApi.getOrders()
    diningApi.getOrder(9)
    diningApi.confirmOrder(9)
    diningApi.cancelOrder(9)

    expect(request.post.mock.calls).toEqual([
      ['/dining/orders', { remark: '少辣' }, {
        headers: { 'Idempotency-Key': 'submit-once-123' },
        retryConfig: { retries: 0 }
      }],
      ['/dining/orders/9/confirm', undefined, { retryConfig: { retries: 0 } }],
      ['/dining/orders/9/cancel', undefined, { retryConfig: { retries: 0 } }]
    ])
    expect(request.get.mock.calls).toEqual([
      ['/dining/orders', { cache: false }],
      ['/dining/orders/9', { cache: false }]
    ])
  })

  it('建单缺少幂等键时在发请求前拒绝', () => {
    expect(() => diningApi.createOrder({ remark: '少辣' })).toThrow(/Idempotency-Key/)
    expect(request.post).not.toHaveBeenCalled()
  })
})
