<template>
  <div class="menu-page">
    <!-- 标签筛选 -->
    <van-tabs v-model:active="activeTab" sticky @change="onTabChange">
      <van-tab title="想去" name="wantToGo"></van-tab>
      <van-tab title="去过" name="beenTo"></van-tab>
      <van-tab title="种草" name="recommended"></van-tab>
      <van-tab title="收藏" name="favorite"></van-tab>
    </van-tabs>

    <!-- 统计卡片 -->
    <div class="stats-card">
      <div class="stat-item">
        <span class="value">{{ stats.wantToGoCount || 0 }}</span>
        <span class="label">想去</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="value">{{ stats.beenToCount || 0 }}</span>
        <span class="label">去过</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="value">{{ stats.recommendedCount || 0 }}</span>
        <span class="label">种草</span>
      </div>
    </div>

    <!-- 下拉刷新 + 无限滚动列表 -->
    <van-pull-refresh v-model:loading="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        :error="error"
        error-text="加载失败，点击重新加载"
        @load="onLoad"
      >
        <!-- 骨架屏 -->
        <template v-if="isSkeleton && menuList.length === 0">
          <div v-for="n in 3" :key="n" class="menu-item card skeleton-item">
            <div class="menu-cover skeleton-cover"></div>
            <div class="menu-content">
              <div class="skeleton-title"></div>
              <div class="skeleton-location"></div>
              <div class="skeleton-dishes"></div>
            </div>
          </div>
        </template>

        <!-- 菜单列表 -->
        <div
          v-for="item in menuList"
          :key="item.id"
          class="menu-item card"
          @click="$router.push(`/menu/${item.id}`)"
        >
          <div class="menu-cover">
            <img
              v-if="item.photoUrl"
              v-lazy="item.photoUrl"
              :alt="item.restaurantName"
              loading="lazy"
            />
            <van-icon v-else name="shop-o" size="40" color="#ccc" />
          </div>
          <div class="menu-content">
            <div class="menu-header">
              <h3 class="menu-name">{{ item.restaurantName }}</h3>
              <van-tag :type="getStatusType(item.status)" size="small">
                {{ getStatusText(item.status) }}
              </van-tag>
            </div>
            <div class="menu-location" v-if="item.location">
              <van-icon name="location-o" size="12" />
              {{ item.location }}
            </div>
            <div class="menu-dishes" v-if="item.dishName">
              {{ item.dishName }}
            </div>
            <div class="menu-footer">
              <div class="menu-meta">
                <span v-if="item.price"><van-icon name="coupon-o" size="12" /> {{ item.price }}</span>
                <span v-if="item.rating"><van-icon name="star" size="12" color="#ffd21e" /> {{ item.rating }}分</span>
              </div>
              <div class="menu-actions">
                <van-icon name="like-o" size="18" @click.stop="handleLike(item)" />
                <van-icon name="star-o" size="18" @click.stop="handleFavorite(item)" />
              </div>
            </div>
          </div>
        </div>

        <van-empty v-if="menuList.length === 0 && !loading" description="暂无餐厅记录">
          <template #image>
            <van-icon name="shop-o" size="40" color="#ccc" />
          </template>
          <van-button type="primary" round size="small" @click="$router.push('/menu/add')">
            添加餐厅
          </van-button>
        </van-empty>
      </van-list>
    </van-pull-refresh>

    <!-- 添加按钮 -->
    <van-button class="add-btn" type="primary" size="large" round @click="$router.push('/menu/add')">
      <van-icon name="plus" />
    </van-button>

    <!-- 底部导航 -->
    <van-tabbar route>
      <van-tabbar-item to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/menu" icon="shop-o">餐厅</van-tabbar-item>
      <van-tabbar-item to="/feed" icon="gift-o">投喂</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import { menuApi } from '@/api'

const route = useRoute()
const activeTab = ref(route.query.type || 'wantToGo')
const menuList = ref([])
const stats = ref({})
const loading = ref(false)
const refreshing = ref(false)
const finished = ref(false)
const error = ref(false)
const isSkeleton = ref(true)

const PAGE_SIZE = 10
let currentPage = 1

