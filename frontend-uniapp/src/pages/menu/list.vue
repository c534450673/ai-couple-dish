<template>
  <view class="menu-page">
    <!-- 标签筛选 -->
    <view class="tabs">
      <view
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-item"
        :class="{ active: activeTab === tab.value }"
        @click="onTabChange(tab.value)"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- 统计卡片 -->
    <view class="stats-card">
      <view class="stat-item">
        <text class="value">{{ stats.wantToGoCount || 0 }}</text>
        <text class="label">想去</text>
      </view>
      <view class="stat-divider"></view>
      <view class="stat-item">
        <text class="value">{{ stats.beenToCount || 0 }}</text>
        <text class="label">去过</text>
      </view>
      <view class="stat-divider"></view>
      <view class="stat-item">
        <text class="value">{{ stats.recommendedCount || 0 }}</text>
        <text class="label">种草</text>
      </view>
    </view>

    <!-- 菜单列表 -->
    <scroll-view scroll-y class="menu-list">
      <view v-for="item in menuList" :key="item.id" class="menu-item" @click="goDetail(item.id)">
        <image v-if="item.photoUrl" :src="item.photoUrl" class="menu-cover" mode="aspectFill" />
        <view v-else class="menu-cover empty">🍽️</view>
        <view class="menu-content">
          <view class="menu-header">
            <text class="menu-name">{{ item.restaurantName }}</text>
            <view class="tag" :class="getStatusClass(item.status)">{{ getStatusText(item.status) }}</view>
          </view>
          <view class="menu-location" v-if="item.location">
            <text>📍 {{ item.location }}</text>
          </view>
          <view class="menu-dishes" v-if="item.dishName">{{ item.dishName }}</view>
          <view class="menu-footer">
            <view class="menu-meta">
              <text v-if="item.price">💰 {{ item.price }}</text>
              <text v-if="item.rating">⭐ {{ item.rating }}分</text>
            </view>
            <view class="menu-actions">
              <text @click.stop="handleLike(item)">❤️</text>
              <text @click.stop="handleFavorite(item)">⭐</text>
            </view>
          </view>
        </view>
      </view>

      <view v-if="menuList.length === 0" class="empty-state">
        <text>暂无餐厅记录</text>
        <view class="add-btn" @click="goAdd">添加餐厅</view>
      </view>
    </scroll-view>

    <!-- 添加按钮 -->
    <view class="add-fab" @click="goAdd">
      <text>+</text>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { menuApi } from '@/api'

const activeTab = ref('wantToGo')
const menuList = ref([])
const stats = ref({})

const tabs = [
  { label: '想去', value: 'wantToGo' },
  { label: '去过', value: 'beenTo' },
  { label: '种草', value: 'recommended' },
  { label: '收藏', value: 'favorite' }
]

const getStatusText = (status) => {
  const map = { 0: '想去', 1: '去过', 2: '种草' }
  return map[status] || '想去'
}

const getStatusClass = (status) => {
  const map = { 0: 'primary', 1: 'success', 2: 'warning' }
  return map[status] || 'primary'
}

const loadMenuList = async () => {
  uni.showLoading({ title: '加载中...' })
  try {
    const params = activeTab.value === 'favorite'
      ? { isFavorite: 1 }
      : activeTab.value !== 'wantToGo'
        ? { status: activeTab.value === 'beenTo' ? 1 : 2 }
        : { status: 0 }

    const res = await menuApi.getMenuList(params)
    menuList.value = res.data?.list || []
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const loadStats = async () => {
  try {
    const res = await menuApi.getMenuStats()
    stats.value = res.data || {}
  } catch (error) {
    console.error('加载统计失败', error)
  }
}

const onTabChange = (value) => {
  activeTab.value = value
  loadMenuList()
}

const goDetail = (id) => uni.navigateTo({ url: `/pages/menu/detail?id=${id}` })
const goAdd = () => uni.navigateTo({ url: '/pages/menu/add' })

const handleLike = async (item) => {
  try {
    await menuApi.likeMenu(item.id)
    uni.showToast({ title: '点赞成功', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

const handleFavorite = async (item) => {
  try {
    await menuApi.favoriteMenu(item.id)
    uni.showToast({ title: item.isFavorite ? '取消收藏' : '收藏成功', icon: 'success' })
    loadMenuList()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

onMounted(() => {
  loadMenuList()
  loadStats()
})
</script>

<style lang="scss" scoped>
.menu-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 120rpx;
}

.tabs {
  display: flex;
  background: #fff;
  padding: 20rpx 0;

  .tab-item {
    flex: 1;
    text-align: center;
    font-size: 28rpx;
    color: #666;
    padding: 16rpx 0;
    position: relative;

    &.active {
      color: #ff4757;
      font-weight: 600;

      &::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 40rpx;
        height: 6rpx;
        background: #ff4757;
        border-radius: 3rpx;
      }
    }
  }
}

.stats-card {
  display: flex;
  margin: 24rpx;
  padding: 32rpx;
  background: #fff;
  border-radius: 24rpx;

  .stat-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;

    .value {
      font-size: 40rpx;
      font-weight: 700;
      color: #ff4757;
    }

    .label {
      font-size: 24rpx;
      color: #999;
      margin-top: 8rpx;
    }
  }

  .stat-divider {
    width: 2rpx;
    height: 60rpx;
    background: #eee;
  }
}

.menu-list {
  height: calc(100vh - 400rpx);
  padding: 0 24rpx;

  .menu-item {
    display: flex;
    background: #fff;
    border-radius: 24rpx;
    padding: 24rpx;
    margin-bottom: 24rpx;

    .menu-cover {
      width: 200rpx;
      height: 200rpx;
      border-radius: 16rpx;
      margin-right: 24rpx;

      &.empty {
        background: #f5f5f5;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 60rpx;
      }
    }

    .menu-content {
      flex: 1;
      display: flex;
      flex-direction: column;

      .menu-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .menu-name {
          font-size: 32rpx;
          font-weight: 600;
          color: #333;
        }

        .tag {
          padding: 6rpx 16rpx;
          border-radius: 8rpx;
          font-size: 22rpx;

          &.primary { background: #fff0f3; color: #ff4757; }
          &.success { background: #f0fff4; color: #56ab2f; }
          &.warning { background: #fffaf0; color: #ff9500; }
        }
      }

      .menu-location {
        font-size: 24rpx;
        color: #999;
        margin-top: 8rpx;
      }

      .menu-dishes {
        font-size: 26rpx;
        color: #666;
        margin-top: 8rpx;
      }

      .menu-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: auto;

        .menu-meta {
          display: flex;
          gap: 20rpx;

          text {
            font-size: 24rpx;
            color: #999;
          }
        }

        .menu-actions {
          display: flex;
          gap: 20rpx;

          text {
            font-size: 36rpx;
          }
        }
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 120rpx 0;

    text {
      font-size: 28rpx;
      color: #999;
    }

    .add-btn {
      margin-top: 30rpx;
      padding: 20rpx 60rpx;
      background: linear-gradient(135deg, #ff6b9d, #ff4757);
      color: #fff;
      border-radius: 50rpx;
      font-size: 28rpx;
    }
  }
}

.add-fab {
  position: fixed;
  right: 40rpx;
  bottom: 200rpx;
  width: 100rpx;
  height: 100rpx;
  background: linear-gradient(135deg, #ff6b9d, #ff4757);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  color: #fff;
  box-shadow: 0 10rpx 30rpx rgba(255, 71, 87, 0.4);
}
</style>
