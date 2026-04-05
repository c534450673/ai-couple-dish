<template>
  <div class="home-page">
    <!-- 用户信息头部 -->
    <div class="home-header">
      <div class="user-info">
        <img class="avatar" :src="userInfo?.avatarUrl || defaultAvatar" alt="avatar" />
        <div class="info">
          <div class="name">{{ userInfo?.nickName || '亲爱的' }}</div>
          <div class="couple-name">和 {{ coupleInfo?.partnerName || 'TA' }} 的私密空间</div>
        </div>
      </div>
      <van-icon name="setting-o" size="24" @click="$router.push('/settings')" />
    </div>

    <!-- 下拉刷新 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <!-- 恋爱计时 -->
      <div class="love-timer card" @click="$router.push('/anniversary')">
        <div class="timer-icon">
          <van-icon name="like" size="32" color="#ff4757" />
        </div>
        <div class="timer-content">
          <div class="timer-label">在一起</div>
          <div class="timer-value">
            <span class="days">{{ loveDays.days }}</span>
            <span class="unit">天</span>
            <span class="time">{{ loveDays.hours }}:{{ loveDays.minutes }}:{{ loveDays.seconds }}</span>
          </div>
        </div>
        <van-icon name="arrow" color="#ccc" />
      </div>

      <!-- 快捷功能 -->
      <div class="quick-actions">
        <div class="action-item" @click="$router.push('/menu/add')">
          <div class="action-icon add">
            <van-icon name="plus" size="24" color="#fff" />
          </div>
          <span>添加餐厅</span>
        </div>
        <div class="action-item" @click="$router.push('/feed')">
          <div class="action-icon feed">
            <van-icon name="gift" size="24" color="#fff" />
          </div>
          <span>投喂TA</span>
        </div>
        <div class="action-item" @click="$router.push('/anniversary')">
          <div class="action-icon anniversary">
            <van-icon name="calendar" size="24" color="#fff" />
          </div>
          <span>纪念日</span>
        </div>
        <div class="action-item" @click="$router.push('/wish')">
          <div class="action-icon wish">
            <van-icon name="star" size="24" color="#fff" />
          </div>
          <span>心愿单</span>
        </div>
      </div>

      <!-- 数据统计 -->
      <div class="stats-grid">
        <div class="stat-item" @click="$router.push('/menu?type=wantToGo')">
          <div class="stat-value">{{ stats.wantToGoCount || 0 }}</div>
          <div class="stat-label">想去</div>
        </div>
        <div class="stat-item" @click="$router.push('/menu?type=beenTo')">
          <div class="stat-value">{{ stats.beenToCount || 0 }}</div>
          <div class="stat-label">去过</div>
        </div>
        <div class="stat-item" @click="$router.push('/menu?type=recommended')">
          <div class="stat-value">{{ stats.recommendedCount || 0 }}</div>
          <div class="stat-label">种草</div>
        </div>
        <div class="stat-item" @click="$router.push('/feed')">
          <div class="stat-value">{{ stats.feedCount || 0 }}</div>
          <div class="stat-label">投喂</div>
        </div>
      </div>

      <!-- 即将到来的纪念日 -->
      <div class="upcoming-anniversary card" v-if="upcomingAnniversary" @click="$router.push('/anniversary')">
        <div class="anniversary-icon">
          <van-icon name="clock" size="20" color="#ff4757" />
        </div>
        <div class="anniversary-info">
          <div class="anniversary-name">{{ upcomingAnniversary.name }}</div>
          <div class="anniversary-days">还有 {{ upcomingAnniversary.days }} 天</div>
        </div>
        <van-icon name="arrow" color="#ccc" />
      </div>

      <!-- 私密菜单列表 -->
      <div class="menu-section">
        <div class="section-header">
          <span class="title">私密菜单</span>
          <span class="more" @click="$router.push('/menu')">查看全部</span>
        </div>

        <!-- 骨架屏 -->
        <div v-if="isSkeleton" class="menu-list">
          <div v-for="n in 3" :key="n" class="menu-item skeleton-item">
            <div class="menu-cover skeleton-cover"></div>
            <div class="menu-info">
              <div class="skeleton-title"></div>
              <div class="skeleton-meta"></div>
            </div>
          </div>
        </div>

        <div v-else class="menu-list">
          <div
            v-for="item in recentMenus"
            :key="item.id"
            class="menu-item"
            @click="$router.push(`/menu/${item.id}`)"
          >
            <div class="menu-cover">
              <img v-if="item.coverImage" v-lazy="item.coverImage" :alt="item.restaurantName" loading="lazy" />
              <van-icon v-else name="shop-o" size="32" color="#ccc" />
            </div>
            <div class="menu-info">
              <div class="menu-name">{{ item.restaurantName }}</div>
              <div class="menu-meta">
                <van-icon name="location-o" size="12" />
                {{ item.location || '暂无位置' }}
              </div>
              <div class="menu-tags">
                <van-tag type="primary" size="small">{{ getStatusText(item.status) }}</van-tag>
              </div>
            </div>
          </div>
          <van-empty v-if="recentMenus.length === 0" description="暂无餐厅记录" />
        </div>
      </div>
    </van-pull-refresh>

    <!-- 底部导航 -->
    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/menu" icon="shop-o">餐厅</van-tabbar-item>
      <van-tabbar-item to="/feed" icon="gift-o">投喂</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { coupleApi, menuApi, anniversaryApi } from '@/api'

