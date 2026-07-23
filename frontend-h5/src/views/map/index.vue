<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMapStore } from '@/stores/map'
import { logUiEvent } from '@/composables/useStructuredLog'

const SDK_TIMEOUT_MS = 8000
const router = useRouter()
const mapStore = useMapStore()
const mapElement = ref(null)
const sheetHandle = ref(null)
const selectedRestaurant = ref(null)
const showDetail = ref(false)
const mapReady = ref(false)
const fallbackMessage = ref('')
const mapInstance = ref(null)
const mapMarkers = ref([])
let sdkScript = null
let sdkTimer = null
let detailTrigger = null

const restaurants = computed(() => mapStore.nearbyRestaurants)
const mode = computed(() => mapStore.viewMode)
const listStatus = computed(() => mapStore.listStatus)
const mapUnavailable = computed(() => !mapReady.value)
const statusTabs = [
  { label: '全部', value: null },
  { label: '想去', value: 0 },
  { label: '去过', value: 1 },
  { label: '种草', value: 2 }
]

const formatDistance = (distance) => mapStore.formatDistance(distance)

const logMapRuntime = (event, startedAt, errorCode = null) => {
  logUiEvent(event, {
    mode: mode.value,
    sdkStage: mapStore.sdkStage,
    permission: mapStore.permissionStage,
    itemCount: restaurants.value.length,
    durationMs: Math.round(performance.now() - startedAt),
    errorCode
  })
}

const setFallback = (message, stage, errorCode, startedAt) => {
  fallbackMessage.value = message
  mapReady.value = false
  mapStore.setSdkStage(stage, errorCode)
  mapStore.setViewMode('list')
  logMapRuntime('map.runtime.fallback', startedAt, errorCode)
}

const loadSdk = (key) => new Promise((resolve, reject) => {
  if (window.QQMap) {
    resolve(window.QQMap)
    return
  }

  mapStore.setSdkStage('loading')
  sdkScript = document.createElement('script')
  sdkScript.dataset.cosmosMapSdk = 'true'
  sdkScript.src = `https://map.qq.com/api/gljs?v=1.exp&key=${encodeURIComponent(key)}`
  sdkScript.async = true
  sdkScript.onload = () => {
    clearTimeout(sdkTimer)
    if (window.QQMap) resolve(window.QQMap)
    else reject(Object.assign(new Error('地图 SDK 未提供 QQMap'), { code: 'QQMAP_MISSING' }))
  }
  sdkScript.onerror = () => {
    clearTimeout(sdkTimer)
    reject(Object.assign(new Error('地图 SDK 加载失败'), { code: 'SDK_LOAD_ERROR' }))
  }
  sdkTimer = setTimeout(() => {
    reject(Object.assign(new Error('地图 SDK 加载超时'), { code: 'SDK_TIMEOUT' }))
  }, SDK_TIMEOUT_MS)
  document.head.appendChild(sdkScript)
})

const clearMapMarkers = () => {
  mapMarkers.value.forEach(marker => marker.setMap?.(null))
  mapMarkers.value = []
}

const renderMarkers = () => {
  clearMapMarkers()
  if (!mapReady.value || !mapInstance.value || !window.QQMap) return

  restaurants.value.forEach((restaurant) => {
    if (restaurant.latitude === null || restaurant.latitude === undefined
      || restaurant.longitude === null || restaurant.longitude === undefined) return

    const marker = new window.QQMap.Marker({
      position: new window.QQMap.latLng(restaurant.latitude, restaurant.longitude),
      map: mapInstance.value,
      title: restaurant.restaurantName
    })
    window.QQMap.event?.addListener(marker, 'click', () => openDetail(restaurant))
    mapMarkers.value.push(marker)
  })
}

