<template>
  <view class="home-page">
    <!-- 顶部用户信息 -->
    <view class="home-header">
      <view class="user-info" @click="goSettings">
        <image class="avatar" :src="userInfo?.avatarUrl || defaultAvatar" mode="aspectFill" />
        <view class="info">
          <text class="name">{{ userInfo?.nickName || '亲爱的' }}</text>
          <text class="couple-name">和 {{ coupleInfo?.partnerName || 'TA' }} 的私密空间</text>
        </view>
      </view>
      <view class="settings-icon" @click="goSettings">
        <text>⚙️</text>
      </view>
    </view>

    <!-- 恋爱计时 -->
    <view class="love-timer" @click="goAnniversary">
      <view class="timer-icon">❤️</view>
      <view class="timer-content">
        <text class="timer-label">在一起</text>
        <view class="timer-value">
          <text class="days">{{ timer.days }}</text>
          <text class="unit">天</text>
          <text class="time">{{ timer.hours }}:{{ timer.minutes }}:{{ timer.seconds }}</text>
        </view>
      </view>
      <text class="arrow">›</text>
    </view>

    <!-- 快捷功能 -->
    <view class="quick-actions">
      <view class="action-item" @click="goMenuAdd">
        <view class="action-icon add">
          <text>+</text>
        </view>
        <text class="action-label">添加餐厅</text>
      </view>
      <view class="action-item" @click="goFeed">
        <view class="action-icon feed">
          <text>🎁</text>
        </view>
        <text class="action-label">投喂TA</text>
      </view>
      <view class="action-item" @click="goAnniversary">
        <view class="action-icon anniversary">
          <text>📅</text>
        </view>
        <text class="action-label">纪念日</text>
      </view>
      <view class="action-item" @click="goWish">
        <view class="action-icon wish">
          <text>⭐</text>
        </view>
        <text class="action-label">心愿单</text>
      </view>
    </view>

    <!-- 数据统计 -->
    <view class="stats-grid">
      <view class="stat-item" @click="goMenu('wantToGo')">
        <text class="stat-value">{{ stats.wantToGoCount || 0 }}</text>
        <text class="stat-label">想去</text>
      </view>
      <view class="stat-item" @click="goMenu('beenTo')">
        <text class="stat-value">{{ stats.beenToCount || 0 }}</text>
        <text class="stat-label">去过</text>
      </view>
      <view class="stat-item" @click="goMenu('recommended')">
        <text class="stat-value">{{ stats.recommendedCount || 0 }}</text>
        <text class="stat-label">种草</text>
      </view>
      <view class="stat-item" @click="goFeed">
        <text class="stat-value">{{ stats.feedCount || 0 }}</text>
        <text class="stat-label">投喂</text>
      </view>
    </view>

    <!-- 即将到来的纪念日 -->
    <view class="upcoming-anniversary" v-if="upcomingAnniversary" @click="goAnniversary">
      <view class="anniversary-icon">⏰</view>
      <view class="anniversary-info">
        <text class="anniversary-name">{{ upcomingAnniversary.name }}</text>
        <text class="anniversary-days">还有 {{ upcomingAnniversary.days }} 天</text>
      </view>
      <text class="arrow">›</text>
    </view>

    <!-- 私密菜单列表 -->
    <view class="menu-section">
      <view class="section-header">
        <text class="title">私密菜单</text>
        <text class="more" @click="goMenu()">查看全部 ›</text>
      </view>
      <view class="menu-list">
        <view v-for="item in recentMenus" :key="item.id" class="menu-item" @click="goMenuDetail(item.id)">
          <image v-if="item.coverImage" :src="item.coverImage" class="menu-cover" mode="aspectFill" />
          <view v-else class="menu-cover empty-cover">🍽️</view>
          <view class="menu-info">
            <text class="menu-name">{{ item.restaurantName }}</text>
            <view class="menu-meta">
              <text v-if="item.location">📍 {{ item.location }}</text>
            </view>
            <view class="menu-tags">
              <view class="tag" :class="getStatusClass(item.status)">{{ getStatusText(item.status) }}</view>
            </view>
          </view>
        </view>
        <view v-if="recentMenus.length === 0" class="empty-state">
          <text>暂无餐厅记录</text>
          <view class="add-btn" @click="goMenuAdd">添加餐厅</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/store/user'
