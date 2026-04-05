<template>
  <div class="feed-page">
    <van-nav-bar title="投喂TA" />

    <!-- 下拉刷新 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <!-- 今日状态 -->
      <div class="today-status card">
        <div class="status-item" :class="{ active: todayStatus.sentToday }">
          <van-icon :name="todayStatus.sentToday ? 'checked' : 'plus'" size="24" />
          <span>{{ todayStatus.sentToday ? '已投喂' : '投喂TA' }}</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item" :class="{ active: todayStatus.receivedToday }">
          <van-icon :name="todayStatus.receivedToday ? 'checked' : 'gift'" size="24" />
          <span>{{ todayStatus.receivedToday ? '已领取' : '待领取' }}</span>
        </div>
      </div>

      <!-- 投喂按钮 -->
      <div class="send-section" v-if="!todayStatus.sentToday">
        <van-button type="primary" block round size="large" @click="showSendDialog = true">
          <van-icon name="plus" /> 投喂TA
        </van-button>
      </div>

      <!-- 收到的投喂 -->
      <div class="received-section">
        <div class="section-title">收到的投喂</div>

        <!-- 骨架屏 -->
        <div v-if="isSkeleton" class="feed-list">
          <div v-for="n in 3" :key="n" class="feed-item card skeleton-item">
            <div class="feed-header">
              <div class="skeleton-avatar"></div>
              <div class="feed-info">
                <div class="skeleton-sender"></div>
                <div class="skeleton-time"></div>
              </div>
            </div>
            <div class="skeleton-content"></div>
          </div>
        </div>

        <div v-else class="feed-list">
          <div v-for="item in receivedFeeds" :key="item.id" class="feed-item card">
            <div class="feed-header">
              <van-icon :name="getFeedIcon(item.feedType)" size="32" :color="getFeedColor(item.feedType)" />
              <div class="feed-info">
                <div class="feed-sender">{{ item.senderName }}</div>
                <div class="feed-time">{{ item.createTime }}</div>
              </div>
              <van-tag :type="getStatusTagType(item.status)">
                {{ getStatusText(item.status) }}
              </van-tag>
            </div>
            <div class="feed-content">{{ item.content }}</div>
            <div class="feed-images" v-if="item.imageUrls">
              <img
                v-for="(url, index) in (typeof item.imageUrls === 'string' ? item.imageUrls.split(',') : item.imageUrls)"
                :key="index"
                v-lazy="url"
                loading="lazy"
              />
            </div>
            <div class="feed-actions" v-if="item.status === 0">
              <van-button size="small" type="primary" @click="handleAccept(item)">接受</van-button>
              <van-button size="small" @click="handleReject(item)">拒绝</van-button>
            </div>
          </div>

          <van-empty v-if="receivedFeeds.length === 0" description="暂无收到的投喂" />
        </div>
      </div>
    </van-pull-refresh>

    <!-- 底部导航 -->
    <van-tabbar route>
      <van-tabbar-item to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/menu" icon="shop-o">餐厅</van-tabbar-item>
      <van-tabbar-item to="/feed" icon="gift-o">投喂</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">我的</van-tabbar-item>
    </van-tabbar>

    <!-- 发送投喂弹窗 -->
    <van-popup v-model:show="showSendDialog" position="bottom" round>
      <div class="send-dialog">
        <div class="dialog-header">
          <span>投喂TA</span>
          <van-icon name="cross" @click="showSendDialog = false" />
        </div>
        <div class="dialog-content">
          <div class="feed-type-select">
            <div
              v-for="type in feedTypes"
              :key="type.value"
              class="type-item"
              :class="{ active: sendForm.feedType === type.value }"
              @click="sendForm.feedType = type.value"
            >
              <van-icon :name="type.icon" size="32" :color="type.color" />
              <span>{{ type.label }}</span>
            </div>
          </div>
          <van-field
            v-model="sendForm.content"
            type="textarea"
            placeholder="说点什么..."
            rows="3"
            autosize
          />
          <van-uploader v-model="sendImages" :max-count="3" multiple />
        </div>
        <div class="dialog-footer">
          <van-button type="primary" block round @click="handleSend">发送</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { feedApi } from '@/api'

const todayStatus = ref({ sentToday: false, receivedToday: false })
const receivedFeeds = ref([])
const showSendDialog = ref(false)
const refreshing = ref(false)
const isSkeleton = ref(true)

const sendForm = ref({
  feedType: 'meal',
  content: ''
})

const sendImages = ref([])
const feedTypes = [
  { value: 'meal', label: '正餐', icon: 'cart-o', color: '#ff6b9d' },
  { value: 'dessert', label: '甜点', icon: 'cake-o', color: '#ffd93d' },
  { value: 'snack', label: '零食', icon: 'bag-o', color: '#56ab2f' },
  { value: 'drink', label: '饮品', icon: 'coupon-o', color: '#4a90e2' }
]

