<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { feedApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

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
  { value: 'meal', label: '正餐', icon: 'cart-o', color: '#894c5c' },
  { value: 'dessert', label: '甜点', icon: 'cake-o', color: '#c98a00' },
  { value: 'snack', label: '零食', icon: 'bag-o', color: '#5f7a4f' },
  { value: 'drink', label: '饮品', icon: 'coupon-o', color: '#4a6fa5' }
]

const getFeedIcon = (type) => {
  const map = { meal: 'cart-o', dessert: 'cake-o', snack: 'bag-o', drink: 'coupon-o' }
  return map[type] || 'gift-o'
}

const getFeedColor = (type) => {
  const map = { meal: '#894c5c', dessert: '#c98a00', snack: '#5f7a4f', drink: '#4a6fa5' }
  return map[type] || '#894c5c'
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

<template>
  <div class="feed-page">
    <header class="feed-topbar">
      <h1 class="page-title">
        投喂 TA
      </h1>
    </header>

    <van-pull-refresh
      v-model="refreshing"
      class="feed-body"
      @refresh="onRefresh"
    >
      <!-- 今日状态 -->
      <div class="today-status">
        <div
          class="status-item"
          :class="{ active: todayStatus.sentToday }"
        >
          <span class="ic"><van-icon
            :name="todayStatus.sentToday ? 'checked' : 'add-o'"
            size="24"
          /></span>
          <span class="tx">{{ todayStatus.sentToday ? '已投喂' : '投喂TA' }}</span>
        </div>
        <i class="status-divider" />
        <div
          class="status-item"
          :class="{ active: todayStatus.receivedToday }"
        >
          <span class="ic"><van-icon
            :name="todayStatus.receivedToday ? 'checked' : 'gift-o'"
            size="24"
          /></span>
          <span class="tx">{{ todayStatus.receivedToday ? '已领取' : '待领取' }}</span>
        </div>
      </div>

      <!-- 投喂按钮 -->
      <div
        v-if="!todayStatus.sentToday"
        class="send-section"
      >
        <button
          class="send-btn"
          @click="showSendDialog = true"
        >
          <van-icon name="plus" /> 投喂 TA
        </button>
      </div>

      <!-- 收到的投喂 -->
      <div class="received-section">
        <div class="section-title">
          收到的投喂
        </div>

        <div v-if="isSkeleton">
          <div
            v-for="n in 3"
            :key="n"
            class="feed-card skeleton"
          >
            <div class="head">
              <div class="sk-avatar sk" />
              <div class="info">
                <div class="sk sk-line sk-sender" />
                <div class="sk sk-line sk-time" />
              </div>
            </div>
            <div class="sk sk-content" />
          </div>
        </div>

        <div v-else>
          <div
            v-for="item in receivedFeeds"
            :key="item.id"
            class="feed-card"
          >
            <div class="head">
              <span
                class="type-ic"
                :style="{ background: getFeedColor(item.feedType) + '22', color: getFeedColor(item.feedType) }"
              >
                <van-icon
                  :name="getFeedIcon(item.feedType)"
                  size="20"
                />
              </span>
              <div class="info">
                <div class="sender">
                  {{ item.senderName }}
                </div>
                <div class="time">
                  {{ item.createTime }}
                </div>
              </div>
              <van-tag
                :type="getStatusTagType(item.status)"
                round
              >
                {{ getStatusText(item.status) }}
              </van-tag>
            </div>
            <div class="content">
              {{ item.content }}
            </div>
            <div
              v-if="item.imageUrls"
              class="images"
            >
              <img
                v-for="(url, index) in (typeof item.imageUrls === 'string' ? item.imageUrls.split(',') : item.imageUrls)"
                :key="index"
                v-lazy="url"
              >
            </div>
            <div
              v-if="item.status === 0"
              class="actions"
            >
              <van-button
                size="small"
                type="primary"
                round
                @click="handleAccept(item)"
              >
                接受
              </van-button>
              <van-button
                size="small"
                round
                @click="handleReject(item)"
              >
                拒绝
              </van-button>
            </div>
          </div>

          <van-empty
            v-if="receivedFeeds.length === 0"
            description="暂无收到的投喂"
          />
        </div>
      </div>
    </van-pull-refresh>

    <app-tabbar />

    <!-- 发送投喂弹窗 -->
    <van-popup
      v-model:show="showSendDialog"
      position="bottom"
      round
    >
      <div class="send-dialog">
        <div class="dialog-header">
          <span>投喂 TA</span>
          <van-icon
            name="cross"
            @click="showSendDialog = false"
          />
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
              <van-icon
                :name="type.icon"
                size="26"
                :color="type.color"
              />
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
          <van-uploader
            v-model="sendImages"
            :max-count="3"
            multiple
          />
        </div>
        <div class="dialog-footer">
          <van-button
            type="primary"
            block
            round
            @click="handleSend"
          >
            发送
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style lang="scss" scoped>
.feed-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 96px;
}