const initializeMap = async () => {
  const startedAt = performance.now()
  const key = String(import.meta.env.VITE_MAP_KEY || '').trim()
  if (!key || key === 'YOUR_MAP_KEY') {
    setFallback('地图密钥未配置，已切换地点列表', 'missing-key', 'MAP_KEY_MISSING', startedAt)
    return
  }

  try {
    const [, location] = await Promise.all([loadSdk(key), mapStore.getCurrentPosition()])
    if (!window.QQMap) {
      setFallback('地图组件不可用，已切换地点列表', 'missing-global', 'QQMAP_MISSING', startedAt)
      return
    }

    try {
      mapInstance.value = new window.QQMap.Map(mapElement.value, {
        center: new window.QQMap.latLng(location.latitude, location.longitude),
        zoom: mapStore.zoomLevel,
        mapStyleId: 'style1'
      })
    } catch {
      setFallback('地图初始化失败，已切换地点列表', 'construct-failed', 'MAP_CONSTRUCT_FAILED', startedAt)
      return
    }

    mapStore.setSdkStage('ready')
    mapReady.value = true
    mapStore.setViewMode('map')
    await mapStore.loadNearbyRestaurants()
    renderMarkers()
    logMapRuntime('map.runtime.ready', startedAt)
  } catch (error) {
    const code = error?.code || mapStore.errorCode || 'MAP_RUNTIME_FAILED'
    const message = code.startsWith('LOCATION_')
      ? `${error.message}，已切换地点列表`
      : `${error?.message || '地图不可用'}，已切换地点列表`
    setFallback(message, code.startsWith('LOCATION_') ? 'location-failed' : 'sdk-failed', code, startedAt)
  }
}

const selectMode = (nextMode) => {
  if (nextMode === 'map' && mapUnavailable.value) return
  mapStore.setViewMode(nextMode)
  logMapRuntime('map.mode.changed', performance.now())
}

const handleStatusFilter = async (status) => {
  mapStore.setStatusFilter(status)
  if (mapStore.currentLocation) await mapStore.loadNearbyRestaurants()
  renderMarkers()
}

const retryList = async () => {
  await mapStore.loadMapRestaurants()
  renderMarkers()
}

const openDetail = async (restaurant, event) => {
  detailTrigger = event?.currentTarget || document.activeElement
  selectedRestaurant.value = restaurant
  showDetail.value = true
  await nextTick()
  sheetHandle.value?.focus()
}

const closeDetail = async () => {
  showDetail.value = false
  selectedRestaurant.value = null
  await nextTick()
  detailTrigger?.focus?.()
  detailTrigger = null
}

const onKeydown = (event) => {
  if (event.key === 'Escape' && showDetail.value) closeDetail()
}

const viewDetail = () => {
  const id = selectedRestaurant.value?.id
  closeDetail()
  if (id) router.push(`/menu/${id}`)
}

const navigationUrl = computed(() => {
  const restaurant = selectedRestaurant.value
  if (!restaurant || restaurant.latitude === null || restaurant.latitude === undefined
    || restaurant.longitude === null || restaurant.longitude === undefined) return ''
  const destination = `${restaurant.longitude},${restaurant.latitude},${restaurant.restaurantName || ''}`
  return `https://uri.amap.com/navigation?to=${encodeURIComponent(destination)}&mode=car&callnative=1`
})

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  await mapStore.loadMapRestaurants()
  await initializeMap()
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  clearTimeout(sdkTimer)
  sdkScript?.remove()
  clearMapMarkers()
})
</script>