const getFeedIcon = (type) => {
  const map = { meal: 'cart-o', dessert: 'cake-o', snack: 'bag-o', drink: 'coupon-o' }
  return map[type] || 'gift-o'
}

const getFeedColor = (type) => {
  const map = { meal: '#ff6b9d', dessert: '#ffd93d', snack: '#56ab2f', drink: '#4a90e2' }
  return map[type] || '#999'
}

const getStatusTagType = (status) => {
  const map = { 0: 'warning', 1: 'success', 2: 'default' }
  return map[status] || 'default'
}

const getStatusText = (status) => {
  const map = { 0: '待领取', 1: '已领取', 2: '已拒绝' }
  return map[status] || '待领取'
}

const loadData = async () => {
  try {
    const [statusRes, receivedRes] = await Promise.all([
      feedApi.getTodayFeedStatus(),
      feedApi.getReceivedFeeds()
    ])
    todayStatus.value = statusRes.data || { sentToday: false, receivedToday: false }
    receivedFeeds.value = receivedRes.data || []
  } catch (error) {
    showToast('加载失败')
  } finally {
    refreshing.value = false
    isSkeleton.value = false
  }
}

const onRefresh = () => {
  isSkeleton.value = true
  refreshing.value = true
  loadData()
}

const handleSend = async () => {
  if (!sendForm.value.content) {
    showToast('请输入投喂内容')
    return
  }

  showLoadingToast({ message: '发送中...', forbidClick: true })
  try {
    await feedApi.sendFeed({
      ...sendForm.value,
      imageUrls: sendImages.value.map(f => f.url).join(',')
    })
    showToast('发送成功')
    showSendDialog.value = false
    sendForm.value = { feedType: 'meal', content: '' }
    sendImages.value = []
    loadData()
  } catch (error) {
    showToast('发送失败')
  } finally {
    closeToast()
  }
}

const handleAccept = async (item) => {
  try {
    await feedApi.acceptFeed(item.id)
    showToast('已接受')
    loadData()
  } catch (error) {
    showToast('操作失败')
  }
}

const handleReject = async (item) => {
  try {
    await feedApi.rejectFeed(item.id)
    showToast('已拒绝')
    loadData()
  } catch (error) {
    showToast('操作失败')
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
  padding-bottom: 70px;
}

.today-status {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin: 12px 16px;
  padding: 20px;

  .status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: #999;

    &.active {
      color: #ff4757;
    }

    span {
      font-size: 14px;
    }
  }

  .status-divider {
    width: 1px;
    height: 40px;
    background: #eee;
  }
}

.send-section {
  padding: 16px;

  .van-button {
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    border: none;
  }
}

.received-section {
  padding: 0 16px;

  .section-title {
    font-size: 14px;
    color: #999;
    margin-bottom: 12px;
  }

  .feed-item {
    margin-bottom: 12px;
    padding: 16px;

    .feed-header {
      display: flex;
      align-items: center;
      margin-bottom: 12px;

      .feed-info {
        flex: 1;
        margin-left: 12px;

        .feed-sender {
          font-size: 14px;
          font-weight: 500;
        }

        .feed-time {
          font-size: 12px;
          color: #999;
        }
      }
    }

    .feed-content {
      font-size: 14px;
      color: #333;
      margin-bottom: 12px;
    }

    .feed-images {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;

      img {
        width: 80px;
        height: 80px;
        border-radius: 8px;
        object-fit: cover;
      }
    }

    .feed-actions {
      display: flex;
      gap: 12px;
    }
  }
}

.send-dialog {
  padding: 16px;

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    span {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .feed-type-select {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;

    .type-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: #f5f5f5;
      border-radius: 12px;

      &.active {
        background: #fff0f3;
        color: #ff4757;
      }

      span {
        font-size: 12px;
        color: #666;
      }
    }
  }

  .dialog-footer {
    margin-top: 16px;

    .van-button {
      background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
      border: none;
    }
  }
}

// 骨架屏样式
.skeleton-item {
  pointer-events: none;

  .feed-header {
    display: flex;
    align-items: center;

    .skeleton-avatar {
      width: 32px;
      height: 32px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 50%;
      margin-right: 12px;
    }

    .feed-info {
      flex: 1;

      .skeleton-sender {
        width: 60%;
        height: 14px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 4px;
        margin-bottom: 6px;
      }

      .skeleton-time {
        width: 40%;
        height: 12px;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 4px;
      }
    }
  }

  .skeleton-content {
    width: 100%;
    height: 60px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 8px;
    margin-top: 12px;
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
</style>
