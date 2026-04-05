<template>
  <view class="feed-page">
    <!-- 今日状态 -->
    <view class="today-status">
      <view class="status-item" :class="{ active: todayStatus.sentToday }">
        <text class="icon">{{ todayStatus.sentToday ? '✅' : '➕' }}</text>
        <text>{{ todayStatus.sentToday ? '已投喂' : '投喂TA' }}</text>
      </view>
      <view class="status-divider"></view>
      <view class="status-item" :class="{ active: todayStatus.receivedToday }">
        <text class="icon">{{ todayStatus.receivedToday ? '✅' : '🎁' }}</text>
        <text>{{ todayStatus.receivedToday ? '已领取' : '待领取' }}</text>
      </view>
    </view>

    <!-- 投喂按钮 -->
    <view class="send-section" v-if="!todayStatus.sentToday">
      <button class="send-btn" @click="showSendDialog = true">
        <text>➕</text> 投喂TA
      </button>
    </view>

    <!-- 收到的投喂 -->
    <view class="received-section">
      <view class="section-title">收到的投喂</view>
      <view v-for="item in receivedFeeds" :key="item.id" class="feed-item">
        <view class="feed-header">
          <text class="feed-icon">{{ getFeedIcon(item.feedType) }}</text>
          <view class="feed-info">
            <text class="feed-sender">{{ item.senderName }}</text>
            <text class="feed-time">{{ item.createTime }}</text>
          </view>
          <view class="feed-status" :class="getStatusClass(item.status)">
            {{ getStatusText(item.status) }}
          </view>
        </view>
        <view class="feed-content">{{ item.content }}</view>
        <view class="feed-images" v-if="item.imageUrls">
          <image v-for="(url, index) in item.imageUrls.split(',')" :key="index" :src="url" mode="aspectFill" />
        </view>
        <view class="feed-actions" v-if="item.status === 0">
          <button class="action-btn accept" @click="handleAccept(item)">接受</button>
          <button class="action-btn reject" @click="handleReject(item)">拒绝</button>
        </view>
      </view>
      <view v-if="receivedFeeds.length === 0" class="empty-state">
        <text>暂无收到的投喂</text>
      </view>
    </view>

    <!-- 发送投喂弹窗 -->
    <view class="send-dialog" v-if="showSendDialog" @click="showSendDialog = false">
      <view class="dialog-content" @click.stop>
        <view class="dialog-header">
          <text>投喂TA</text>
          <text class="close" @click="showSendDialog = false">✕</text>
        </view>
        <view class="feed-type-select">
          <view
            v-for="type in feedTypes"
            :key="type.value"
            class="type-item"
            :class="{ active: sendForm.feedType === type.value }"
            @click="sendForm.feedType = type.value"
          >
            <text class="type-icon">{{ type.icon }}</text>
            <text class="type-label">{{ type.label }}</text>
          </view>
        </view>
        <textarea v-model="sendForm.content" placeholder="说点什么..." class="content-input" />
        <button class="submit-btn" @click="handleSend">发送</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { feedApi } from '@/api'

const todayStatus = ref({ sentToday: false, receivedToday: false })
const receivedFeeds = ref([])
const showSendDialog = ref(false)

const sendForm = ref({
  feedType: 'meal',
  content: ''
})

const feedTypes = [
  { value: 'meal', label: '正餐', icon: '🍽️' },
  { value: 'dessert', label: '甜点', icon: '🍰' },
  { value: 'snack', label: '零食', icon: '🍿' },
  { value: 'drink', label: '饮品', icon: '🥤' }
]

const getFeedIcon = (type) => {
  const map = { meal: '🍽️', dessert: '🍰', snack: '🍿', drink: '🥤' }
  return map[type] || '🎁'
}

