import { readFile } from 'node:fs/promises'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { reactive } from 'vue'

const mocks = vi.hoisted(() => ({
  router: { replace: vi.fn() },
  store: {
    resources: {},
    loadAll: vi.fn(),
    retryResource: vi.fn(),
    invalidatePending: vi.fn()
  },
  userStore: { userInfo: { avatarUrl: '/me.webp' } },
  logUiEvent: vi.fn()
}))

vi.mock('vue-router', () => ({ useRouter: () => mocks.router }))
vi.mock('@/stores/home', () => ({ useHomeStore: () => mocks.store }))
vi.mock('@/stores/user', () => ({ useUserStore: () => mocks.userStore }))
vi.mock('@/composables/useReducedMotion', async () => {
  const { ref } = await import('vue')
  return { useReducedMotion: () => ref(true) }
})
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: mocks.logUiEvent }))

import HomeView from '@/views/home/index.vue'

const resource = (status, data = null, extra = {}) => ({
  status, data, requestId: 1, startedAt: null, errorCode: null,
  retryCount: 0, flow: null, degradedSides: [], ...extra
})

const successResources = () => ({
  couple: resource('success', { partner: { nickName: '星河', avatarUrl: '/partner.webp' } }),
  timer: resource('success', { loveDays: 1314 }),
  recipe: resource('success', { item: { title: '星空汤' }, total: 12, current: 1, size: 1, pages: 12 }),
  footprint: resource('unavailable'),
  anniversary: resource('success', { name: '相识日', daysUntil: 23, anniversaryDate: '2026-08-15', typeName: '纪念日' }),
  wish: resource('success', { title: '一起看海', statusName: '进行中', createTime: '2026-07-20T10:00:00' }),
  feed: resource('success', { content: '今天一起做饭', createTime: '2026-07-22T10:00:00', imageUrls: [] })
})

const mountHome = () => mount(HomeView, {
  global: {
    stubs: {
      RouterLink: RouterLinkStub,
      'van-icon': { template: '<i />' }
    }
  }
})

