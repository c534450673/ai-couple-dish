<template>
  <view class="wish-page">
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

    <view class="wish-list">
      <view v-for="item in wishList" :key="item.id" class="wish-item">
        <view class="wish-icon">{{ getTypeIcon(item.wishType) }}</view>
        <view class="wish-info">
          <text class="wish-title">{{ item.title }}</text>
          <text class="wish-desc" v-if="item.description">{{ item.description }}</text>
        </view>
        <view class="wish-status" :class="item.status === 1 ? 'fulfilled' : 'pending'">
          {{ item.status === 1 ? '已实现' : '待实现' }}
        </view>
        <view class="wish-actions">
          <view v-if="item.status === 0" class="action-btn" @click="handleFulfill(item)">实现</view>
          <view class="action-btn delete" @click="handleDelete(item)">删除</view>
        </view>
      </view>
      <view v-if="wishList.length === 0" class="empty-state">
        <text>暂无心愿</text>
        <view class="add-btn" @click="showAddDialog = true">添加心愿</view>
      </view>
    </view>

    <view class="add-fab" @click="showAddDialog = true">
      <text>+</text>
    </view>

    <!-- 添加心愿弹窗 -->
    <view class="dialog" v-if="showAddDialog" @click="showAddDialog = false">
      <view class="dialog-content" @click.stop>
        <view class="dialog-header">
          <text>添加心愿</text>
          <text class="close" @click="showAddDialog = false">✕</text>
        </view>
        <input v-model="addForm.title" class="input" placeholder="想和TA一起做什么？" />
        <textarea v-model="addForm.description" class="textarea" placeholder="详细描述..." />
        <view class="type-select">
          <view
            v-for="type in typeList"
            :key="type.value"
            class="type-item"
            :class="{ active: addForm.wishType === type.value }"
            @click="addForm.wishType = type.value"
          >
            <text class="type-icon">{{ type.icon }}</text>
            <text class="type-label">{{ type.label }}</text>
          </view>
        </view>
        <button class="submit-btn" @click="handleAdd">保存</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { wishApi } from '@/api'

const activeTab = ref('all')
const wishList = ref([])
const showAddDialog = ref(false)

const addForm = ref({
  title: '',
  description: '',
  wishType: 'restaurant'
})

const tabs = [
  { label: '全部', value: 'all' },
  { label: '待实现', value: '0' },
  { label: '已实现', value: '1' }
]

const typeList = [
  { value: 'restaurant', label: '餐厅', icon: '🍽️' },
  { value: 'dish', label: '菜品', icon: '🍜' },
  { value: 'recipe', label: '食谱', icon: '👨‍🍳' }
]

const getTypeIcon = (type) => {
  const map = { restaurant: '🍽️', dish: '🍜', recipe: '👨‍🍳' }
  return map[type] || '⭐'
}

const loadWishList = async () => {
  uni.showLoading({ title: '加载中...' })
  try {
    const params = activeTab.value !== 'all' ? { status: activeTab.value } : {}
    const res = await wishApi.getWishList(params)
    wishList.value = res.data || []
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const onTabChange = (value) => {
  activeTab.value = value
  loadWishList()
}

const handleAdd = async () => {
  if (!addForm.value.title) {
    uni.showToast({ title: '请输入心愿', icon: 'none' })
    return
  }

  try {
    await wishApi.addWish(addForm.value)
    uni.showToast({ title: '添加成功', icon: 'success' })
    showAddDialog.value = false
    addForm.value = { title: '', description: '', wishType: 'restaurant' }
    loadWishList()
  } catch (error) {
    uni.showToast({ title: '添加失败', icon: 'none' })
  }
}

const handleFulfill = async (item) => {
  try {
    await wishApi.fulfillWish(item.id)
    uni.showToast({ title: '已实现', icon: 'success' })
    loadWishList()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

const handleDelete = async (item) => {
  const res = await uni.showModal({
    title: '确认删除',
    content: '确定要删除这个心愿吗？'
  })

  if (res.confirm) {
    try {
      await wishApi.deleteWish(item.id)
      uni.showToast({ title: '已删除', icon: 'success' })
      loadWishList()
    } catch (error) {
      uni.showToast({ title: '删除失败', icon: 'none' })
    }
  }
}

onMounted(() => {
  loadWishList()
})
</script>

<style lang="scss" scoped>
.wish-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 140rpx;
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

.wish-list {
  padding: 24rpx;

  .wish-item {
    display: flex;
    align-items: center;
    background: #fff;
    border-radius: 24rpx;
    padding: 30rpx;
    margin-bottom: 24rpx;

    .wish-icon {
      font-size: 48rpx;
      margin-right: 20rpx;
    }

    .wish-info {
      flex: 1;
      display: flex;
      flex-direction: column;

      .wish-title {
        font-size: 30rpx;
        font-weight: 500;
        color: #333;
      }

      .wish-desc {
        font-size: 26rpx;
        color: #999;
        margin-top: 6rpx;
      }
    }

    .wish-status {
      padding: 8rpx 16rpx;
      border-radius: 8rpx;
      font-size: 22rpx;
      margin-right: 16rpx;

      &.fulfilled {
        background: #f0fff4;
        color: #56ab2f;
      }

      &.pending {
        background: #fff7e6;
        color: #ff9500;
      }
    }

    .wish-actions {
      display: flex;
      gap: 12rpx;

      .action-btn {
        padding: 10rpx 20rpx;
        background: #fff0f3;
        color: #ff4757;
        border-radius: 8rpx;
        font-size: 24rpx;

        &.delete {
          background: #f5f5f5;
          color: #999;
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

.dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;

  .dialog-content {
    width: 600rpx;
    background: #fff;
    border-radius: 24rpx;
    padding: 40rpx;

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 30rpx;

      text {
        font-size: 36rpx;
        font-weight: 600;
      }

      .close {
        font-size: 40rpx;
        color: #999;
      }
    }

    .input {
      width: 100%;
      height: 96rpx;
      background: #f5f5f5;
      border-radius: 16rpx;
      padding: 0 30rpx;
      font-size: 28rpx;
      box-sizing: border-box;
      margin-bottom: 20rpx;
    }

    .textarea {
      width: 100%;
      height: 120rpx;
      background: #f5f5f5;
      border-radius: 16rpx;
      padding: 20rpx 30rpx;
      font-size: 28rpx;
      box-sizing: border-box;
      margin-bottom: 20rpx;
    }

    .type-select {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16rpx;
      margin-bottom: 30rpx;

      .type-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8rpx;
        padding: 20rpx;
        background: #f5f5f5;
        border-radius: 16rpx;

        &.active {
          background: #fff0f3;
        }

        .type-icon {
          font-size: 40rpx;
        }

        .type-label {
          font-size: 24rpx;
          color: #666;
        }
      }
    }

    .submit-btn {
      width: 100%;
      height: 96rpx;
      background: linear-gradient(135deg, #ff6b9d, #ff4757);
      color: #fff;
      border-radius: 48rpx;
      font-size: 32rpx;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}
</style>
