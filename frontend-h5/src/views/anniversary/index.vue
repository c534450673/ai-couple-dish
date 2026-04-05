<template>
  <div class="anniversary-page">
    <van-nav-bar title="纪念日" />

    <!-- 下拉刷新 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <!-- 恋爱计时 -->
      <div class="love-timer card">
        <div class="timer-main">
          <div class="timer-value">{{ timer.days }}</div>
          <div class="timer-unit">天</div>
        </div>
        <div class="timer-secondary">
          {{ timer.hours }}小时 {{ timer.minutes }}分 {{ timer.seconds }}秒
        </div>
        <div class="timer-label">在一起的每一天</div>
      </div>

      <!-- 即将到来 -->
      <div class="upcoming-section" v-if="upcomingList.length > 0">
        <div class="section-title">即将到来</div>
        <div class="upcoming-list">
          <div v-for="item in upcomingList" :key="item.id" class="upcoming-item card">
            <div class="upcoming-icon">
              <van-icon name="clock" size="24" color="#ff4757" />
            </div>
            <div class="upcoming-info">
              <div class="upcoming-name">{{ item.name }}</div>
              <div class="upcoming-date">{{ item.anniversaryDate }}</div>
            </div>
            <div class="upcoming-days">
              <span class="days">{{ item.days }}</span>
              <span class="unit">天后</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 全部纪念日 -->
      <div class="all-section">
        <div class="section-header">
          <span class="section-title">全部纪念日</span>
          <van-button size="small" type="primary" round icon="plus" @click="showAddDialog = true">
            添加
          </van-button>
        </div>

        <!-- 骨架屏 -->
        <div v-if="isSkeleton" class="anniversary-list">
          <div v-for="n in 3" :key="n" class="anniversary-item card skeleton-item">
            <div class="skeleton-info">
              <div class="skeleton-name"></div>
              <div class="skeleton-date"></div>
            </div>
            <div class="skeleton-days"></div>
          </div>
        </div>

        <div v-else class="anniversary-list">
          <div v-for="item in anniversaryList" :key="item.id" class="anniversary-item card">
            <div class="anniversary-info">
              <div class="anniversary-name">{{ item.name }}</div>
              <div class="anniversary-date">{{ item.anniversaryDate }}</div>
            </div>
            <div class="anniversary-days">
              <span class="days">{{ item.days }}</span>
              <span class="unit">天</span>
            </div>
          </div>
          <van-empty v-if="anniversaryList.length === 0" description="暂无纪念日">
            <van-button size="small" type="primary" round @click="showAddDialog = true">
              添加纪念日
            </van-button>
          </van-empty>
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

    <!-- 添加弹窗 -->
    <van-popup v-model:show="showAddDialog" position="bottom" round>
      <div class="add-dialog">
        <div class="dialog-header">
          <span>添加纪念日</span>
          <van-icon name="cross" @click="showAddDialog = false" />
        </div>
        <div class="dialog-content">
          <van-field
            v-model="addForm.name"
            label="名称"
            placeholder="如：在一起纪念日"
          />
          <van-field
            v-model="addForm.date"
            type="date"
            label="日期"
            placeholder="选择日期"
          />
          <van-radio-group v-model="addForm.type" direction="horizontal">
            <van-radio name="1">相识</van-radio>
            <van-radio name="2">恋爱</van-radio>
            <van-radio name="3">表白</van-radio>
            <van-radio name="4">其他</van-radio>
          </van-radio-group>
        </div>
        <div class="dialog-footer">
          <van-button type="primary" block round @click="handleAdd">保存</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { showToast } from 'vant'
import { anniversaryApi } from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const anniversaryList = ref([])
const upcomingList = ref([])
const showAddDialog = ref(false)
const refreshing = ref(false)
const isSkeleton = ref(true)

const addForm = ref({
  name: '',
  date: '',
  type: '2'
})

let timerInterval = null
const timer = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })

const loadAnniversaryList = async () => {
  try {
    const res = await anniversaryApi.getAnniversaryList()
    anniversaryList.value = res.data || []
    upcomingList.value = anniversaryList.value.filter(a => a.days > 0 && a.days <= 30)
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
  loadAnniversaryList()
}

const startTimer = () => {
  timerInterval = setInterval(() => {
    const startDate = userStore.coupleInfo?.startDate
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

const handleAdd = async () => {
  if (!addForm.value.name || !addForm.value.date) {
    showToast('请填写完整')
    return
  }

  try {
    await anniversaryApi.addAnniversary(addForm.value)
    showToast('添加成功')
    showAddDialog.value = false
    onRefresh()
  } catch (error) {
    showToast('添加失败')
  }
}

onMounted(() => {
  loadAnniversaryList()
  startTimer()
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<style lang="scss" scoped>
.anniversary-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 70px;
}

.love-timer {
  text-align: center;
  margin: 12px 16px;
  padding: 24px;
  background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
  color: #fff;

  .timer-main {
    display: flex;
    justify-content: center;
    align-items: baseline;
    gap: 8px;

    .timer-value {
      font-size: 64px;
      font-weight: 700;
    }

    .timer-unit {
      font-size: 24px;
    }
  }

  .timer-secondary {
    font-size: 16px;
    opacity: 0.9;
    margin: 8px 0;
  }

  .timer-label {
    font-size: 12px;
    opacity: 0.7;
  }
}

.upcoming-section,
.all-section {
  padding: 0 16px;

  .section-title {
    font-size: 14px;
    color: #999;
    margin-bottom: 12px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
}

.upcoming-list {
  .upcoming-item {
    display: flex;
    align-items: center;
    padding: 16px;
    margin-bottom: 12px;

    .upcoming-icon {
      width: 48px;
      height: 48px;
      background: #fff0f3;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
    }

    .upcoming-info {
      flex: 1;

      .upcoming-name {
        font-size: 15px;
        font-weight: 500;
        color: #333;
      }

      .upcoming-date {
        font-size: 12px;
        color: #999;
        margin-top: 4px;
      }
    }

    .upcoming-days {
      text-align: right;

      .days {
        font-size: 24px;
        font-weight: 700;
        color: #ff4757;
      }

      .unit {
        font-size: 12px;
        color: #999;
      }
    }
  }
}

.anniversary-list {
  .anniversary-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    margin-bottom: 12px;

    .anniversary-name {
      font-size: 15px;
      font-weight: 500;
      color: #333;
    }

    .anniversary-date {
      font-size: 12px;
      color: #999;
      margin-top: 4px;
    }

    .anniversary-days {
      text-align: right;

      .days {
        font-size: 20px;
        font-weight: 700;
        color: #ff4757;
      }

      .unit {
        font-size: 12px;
        color: #999;
        margin-left: 2px;
      }
    }
  }
}

.add-dialog {
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

  .dialog-content {
    .van-field {
      margin-bottom: 12px;
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

  .skeleton-info {
    .skeleton-name {
      width: 60%;
      height: 15px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .skeleton-date {
      width: 40%;
      height: 12px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }
  }

  .skeleton-days {
    width: 50px;
    height: 24px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
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
