import { defineStore } from 'pinia'
import { mapApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const DEFAULT_CENTER = { latitude: 39.9042, longitude: 116.4074 }

const locationError = (error) => {
  if (!error) return { message: '获取位置失败', code: 'LOCATION_FAILED' }
  if (error.code === error.PERMISSION_DENIED || error.code === 1) {
    return { message: '定位权限被拒绝', code: 'LOCATION_DENIED' }
  }
  if (error.code === error.POSITION_UNAVAILABLE || error.code === 2) {
    return { message: '位置信息不可用', code: 'LOCATION_UNAVAILABLE' }
  }
  if (error.code === error.TIMEOUT || error.code === 3) {
    return { message: '定位请求超时', code: 'LOCATION_TIMEOUT' }
  }
  return { message: '获取位置失败', code: 'LOCATION_FAILED' }
}

export const useMapStore = defineStore('map', {
  state: () => ({
    currentLocation: null,
    center: { ...DEFAULT_CENTER },
    zoomLevel: 15,
    markers: [],
    selectedMarker: null,
    allRestaurants: [],
    nearbyRestaurants: [],
    searchRadius: 5000,
    statusFilter: null,
    viewMode: 'list',
    listStatus: 'idle',
    sdkStage: 'idle',
    permissionStage: 'idle',
    isLoading: false,
    isLocated: false,
    error: null,
    errorCode: null,
    activeListRequestId: 0
  }),

  getters: {
    canSelectLocation: (state) => Boolean(state.currentLocation),
    filteredMarkers: (state) => state.markers,
    formatDistance: () => (distance) => {
      if (distance === null || distance === undefined) return ''
      if (distance < 1000) return `${Math.round(distance)}m`
      return `${(distance / 1000).toFixed(1)}km`
    }
  },

  actions: {
    setCurrentLocation(location) {
      this.currentLocation = location
      this.center = { latitude: location.latitude, longitude: location.longitude }
      this.isLocated = true
      this.permissionStage = 'granted'
    },

    setCenter(lat, lng) {
      this.center = { latitude: lat, longitude: lng }
    },

    setZoomLevel(level) {
      this.zoomLevel = level
    },

    setSelectedMarker(marker) {
      this.selectedMarker = marker
    },

    clearSelectedMarker() {
      this.selectedMarker = null
    },

    setSearchRadius(radius) {
      this.searchRadius = radius
    },

    setStatusFilter(status) {
      this.statusFilter = status
      this.applyRestaurantFilter()
    },

    setViewMode(mode) {
      if (mode === 'list' || mode === 'map') this.viewMode = mode
    },

    setSdkStage(stage, errorCode = null) {
      this.sdkStage = stage
      this.errorCode = errorCode
      if (errorCode) this.viewMode = 'list'
    },

    applyRestaurantFilter() {
      const filtered = this.statusFilter === null
        ? this.allRestaurants
        : this.allRestaurants.filter(item => item.status === this.statusFilter)
      this.nearbyRestaurants = filtered
      this.markers = this.buildMarkers(filtered)
    },

    async loadNearbyRestaurants() {
      if (!this.currentLocation) return false

      const requestId = ++this.activeListRequestId
      const startedAt = performance.now()
      this.isLoading = true
      this.listStatus = this.nearbyRestaurants.length ? 'success' : 'loading'
      this.error = null
      this.errorCode = null

      try {
        const params = {
          latitude: this.currentLocation.latitude,
          longitude: this.currentLocation.longitude,
          radiusMeters: this.searchRadius,
          ...(this.statusFilter === null ? {} : { status: this.statusFilter })
        }
        const response = await mapApi.getNearbyRestaurants(params)
        if (requestId !== this.activeListRequestId) return false
        this.allRestaurants = Array.isArray(response?.data) ? response.data : []
        this.applyRestaurantFilter()
        this.listStatus = this.nearbyRestaurants.length ? 'success' : 'empty'
        logUiEvent('map.list.loaded', {
          mode: this.viewMode,
          sdkStage: this.sdkStage,
          permission: this.permissionStage,
          itemCount: this.nearbyRestaurants.length,
          durationMs: Math.round(performance.now() - startedAt),
          errorCode: null
        })
        return true
      } catch {
        if (requestId !== this.activeListRequestId) return false
        this.error = '附近地点加载失败，请重试'
        this.errorCode = 'NEARBY_REQUEST_FAILED'
        this.listStatus = this.nearbyRestaurants.length ? 'success' : 'error'
        logUiEvent('map.list.failed', {
          mode: this.viewMode,
          sdkStage: this.sdkStage,
          permission: this.permissionStage,
          itemCount: this.nearbyRestaurants.length,
          durationMs: Math.round(performance.now() - startedAt),
          errorCode: this.errorCode
        })
        return false
      } finally {
        if (requestId === this.activeListRequestId) this.isLoading = false
      }
    },

    async loadMapRestaurants() {
      const requestId = ++this.activeListRequestId
      const startedAt = performance.now()
      this.isLoading = true
      this.listStatus = this.nearbyRestaurants.length ? 'success' : 'loading'
      this.error = null
      this.errorCode = null

      try {
        const response = await mapApi.getMapRestaurants({})
        if (requestId !== this.activeListRequestId) return false
        this.allRestaurants = Array.isArray(response?.data) ? response.data : []
        this.applyRestaurantFilter()
        this.listStatus = this.nearbyRestaurants.length ? 'success' : 'empty'
        logUiEvent('map.list.loaded', {
          mode: this.viewMode,
          sdkStage: this.sdkStage,
          permission: this.permissionStage,
          itemCount: this.nearbyRestaurants.length,
          durationMs: Math.round(performance.now() - startedAt),
          errorCode: null
        })
        return true
      } catch {
        if (requestId !== this.activeListRequestId) return false
        this.error = '地点加载失败，请重试'
        this.errorCode = 'MAP_LIST_REQUEST_FAILED'
        this.listStatus = this.nearbyRestaurants.length ? 'success' : 'error'
        logUiEvent('map.list.failed', {
          mode: this.viewMode,
          sdkStage: this.sdkStage,
          permission: this.permissionStage,
          itemCount: this.nearbyRestaurants.length,
          durationMs: Math.round(performance.now() - startedAt),
          errorCode: this.errorCode
        })
        return false
      } finally {
        if (requestId === this.activeListRequestId) this.isLoading = false
      }
    },

    buildMarkers(restaurants) {
      return restaurants
        .filter(item => item.latitude !== null && item.latitude !== undefined
          && item.longitude !== null && item.longitude !== undefined)
        .map(item => ({ ...item, title: item.restaurantName }))
    },

    getCurrentPosition() {
      const startedAt = performance.now()
      this.permissionStage = 'requesting'
      if (!navigator.geolocation) {
        this.permissionStage = 'unsupported'
        this.errorCode = 'LOCATION_UNSUPPORTED'
        logUiEvent('map.location.failed', {
          mode: this.viewMode,
          sdkStage: this.sdkStage,
          permission: this.permissionStage,
          itemCount: this.nearbyRestaurants.length,
          durationMs: Math.round(performance.now() - startedAt),
          errorCode: this.errorCode
        })
        return Promise.reject(new Error('浏览器不支持地理定位'))
      }

      return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const location = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            }
            this.setCurrentLocation(location)
            logUiEvent('map.location.completed', {
              mode: this.viewMode,
              sdkStage: this.sdkStage,
              permission: this.permissionStage,
              itemCount: this.nearbyRestaurants.length,
              durationMs: Math.round(performance.now() - startedAt),
              errorCode: null
            })
            resolve(location)
          },
          (error) => {
            const normalized = locationError(error)
            this.permissionStage = normalized.code === 'LOCATION_DENIED' ? 'denied' : 'failed'
            this.errorCode = normalized.code
            this.viewMode = 'list'
            logUiEvent('map.location.failed', {
              mode: this.viewMode,
              sdkStage: this.sdkStage,
              permission: this.permissionStage,
              itemCount: this.nearbyRestaurants.length,
              durationMs: Math.round(performance.now() - startedAt),
              errorCode: normalized.code
            })
            reject(new Error(normalized.message))
          },
          { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
        )
      })
    },

    reset() {
      this.currentLocation = null
      this.center = { ...DEFAULT_CENTER }
      this.zoomLevel = 15
      this.markers = []
      this.selectedMarker = null
      this.allRestaurants = []
      this.nearbyRestaurants = []
      this.viewMode = 'list'
      this.listStatus = 'idle'
      this.sdkStage = 'idle'
      this.permissionStage = 'idle'
      this.isLoading = false
      this.isLocated = false
      this.error = null
      this.errorCode = null
      this.activeListRequestId += 1
    }
  }
})
