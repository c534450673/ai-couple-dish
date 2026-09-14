import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.unmock('vue-router')
vi.unmock('@/router')

const { createMemoryHistory } = await import('vue-router')
const { createCosmosRouter, routes } = await import('@/router')

const storage = (values = {}) => ({
  getItem: vi.fn((key) => values[key] ?? null)
})

describe('后台管理路由', () => {
  beforeEach(() => { document.title = '' })

  it('注册后台登录与工作台路由，并关闭用户 shell', () => {
    expect(routes.find(route => route.name === 'AdminLogin')).toMatchObject({
      path: '/admin/login',
      meta: { requiresAdmin: false, shell: false }
    })
    expect(routes.find(route => route.name === 'AdminDashboard')).toMatchObject({
      path: '/admin',
      meta: { requiresAdmin: true, shell: false }
    })
  })

  it('没有 adminToken 时跳转管理员登录页', async () => {
    const router = createCosmosRouter({ history: createMemoryHistory(), storage: storage() })
    await router.push('/admin')
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('AdminLogin')
    expect(router.currentRoute.value.query.redirect).toBe('/admin')
  })

  it('有 adminToken 时允许后台工作台，普通 token 不代替管理员令牌', async () => {
    const router = createCosmosRouter({
      history: createMemoryHistory(),
      storage: storage({ token: 'user-token', adminToken: 'admin-token' })
    })
    await router.push('/admin')
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('AdminDashboard')
  })
})