const getStatusType = (status) => {
  const map = { 0: 'primary', 1: 'success', 2: 'warning' }
  return map[status] || 'primary'
}

const getStatusText = (status) => {
  const map = { 0: '想去', 1: '去过', 2: '种草' }
  return map[status] || '想去'
}

const getParams = () => {
  if (activeTab.value === 'favorite') {
    return { isFavorite: 1, page: currentPage, pageSize: PAGE_SIZE }
  }
  const statusMap = { wantToGo: 0, beenTo: 1, recommended: 2 }
  return { status: statusMap[activeTab.value] ?? 0, page: currentPage, pageSize: PAGE_SIZE }
}

const loadMenuList = async (isRefresh = false) => {
  if (loading.value && !isRefresh && !refreshing.value) return

  try {
    const params = getParams()
    const res = await menuApi.getMenuList(params)
    const list = res.data?.list || []
    const total = res.data?.total || 0

    if (isRefresh || refreshing.value) {
      menuList.value = list
      currentPage = 1
    } else {
      menuList.value.push(...list)
    }

    finished.value = menuList.value.length >= total
    error.value = false
  } catch (err) {
    error.value = true
    if (!isRefresh && !refreshing.value) {
      showToast('加载失败')
    }
  } finally {
    loading.value = false
    refreshing.value = false
    isSkeleton.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await menuApi.getMenuStats()
    stats.value = res.data || {}
  } catch (err) {
    console.error('加载统计失败', err)
  }
}

const onLoad = () => {
  currentPage++
  loadMenuList()
}

const onRefresh = () => {
  finished.value = false
  refreshing.value = true
  isSkeleton.value = true
  currentPage = 1
  loadMenuList(true)
}

const onTabChange = () => {
  menuList.value = []
  finished.value = false
  error.value = false
  isSkeleton.value = true
  currentPage = 1
  loading.value = false
  loadMenuList()
}

const handleLike = async (item) => {
  try {
    await menuApi.likeMenu(item.id)
    showToast('点赞成功')
  } catch (err) {
    showToast('操作失败')
  }
}

const handleFavorite = async (item) => {
  try {
    await menuApi.favoriteMenu(item.id)
    showToast(item.isFavorite ? '取消收藏' : '收藏成功')
    onRefresh()
  } catch (err) {
    showToast('操作失败')
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
  padding-bottom: 70px;
}

.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  margin: 12px 16px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;

    .value {
      font-size: 20px;
      font-weight: 700;
      color: #ff4757;
    }

    .label {
      font-size: 12px;
      color: #999;
      margin-top: 4px;
    }
  }

  .stat-divider {
    width: 1px;
    height: 30px;
    background: #eee;
  }
}

.menu-list {
  padding: 0 16px;
}

.menu-item {
  display: flex;
  padding: 12px;

  .menu-cover {
    width: 100px;
    height: 100px;
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

  .menu-content {
    flex: 1;
    display: flex;
    flex-direction: column;

    .menu-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;

      .menu-name {
        font-size: 16px;
        font-weight: 600;
        color: #333;
      }
    }

    .menu-location {
      font-size: 12px;
      color: #999;
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 4px;
    }

    .menu-dishes {
      font-size: 13px;
      color: #666;
      margin-bottom: 8px;
    }

    .menu-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: auto;

      .menu-meta {
        display: flex;
        gap: 12px;

        span {
          font-size: 12px;
          color: #999;
          display: flex;
          align-items: center;
          gap: 2px;
        }
      }

      .menu-actions {
        display: flex;
        gap: 12px;
        color: #999;
      }
    }
  }
}

// 骨架屏样式
.skeleton-item {
  pointer-events: none;

  .skeleton-cover {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
  }

  .menu-content {
    .skeleton-title {
      width: 60%;
      height: 16px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .skeleton-location {
      width: 80%;
      height: 12px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .skeleton-dishes {
      width: 40%;
      height: 12px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }
  }
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.add-btn {
  position: fixed;
  right: 20px;
  bottom: 80px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(255, 71, 87, 0.4);

  :deep(.van-icon) {
    font-size: 24px;
  }
}
</style>