<template>
  <main class="map-page">
    <header class="map-header">
      <div>
        <p>OUR PLACES</p>
        <h1>味觉星图</h1>
      </div>
      <div
        class="mode-switch"
        aria-label="地图展示模式"
      >
        <button
          type="button"
          data-test="map-mode-map"
          :aria-pressed="mode === 'map'"
          :disabled="mapUnavailable"
          @click="selectMode('map')"
        >
          <van-icon name="location-o" />
          地图
        </button>
        <button
          type="button"
          data-test="map-mode-list"
          :aria-pressed="mode === 'list'"
          @click="selectMode('list')"
        >
          <van-icon name="bars" />
          列表
        </button>
      </div>
    </header>

    <p
      v-if="fallbackMessage"
      class="fallback-banner"
      role="status"
    >
      {{ fallbackMessage }}
    </p>

    <section
      class="capability-note"
      aria-label="地图能力说明"
    >
      <span>关键字搜索暂不可用</span>
      <span>路线、足迹与地图选点暂不可用</span>
    </section>

    <nav
      class="status-tabs"
      aria-label="到访状态筛选"
    >
      <button
        v-for="tab in statusTabs"
        :key="String(tab.value)"
        type="button"
        :class="{ active: mapStore.statusFilter === tab.value }"
        :aria-pressed="mapStore.statusFilter === tab.value"
        @click="handleStatusFilter(tab.value)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <section
      v-show="mode === 'map'"
      class="map-stage"
      aria-label="餐厅地图"
    >
      <div
        ref="mapElement"
        class="map-canvas"
      />
    </section>

    <section
      v-show="mode === 'list'"
      class="place-list"
      aria-live="polite"
    >
      <div
        v-if="mapStore.error"
        class="list-error"
        data-test="map-error"
        role="alert"
      >
        <p>{{ mapStore.error }}</p>
        <button
          type="button"
          data-test="map-retry"
          @click="retryList"
        >
          重新加载
        </button>
      </div>

      <div
        v-if="listStatus === 'loading'"
        class="list-state"
      >
        <van-loading />
        <p>正在加载地点</p>
      </div>

      <div
        v-else-if="restaurants.length"
        class="place-items"
      >
        <button
          v-for="restaurant in restaurants"
          :key="restaurant.id"
          type="button"
          class="place-item"
          :data-test="`map-item-${restaurant.id}`"
          @click="openDetail(restaurant, $event)"
        >
          <span
            class="place-cover cosmos-media cosmos-media--place"
            aria-hidden="true"
          />
          <span class="place-copy">
            <strong>{{ restaurant.restaurantName || '未命名餐厅' }}</strong>
            <span>{{ restaurant.dishName || restaurant.statusName || '共同收藏地点' }}</span>
            <small v-if="restaurant.distance !== null && restaurant.distance !== undefined">
              {{ formatDistance(restaurant.distance) }}
            </small>
          </span>
          <van-icon name="arrow" />
        </button>
      </div>

      <div
        v-else-if="listStatus !== 'error'"
        class="list-state"
        data-test="map-empty"
      >
        <van-icon
          name="shop-o"
          size="36"
        />
        <h2>还没有带坐标的餐厅</h2>
        <p>地图接口只返回已有坐标的情侣菜单地点。</p>
      </div>
    </section>

    <div
      v-if="showDetail"
      class="sheet-backdrop"
      @click.self="closeDetail"
    >
      <section
        v-if="selectedRestaurant"
        class="detail-sheet"
        data-test="map-detail-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="map-detail-title"
      >
        <button
          ref="sheetHandle"
          type="button"
          class="sheet-handle"
          data-test="map-sheet-handle"
          aria-label="关闭地点详情"
          @click="closeDetail"
        >
          <span />
        </button>
        <div
          class="detail-hero cosmos-media cosmos-media--place"
          aria-hidden="true"
        />
        <div class="detail-content">
          <p>{{ selectedRestaurant.statusName || '共同地点' }}</p>
          <h2 id="map-detail-title">
            {{ selectedRestaurant.restaurantName }}
          </h2>
          <span v-if="selectedRestaurant.location">{{ selectedRestaurant.location }}</span>
          <div class="detail-actions">
            <a
              v-if="navigationUrl"
              :href="navigationUrl"
              target="_blank"
              rel="noopener noreferrer"
            >外部导航</a>
            <button
              v-else
              type="button"
              disabled
            >
              导航不可用
            </button>
            <button
              type="button"
              @click="viewDetail"
            >
              查看详情
            </button>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<style lang="scss" scoped>