const getStatusClass = (status) => {
  const map = { 0: 'warning', 1: 'success', 2: 'default' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { 0: '待领取', 1: '已领取', 2: '已拒绝' }
  return map[status] || '待领取'
}

const loadData = async () => {
  uni.showLoading({ title: '加载中...' })
  try {
    const [statusRes, receivedRes] = await Promise.all([
      feedApi.getTodayFeedStatus(),
      feedApi.getReceivedFeeds()
    ])
    todayStatus.value = statusRes.data || { sentToday: false, receivedToday: false }
    receivedFeeds.value = receivedRes.data || []
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const handleSend = async () => {
  if (!sendForm.value.content) {
    uni.showToast({ title: '请输入投喂内容', icon: 'none' })
    return
  }

  uni.showLoading({ title: '发送中...' })
  try {
    await feedApi.sendFeed(sendForm.value)
    uni.showToast({ title: '发送成功', icon: 'success' })
    showSendDialog.value = false
    sendForm.value = { feedType: 'meal', content: '' }
    loadData()
  } catch (error) {
    uni.showToast({ title: '发送失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

const handleAccept = async (item) => {
  try {
    await feedApi.acceptFeed(item.id)
    uni.showToast({ title: '已接受', icon: 'success' })
    loadData()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

const handleReject = async (item) => {
  try {
    await feedApi.rejectFeed(item.id)
    uni.showToast({ title: '已拒绝', icon: 'success' })
    loadData()
  } catch (error) {
    uni.showToast({ title: '操作失败', icon: 'none' })
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.feed-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 24rpx;
  padding-bottom: 140rpx;
}

.today-status {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 40rpx;
  background: #fff;
  border-radius: 24rpx;
  margin-bottom: 24rpx;

  .status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16rpx;
    color: #999;

    &.active {
      color: #ff4757;
    }

    .icon {
      font-size: 48rpx;
    }
  }

  .status-divider {
    width: 2rpx;
    height: 80rpx;
    background: #eee;
  }
}

.send-section {
  margin-bottom: 24rpx;

  .send-btn {
    width: 100%;
    height: 96rpx;
    background: linear-gradient(135deg, #ff6b9d, #ff4757);
    color: #fff;
    border-radius: 48rpx;
    font-size: 32rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;

    text {
      margin-right: 10rpx;
    }
  }
}

.received-section {
  .section-title {
    font-size: 28rpx;
    color: #999;
    margin-bottom: 20rpx;
  }

  .feed-item {
    background: #fff;
    border-radius: 24rpx;
    padding: 24rpx;
    margin-bottom: 24rpx;

    .feed-header {
      display: flex;
      align-items: center;
      margin-bottom: 16rpx;

      .feed-icon {
        font-size: 48rpx;
        margin-right: 20rpx;
      }

      .feed-info {
        flex: 1;
        display: flex;
        flex-direction: column;

        .feed-sender {
          font-size: 28rpx;
          font-weight: 500;
          color: #333;
        }

        .feed-time {
          font-size: 24rpx;
          color: #999;
          margin-top: 4rpx;
        }
      }

      .feed-status {
        padding: 6rpx 16rpx;
        border-radius: 8rpx;
        font-size: 22rpx;

        &.warning { background: #fff7e6; color: #ff9500; }
        &.success { background: #f0fff4; color: #56ab2f; }
      }
    }

    .feed-content {
      font-size: 28rpx;
      color: #333;
      line-height: 1.5;
    }

    .feed-images {
      display: flex;
      gap: 12rpx;
      margin-top: 16rpx;

      image {
        width: 160rpx;
        height: 160rpx;
        border-radius: 12rpx;
      }
    }

    .feed-actions {
      display: flex;
      gap: 20rpx;
      margin-top: 20rpx;

      .action-btn {
        flex: 1;
        height: 72rpx;
        border-radius: 36rpx;
        font-size: 28rpx;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;

        &.accept {
          background: linear-gradient(135deg, #ff6b9d, #ff4757);
          color: #fff;
        }

        &.reject {
          background: #f5f5f5;
          color: #666;
        }
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 60rpx 0;

    text {
      font-size: 28rpx;
      color: #999;
    }
  }
}

.send-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  z-index: 999;

  .dialog-content {
    width: 100%;
    background: #fff;
    border-radius: 32rpx 32rpx 0 0;
    padding: 32rpx;

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32rpx;

      text {
        font-size: 36rpx;
        font-weight: 600;
      }

      .close {
        font-size: 40rpx;
        color: #999;
      }
    }

    .feed-type-select {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20rpx;
      margin-bottom: 32rpx;

      .type-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10rpx;
        padding: 24rpx;
        background: #f5f5f5;
        border-radius: 16rpx;

        &.active {
          background: #fff0f3;
        }

        .type-icon {
          font-size: 48rpx;
        }

        .type-label {
          font-size: 24rpx;
          color: #666;
        }
      }
    }

    .content-input {
      width: 100%;
      height: 160rpx;
      background: #f5f5f5;
      border-radius: 16rpx;
      padding: 24rpx;
      font-size: 28rpx;
      box-sizing: border-box;
    }

    .submit-btn {
      width: 100%;
      height: 96rpx;
      background: linear-gradient(135deg, #ff6b9d, #ff4757);
      color: #fff;
      border-radius: 48rpx;
      font-size: 32rpx;
      margin-top: 32rpx;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}
</style>
