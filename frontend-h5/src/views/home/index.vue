<template>
  <div class="home-page">
    <!-- 固定玻璃顶栏：双头像 + 恋爱天数 -->
    <header class="home-topbar">
      <img
        class="avatar"
        :src="userInfo?.avatarUrl || defaultAvatar"
        alt="me"
        @click="$router.push('/settings')"
      >
      <div class="love-days">
        恋爱 <span class="num">{{ loveDays.days }}</span> 天
      </div>
      <img
        class="avatar"
        :src="coupleInfo?.partner?.avatarUrl || partnerAvatar"
        alt="ta"
      >
    </header>

    <van-pull-refresh
      v-model="refreshing"
      class="home-body"
      @refresh="onRefresh"
    >
      <!-- 快捷功能 -->
      <section class="quick-actions">
        <button
          class="qa-item"
          @click="$router.push('/menu/add')"
        >
          <span class="qa-icon qa-add"><van-icon name="plus" size="20" /></span>
          <span class="qa-text">添加餐厅</span>
        </button>
        <button
          class="qa-item"
          @click="$router.push('/feed')"
        >
          <span class="qa-icon qa-feed"><van-icon name="gift-o" size="20" /></span>
          <span class="qa-text">投喂</span>
        </button>
        <button
          class="qa-item"
          @click="$router.push('/anniversary')"
        >
          <span class="qa-icon qa-anniv"><van-icon name="calendar-o" size="20" /></span>
          <span class="qa-text">纪念日</span>
        </button>
        <button
          class="qa-item"
          @click="$router.push('/wish')"
        >
          <span class="qa-icon qa-wish"><van-icon name="like-o" size="20" /></span>
          <span class="qa-text">心愿单</span>
        </button>
      </section>

      <!-- 统计卡片 -->
      <section class="stats-card">
        <div
          class="stat"
          @click="$router.push('/menu?type=wantToGo')"
        >
          <span class="stat-label">想去</span>
          <span class="stat-value">{{ stats.wantToGoCount || 0 }}</span>
        </div>
        <i class="stat-divider" />
        <div
          class="stat"
          @click="$router.push('/menu?type=beenTo')"
        >
          <span class="stat-label">去过</span>
          <span class="stat-value">{{ stats.beenToCount || 0 }}</span>
        </div>
        <i class="stat-divider" />
        <div
          class="stat"
          @click="$router.push('/menu?type=recommended')"
        >
          <span class="stat-label">种草</span>
          <span class="stat-value">{{ stats.recommendedCount || 0 }}</span>
        </div>
        <i class="stat-divider" />
        <div
          class="stat"
          @click="$router.push('/map')"
        >
          <span class="stat-label">地图</span>
          <span class="stat-value"><van-icon name="location-o" size="20" /></span>
        </div>
      </section>

      <!-- 即将到来的纪念日 -->
      <section
        v-if="upcomingAnniversary"
        class="anniversary-card"
        @click="$router.push('/anniversary')"
      >
        <i class="deco" />
        <div class="anniv-row">
          <div class="anniv-left">
            <div class="anniv-label">
              即将到来的纪念日
            </div>
            <div class="anniv-name">
              {{ upcomingAnniversary.name }}
            </div>
          </div>
          <div class="anniv-right">
            <span class="anniv-days">{{ upcomingAnniversary.days }}</span>
            <span class="anniv-unit">天</span>
          </div>
        </div>
        <div class="anniv-progress">
          <div
            class="bar"
            :style="{ width: anniversaryProgress + '%' }"
          />
        </div>
      </section>

      <!-- 最近记录 -->
      <section class="recent">
        <div class="section-head">
          <span class="title">最近记录</span>
          <span
            class="more"
            @click="$router.push('/menu')"
          >查看全部</span>
        </div>

        <!-- 骨架屏 -->
        <div v-if="isSkeleton">
          <div
            v-for="n in 2"
            :key="n"
            class="recent-card skeleton"
          >
            <div class="cover sk-block" />
            <div class="meta">
              <div class="sk-line sk-title" />
              <div class="sk-line sk-sub" />
            </div>
          </div>
        </div>

        <div v-else>
          <div
            v-for="item in recentMenus"
            :key="item.id"
            class="recent-card"
            @click="$router.push(`/menu/${item.id}`)"
          >
            <div class="cover">
              <img
                v-if="item.coverImage"
                v-lazy="item.coverImage"
                :alt="item.restaurantName"
              >
              <van-icon
                v-else
                name="shop-o"
                size="32"
                color="#d6c1c5"
              />
              <span class="status-pill">{{ getStatusText(item.status) }}</span>
            </div>
            <div class="meta">
              <div class="name">
                {{ item.restaurantName }}
              </div>
              <div class="sub">
                <van-icon name="location-o" size="13" />
                {{ item.location || '暂无位置' }}
              </div>
            </div>
          </div>
          <van-empty
            v-if="recentMenus.length === 0"
            description="还没有餐厅记录，去添加第一家吧"
          />
        </div>
      </section>
    </van-pull-refresh>

    <app-tabbar />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { coupleApi, menuApi, anniversaryApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

const userStore = useUserStore()

const defaultAvatar = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'
const partnerAvatar = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'
const recentMenus = ref([])
const stats = ref({})
const upcomingAnniversary = ref(null)
const loveDays = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })
const refreshing = ref(false)
const isSkeleton = ref(true)

