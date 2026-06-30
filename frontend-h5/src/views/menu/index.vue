<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import { menuApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

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

<template>
  <div class="menu-page">
    <!-- 顶部标题 -->
    <header class="menu-topbar">
      <h1 class="page-title">
        私密菜单
      </h1>
    </header>

    <!-- 标签筛选 -->
    <van-tabs
      v-model:active="activeTab"
      sticky
      offset-top="52"
      class="menu-tabs"
      @change="onTabChange"
    >
      <van-tab
        title="想去"
        name="wantToGo"
      />
      <van-tab
        title="去过"
        name="beenTo"
      />
      <van-tab
        title="种草"
        name="recommended"
      />
      <van-tab
        title="收藏"
        name="favorite"
      />
    </van-tabs>

    <div class="menu-body">
      <!-- 统计卡片 -->
      <div class="stats-card">
        <div class="stat-item">
          <span class="label">想去</span>
          <span class="value">{{ stats.wantToGoCount || 0 }}</span>
        </div>
        <i class="stat-divider" />
        <div class="stat-item">
          <span class="label">去过</span>
          <span class="value">{{ stats.beenToCount || 0 }}</span>
        </div>
        <i class="stat-divider" />
        <div class="stat-item">
          <span class="label">收藏</span>
          <span class="value">{{ stats.recommendedCount || 0 }}</span>
        </div>
      </div>

      <!-- 下拉刷新 + 无限滚动列表 -->
      <van-pull-refresh
        v-model:loading="refreshing"
        @refresh="onRefresh"
      >
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
            <div
              v-for="n in 3"
              :key="n"
              class="menu-card skeleton"
            >
              <div class="cover sk-block" />
              <div class="body">
                <div class="sk-line sk-title" />
                <div class="sk-line sk-sub" />
              </div>
            </div>
          </template>

          <!-- 菜单列表 -->
          <div
            v-for="item in menuList"
            :key="item.id"
            class="menu-card"
            @click="$router.push(`/menu/${item.id}`)"
          >
            <div class="cover">
              <img
                v-if="item.photoUrl"
                v-lazy="item.photoUrl"
                :alt="item.restaurantName"
              >
              <van-icon
                v-else
                name="shop-o"
                size="40"
                color="#d6c1c5"
              />
              <span class="status-pill">{{ getStatusText(item.status) }}</span>
            </div>
            <div class="body">
              <div class="title-row">
                <h3 class="name">
                  {{ item.restaurantName }}
                </h3>
                <span
                  v-if="item.rating"
                  class="rating"
                >
                  <van-icon
                    name="star"
                    size="13"
                  />{{ item.rating }}
                </span>
              </div>
              <div
                v-if="item.dishName"
                class="dish"
              >
                <van-icon
                  name="fire-o"
                  size="13"
                /> 推荐：{{ item.dishName }}
              </div>
              <div class="footer">
                <div class="meta">
                  <span v-if="item.price"><van-icon
                    name="coupon-o"
                    size="13"
                  /> {{ item.price }}</span>
                  <span v-if="item.location"><van-icon
                    name="location-o"
                    size="13"
                  /> {{ item.location }}</span>
                </div>
                <div class="actions">
                  <van-icon
                    name="like-o"
                    size="18"
                    @click.stop="handleLike(item)"
                  />
                  <van-icon
                    name="star-o"
                    size="18"
                    @click.stop="handleFavorite(item)"
                  />
                </div>
              </div>
            </div>
          </div>

          <van-empty
            v-if="menuList.length === 0 && !loading"
            description="暂无餐厅记录"
          >
            <van-button
              type="primary"
              round
              size="small"
              @click="$router.push('/menu/add')"
            >
              添加餐厅
            </van-button>
          </van-empty>
        </van-list>
      </van-pull-refresh>
    </div>

    <!-- 添加按钮 -->
    <button
      class="fab"
      @click="$router.push('/menu/add')"
    >
      <van-icon
        name="plus"
        size="26"
      />
    </button>

    <app-tabbar />
  </div>
</template>

<style lang="scss" scoped>
.menu-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 96px;
}

.menu-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  @include glass(0.7);

  .page-title {
    font-size: $fs-title;
    font-weight: $fw-semibold;
    color: $color-on-surface;
  }
}

.menu-tabs {
  :deep(.van-tabs__wrap) {
    background: $color-background;
  }
}

.menu-body {
  padding: $space-4 $page-padding 0;
}

.stats-card {
  display: flex;
  align-items: center;
  @include card($radius-lg, $space-4);
  margin-bottom: $space-5;

  .stat-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-1;

    .value { font-size: $fs-headline; font-weight: $fw-bold; color: $color-primary; line-height: 1; }
    .label { font-size: $fs-caption; color: $color-on-surface-variant; }
  }

  .stat-divider { width: 1px; height: 28px; background: $color-surface-variant; }
}

.menu-card {
  background: $color-surface-lowest;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;
  overflow: hidden;
  margin-bottom: $space-4;
  transition: transform $transition-base;

  &:active { transform: scale(0.98); }

  .cover {
    position: relative;
    height: 168px;
    background: $color-surface-low;
    display: flex;
    align-items: center;
    justify-content: center;

    img { width: 100%; height: 100%; object-fit: cover; }

    .status-pill {
      position: absolute;
      top: $space-3;
      right: $space-3;
      padding: 3px 12px;
      font-size: $fs-caption;
      color: $color-primary;
      @include glass(0.82);
      border-radius: $radius-pill;
    }
  }

  .body { padding: $space-4; }

  .title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $space-2;

    .name {
      font-size: $fs-title;
      font-weight: $fw-semibold;
      color: $color-on-surface;
      @include ellipsis;
    }

    .rating {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 2px;
      font-size: $fs-label;
      font-weight: $fw-semibold;
      color: $color-secondary;
      margin-left: $space-2;
    }
  }

  .dish {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: $fs-label;
    color: $color-on-surface-variant;
    margin-bottom: $space-3;
    @include ellipsis;
    .van-icon { color: $color-primary; }
  }

  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .meta {
      display: flex;
      gap: $space-4;

      span {
        display: flex;
        align-items: center;
        gap: 3px;
        font-size: $fs-caption;
        color: $color-on-surface-variant;
      }
    }

    .actions {
      display: flex;
      gap: $space-4;
      color: $color-primary;
    }
  }
}

// 骨架屏
.skeleton {
  pointer-events: none;

  .sk-block,
  .sk-line {
    background: linear-gradient(90deg, $color-surface-high 25%, $color-surface-low 50%, $color-surface-high 75%);
    background-size: 200% 100%;
    animation: sk-loading 1.5s infinite;
  }

  .sk-block { height: 168px; }
  .body { padding: $space-4; }
  .sk-line { height: 14px; border-radius: 4px; }
  .sk-title { width: 55%; margin-bottom: $space-2; }
  .sk-sub { width: 75%; height: 12px; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.fab {
  position: fixed;
  right: $page-padding;
  bottom: 84px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: $color-primary;
  color: $color-on-primary;
  box-shadow: $shadow-float;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 30;
  transition: transform $transition-base;

  &:active { transform: scale(0.92); }
}
</style>
