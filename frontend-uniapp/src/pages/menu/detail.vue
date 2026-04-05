<template>
  <view class="menu-detail-page">
    <!-- 封面图片 -->
    <view class="cover-section" v-if="menuDetail.photoUrls">
      <swiper class="cover-swiper" @change="onSwipeChange">
        <swiper-item v-for="(url, index) in photoList" :key="index">
          <image :src="url" mode="aspectFill" />
        </swiper-item>
      </swiper>
      <view class="swipe-indicator">{{ currentSwipe + 1 }} / {{ photoList.length }}</view>
    </view>

    <!-- 餐厅信息 -->
    <view class="info-section">
      <view class="restaurant-header">
        <text class="restaurant-name">{{ menuDetail.restaurantName }}</text>
        <view class="status-tag" :class="getStatusClass(menuDetail.status)">
          {{ getStatusText(menuDetail.status) }}
        </view>
      </view>

      <view class="info-row" v-if="menuDetail.location">
        <text>📍 {{ menuDetail.location }}</text>
      </view>
      <view class="info-row" v-if="menuDetail.price">
        <text>💰 {{ menuDetail.price }}</text>
      </view>
      <view class="info-row" v-if="menuDetail.rating">
        <text>⭐ {{ menuDetail.rating }}分</text>
      </view>
    </view>

    <!-- 推荐菜品 -->
    <view class="section" v-if="menuDetail.dishName">
      <view class="section-title">推荐菜品</view>
      <view class="section-content">{{ menuDetail.dishName }}</view>
    </view>

    <!-- 私密笔记 -->
    <view class="section" v-if="menuDetail.note">
      <view class="section-title">私密笔记</view>
      <view class="section-content">{{ menuDetail.note }}</view>
    </view>

    <!-- 操作按钮 -->
    <view class="action-section">
      <view class="action-btn" @click="handleLike">
        <text>❤️</text>
        <text>{{ menuDetail.likeCount || 0 }} 点赞</text>
      </view>
      <view class="action-btn" @click="handleFavorite">
        <text>{{ menuDetail.isFavorite ? '⭐' : '☆' }}</text>
        <text>{{ menuDetail.isFavorite ? '取消收藏' : '收藏' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { menuApi } from '@/api'

const menuDetail = ref({})
const photoList = ref([])
const currentSwipe = ref(0)

const getStatusText = (status) => {
  const map = { 0: '想去', 1: '去过', 2: '种草' }
  return map[status] || '想去'
}

const getStatusClass = (status) => {
  const map = { 0: 'primary', 1: 'success', 2: 'warning' }
  return map[status] || 'primary'
}

const loadDetail = async () => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const id = currentPage.options?.id

  uni.showLoading({ title: '加载中...' })
  try {
    const res = await menuApi.getMenuDetail(id)
    menuDetail.value = res.data
    if (res.data.photoUrls) {
      photoList.value = res.data.photoUrls.split(',').filter(Boolean)
    }
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const onSwipeChange = (e) => {
  currentSwipe.value = e.detail.current
}

const handleLike = async () => {
  try {
    await menuApi.likeMenu(menuDetail.value.id)
    uni.showToast({ title: '点赞成功', icon: 'success' })
    loadDetail()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

const handleFavorite = async () => {
  try {
    await menuApi.favoriteMenu(menuDetail.value.id)
    uni.showToast({ title: menuDetail.value.isFavorite ? '取消收藏' : '收藏成功', icon: 'success' })
    loadDetail()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<style lang="scss" scoped>
.menu-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 40rpx;
}

.cover-section {
  position: relative;
  height: 500rpx;

  .cover-swiper {
    width: 100%;
    height: 100%;

    image {
      width: 100%;
      height: 100%;
    }
  }

  .swipe-indicator {
    position: absolute;
    right: 30rpx;
    bottom: 30rpx;
    background: rgba(0, 0, 0, 0.5);
    color: #fff;
    padding: 8rpx 24rpx;
    border-radius: 24rpx;
    font-size: 24rpx;
  }
}

.info-section {
  background: #fff;
  margin: 24rpx;
  padding: 30rpx;
  border-radius: 24rpx;

  .restaurant-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20rpx;

    .restaurant-name {
      font-size: 36rpx;
      font-weight: 600;
      color: #333;
    }

    .status-tag {
      padding: 8rpx 20rpx;
      border-radius: 8rpx;
      font-size: 24rpx;

      &.primary { background: #fff0f3; color: #ff4757; }
      &.success { background: #f0fff4; color: #56ab2f; }
      &.warning { background: #fffaf0; color: #ff9500; }
    }
  }

  .info-row {
    font-size: 28rpx;
    color: #666;
    margin-top: 16rpx;
  }
}

.section {
  background: #fff;
  margin: 0 24rpx 24rpx;
  padding: 30rpx;
  border-radius: 24rpx;

  .section-title {
    font-size: 28rpx;
    color: #999;
    margin-bottom: 16rpx;
  }

  .section-content {
    font-size: 28rpx;
    color: #333;
    line-height: 1.6;
  }
}

.action-section {
  display: flex;
  gap: 30rpx;
  padding: 0 24rpx;

  .action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10rpx;
    height: 96rpx;
    background: #fff;
    border-radius: 48rpx;
    font-size: 28rpx;
    color: #666;
  }
}
</style>
