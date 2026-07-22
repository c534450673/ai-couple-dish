import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.unmock('vue-router')
vi.unmock('@/router')

const { createMemoryHistory } = await import('vue-router')
const { createCosmosRouter, routes } = await import('@/router')

const createStorage = (values = {}) => ({
  getItem: vi.fn((key) => values[key] ?? null)
})

const createTestRouter = (storage) => createCosmosRouter({
  history: createMemoryHistory(),
  storage
})

describe('Couple Cosmos 路由', () => {
  beforeEach(() => {
    document.title = ''
  })

  it('保留既有 name/path 并注册 Task 3 路由', () => {
    const routeMap = routes.map(({ name, path }) => [name, path])

    expect(routeMap).toEqual(expect.arrayContaining([
      ['Login', '/login'],
      ['Bind', '/bind'],
      ['Home', '/home'],
      ['Menu', '/menu'],
      ['MenuAdd', '/menu/add'],
      ['MenuDetail', '/menu/:id'],
      ['RecipeAdd', '/recipe/add'],
      ['Anniversary', '/anniversary'],
      ['Feed', '/feed'],
      ['Note', '/note'],
      ['Wish', '/wish'],
      ['Map', '/map'],
      ['Settings', '/settings'],
      ['Recipes', '/recipes'],
      ['RecipeDetail', '/recipes/:id'],
      ['RecipeNew', '/recipes/new'],
      ['RecipeEdit', '/recipes/:id/edit'],
      ['Memories', '/memories'],
      ['MemoryNoteNew', '/memories/notes/new'],
      ['MemoryNoteDetail', '/memories/notes/:id'],
      ['Ai', '/ai'],
      ['Notifications', '/notifications'],
      ['Legal', '/legal'],
      ['States', '/states']
    ]))
  })

  it('五个主入口编码精确 tab meta，登录和绑定关闭 shell', () => {
    const tabs = routes
      .filter((route) => route.meta?.tab)
      .map((route) => [route.meta.tab, route.path])

    expect(tabs).toEqual([
      ['星球', '/home'],
      ['菜单', '/menu'],
      ['投喂', '/feed'],
      ['回忆', '/memories'],
      ['我们', '/settings']
    ])
    expect(routes.find((route) => route.name === 'Login').meta.shell).toBe(false)
    expect(routes.find((route) => route.name === 'Bind').meta.shell).toBe(false)
  })

  it('无 token 时优先跳转登录并完整保留 redirect', async () => {
    const router = createTestRouter(createStorage())

    await router.push('/memories/notes/new?source=fab')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query.redirect).toBe('/memories/notes/new?source=fab')
  })

  it('有 token 但未绑定时跳转绑定并完整保留 redirect', async () => {
    const router = createTestRouter(createStorage({ token: 'session-token' }))

    await router.push('/recipes/42/edit?from=detail')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Bind')
    expect(router.currentRoute.value.query.redirect).toBe('/recipes/42/edit?from=detail')
  })

  it('情侣门禁只读取 hydration 快照且绑定后允许访问', async () => {
    const storage = createStorage({
      token: 'session-token',
      coupleInfo: JSON.stringify({ id: 7 })
    })
    const router = createTestRouter(storage)

    await router.push('/feed')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Feed')
    expect(storage.getItem).toHaveBeenCalledWith('token')
    expect(storage.getItem).toHaveBeenCalledWith('coupleInfo')
  })

  it('已登录用户访问 guest 页面仍跳转 Home', async () => {
    const router = createTestRouter(createStorage({
      token: 'session-token',
      coupleInfo: JSON.stringify({ id: 7 })
    }))

    await router.push('/login?redirect=/feed')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('Home')
  })
})