import { coupleApi, menuApi, anniversaryApi } from '@/api'

const userStore = useUserStore()

const defaultAvatar = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4Fbnqp6Hf4nNOvcriabISB5JpLxI1N0icm4qYiag/0'
const recentMenus = ref([])
const stats = ref({})
const upcomingAnniversary = ref(null)
const timer = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })

let timerInterval = null

const userInfo = computed(() => userStore.userInfo)
const coupleInfo = computed(() => userStore.coupleInfo)

const loadData = async () => {
  try {
    const [homeRes, menuRes, statsRes, anniversaryRes, timerRes] = await Promise.all([
      coupleApi.getCoupleHome(),
      menuApi.getMenuList({ page: 1, pageSize: 3 }),
      menuApi.getMenuStats(),
      anniversaryApi.getNextAnniversary(),
      coupleApi.getLoveTimer()
    ])

    recentMenus.value = menuRes.data?.list || []
    stats.value = statsRes.data || {}
    upcomingAnniversary.value = anniversaryRes.data
    timer.value = timerRes.data || { days: 0, hours: 0, minutes: 0, seconds: 0 }
  } catch (error) {
    console.error('加载失败', error)
  }
}

const startTimer = () => {
  timerInterval = setInterval(() => {
    const startDate = coupleInfo.value?.startDate
    if (startDate) {
      const now = new Date()
      const start = new Date(startDate)
      const diff = now - start

      timer.value = {
        days: Math.floor(diff / (1000 * 60 * 60 * 24)),
        hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
        seconds: Math.floor((diff % (1000 * 60)) / 1000)
      }
    }
  }, 1000)
}

const getStatusText = (status) => {
  const map = { 0: '想去', 1: '去过', 2: '种草' }
  return map[status] || '想去'
}

const getStatusClass = (status) => {
  const map = { 0: 'primary', 1: 'success', 2: 'warning' }
  return map[status] || 'primary'
}

const goSettings = () => uni.navigateTo({ url: '/pages/settings/index' })
const goMenuAdd = () => uni.navigateTo({ url: '/pages/menu/add' })
const goFeed = () => uni.navigateTo({ url: '/pages/feed/index' })
const goAnniversary = () => uni.navigateTo({ url: '/pages/anniversary/index' })
const goWish = () => uni.navigateTo({ url: '/pages/wish/index' })
const goMenu = (type) => uni.navigateTo({ url: `/pages/menu/list?type=${type || ''}` })
const goMenuDetail = (id) => uni.navigateTo({ url: `/pages/menu/detail?id=${id}` })

onMounted(() => {
  userStore.checkLoginStatus()
  loadData()
  startTimer()
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 120rpx;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);

  .user-info {
    display: flex;
    align-items: center;

    .avatar {
      width: 96rpx;
      height: 96rpx;
      border-radius: 50%;
      border: 4rpx solid rgba(255, 255, 255, 0.3);
    }

    .info {
      margin-left: 24rpx;
      display: flex;
      flex-direction: column;

      .name {
        font-size: 36rpx;
        font-weight: 600;
        color: #fff;
      }

      .couple-name {
        font-size: 24rpx;
        color: rgba(255, 255, 255, 0.8);
        margin-top: 6rpx;
      }
    }
  }

  .settings-icon {
    font-size: 48rpx;
  }
}

