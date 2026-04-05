<template>
  <div class="menu-detail-page">
    <van-nav-bar
      :title="menuDetail.restaurantName || '餐厅详情'"
      left-text="返回"
      left-arrow
      @click-left="$router.back()"
    >
      <template #right>
        <van-icon name="ellipsis" size="20" @click="showActions" />
      </template>
    </van-nav-bar>

    <div class="detail-content" v-if="menuDetail.id">
      <!-- 封面图片 -->
      <div class="cover-section" v-if="menuDetail.photoUrls">
        <van-swipe @change="onSwipeChange">
          <van-swipe-item v-for="(url, index) in photoList" :key="index">
            <img :src="url" alt="cover" />
          </van-swipe-item>
          <template #indicator>
            <div class="swipe-indicator">
              {{ currentSwipe + 1 }} / {{ photoList.length }}
            </div>
          </template>
        </van-swipe>
      </div>

      <!-- 餐厅信息 -->
      <div class="info-section card">
        <div class="restaurant-header">
          <h2 class="restaurant-name">{{ menuDetail.restaurantName }}</h2>
          <van-tag :type="getStatusType(menuDetail.status)">
            {{ getStatusText(menuDetail.status) }}
          </van-tag>
        </div>

        <div class="info-row" v-if="menuDetail.location">
          <van-icon name="location-o" />
          <span>{{ menuDetail.location }}</span>
        </div>

        <div class="info-row" v-if="menuDetail.price">
          <van-icon name="coupon-o" />
          <span>{{ menuDetail.price }}</span>
        </div>

        <div class="info-row" v-if="menuDetail.rating">
          <van-icon name="star" color="#ffd21e" />
          <span>{{ menuDetail.rating }}分</span>
        </div>
      </div>

      <!-- 推荐菜品 -->
      <div class="dishes-section card" v-if="menuDetail.dishName">
        <div class="section-title">推荐菜品</div>
        <div class="dishes-content">{{ menuDetail.dishName }}</div>
      </div>

      <!-- 私密笔记 -->
      <div class="note-section card" v-if="menuDetail.note">
        <div class="section-title">私密笔记</div>
        <div class="note-content">{{ menuDetail.note }}</div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-section">
        <van-button type="primary" icon="like-o" @click="handleLike">
          {{ menuDetail.likeCount || 0 }} 点赞
        </van-button>
        <van-button type="default" icon="star-o" @click="handleFavorite">
          {{ menuDetail.isFavorite ? '取消收藏' : '收藏' }}
        </van-button>
      </div>
    </div>

    <van-loading v-else class="loading" />

    <!-- 操作菜单 -->
    <van-action-sheet
      v-model:show="showActionSheet"
      :actions="actions"
      @select="onActionSelect"
    />
  </div>
</template>

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

<style lang="scss" scoped>
.menu-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 20px;
}

.cover-section {
  position: relative;

  img {
    width: 100%;
    height: 250px;
    object-fit: cover;
  }

  .swipe-indicator {
    position: absolute;
    right: 16px;
    bottom: 16px;
    background: rgba(0, 0, 0, 0.5);
    color: #fff;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
  }
}

.info-section,
.dishes-section,
.note-section {
  margin: 12px 16px;
  padding: 16px;

  .restaurant-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .restaurant-name {
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }
  }

  .info-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #666;
    margin-bottom: 8px;
  }

  .section-title {
    font-size: 14px;
    color: #999;
    margin-bottom: 12px;
  }

  .dishes-content,
  .note-content {
    font-size: 14px;
    color: #333;
    line-height: 1.6;
  }
}

.action-section {
  display: flex;
  gap: 12px;
  padding: 16px;

  .van-button {
    flex: 1;
    border-radius: 24px;
  }
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}
</style>