const userStore = useUserStore()

const activeTab = ref(0)
const defaultAvatar = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'
const recentMenus = ref([])
const stats = ref({})
const upcomingAnniversary = ref(null)
const loveDays = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })
const refreshing = ref(false)
const isSkeleton = ref(true)

const userInfo = computed(() => userStore.userInfo)
const coupleInfo = computed(() => userStore.coupleInfo)

let timer = null

const loadHomeData = async (isRefresh = false) => {
  if (!isRefresh) {
    refreshing.value = false
  }

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
    loveDays.value = timerRes.data || { days: 0, hours: 0, minutes: 0, seconds: 0 }
  } catch (error) {
    console.error('加载失败', error)
  } finally {
    refreshing.value = false
    isSkeleton.value = false
  }
}

const onRefresh = () => {
  isSkeleton.value = true
  loadHomeData(true)
}

const startTimer = () => {
  timer = setInterval(() => {
    const startDate = coupleInfo.value?.startDate
    if (startDate) {
      const now = new Date()
      const start = new Date(startDate)
      const diff = now - start

      loveDays.value = {
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

onMounted(() => {
  loadHomeData()
  startTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 60px;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
  color: #fff;

  .user-info {
    display: flex;
    align-items: center;

    .avatar {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      margin-right: 12px;
      border: 2px solid rgba(255, 255, 255, 0.3);
    }

    .info {
      .name {
        font-size: 18px;
        font-weight: 600;
      }

      .couple-name {
        font-size: 12px;
        opacity: 0.8;
      }
    }
  }
}

.love-timer {
  display: flex;
  align-items: center;
  margin: 16px;
  padding: 20px;

  .timer-icon {
    width: 56px;
    height: 56px;
    background: #fff0f3;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 16px;
  }

  .timer-content {
    flex: 1;

    .timer-label {
      font-size: 12px;
      color: #999;
      margin-bottom: 4px;
    }

    .timer-value {
      .days {
        font-size: 32px;
        font-weight: 700;
        color: #ff4757;
      }

      .unit {
        font-size: 14px;
        color: #666;
        margin-left: 4px;
      }

      .time {
        font-size: 14px;
        color: #999;
        margin-left: 12px;
      }
    }
  }
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 0 16px;
  margin-bottom: 16px;

  .action-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;

    .action-icon {
      width: 48px;
      height: 48px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 8px;

      &.add { background: linear-gradient(135deg, #ff6b9d, #ff4757); }
      &.feed { background: linear-gradient(135deg, #ffd93d, #ff9500); }
      &.anniversary { background: linear-gradient(135deg, #6bcbff, #4a90e2); }
      &.wish { background: linear-gradient(135deg, #a8e6cf, #56ab2f); }
    }

    span {
      font-size: 12px;
      color: #666;
    }
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: #eee;
  margin: 0 16px 16px;
  border-radius: 12px;
  overflow: hidden;

  .stat-item {
    background: #fff;
    padding: 16px 0;
    text-align: center;
    cursor: pointer;

    .stat-value {
      font-size: 20px;
      font-weight: 700;
      color: #ff4757;
    }

    .stat-label {
      font-size: 12px;
      color: #999;
      margin-top: 4px;
    }
  }
}

.upcoming-anniversary {
  display: flex;
  align-items: center;
  margin: 0 16px 16px;
  padding: 16px;

  .anniversary-icon {
    width: 40px;
    height: 40px;
    background: #fff0f3;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
  }

  .anniversary-info {
    flex: 1;

    .anniversary-name {
      font-size: 14px;
      font-weight: 500;
      color: #333;
    }

    .anniversary-days {
      font-size: 12px;
      color: #ff4757;
      margin-top: 2px;
    }
  }
}

.menu-section {
  padding: 0 16px;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .more {
      font-size: 12px;
      color: #999;
    }
  }

  .menu-list {
    .menu-item {
      display: flex;
      background: #fff;
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 12px;

      .menu-cover {
        width: 80px;
        height: 80px;
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

      .menu-info {
        flex: 1;

        .menu-name {
          font-size: 15px;
          font-weight: 500;
          color: #333;
          margin-bottom: 4px;
        }

        .menu-meta {
          font-size: 12px;
          color: #999;
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .menu-tags {
          margin-top: 8px;
        }
      }
    }
  }
}

// 骨架屏样式
.skeleton-item {
  pointer-events: none;

  .skeleton-cover {
    width: 80px;
    height: 80px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 8px;
  }

  .menu-info {
    .skeleton-title {
      width: 60%;
      height: 15px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .skeleton-meta {
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
</style>
