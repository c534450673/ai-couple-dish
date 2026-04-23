<template>
  <div class="map-page">
    <!-- 地图容器 -->
    <div class="map-container" ref="mapContainer">
      <div id="map" class="map-view"></div>
    </div>

    <!-- 顶部搜索栏 -->
    <div class="map-header">
      <div class="search-bar">
        <van-icon name="search" class="search-icon" />
        <input
          type="text"
          v-model="searchKeyword"
          placeholder="搜索餐厅"
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <van-icon
          v-if="searchKeyword"
          name="clear"
          class="clear-icon"
          @click="searchKeyword = ''"
        />
      </div>
    </div>

    <!-- 定位按钮 -->
    <div class="location-btn" @click="handleLocation">
      <van-icon :name="isLocating ? 'loading' : 'location-o'" :class="{ locating: isLocating }" />
    </div>

    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <div class="zoom-btn" @click="handleZoomIn">
        <van-icon name="plus" />
      </div>
      <div class="zoom-btn" @click="handleZoomOut">
        <van-icon name="minus" />
      </div>
    </div>

    <!-- 状态筛选 -->
    <div class="filter-tabs">
      <div
        v-for="tab in statusTabs"
        :key="tab.value"
        class="filter-tab"
        :class="{ active: statusFilter === tab.value }"
        @click="handleStatusFilter(tab.value)"
      >
        {{ tab.label }}
      </div>
    </div>

    <!-- 餐厅列表面板 -->
    <div class="restaurant-panel" :class="{ expanded: isPanelExpanded }">
      <div class="panel-handle" @click="isPanelExpanded = !isPanelExpanded">
        <div class="handle-bar"></div>
      </div>

      <div class="panel-header">
        <span class="panel-title">附近的餐厅</span>
        <span class="restaurant-count" v-if="nearbyRestaurants.length">{{ nearbyRestaurants.length }} 家</span>
      </div>

      <div class="restaurant-list" v-if="!isLoading && nearbyRestaurants.length">
        <div
          v-for="restaurant in nearbyRestaurants"
          :key="restaurant.id"
          class="restaurant-item"
          :class="{ selected: selectedId === restaurant.id }"
          @click="handleRestaurantClick(restaurant)"
        >
          <div class="restaurant-cover">
            <img v-if="restaurant.coverImage" :src="restaurant.coverImage" :alt="restaurant.restaurantName" />
            <van-icon v-else name="shop-o" size="24" color="#ccc" />
          </div>
          <div class="restaurant-info">
            <div class="restaurant-name">{{ restaurant.restaurantName }}</div>
            <div class="restaurant-meta">
              <van-tag type="primary" size="small">{{ restaurant.statusName }}</van-tag>
              <span class="distance" v-if="restaurant.distance">{{ formatDistance(restaurant.distance) }}</span>
            </div>
            <div class="restaurant-dish" v-if="restaurant.dishName">{{ restaurant.dishName }}</div>
          </div>
          <van-icon name="arrow" class="arrow-icon" />
        </div>
      </div>

      <div class="empty-state" v-else-if="!isLoading">
        <van-empty description="附近暂无餐厅" />
      </div>

      <van-loading v-if="isLoading" class="loading-state" />
    </div>

    <!-- 餐厅详情弹窗 -->
    <van-popup v-model:show="showDetail" position="bottom" round :style="{ height: '40%' }">
      <div class="detail-popup" v-if="selectedRestaurant">
        <div class="detail-header">
          <img
            v-if="selectedRestaurant.coverImage"
            :src="selectedRestaurant.coverImage"
            class="detail-cover"
          />
          <div class="detail-info">
            <div class="detail-name">{{ selectedRestaurant.restaurantName }}</div>
            <div class="detail-location" v-if="selectedRestaurant.location">
              <van-icon name="location-o" size="14" />
              {{ selectedRestaurant.location }}
            </div>
            <div class="detail-tags">
              <van-tag type="primary">{{ selectedRestaurant.statusName }}</van-tag>
              <van-tag v-if="selectedRestaurant.rating" type="warning">
                {{ '★'.repeat(selectedRestaurant.rating) }}
              </van-tag>
              <span class="detail-price" v-if="selectedRestaurant.price">
                ¥{{ selectedRestaurant.price }}
              </span>
            </div>
          </div>
        </div>
        <div class="detail-actions">
          <van-button type="primary" size="small" @click="handleNavigate(selectedRestaurant)">
            导航
          </van-button>
          <van-button size="small" @click="handleViewDetail(selectedRestaurant)">
            查看详情
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useMapStore } from '@/stores/map'
import { mapApi } from '@/api'

const router = useRouter()
const mapStore = useMapStore()

