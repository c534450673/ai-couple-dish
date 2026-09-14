import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const { router, adminApi } = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  adminApi: {
    login: vi.fn(), getAudit: vi.fn(), getOrders: vi.fn(), getCatalogImports: vi.fn(),
    getDailyReport: vi.fn(), getHourlyReport: vi.fn(), reviewCatalog: vi.fn(),
    publishCatalog: vi.fn(), flagOrder: vi.fn()
  }
}))

vi.mock('vue-router', () => ({ useRouter: () => router, useRoute: () => ({ query: {} }) }))
vi.mock('@/api', () => ({ adminApi }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import AdminLogin from '@/views/admin/login.vue'
import AdminDashboard from '@/views/admin/index.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))

describe('管理后台页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    adminApi.getAudit.mockResolvedValue({ data: { items: [{ id: '1', operation: 'catalog.review', target: 'mapo-tofu', reviewStatus: 'approved', result: 'success', createdAt: '2026-09-14T10:00:00Z' }], total: 1 } })
    adminApi.getOrders.mockResolvedValue({ data: { items: [{ orderId: 'order-1', status: 'pending', totalAmount: '39.80' }], total: 1 } })
    adminApi.getCatalogImports.mockResolvedValue({ data: { items: [], total: 0 } })
    adminApi.getDailyReport.mockResolvedValue({ data: { period: '2026-09-14', views: 12, cartAdds: 8, orders: 3, completed: 2, cancelled: 1, conversionRate: 25, singleModeRatio: 20, eventCounts: {} } })
    adminApi.getHourlyReport.mockResolvedValue({ data: { items: [], total: 0 } })
  })

  it('登录页保存 adminToken 并跳转，不覆盖普通用户 token', async () => {
    localStorage.setItem('token', 'user-token')
    adminApi.login.mockResolvedValue({ data: { token: 'admin-token' } })
    const wrapper = mount(AdminLogin)
    await wrapper.find('[data-test="admin-username"]').setValue('admin')
    await wrapper.find('[data-test="admin-password"]').setValue('secret')
    await wrapper.find('form').trigger('submit')
    await flush()

    expect(localStorage.getItem('adminToken')).toBe('admin-token')
    expect(localStorage.getItem('token')).toBe('user-token')
    expect(router.replace).toHaveBeenCalledWith('/admin')
  })

  it('工作台展示报表、订单、菜品审核和审计，并支持审核动作', async () => {
    localStorage.setItem('adminToken', 'admin-token')
    const wrapper = mount(AdminDashboard)
    await flush()
    await flush()

    expect(wrapper.text()).toContain('运营指挥台')
    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('order-1')
    expect(wrapper.text()).toContain('mapo-tofu')
    expect(wrapper.text()).toContain('catalog.review')

    const reviewButton = wrapper.find('[data-test="catalog-approve"]')
    expect(reviewButton.exists()).toBe(true)
    await reviewButton.trigger('click')
    expect(adminApi.reviewCatalog).toHaveBeenCalledWith(expect.objectContaining({ slug: 'mapo-tofu', approved: true }))
  })
})