.love-timer {
  display: flex;
  align-items: center;
  margin: 30rpx;
  padding: 40rpx;
  background: #fff;
  border-radius: 24rpx;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.05);

  .timer-icon {
    font-size: 64rpx;
    margin-right: 30rpx;
  }

  .timer-content {
    flex: 1;

    .timer-label {
      font-size: 24rpx;
      color: #999;
    }

    .timer-value {
      display: flex;
      align-items: baseline;
      margin-top: 8rpx;

      .days {
        font-size: 64rpx;
        font-weight: 700;
        color: #ff4757;
      }

      .unit {
        font-size: 28rpx;
        color: #666;
        margin-left: 8rpx;
      }

      .time {
        font-size: 28rpx;
        color: #999;
        margin-left: 24rpx;
      }
    }
  }

  .arrow {
    font-size: 40rpx;
    color: #ccc;
  }
}

.quick-actions {
  display: flex;
  padding: 0 30rpx;
  margin-bottom: 30rpx;

  .action-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;

    .action-icon {
      width: 96rpx;
      height: 96rpx;
      border-radius: 24rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 48rpx;
      margin-bottom: 16rpx;

      &.add { background: linear-gradient(135deg, #ff6b9d, #ff4757); }
      &.feed { background: linear-gradient(135deg, #ffd93d, #ff9500); }
      &.anniversary { background: linear-gradient(135deg, #6bcbff, #4a90e2); }
      &.wish { background: linear-gradient(135deg, #a8e6cf, #56ab2f); }
    }

    .action-label {
      font-size: 24rpx;
      color: #666;
    }
  }
}

.stats-grid {
  display: flex;
  margin: 0 30rpx 30rpx;
  background: #fff;
  border-radius: 24rpx;
  overflow: hidden;

  .stat-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30rpx 0;

    .stat-value {
      font-size: 40rpx;
      font-weight: 700;
      color: #ff4757;
    }

    .stat-label {
      font-size: 24rpx;
      color: #999;
      margin-top: 8rpx;
    }
  }
}

.upcoming-anniversary {
  display: flex;
  align-items: center;
  margin: 0 30rpx 30rpx;
  padding: 30rpx;
  background: #fff;
  border-radius: 24rpx;

  .anniversary-icon {
    font-size: 48rpx;
    margin-right: 24rpx;
  }

  .anniversary-info {
    flex: 1;
    display: flex;
    flex-direction: column;

    .anniversary-name {
      font-size: 28rpx;
      font-weight: 500;
      color: #333;
    }

    .anniversary-days {
      font-size: 24rpx;
      color: #ff4757;
      margin-top: 6rpx;
    }
  }

  .arrow {
    font-size: 40rpx;
    color: #ccc;
  }
}

.menu-section {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 30rpx;
    margin-bottom: 20rpx;

    .title {
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
    }

    .more {
      font-size: 24rpx;
      color: #999;
    }
  }

  .menu-list {
    .menu-item {
      display: flex;
      margin: 0 30rpx 24rpx;
      padding: 24rpx;
      background: #fff;
      border-radius: 24rpx;

      .menu-cover {
        width: 160rpx;
        height: 160rpx;
        border-radius: 16rpx;
        margin-right: 24rpx;

        &.empty-cover {
          background: #f5f5f5;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 60rpx;
        }
      }

      .menu-info {
        flex: 1;
        display: flex;
        flex-direction: column;

        .menu-name {
          font-size: 30rpx;
          font-weight: 500;
          color: #333;
        }

        .menu-meta {
          font-size: 24rpx;
          color: #999;
          margin-top: 8rpx;
        }

        .menu-tags {
          margin-top: 12rpx;

          .tag {
            padding: 4rpx 16rpx;
            border-radius: 8rpx;
            font-size: 22rpx;

            &.primary { background: #fff0f3; color: #ff4757; }
            &.success { background: #f0fff4; color: #56ab2f; }
            &.warning { background: #fffaf0; color: #ff9500; }
          }
        }
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60rpx 0;

    text {
      font-size: 28rpx;
      color: #999;
    }

    .add-btn {
      margin-top: 20rpx;
      padding: 16rpx 40rpx;
      background: linear-gradient(135deg, #ff6b9d, #ff4757);
      color: #fff;
      border-radius: 40rpx;
      font-size: 28rpx;
    }
  }
}
</style>