// Refs
const mapContainer = ref(null)
const map = ref(null)
const markers = ref([])
const searchKeyword = ref('')
const isLocating = ref(false)
const isPanelExpanded = ref(false)
const showDetail = ref(false)
const selectedRestaurant = ref(null)
const selectedId = ref(null)

// Status tabs
const statusTabs = [
  { label: '全部', value: null },
  { label: '想去', value: 0 },
  { label: '去过', value: 1 },
  { label: '种草', value: 2 }
]

// Computed
const isLoading = computed(() => mapStore.isLoading)
const statusFilter = computed(() => mapStore.statusFilter)
const nearbyRestaurants = computed(() => mapStore.nearbyRestaurants)
const currentLocation = computed(() => mapStore.currentLocation)

// Methods
const formatDistance = (distance) => {
  if (!distance) return ''
  if (distance < 1000) {
    return `${Math.round(distance)}m`
  }
  return `${(distance / 1000).toFixed(1)}km`
}

const handleLocation = async () => {
  isLocating.value = true
  try {
    await mapStore.getCurrentPosition()
    showToast('定位成功')
    await loadNearbyRestaurants()
    updateMapCenter()
  } catch (error) {
    showToast(error.message || '定位失败')
  } finally {
    isLocating.value = false
  }
}

const handleZoomIn = () => {
  if (map.value) {
    const zoom = map.value.getZoom() + 1
    map.value.setZoom(zoom)
    mapStore.setZoomLevel(zoom)
  }
}

const handleZoomOut = () => {
  if (map.value) {
    const zoom = map.value.getZoom() - 1
    map.value.setZoom(zoom)
    mapStore.setZoomLevel(zoom)
  }
}

const handleStatusFilter = (status) => {
  mapStore.setStatusFilter(status)
  loadNearbyRestaurants()
}

const handleSearch = () => {
  loadNearbyRestaurants()
}

const handleRestaurantClick = (restaurant) => {
  selectedId.value = restaurant.id
  selectedRestaurant.value = restaurant
  showDetail.value = true

  // Pan to marker
  if (map.value && restaurant.latitude && restaurant.longitude) {
    map.value.panTo(new window.QQMap.latLng(restaurant.latitude, restaurant.longitude))
  }
}

const handleNavigate = (restaurant) => {
  if (!restaurant.latitude || !restaurant.longitude) {
    showToast('暂无位置信息')
    return
  }

  // 使用高德地图导航
  const url = `https://uri.amap.com/navigation?to=${restaurant.longitude},${restaurant.latitude},${restaurant.restaurantName}&mode=car&callnative=1`
  window.location.href = url
}

const handleViewDetail = (restaurant) => {
  showDetail.value = false
  router.push(`/menu/${restaurant.id}`)
}

const loadNearbyRestaurants = async () => {
  if (!currentLocation.value) {
    // 使用默认中心点加载数据
    await mapStore.loadMapRestaurants()
  } else {
    await mapStore.loadNearbyRestaurants()
  }
  updateMarkers()
}

const updateMapCenter = () => {
  if (map.value && currentLocation.value) {
    map.value.setCenter(new window.QQMap.latLng(
      currentLocation.value.latitude,
      currentLocation.value.longitude
    ))
  }
}

const updateMarkers = () => {
  // Clear existing markers
  if (markers.value) {
    markers.value.forEach(marker => marker.setMap(null))
  }
  markers.value = []

  // Add new markers
  nearbyRestaurants.value.forEach(restaurant => {
    if (!restaurant.latitude || !restaurant.longitude) return

    const marker = new window.QQMap.Marker({
      position: new window.QQMap.latLng(restaurant.latitude, restaurant.longitude),
      map: map.value,
      title: restaurant.restaurantName
    })

    // Custom marker icon based on status
    const iconColor = restaurant.status === 0 ? '#ff4757' : restaurant.status === 1 ? '#56ab2f' : '#ffa502'
    marker.setIcon(new window.QQMap.MarkerImage(
      `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="36" viewBox="0 0 24 36"><path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24c0-6.6-5.4-12-12-12z" fill="${iconColor}"/><circle cx="12" cy="12" r="5" fill="white"/></svg>`)}`,
      new window.QQMap.Size(24, 36),
      new window.QQMap.Point(0, 0),
      new window.QQMap.Point(12, 36)
    ))

    // Click event
    window.QQMap.event.addListener(marker, 'click', () => {
      handleRestaurantClick(restaurant)
    })

    markers.value.push(marker)
  })
}

const initMap = () => {
  if (!window.QQMap) {
    console.error('QQMap SDK 未加载')
    return
  }

  const center = currentLocation.value
    ? new window.QQMap.latLng(currentLocation.value.latitude, currentLocation.value.longitude)
    : new window.QQMap.latLng(mapStore.center.latitude, mapStore.center.longitude)

  map.value = new window.QQMap.Map('#map', {
    center: center,
    zoom: mapStore.zoomLevel,
    mapStyleId: 'style1'
  })

  // Map click event
  window.QQMap.event.addListener(map.value, 'click', (e) => {
    selectedId.value = null
    showDetail.value = false
  })

  // Load initial data
  loadNearbyRestaurants()
}

// Watch for status filter changes
watch(statusFilter, () => {
  loadNearbyRestaurants()
})

onMounted(() => {
  // Load QQMap SDK dynamically
  const script = document.createElement('script')
  script.src = `https://map.qq.com/api/gljs?v=1.exp&key=${import.meta.env.VITE_MAP_KEY || 'YOUR_MAP_KEY'}`
  script.onload = () => {
    // Wait for SDK to be ready
    setTimeout(initMap, 500)
  }
  document.head.appendChild(script)

  // Auto locate on mount
  handleLocation()
})

onUnmounted(() => {
  if (markers.value) {
    markers.value.forEach(marker => marker.setMap(null))
  }
  mapStore.reset()
})
</script>

<style lang="scss" scoped>
.map-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  position: relative;
}

