<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { menuApi } from '@/api'

const route = useRoute()
const router = useRouter()

const menuDetail = ref({})
const photoList = ref([])
const currentSwipe = ref(0)
const showActionSheet = ref(false)

const actions = [
  { name: '编辑', action: 'edit' },
  { name: '删除', action: 'delete', color: '#ee0a24' }
]

const getStatusType = (status) => {
  const map = { 0: 'primary', 1: 'success', 2: 'warning' }
  return map[status] || 'primary'
}

const getStatusText = (status) => {
  const map = { 0: '想去', 1: '去过', 2: '种草' }
  return map[status] || '想去'
}

const loadDetail = async () => {
  showLoadingToast({ message: '加载中...', forbidClick: true })
  try {
    const res = await menuApi.getMenuDetail(route.params.id)
    menuDetail.value = res.data
    if (res.data.photoUrls) {
      photoList.value = (typeof res.data.photoUrls === 'string' ? res.data.photoUrls.split(',') : res.data.photoUrls).filter(Boolean)
    }
  } catch (error) {
    showToast('加载失败')
  } finally {
    closeToast()
  }
}

const onSwipeChange = (index) => {
  currentSwipe.value = index
}

const showActions = () => {
  showActionSheet.value = true
}

const onActionSelect = (action) => {
  showActionSheet.value = false
  if (action.action === 'edit') {
    router.push(`/menu/edit/${route.params.id}`)
  } else if (action.action === 'delete') {
    handleDelete()
  }
}

const handleLike = async () => {
  try {
    await menuApi.likeMenu(route.params.id)
    showToast('点赞成功')
    loadDetail()
  } catch (error) {
    showToast('操作失败')
  }
}

const handleFavorite = async () => {
  try {
    await menuApi.favoriteMenu(route.params.id)
    showToast(menuDetail.value.isFavorite ? '取消收藏' : '收藏成功')
    loadDetail()
  } catch (error) {
    showToast('操作失败')
  }
}

const handleDelete = async () => {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这个餐厅吗？'
    })
    await menuApi.deleteMenu(route.params.id)
    showToast('删除成功')
    router.back()
  } catch (error) {
    if (error !== 'cancel') {
      showToast('删除失败')
    }
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<template>
  <div class="menu-detail-page">
    <!-- 封面 + 浮动按钮 -->
    <div class="cover">
      <van-swipe
        v-if="photoList.length"
        @change="onSwipeChange"
      >
        <van-swipe-item
          v-for="(url, index) in photoList"
          :key="index"
        >
          <img
            :src="url"
            alt="cover"
          >
        </van-swipe-item>
        <template #indicator>
          <div class="swipe-indicator">
            {{ currentSwipe + 1 }} / {{ photoList.length }}
          </div>
        </template>
      </van-swipe>
      <div
        v-else
        class="cover-empty"
      >
        <van-icon
          name="shop-o"
          size="48"
          color="#d6c1c5"
        />
      </div>

      <button
        class="float-btn back"
        @click="$router.back()"
      >
        <van-icon
          name="arrow-left"
          size="20"
        />
      </button>
      <button
        class="float-btn more"
        @click="showActions"
      >
        <van-icon
          name="ellipsis"
          size="20"
        />
      </button>
    </div>

    <div
      v-if="menuDetail.id"
      class="detail-body"
    >
      <!-- 餐厅信息 -->
      <div class="info card">
        <div class="head">
          <h2 class="name">
            {{ menuDetail.restaurantName }}
          </h2>
          <span
            v-if="menuDetail.rating"
            class="rating"
          ><van-icon
            name="star"
            size="14"
          /> {{ menuDetail.rating }}</span>
        </div>
        <div class="tags">
          <van-tag
            :type="getStatusType(menuDetail.status)"
            round
          >
            {{ getStatusText(menuDetail.status) }}
          </van-tag>
        </div>
        <div
          v-if="menuDetail.price"
          class="info-row"
        >
          <van-icon name="coupon-o" /> <span>{{ menuDetail.price }}</span>
        </div>
        <div
          v-if="menuDetail.location"
          class="info-row"
        >
          <van-icon name="location-o" /> <span>{{ menuDetail.location }}</span>
        </div>
      </div>

      <!-- 推荐菜品 -->
      <div
        v-if="menuDetail.dishName"
        class="card section"
      >
        <div class="section-title">
          推荐菜品
        </div>
        <div class="section-content">
          {{ menuDetail.dishName }}
        </div>
      </div>

      <!-- 私密笔记 -->
      <div
        v-if="menuDetail.note"
        class="card note-card"
      >
        <div class="section-title">
          <van-icon
            name="like"
            size="14"
          /> 我们的回忆
        </div>
        <div class="section-content">
          {{ menuDetail.note }}
        </div>
      </div>
    </div>

    <van-loading
      v-else
      class="loading"
    />

    <!-- 底部操作栏 -->
    <div
      v-if="menuDetail.id"
      class="action-bar"
    >
      <button
        class="act"
        @click="handleLike"
      >
        <van-icon
          name="like-o"
          size="20"
        />
        <span>{{ menuDetail.likeCount || 0 }} 点赞</span>
      </button>
      <button
        class="act primary"
        @click="handleFavorite"
      >
        <van-icon
          name="star-o"
          size="20"
        />
        <span>{{ menuDetail.isFavorite ? '取消收藏' : '收藏' }}</span>
      </button>
    </div>

    <!-- 操作菜单 -->
    <van-action-sheet
      v-model:show="showActionSheet"
      :actions="actions"
      cancel-text="取消"
      @select="onActionSelect"
    />
  </div>
</template>

<style lang="scss" scoped>
.menu-detail-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 88px;
}

