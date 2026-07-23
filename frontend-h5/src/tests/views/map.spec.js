import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

const mapApi = vi.hoisted(() => ({
  getMapRestaurants: vi.fn(),
  getNearbyRestaurants: vi.fn()
}))
const structuredLog = vi.hoisted(() => ({ logUiEvent: vi.fn() }))

vi.mock('@/api', () => ({ mapApi }))
vi.mock('@/composables/useStructuredLog', () => structuredLog)

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

const qqMapRuntime = (mapFactory = () => ({ setCenter: vi.fn() }), readyEvent = null) => {
  const listeners = new Map()
  const runtime = {
    latLng: vi.fn((latitude, longitude) => ({ latitude, longitude })),
    Map: vi.fn(() => {
      const map = mapFactory()
      if (readyEvent) queueMicrotask(() => runtime.emit(readyEvent))
      return map
    }),
    Marker: vi.fn(() => ({ setMap: vi.fn() })),
    event: {
      addListener: vi.fn((target, eventName, handler) => {
        const entry = { eventName, handler, removed: false }
        listeners.set(eventName, [...(listeners.get(eventName) || []), entry])
        return entry
      }),
      removeListener: vi.fn((entry) => {
        if (entry) entry.removed = true
      })
    },
    emit(eventName, payload) {
      listeners.get(eventName)?.forEach((entry) => {
        if (!entry.removed) entry.handler(payload)
      })
    }
  }
  return runtime
}

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

  it.each(['tilesloaded', 'idle'])('等待 QQMap %s 首次就绪后才切换地图', async (readyEvent) => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    const runtime = qqMapRuntime()
    window.QQMap = runtime
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{ id: 21, restaurantName: '初始地点', latitude: 1, longitude: 2 }]
    })
    mapApi.getNearbyRestaurants.mockResolvedValueOnce({
      data: [{ id: 22, restaurantName: '附近地点', latitude: 31.2, longitude: 121.5 }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()

    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('.map-stage').classes()).toContain('map-stage--pending')
    expect(wrapper.get('.map-stage').attributes('style') || '').not.toContain('display: none')
    expect(mapApi.getNearbyRestaurants).not.toHaveBeenCalled()

    runtime.emit(readyEvent)
    await flush()

    expect(wrapper.get('[data-test="map-mode-map"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('.map-stage').classes()).not.toContain('map-stage--pending')
    expect(mapApi.getNearbyRestaurants).toHaveBeenCalledOnce()
    expect(runtime.event.removeListener).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('QQMap 异步 error 与 render timeout 均降级并清理监听器', async () => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    const runtime = qqMapRuntime()
    window.QQMap = runtime
    mapApi.getMapRestaurants.mockResolvedValue({
      data: [{ id: 23, restaurantName: '保留地点', latitude: 1, longitude: 2 }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const failed = mount(MapView, { global: { plugins: [pinia] } })
    await flush()

    runtime.emit('error', new Error('private map error'))
    await flush()
    expect(failed.text()).toContain('地图渲染失败')
    expect(failed.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(runtime.event.removeListener).toHaveBeenCalledTimes(3)
    failed.unmount()

    vi.useFakeTimers()
    const timeoutRuntime = qqMapRuntime()
    window.QQMap = timeoutRuntime
    const timeoutPinia = createPinia()
    setActivePinia(timeoutPinia)
    const timedOut = mount(MapView, { global: { plugins: [timeoutPinia] } })
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(8000)

    expect(timedOut.text()).toContain('地图渲染超时')
    expect(timedOut.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(timeoutRuntime.event.removeListener).toHaveBeenCalledTimes(3)
    timedOut.unmount()
  })

  it('地图结构化日志仅包含允许字段且不泄露运行时敏感值', async () => {
    const sentinels = {
      key: 'MAP_KEY_SENTINEL_PRIVATE',
      latitude: 81.23456789,
      longitude: -171.98765432,
      address: 'ADDRESS_SENTINEL_PRIVATE',
      navigation: 'NAVIGATION_URL_SENTINEL_PRIVATE',
      asyncError: 'ASYNC_ERROR_DETAIL_SENTINEL_PRIVATE'
    }
    vi.stubEnv('VITE_MAP_KEY', sentinels.key)
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: vi.fn(success => success({
          coords: {
            latitude: sentinels.latitude,
            longitude: sentinels.longitude,
            accuracy: 7
          }
        }))
      }
    })
    const runtime = qqMapRuntime()
    window.QQMap = runtime
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{
        id: 26,
        restaurantName: sentinels.navigation,
        location: sentinels.address,
        latitude: sentinels.latitude,
        longitude: sentinels.longitude
      }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()

    await wrapper.get('[data-test="map-item-26"]').trigger('click')
    await flush()
    expect(wrapper.get('.detail-content').text()).toContain(sentinels.address)
    expect(decodeURIComponent(wrapper.get('.detail-actions a').attributes('href')))
      .toContain(sentinels.navigation)

    runtime.emit('error', new Error(sentinels.asyncError))
    await flush()

    const allowedFields = [
      'mode', 'sdkStage', 'permission', 'itemCount', 'durationMs', 'errorCode'
    ].sort()
    expect(structuredLog.logUiEvent).toHaveBeenCalled()
    structuredLog.logUiEvent.mock.calls.forEach(([, fields]) => {
      expect(Object.keys(fields).sort()).toEqual(allowedFields)
    })
    const serializedLogs = JSON.stringify(structuredLog.logUiEvent.mock.calls)
    Object.values(sentinels).forEach((sentinel) => {
      expect(serializedLogs).not.toContain(String(sentinel))
    })
    wrapper.unmount()
  })

  it('地图就绪前卸载会移除监听器并取消 render timeout', async () => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    const runtime = qqMapRuntime()
    window.QQMap = runtime
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{ id: 25, restaurantName: '待渲染地点', latitude: 1, longitude: 2 }]
    })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(0)

    expect(runtime.event.addListener).toHaveBeenCalledTimes(3)
    wrapper.unmount()
    expect(runtime.event.removeListener).toHaveBeenCalledTimes(3)
    await vi.advanceTimersByTimeAsync(8000)
    expect(runtime.event.removeListener).toHaveBeenCalledTimes(3)
  })

  it.each([
    ['地图列表接口失败', 'map-error'],
    ['附近接口失败', 'nearby-error'],
    ['附近真实零点位', 'nearby-empty']
  ])('%s 时即使 SDK 已就绪也保持列表', async (name, scenario) => {
    vi.stubEnv('VITE_MAP_KEY', 'valid-map-key')
    vi.stubGlobal('navigator', successfulLocation())
    const runtime = qqMapRuntime(undefined, 'tilesloaded')
    window.QQMap = runtime
    const point = { id: 24, restaurantName: '可用地点', latitude: 31.2, longitude: 121.5 }
    if (scenario === 'map-error') mapApi.getMapRestaurants.mockRejectedValueOnce(new Error('private list error'))
    else mapApi.getMapRestaurants.mockResolvedValueOnce({ data: [point] })
    if (scenario === 'nearby-error') mapApi.getNearbyRestaurants.mockRejectedValueOnce(new Error('private nearby error'))
    else mapApi.getNearbyRestaurants.mockResolvedValueOnce({ data: scenario === 'nearby-empty' ? [] : [point] })
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(MapView, { global: { plugins: [pinia] } })
    await flush()
    await flush()

    expect(wrapper.get('[data-test="map-mode-list"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-test="map-mode-map"]').attributes('disabled')).toBeDefined()
    if (scenario === 'nearby-empty') expect(wrapper.get('[data-test="map-empty"]').exists()).toBe(true)
    else expect(wrapper.get('[data-test="map-error"]').exists()).toBe(true)
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
    window.QQMap = qqMapRuntime(undefined, 'tilesloaded')
    mapApi.getMapRestaurants.mockResolvedValueOnce({
      data: [{ id: 30, restaurantName: '初始地点', latitude: 1, longitude: 2 }]
    })
    mapApi.getNearbyRestaurants.mockResolvedValueOnce({
      data: [{ id: 31, restaurantName: '附近地点', latitude: 31.2, longitude: 121.5 }]
    })
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