describe('home-emotion 首页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.store.resources = reactive(successResources())
    mocks.store.loadAll.mockResolvedValue([])
    mocks.store.retryResource.mockResolvedValue(undefined)
    mocks.userStore.userInfo = { avatarUrl: '/me.webp' }
  })

  it('只呈现选定的信息层级和精确真实路由', () => {
    const wrapper = mountHome()

    expect(wrapper.findComponent('[data-test="home-hero"]').props('to')).toBe('/ai')
    expect(wrapper.findComponent('[data-test="recipe-link"]').props('to')).toBe('/recipes')
    expect(wrapper.findComponent('[data-test="footprint-link"]').props('to')).toBe('/map')
    expect(wrapper.findComponent('[data-test="anniversary-link"]').props('to')).toEqual({ path: '/memories', query: { type: 'anniversary' } })
    expect(wrapper.findComponent('[data-test="wish-link"]').props('to')).toEqual({ path: '/memories', query: { type: 'wish' } })
    expect(wrapper.findComponent('[data-test="feed-link"]').props('to')).toBe('/feed')
    expect(wrapper.text()).toContain('今晚吃什么')
    expect(wrapper.text()).toContain('最近动态')
    expect(wrapper.text()).not.toMatch(/最近探店|米其林|正在线|Hungry|home-food|home-memory/)
  })

  it('Hero 使用本地稳定 LCP 尺寸且不延迟加载', () => {
    const hero = mountHome().find('[data-test="hero-image"]')

    expect(hero.attributes('src')).toContain('food-hero.webp')
    expect(hero.attributes()).toMatchObject({ width: '1280', height: '871', fetchpriority: 'high' })
    expect(hero.attributes('loading')).toBeUndefined()
  })

  it('单卡失败不隐藏其余成功数据，retry 只重发目标资源', async () => {
    mocks.store.resources.recipe = resource('error', null, { errorCode: 'NETWORK_ERROR' })
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('一起看海')
    expect(wrapper.text()).toContain('今天一起做饭')
    expect(wrapper.find('[data-test="retry-recipe"]').exists()).toBe(true)
    await wrapper.find('[data-test="retry-recipe"]').trigger('click')
    expect(mocks.store.retryResource).toHaveBeenCalledOnce()
    expect(mocks.store.retryResource).toHaveBeenCalledWith('recipe')
  })

  it('六个可请求资源均提供自身 retry，不借机重载其他资源', async () => {
    const retryTargets = [
      ['couple', 'retry-couple'],
      ['timer', 'retry-timer'],
      ['recipe', 'retry-recipe'],
      ['anniversary', 'retry-anniversary'],
      ['wish', 'retry-wish'],
      ['feed', 'retry-feed']
    ]

    for (const [resourceKey, testId] of retryTargets) {
      mocks.store.resources = reactive(successResources())
      mocks.store.resources[resourceKey] = resource('error', null, { errorCode: 'NETWORK_ERROR' })
      const wrapper = mountHome()
      await wrapper.find(`[data-test="${testId}"]`).trigger('click')
      expect(mocks.store.retryResource).toHaveBeenLastCalledWith(resourceKey)
      wrapper.unmount()
    }

    expect(mocks.store.retryResource).toHaveBeenCalledTimes(retryTargets.length)
  })

  it('footprint 固定不可用且不伪造到访内容', () => {
    const wrapper = mountHome()

    expect(wrapper.find('[data-test="footprint-state"]').text()).toContain('不提供到访记录')
    expect(wrapper.text()).not.toMatch(/昨晚|滨江大道|到访\s*\d+|最近足迹/)
  })

  it('非成功状态不以 0、假正文或假图片冒充数据', () => {
    mocks.store.resources.timer = resource('error')
    mocks.store.resources.anniversary = resource('empty')
    mocks.store.resources.wish = resource('loading')
    mocks.store.resources.feed = resource('empty')
    const wrapper = mountHome()

    expect(wrapper.find('[data-test="timer-state"]').text()).not.toContain('0 天')
    expect(wrapper.find('[data-test="anniversary-state"]').text()).not.toContain('0天')
    expect(wrapper.text()).not.toMatch(/想吃的私房菜|记录昨晚的美味时刻/)
    expect(wrapper.find('[data-test="feed-image"]').exists()).toBe(false)
  })

  it('Feed 单侧降级时保留真实最新项并显示局部提示', () => {
    mocks.store.resources.feed = resource('success', {
      content: '成功侧真实动态', createTime: '2026-07-22T10:00:00', imageUrls: []
    }, { degradedSides: ['received'] })
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('成功侧真实动态')
    expect(wrapper.find('[data-test="feed-degraded"]').text()).toContain('部分动态暂未加载')
  })

  it('Feed 成功但 content/message 为空时进入局部空态，不生成合成正文', () => {
    mocks.store.resources.feed = resource('success', { content: '', message: '', imageUrls: [] })
    const wrapper = mountHome()

    expect(wrapper.find('[data-test="feed-state"]').text()).toContain('暂无可显示的动态')
    expect(wrapper.find('.recent-feed__text').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('动态内容未填写')
  })

  it('Feed content 为空白时继续展示真实 message 字段', () => {
    mocks.store.resources.feed = resource('success', {
      content: '   ', message: '真实动态消息', imageUrls: []
    })
    const wrapper = mountHome()

    expect(wrapper.find('.recent-feed__text').text()).toBe('真实动态消息')
  })

  it('401 与 2006 分别进入登录和绑定流程，卸载时使请求上下文失效', async () => {
    mocks.store.resources.couple = resource('error', null, { errorCode: '401', flow: 'login' })
    let wrapper = mountHome()
    await flushPromises()
    expect(mocks.router.replace).toHaveBeenCalledWith('/login')
    wrapper.unmount()
    expect(mocks.store.invalidatePending).toHaveBeenCalledOnce()

    vi.clearAllMocks()
    mocks.store.loadAll.mockResolvedValue([])
    mocks.store.resources.couple = resource('error', null, { errorCode: '2006', flow: 'bind' })
    wrapper = mountHome()
    await flushPromises()
    expect(mocks.router.replace).toHaveBeenCalledWith('/bind')
    wrapper.unmount()
  })

  it('卸载后迟到的 loadAll 不会触发访问流程导航', async () => {
    let resolveLoadAll
    mocks.store.loadAll.mockReturnValueOnce(new Promise(resolve => { resolveLoadAll = resolve }))
    mocks.store.resources.couple = resource('error', null, { errorCode: '401', flow: 'login' })
    const wrapper = mountHome()
    await flushPromises()
    expect(mocks.store.loadAll).toHaveBeenCalledOnce()

    wrapper.unmount()
    resolveLoadAll([])
    await flushPromises()

    expect(mocks.router.replace).not.toHaveBeenCalled()
    expect(mocks.store.invalidatePending).toHaveBeenCalledOnce()
  })

  it('导航日志只记录目标路由和动效偏好', async () => {
    const wrapper = mountHome()
    await wrapper.find('[data-test="home-hero"]').trigger('click')

    expect(mocks.logUiEvent).toHaveBeenCalledWith('home.navigation', expect.objectContaining({
      targetRoute: '/ai', reducedMotion: true
    }))
    expect(JSON.stringify(mocks.logUiEvent.mock.calls)).not.toMatch(/星河|partner\.webp|今天一起做饭/)
  })

  it('源码不引用未选方案或禁止的展示资源', async () => {
    const source = await readFile('src/views/home/index.vue', 'utf8')

    expect(source).not.toMatch(/home-food|home-memory|googleapis|gstatic|tailwindcdn|jsdelivr|lh3\.googleusercontent|material-symbols/)
  })
})