.map-page { min-height: calc(100vh - 64px); padding: $space-5 $page-padding 100px; color: $cosmos-text; background: $cosmos-bg; }
.map-header { display: flex; gap: $space-4; align-items: center; justify-content: space-between; }
.map-header p { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; }
.map-header h1 { font-size: $fs-headline; letter-spacing: 0; }
.mode-switch { display: flex; padding: 3px; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; }
.mode-switch button { display: flex; min-height: 40px; gap: $space-1; align-items: center; padding: 0 $space-3; border: 0; border-radius: 6px; background: transparent; color: $cosmos-text-muted; }
.mode-switch button[aria-pressed='true'] { background: $cosmos-primary; color: #fff; }
.mode-switch button:disabled { opacity: .42; }
.fallback-banner, .capability-note { margin-top: $space-4; border: 1px solid $cosmos-border; border-radius: 8px; color: $cosmos-text-muted; font-size: $fs-caption; }
.fallback-banner { padding: $space-3; border-color: rgba(255,200,87,.55); background: rgba(255,200,87,.08); color: $cosmos-gold; }
.capability-note { display: flex; flex-wrap: wrap; gap: $space-2 $space-4; padding: $space-3; background: $cosmos-surface; }
.status-tabs { display: flex; gap: $space-2; margin: $space-4 0; overflow-x: auto; }
.status-tabs button { min-height: 40px; padding: 0 $space-4; border: 1px solid $cosmos-border; border-radius: 999px; background: transparent; color: $cosmos-text-muted; white-space: nowrap; }
.status-tabs button.active { border-color: $cosmos-secondary; color: $cosmos-secondary; }
.map-stage { overflow: hidden; min-height: 520px; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; }
.map-canvas { width: 100%; height: 520px; }
.place-list { min-height: 420px; }
.place-items { display: grid; gap: $space-3; }
.place-item { display: grid; grid-template-columns: 82px minmax(0, 1fr) 24px; min-height: 96px; gap: $space-3; align-items: center; width: 100%; padding: $space-2; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; color: $cosmos-text; text-align: left; }
.place-cover { width: 82px; height: 80px; border-radius: 6px; }
.place-copy { display: grid; min-width: 0; gap: $space-1; }
.place-copy strong, .place-copy span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.place-copy span, .place-copy small { color: $cosmos-text-muted; }
.place-copy small { color: $cosmos-gold; }
.list-state, .list-error { display: grid; min-height: 300px; place-items: center; align-content: center; gap: $space-3; color: $cosmos-text-muted; text-align: center; }
.list-state h2 { color: $cosmos-text; font-size: $fs-title; }
.list-error button { min-height: 44px; padding: 0 $space-5; border: 1px solid $cosmos-primary; border-radius: 6px; background: transparent; color: $cosmos-primary; }
.sheet-backdrop { position: fixed; z-index: 1200; inset: 0; display: flex; align-items: flex-end; justify-content: center; background: rgba(5,8,20,.72); }
.detail-sheet { overflow: hidden; width: min(100%, 560px); padding: 0 $page-padding calc($space-6 + env(safe-area-inset-bottom)); border: 1px solid $cosmos-glass-border; border-radius: 28px 28px 0 0; background: $cosmos-surface-raised; box-shadow: $shadow-float; }
.sheet-handle { display: grid; width: 100%; min-height: 44px; place-items: center; border: 0; background: transparent; }
.sheet-handle span { width: 48px; height: 4px; border-radius: 4px; background: $cosmos-text-muted; }
.sheet-handle:focus-visible { outline: 2px solid $cosmos-secondary; outline-offset: -4px; }
.detail-hero { height: 150px; border-radius: 8px; }
.detail-content { padding-top: $space-4; }
.detail-content > p { color: $cosmos-secondary; font-size: $fs-caption; }
.detail-content h2 { margin-top: $space-1; font-size: $fs-title; }
.detail-content > span { display: block; margin-top: $space-2; color: $cosmos-text-muted; }
.detail-actions { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; margin-top: $space-5; }
.detail-actions a, .detail-actions button { display: grid; min-height: 46px; place-items: center; border: 1px solid $cosmos-primary; border-radius: 6px; background: transparent; color: $cosmos-primary; }
.detail-actions button:last-child { background: $cosmos-primary; color: #fff; }
.detail-actions button:disabled { opacity: .45; }
@media (min-width: 760px) { .place-items { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