const userInfo = computed(() => userStore.userInfo)
const coupleInfo = computed(() => userStore.coupleInfo)

const anniversaryProgress = computed(() => {
  const d = upcomingAnniversary.value?.days
  if (d == null) return 0
  return Math.max(6, Math.min(100, Math.round(((365 - d) / 365) * 100)))
})

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
  background: $color-background;
}

// 固定玻璃顶栏
.home-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $page-padding;
  @include glass(0.7);
  box-shadow: $shadow-card;

  .avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid rgba(255, 255, 255, 0.6);
  }

  .love-days {
    font-size: $fs-title;
    font-weight: $fw-semibold;
    color: $color-primary;
    letter-spacing: -0.01em;

    .num { font-size: 22px; }
  }
}

.home-body {
  padding: 76px $page-padding 96px;
  min-height: 100vh;
}

// 快捷功能
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $space-3;
  margin-bottom: $space-8;

  .qa-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-2;
    padding: $space-3 0;
    background: $color-surface-lowest;
    border: none;
    border-radius: $radius-lg;
    box-shadow: $shadow-card;
    cursor: pointer;
    transition: transform $transition-base;

    &:active { transform: scale(0.95); }

    .qa-icon {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .qa-add { background: $color-primary-container; color: $color-on-primary-container; }
    .qa-feed { background: $color-secondary-container; color: $color-on-secondary-container; }
    .qa-anniv { background: $color-surface-variant; color: $color-on-surface-variant; }
    .qa-wish { background: $color-primary-fixed; color: $color-primary; }

    .qa-text {
      font-size: $fs-caption;
      color: $color-on-surface;
    }
  }
}

// 统计卡片
.stats-card {
  display: flex;
  align-items: center;
  @include card($radius-lg, $space-4);
  margin-bottom: $space-8;

  .stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-1;
    cursor: pointer;

    .stat-label { font-size: $fs-caption; color: $color-on-surface-variant; }
    .stat-value {
      font-size: $fs-headline;
      font-weight: $fw-bold;
      color: $color-primary;
      line-height: 1;
    }
  }

  .stat-divider {
    width: 1px;
    height: 28px;
    background: $color-surface-variant;
  }
}

// 纪念日卡片
.anniversary-card {
  position: relative;
  overflow: hidden;
  @include card($radius-xl, $space-6);
  margin-bottom: $space-8;
  cursor: pointer;

  .deco {
    position: absolute;
    top: 0;
    right: 0;
    width: 120px;
    height: 120px;
    background: $color-primary-container;
    opacity: 0.18;
    border-bottom-left-radius: 100%;
  }

  .anniv-row {
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: $space-4;
  }

  .anniv-label { font-size: $fs-caption; color: $color-on-surface-variant; margin-bottom: $space-1; }
  .anniv-name { font-size: $fs-headline; font-weight: $fw-semibold; color: $color-on-surface; }
  .anniv-right { line-height: 1; }
  .anniv-days { font-size: $fs-display; font-weight: $fw-bold; color: $color-primary; }
  .anniv-unit { font-size: $fs-caption; color: $color-on-surface-variant; margin-left: 2px; }

  .anniv-progress {
    position: relative;
    height: 8px;
    border-radius: $radius-pill;
    background: $color-surface-variant;
    overflow: hidden;

    .bar {
      height: 100%;
      border-radius: $radius-pill;
      background: $gradient-primary;
      transition: width 600ms $ease-standard;
    }
  }
}

// 最近记录
.recent {
  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-4;
    padding: 0 $space-1;

    .title { font-size: $fs-label; font-weight: $fw-semibold; color: $color-on-surface; }
    .more { font-size: $fs-caption; color: $color-primary; }
  }

  .recent-card {
    background: $color-surface-lowest;
    border-radius: $radius-lg;
    box-shadow: $shadow-card;
    overflow: hidden;
    margin-bottom: $space-4;
    transition: transform $transition-base;

    &:active { transform: scale(0.98); }

    .cover {
      position: relative;
      height: 160px;
      background: $color-surface-low;
      display: flex;
      align-items: center;
      justify-content: center;

      img { width: 100%; height: 100%; object-fit: cover; }

      .status-pill {
        position: absolute;
        top: $space-3;
        right: $space-3;
        padding: 2px 10px;
        font-size: $fs-caption;
        color: $color-primary;
        @include glass(0.8);
        border-radius: $radius-pill;
      }
    }

    .meta {
      padding: $space-4;

      .name {
        font-size: $fs-label;
        font-weight: $fw-semibold;
        color: $color-on-surface;
        margin-bottom: $space-1;
        @include ellipsis;
      }

      .sub {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: $fs-caption;
        color: $color-on-surface-variant;
      }
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

  .sk-block { height: 160px; }
  .meta { padding: $space-4; }
  .sk-line { height: 14px; border-radius: 4px; }
  .sk-title { width: 60%; margin-bottom: $space-2; }
  .sk-sub { width: 40%; height: 12px; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