.feed-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  @include glass(0.7);

  .page-title { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
}

.feed-body {
  padding: $space-4 $page-padding 0;
}

.today-status {
  display: flex;
  align-items: center;
  @include card($radius-lg, $space-5);
  margin-bottom: $space-4;

  .status-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-2;
    color: $color-on-surface-variant;

    .ic {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: $color-surface-low;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .tx { font-size: $fs-label; }

    &.active {
      color: $color-primary;
      .ic { background: $color-primary-fixed; }
    }
  }

  .status-divider { width: 1px; height: 48px; background: $color-surface-variant; }
}

.send-section {
  margin-bottom: $space-5;

  .send-btn {
    width: 100%;
    height: 48px;
    @include btn-primary;
    font-size: $fs-body;
    box-shadow: $shadow-float;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;

    &:active { opacity: 0.9; }
  }
}

.received-section {
  .section-title {
    font-size: $fs-label;
    font-weight: $fw-semibold;
    color: $color-on-surface;
    margin-bottom: $space-3;
    padding: 0 $space-1;
  }

  .feed-card {
    @include card($radius-lg, $space-4);
    margin-bottom: $space-3;

    .head {
      display: flex;
      align-items: center;
      gap: $space-3;
      margin-bottom: $space-3;

      .type-ic {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .info {
        flex: 1;
        .sender { font-size: $fs-label; font-weight: $fw-medium; color: $color-on-surface; }
        .time { font-size: $fs-caption; color: $color-on-surface-variant; }
      }
    }

    .content { font-size: $fs-label; color: $color-on-surface; margin-bottom: $space-3; line-height: 1.5; }

    .images {
      display: flex;
      gap: $space-2;
      margin-bottom: $space-3;

      img { width: 80px; height: 80px; border-radius: $radius-md; object-fit: cover; }
    }

    .actions { display: flex; gap: $space-3; }
  }
}

.send-dialog {
  padding: $space-5;

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-5;

    span { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
    .van-icon { color: $color-on-surface-variant; }
  }

  .feed-type-select {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: $space-3;
    margin-bottom: $space-4;

    .type-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-2;
      padding: $space-3 0;
      background: $color-surface-low;
      border-radius: $radius-md;
      transition: background $transition-base;

      &.active { background: $color-primary-fixed; color: $color-primary; }

      span { font-size: $fs-caption; color: $color-on-surface-variant; }
    }
  }

  .dialog-footer { margin-top: $space-4; }
}

// 骨架屏
.skeleton {
  pointer-events: none;

  .sk {
    background: linear-gradient(90deg, $color-surface-high 25%, $color-surface-low 50%, $color-surface-high 75%);
    background-size: 200% 100%;
    animation: sk-loading 1.5s infinite;
  }

  .head { display: flex; align-items: center; gap: $space-3; }
  .sk-avatar { width: 40px; height: 40px; border-radius: 50%; }
  .info { flex: 1; }
  .sk-line { border-radius: 4px; }
  .sk-sender { width: 50%; height: 14px; margin-bottom: 6px; }
  .sk-time { width: 30%; height: 12px; }
  .sk-content { width: 100%; height: 56px; border-radius: $radius-md; margin-top: $space-3; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
