import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const router = { push: vi.fn(), replace: vi.fn() }
const diningApi = vi.hoisted(() => ({
  getCuisines: vi.fn(),
  getDishes: vi.fn(),
  getCart: vi.fn(),
  addItem: vi.fn(),
  updateItem: vi.fn(),
  removeItem: vi.fn(),
  clearCart: vi.fn(),
  createOrder: vi.fn(),
  getOrders: vi.fn(),
  confirmOrder: vi.fn(),
  cancelOrder: vi.fn()
}))
const userStore = vi.hoisted(() => ({ coupleInfo: null }))
const logUiEvent = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({ useRouter: () => router }))
vi.mock('@/api', () => ({ diningApi }))
vi.mock('@/stores/user', () => ({ useUserStore: () => userStore }))
vi.mock('@/composables/useStructuredLog', async () => {
  const actual = await vi.importActual('@/composables/useStructuredLog')
  return { ...actual, logUiEvent }
})

import DiningIndex from '@/views/dining/index.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))
const emptyCart = { items: [], count: 0, totalAmount: '0.00' }

describe('点菜页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    userStore.coupleInfo = null
    diningApi.getCuisines.mockResolvedValue({ data: [{ slug: '川菜', name: '川菜' }, { slug: '粤菜', name: '粤菜' }] })
    diningApi.getDishes.mockResolvedValue({ data: { items: [
      { id: 7, name: '宫保鸡丁', cuisine: '川菜', unitPrice: '38.00', imageUrl: '/dish.jpg', tags: ['下饭'] },
      { id: 8, name: '白切鸡', cuisine: '粤菜', unitPrice: '48.00', imageUrl: '/chicken.jpg', tags: [] }
    ], total: 2 } })
    diningApi.getCart.mockResolvedValue({ data: emptyCart })
    diningApi.getOrders.mockResolvedValue({ data: { records: [] } })
    diningApi.addItem.mockResolvedValue({ data: { id: 1 } })
    diningApi.createOrder.mockResolvedValue({ data: { id: 9, orderNo: 'D2026091401', status: 'pending_confirmation', totalAmount: '38.00' } })
    diningApi.confirmOrder.mockResolvedValue({ data: { id: 9, status: 'confirmed' } })
    diningApi.cancelOrder.mockResolvedValue({ data: { id: 9, status: 'cancelled' } })
  })

  it('单人模式可以加载菜品、筛选并加购', async () => {
    const wrapper = mount(DiningIndex)
    await flush()

    expect(wrapper.text()).toContain('今晚吃什么')
    expect(wrapper.text()).toContain('单人模式可用')
    expect(wrapper.find('[data-test="dish-card-7"]').exists()).toBe(true)
    await wrapper.find('[data-test="cuisine-粤菜"]').trigger('click')
    await flush()
    expect(diningApi.getDishes).toHaveBeenLastCalledWith(expect.objectContaining({ cuisine: '粤菜' }))
    await wrapper.find('[data-test="add-dish-7"]').trigger('click')
    await flush()
    expect(diningApi.addItem).toHaveBeenCalledWith({ dishId: 7, quantity: 1 })
    expect(logUiEvent).toHaveBeenCalledWith('dining.add_item', expect.objectContaining({ result: 'success' }))
  })

  it('购物车支持数量调整、备注和去结算，建单携带幂等键', async () => {
    diningApi.getCart.mockResolvedValue({ data: {
      items: [{ id: 3, dishId: 7, dishName: '宫保鸡丁', unitPrice: '38.00', quantity: 2, subtotal: '76.00' }],
      count: 2, totalAmount: '76.00'
    } })
    const wrapper = mount(DiningIndex)
    await flush()
    await wrapper.find('[data-test="cart-toggle"]').trigger('click')
    expect(wrapper.find('[data-test="cart-drawer"]').exists()).toBe(true)
    await wrapper.find('[data-test="cart-increase-3"]').trigger('click')
    expect(diningApi.updateItem).toHaveBeenCalledWith(3, 3)
    await wrapper.find('[data-test="order-remark"]').setValue('少辣')
    await wrapper.find('[data-test="checkout-submit"]').trigger('click')
    await flush()
    expect(diningApi.createOrder).toHaveBeenCalledWith({ remark: '少辣' }, expect.any(String))
    expect(wrapper.text()).toContain('订单已创建')
  })

  it('订单可以确认或取消，操作期间按钮禁用且单人不被情侣门禁阻断', async () => {
    diningApi.getOrders.mockResolvedValueOnce({ data: { records: [
      { id: 9, orderNo: 'D9', status: 'pending_confirmation', statusDesc: '待确认', totalAmount: '38.00' }
    ] } }).mockResolvedValueOnce({ data: { records: [
      { id: 9, orderNo: 'D9', status: 'confirmed', statusDesc: '已确认', totalAmount: '38.00' }
    ] } })
    const wrapper = mount(DiningIndex)
    await flush()
    await wrapper.find('[data-test="order-confirm-9"]').trigger('click')
    expect(diningApi.confirmOrder).toHaveBeenCalledWith(9)
    await flush()
    expect(wrapper.text()).toContain('已确认')
    expect(logUiEvent).toHaveBeenCalledWith('dining.confirm_order', expect.objectContaining({ result: 'success' }))
  })

  it('建单成功后购物车或订单刷新失败不会覆盖成功通知', async () => {
    const initialCart = {
      items: [{ id: 3, dishId: 7, dishName: '宫保鸡丁', unitPrice: '38.00', quantity: 1, subtotal: '38.00' }],
      count: 1,
      totalAmount: '38.00'
    }
    diningApi.getCart.mockResolvedValueOnce({ data: initialCart }).mockRejectedValueOnce({ code: 'CART_REFRESH_ERROR' })
    diningApi.getOrders.mockResolvedValueOnce({ data: { records: [] } }).mockRejectedValueOnce({ code: 'ORDERS_REFRESH_ERROR' })
    const wrapper = mount(DiningIndex)
    await flush()
    await wrapper.find('[data-test="cart-toggle"]').trigger('click')
    await wrapper.find('[data-test="checkout-submit"]').trigger('click')
    await flush()

    expect(diningApi.createOrder).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('订单已创建')
    expect(wrapper.text()).not.toContain('订单创建失败')
    expect(logUiEvent).toHaveBeenCalledWith('dining.refresh', expect.objectContaining({ result: 'error' }))
  })

  it('加载失败提供显式重试并记录错误', async () => {
    diningApi.getDishes.mockRejectedValueOnce({ code: 'NETWORK_ERROR' })
    const wrapper = mount(DiningIndex)
    await flush()
    expect(wrapper.find('[data-test="dining-retry"]').exists()).toBe(true)
    await wrapper.find('[data-test="dining-retry"]').trigger('click')
    expect(diningApi.getDishes).toHaveBeenCalledTimes(2)
    expect(logUiEvent).toHaveBeenCalledWith('dining.load', expect.objectContaining({ result: 'error' }))
    expect(logUiEvent).toHaveBeenCalledWith('dining.retry', expect.any(Object))
  })
})