.map-container {
  flex: 1;
  position: relative;

  .map-view {
    width: 100%;
    height: 100%;
  }
}

.map-header {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  z-index: 100;

  .search-bar {
    display: flex;
    align-items: center;
    background: #fff;
    border-radius: 20px;
    padding: 8px 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

    .search-icon {
      color: #999;
      margin-right: 8px;
    }

    .search-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 14px;

      &::placeholder {
        color: #999;
      }
    }

    .clear-icon {
      color: #999;
      cursor: pointer;
    }
  }
}

.location-btn {
  position: absolute;
  right: 16px;
  bottom: 280px;
  z-index: 100;
  width: 44px;
  height: 44px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;

  .locating {
    animation: rotate 1s linear infinite;
  }

  @keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
}

.zoom-controls {
  position: absolute;
  right: 16px;
  bottom: 200px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 8px;

  .zoom-btn {
    width: 44px;
    height: 44px;
    background: #fff;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    cursor: pointer;
  }
}

.filter-tabs {
  position: absolute;
  top: 70px;
  left: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  gap: 8px;

  .filter-tab {
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 16px;
    font-size: 12px;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;

    &.active {
      background: #ff4757;
      color: #fff;
    }
  }
}

.restaurant-panel {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  background: #fff;
  border-radius: 16px 16px 0 0;
  max-height: 280px;
  transition: max-height 0.3s ease;
  overflow: hidden;

  &.expanded {
    max-height: 60vh;
  }

  .panel-handle {
    padding: 8px;
    display: flex;
    justify-content: center;
    cursor: pointer;

    .handle-bar {
      width: 40px;
      height: 4px;
      background: #ddd;
      border-radius: 2px;
    }
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px 12px;
    border-bottom: 1px solid #eee;

    .panel-title {
      font-size: 16px;
      font-weight: 600;
    }

    .restaurant-count {
      font-size: 12px;
      color: #999;
    }
  }

  .restaurant-list {
    max-height: 200px;
    overflow-y: auto;

    &.expanded {
      max-height: calc(60vh - 60px);
    }
  }

  .restaurant-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    transition: background 0.2s;

    &:active {
      background: #f5f5f5;
    }

    &.selected {
      background: #fff5f5;
    }

    .restaurant-cover {
      width: 48px;
      height: 48px;
      background: #f5f5f5;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    .restaurant-info {
      flex: 1;

      .restaurant-name {
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 4px;
      }

      .restaurant-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;

        .distance {
          font-size: 12px;
          color: #ff4757;
        }
      }

      .restaurant-dish {
        font-size: 12px;
        color: #999;
      }
    }

    .arrow-icon {
      color: #ccc;
    }
  }

  .empty-state,
  .loading-state {
    padding: 40px 0;
    display: flex;
    justify-content: center;
  }
}

.detail-popup {
  padding: 16px;

  .detail-header {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;

    .detail-cover {
      width: 80px;
      height: 80px;
      border-radius: 8px;
      object-fit: cover;
    }

    .detail-info {
      flex: 1;

      .detail-name {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 4px;
      }

      .detail-location {
        font-size: 12px;
        color: #666;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .detail-tags {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;

        .detail-price {
          font-size: 14px;
          color: #ff4757;
          font-weight: 500;
        }
      }
    }
  }

  .detail-actions {
    display: flex;
    gap: 12px;

    .van-button {
      flex: 1;
    }
  }
}
</style>