.cover {
  position: relative;

  :deep(.van-swipe),
  img,
  .cover-empty {
    width: 100%;
    height: 260px;
  }

  img { object-fit: cover; }

  .cover-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    background: $color-surface-low;
  }

  .swipe-indicator {
    position: absolute;
    right: $space-4;
    bottom: $space-4;
    @include glass(0.6);
    color: $color-on-surface;
    padding: 3px 12px;
    border-radius: $radius-pill;
    font-size: $fs-caption;
  }

  .float-btn {
    position: absolute;
    top: 16px;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: none;
    @include glass(0.7);
    color: $color-on-surface;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: $shadow-sm;
    cursor: pointer;

    &.back { left: $page-padding; }
    &.more { right: $page-padding; }
  }
}

.detail-body {
  position: relative;
  margin-top: -20px;
  padding: 0 $page-padding;
}

.card {
  @include card($radius-lg, $space-5);
  margin-bottom: $space-4;
}

.info {
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $space-3;

    .name { font-size: $fs-headline; font-weight: $fw-bold; color: $color-on-surface; }
    .rating {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 3px;
      font-size: $fs-label;
      font-weight: $fw-semibold;
      color: $color-secondary;
    }
  }

  .tags { margin-bottom: $space-3; }

  .info-row {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $fs-label;
    color: $color-on-surface-variant;
    margin-bottom: $space-2;
    .van-icon { color: $color-primary; }
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $fs-caption;
  color: $color-on-surface-variant;
  margin-bottom: $space-3;
  .van-icon { color: $color-primary; }
}

.section-content {
  font-size: $fs-label;
  color: $color-on-surface;
  line-height: 1.7;
}

.note-card {
  background: $color-primary-fixed;

  .section-title { color: $color-on-primary-container; }
  .section-content { color: $color-on-primary-container; }
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: $space-3;
  padding: $space-3 $page-padding;
  padding-bottom: calc(#{$space-3} + env(safe-area-inset-bottom));
  @include glass(0.9);
  box-shadow: $shadow-nav;

  .act {
    flex: 1;
    height: 46px;
    border-radius: $radius-pill;
    border: 1px solid $color-outline-variant;
    background: $color-surface-lowest;
    color: $color-on-surface;
    font-size: $fs-label;
    font-weight: $fw-medium;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    cursor: pointer;

    &.primary {
      @include btn-primary;
      border: none;
    }
  }
}
</style>
