/**
 * 地图 Store
 */
import { defineStore } from 'pinia'
import { mapApi } from '@/api'

export const useMapStore = defineStore('map', {
  state: () => ({
    // 当前用户位置
    currentLocation: null,
    // 地图中心点
    center: {
      latitude: 39.9042, // 默认北京
      longitude: 116.4074
    },
    // 缩放级别
    zoomLevel: 15,
    // 地图标记列表
    markers: [],
    // 选中的标记
    selectedMarker: null,
    // 附近的餐厅列表
    nearbyRestaurants: [],
    // 搜索半径（米）
    searchRadius: 5000,
    // 状态筛选
    statusFilter: null,
    // 加载状态
    isLoading: false,
    // 是否已定位
    isLocated: false,
    // 错误信息
    error: null
  }),

  getters: {
    // 是否可以选择位置
    canSelectLocation: (state) => !!state.currentLocation,

    // 获取筛选后的标记
    filteredMarkers: (state) => {
      if (state.statusFilter === null) {
        return state.markers
      }
      return state.markers.filter(m => m.status === state.statusFilter)
    },

    // 获取距离格式化
    formatDistance: () => (distance) => {
      if (!distance) return ''
      if (distance < 1000) {
        return `${Math.round(distance)}m`
      }
      return `${(distance / 1000).toFixed(1)}km`
    }
  },

  actions: {
    // 设置当前位置
    setCurrentLocation(location) {
      this.currentLocation = location
      this.center = {
        latitude: location.latitude,
        longitude: location.longitude
      }
      this.isLocated = true
    },

    // 设置地图中心
    setCenter(lat, lng) {
      this.center = { latitude: lat, longitude: lng }
    },

    // 设置缩放级别
    setZoomLevel(level) {
      this.zoomLevel = level
    },

    // 设置选中的标记
    setSelectedMarker(marker) {
      this.selectedMarker = marker
    },

    // 清除选中标记
    clearSelectedMarker() {
      this.selectedMarker = null
    },

    // 设置搜索半径
    setSearchRadius(radius) {
      this.searchRadius = radius
    },

    // 设置状态筛选
    setStatusFilter(status) {
      this.statusFilter = status
    },

    // 加载附近的餐厅
    async loadNearbyRestaurants() {
      if (!this.currentLocation) {
        this.error = '请先获取位置'
        return
      }

      this.isLoading = true
      this.error = null

      try {
        const res = await mapApi.getNearbyRestaurants({
          latitude: this.currentLocation.latitude,
          longitude: this.currentLocation.longitude,
          radiusMeters: this.searchRadius,
          status: this.statusFilter
        })

        this.nearbyRestaurants = res.data || []
        this.markers = this.buildMarkers(this.nearbyRestaurants)
      } catch (error) {
        this.error = '加载附近的餐厅失败'
        console.error('加载附近的餐厅失败', error)
      } finally {
        this.isLoading = false
      }
    },

    // 加载地图视图的餐厅数据
    async loadMapRestaurants() {
      this.isLoading = true
      this.error = null

      try {
        const res = await mapApi.getMapRestaurants({
          centerLat: this.center.latitude,
          centerLng: this.center.longitude,
          zoomLevel: this.zoomLevel
        })

        this.nearbyRestaurants = res.data || []
        this.markers = this.buildMarkers(this.nearbyRestaurants)
      } catch (error) {
        this.error = '加载地图数据失败'
        console.error('加载地图数据失败', error)
      } finally {
        this.isLoading = false
      }
    },

    // 构建地图标记
    buildMarkers(restaurants) {
      return restaurants
        .filter(r => r.latitude && r.longitude)
        .map(r => ({
          id: r.id,
          latitude: r.latitude,
          longitude: r.longitude,
          title: r.restaurantName,
          snippet: r.dishName || r.location || '',
          status: r.status,
          statusName: r.statusName,
          distance: r.distance,
          rating: r.rating,
          price: r.price,
          coverImage: r.photoUrls ? r.photoUrls.split(',')[0] : null
        }))
    },

    // 获取当前位置
    getCurrentPosition() {
      return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
          this.error = '浏览器不支持地理定位'
          reject(new Error('浏览器不支持地理定位'))
          return
        }

        navigator.geolocation.getCurrentPosition(
          (position) => {
            const location = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy
            }
            this.setCurrentLocation(location)
            resolve(location)
          },
          (error) => {
            let message = '获取位置失败'
            switch (error.code) {
              case error.PERMISSION_DENIED:
                message = '定位权限被拒绝'
                break
              case error.POSITION_UNAVAILABLE:
                message = '位置信息不可用'
                break
              case error.TIMEOUT:
                message = '定位请求超时'
                break
            }
            this.error = message
            reject(new Error(message))
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
          }
        )
      })
    },

    // 重置状态
    reset() {
      this.currentLocation = null
      this.center = { latitude: 39.9042, longitude: 116.4074 }
      this.zoomLevel = 15
      this.markers = []
      this.selectedMarker = null
      this.nearbyRestaurants = []
      this.isLoading = false
      this.isLocated = false
      this.error = null
    }
  }
})