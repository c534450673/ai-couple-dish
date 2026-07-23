import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

const mapApi = vi.hoisted(() => ({
  getMapRestaurants: vi.fn(),
  getNearbyRestaurants: vi.fn()
}))

vi.mock('@/api', () => ({ mapApi }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { useMapStore } from '@/stores/map'
import MapView from '@/views/map/index.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))

const successfulLocation = () => ({
  geolocation: {
    getCurrentPosition: vi.fn(success => success({
      coords: { latitude: 31.2, longitude: 121.5, accuracy: 10 }
    }))
  }
})

const qqMapRuntime = (mapFactory = () => ({ setCenter: vi.fn() })) => ({
  latLng: vi.fn((latitude, longitude) => ({ latitude, longitude })),
  Map: vi.fn(mapFactory),
  Marker: vi.fn(() => ({ setMap: vi.fn() })),
  event: { addListener: vi.fn() }
})

describe('地图真实降级', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    setActivePinia(createPinia())
    mapApi.getMapRestaurants.mockResolvedValue({ data: [] })
    mapApi.getNearbyRestaurants.mockResolvedValue({ data: [] })
    vi.stubEnv('VITE_MAP_KEY', '')
    vi.stubGlobal('navigator', {})
    delete window.QQMap
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('列表接口不依赖中心点，并在 SDK/定位前独立加载', async () => {
    const wrapper = mount(MapView, { global: { plugins: [createPinia()] } })
    await flush()

    expect(mapApi.getMapRestaurants).toHaveBeenCalledWith({})
    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain('地图密钥未配置')
  })

  it('地点为空与接口失败分别显示真实空态和单次重试入口', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const empty = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    expect(empty.get('[data-test="map-empty"]').text()).toContain('还没有带坐标的餐厅')
    empty.unmount()

    mapApi.getMapRestaurants.mockRejectedValueOnce(new Error('private address'))
    const failedPinia = createPinia()
    setActivePinia(failedPinia)
    const failed = mount(MapView, { global: { plugins: [failedPinia] } })
    await flush()
    expect(failed.get('[data-test="map-error"]').text()).toContain('地点加载失败')
    await failed.get('[data-test="map-retry"]').trigger('click')
    expect(mapApi.getMapRestaurants).toHaveBeenCalledTimes(3)
  })

  it('旧列表请求不会覆盖新的状态筛选结果', async () => {
    const first = Promise.withResolvers()
    const second = Promise.withResolvers()
    mapApi.getMapRestaurants
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const store = useMapStore()

    const oldRequest = store.loadMapRestaurants()
    store.setStatusFilter(1)
    const newRequest = store.loadMapRestaurants()
    second.resolve({ data: [{ id: 2, restaurantName: '新结果', latitude: 1, longitude: 2, status: 1 }] })
    await newRequest
    first.resolve({ data: [{ id: 1, restaurantName: '旧结果', latitude: 1, longitude: 2, status: 0 }] })
    await oldRequest

    expect(store.nearbyRestaurants.map(item => item.id)).toEqual([2])
  })

  it('详情 sheet 使用 button handle，Escape 关闭并恢复触发点焦点', async () => {
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{ id: 9, restaurantName: '星港餐厅', latitude: 1, longitude: 2, statusName: '想去' }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { attachTo: document.body, global: { plugins: [pinia] } })
    await flush()
    const trigger = wrapper.get('[data-test="map-item-9"]')
    await trigger.trigger('click')
    await flush()

    expect(wrapper.get('[data-test="map-sheet-handle"]').element).toBe(document.activeElement)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flush()
    expect(wrapper.find('[data-test="map-detail-sheet"]').exists()).toBe(false)
    expect(trigger.element).toBe(document.activeElement)
    wrapper.unmount()
  })

  it('明确标记关键字搜索、路线、足迹和选点为 unavailable', async () => {
    const wrapper = mount(MapView, { global: { plugins: [createPinia()] } })
    await flush()

    expect(wrapper.text()).toContain('关键字搜索暂不可用')
    expect(wrapper.text()).toContain('路线、足迹与地图选点暂不可用')
  })

  it.each([
    ['脚本加载失败', 'onerror', '地图 SDK 加载失败'],
    ['脚本加载后 QQMap 缺失', 'onload', '地图 SDK 未提供 QQMap']
  ])('%s 时自动回到列表且不把画布当成功', async (name, callback, message) => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    vi.spyOn(document.head, 'appendChild').mockImplementation((node) => {
      queueMicrotask(() => node[callback]?.(new Event(callback.slice(2))))
      return node
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    await flush()

    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain(message)
    expect(wrapper.get('[data-test="map-mode-map"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('SDK 超时自动降级列表', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    vi.spyOn(document.head, 'appendChild').mockImplementation(node => node)
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await Promise.resolve()
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(8000)

    expect(wrapper.text()).toContain('地图 SDK 加载超时')
    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    wrapper.unmount()
  })

  it('地图构造异常自动降级列表', async () => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    window.QQMap = qqMapRuntime(() => { throw new Error('constructor private detail') })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    await flush()

    expect(wrapper.text()).toContain('地图初始化失败')
    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    wrapper.unmount()
  })

  it.each([
    ['定位权限被拒绝', 1, '定位权限被拒绝'],
    ['定位请求超时', 3, '定位请求超时']
  ])('%s 时保留已加载列表并禁用地图模式', async (name, code, message) => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    window.QQMap = qqMapRuntime()
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn((success, fail) => fail({
          code,
          PERMISSION_DENIED: 1,
          POSITION_UNAVAILABLE: 2,
          TIMEOUT: 3
        }))
      }
    })
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{ id: 12, restaurantName: '已加载地点', latitude: 1, longitude: 2 }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    await flush()

    expect(wrapper.text()).toContain(message)
    expect(wrapper.text()).toContain('已加载地点')
    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    wrapper.unmount()
  })

  it('地图成功后仍可随时切换回列表', async () => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    window.QQMap = qqMapRuntime()
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    await flush()

    expect(wrapper.get('[data-test="map-mode-map"]').attributes('aria-pressed')).toBe('true')
    await wrapper.get('[data-test="map-mode-list"]').trigger('click')
    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    wrapper.unmount()
  })
})
