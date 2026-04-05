<template>
  <view class="anniversary-page">
    <!-- 恋爱计时 -->
    <view class="love-timer">
      <view class="timer-main">
        <text class="days">{{ timer.days }}</text>
        <text class="unit">天</text>
      </view>
      <view class="timer-secondary">
        {{ timer.hours }}小时 {{ timer.minutes }}分 {{ timer.seconds }}秒
      </view>
      <view class="timer-label">在一起的每一天</view>
    </view>

    <!-- 即将到来 -->
    <view class="section" v-if="upcomingList.length > 0">
      <view class="section-title">即将到来</view>
      <view v-for="item in upcomingList" :key="item.id" class="anniversary-item upcoming">
        <view class="anniversary-icon">⏰</view>
        <view class="anniversary-info">
          <text class="anniversary-name">{{ item.name }}</text>
          <text class="anniversary-date">{{ item.anniversaryDate }}</text>
        </view>
        <view class="anniversary-days">
          <text class="days">{{ item.days }}</text>
          <text class="unit">天后</text>
        </view>
      </view>
    </view>

    <!-- 全部纪念日 -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">全部纪念日</text>
        <view class="add-btn" @click="showAddDialog = true">➕ 添加</view>
      </view>
      <view v-for="item in anniversaryList" :key="item.id" class="anniversary-item">
        <view class="anniversary-info">
          <text class="anniversary-name">{{ item.name }}</text>
          <text class="anniversary-date">{{ item.anniversaryDate }}</text>
        </view>
        <view class="anniversary-days">
          <text class="days">{{ item.days }}</text>
          <text class="unit">天</text>
        </view>
      </view>
      <view v-if="anniversaryList.length === 0" class="empty-state">
        <text>暂无纪念日</text>
      </view>
    </view>

    <!-- 添加弹窗 -->
    <view class="dialog" v-if="showAddDialog" @click="showAddDialog = false">
      <view class="dialog-content" @click.stop>
        <view class="dialog-header">
          <text>添加纪念日</text>
          <text class="close" @click="showAddDialog = false">✕</text>
        </view>
        <input v-model="addForm.name" class="input" placeholder="如：在一起纪念日" />
        <picker mode="date" @change="onDateChange">
          <input v-model="addForm.date" class="input" placeholder="选择日期" disabled />
        </picker>
        <view class="type-select">
          <view
            v-for="type in typeList"
            :key="type.value"
            class="type-item"
            :class="{ active: addForm.type === type.value }"
            @click="addForm.type = type.value"
          >
            {{ type.label }}
          </view>
        </view>
        <button class="submit-btn" @click="handleAdd">保存</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/store/user'
import { anniversaryApi } from '@/api'

const userStore = useUserStore()

const anniversaryList = ref([])
const upcomingList = ref([])
const showAddDialog = ref(false)

const addForm = ref({
  name: '',
  date: '',
  type: '2'
})

const typeList = [
  { label: '相识', value: '1' },
  { label: '恋爱', value: '2' },
  { label: '表白', value: '3' },
  { label: '其他', value: '4' }
]

let timerInterval = null
const timer = ref({ days: 0, hours: 0, minutes: 0, seconds: 0 })

const loadAnniversaryList = async () => {
  uni.showLoading({ title: '加载中...' })
  try {
    const res = await anniversaryApi.getAnniversaryList()
    anniversaryList.value = res.data || []
    upcomingList.value = anniversaryList.value.filter(a => a.days > 0 && a.days <= 30)
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
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

const onDateChange = (e) => {
  addForm.value.date = e.detail.value
}

const handleAdd = async () => {
  if (!addForm.value.name || !addForm.value.date) {
    uni.showToast({ title: '请填写完整', icon: 'none' })
    return
  }

  try {
    await anniversaryApi.addAnniversary(addForm.value)
    uni.showToast({ title: '添加成功', icon: 'success' })
    showAddDialog.value = false
    loadAnniversaryList()
  } catch (error) {
    uni.showToast({ title: '添加失败', icon: 'none' })
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
  padding-bottom: 40rpx;
}

.love-timer {
  background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
  color: #fff;
  text-align: center;
  padding: 60rpx 40rpx;

  .timer-main {
    display: flex;
    justify-content: center;
    align-items: baseline;
    gap: 12rpx;

    .days {
      font-size: 128rpx;
      font-weight: 700;
    }

    .unit {
      font-size: 48rpx;
    }
  }

  .timer-secondary {
    font-size: 32rpx;
    opacity: 0.9;
    margin: 16rpx 0;
  }

  .timer-label {
    font-size: 24rpx;
    opacity: 0.7;
  }
}

.section {
  margin: 24rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 30rpx;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20rpx;
  }

  .section-title {
    font-size: 28rpx;
    color: #999;
  }

  .add-btn {
    font-size: 28rpx;
    color: #ff4757;
  }

  .anniversary-item {
    display: flex;
    align-items: center;
    padding: 24rpx 0;
    border-bottom: 1px solid #f5f5f5;

    &:last-child {
      border-bottom: none;
    }

    &.upcoming {
      .anniversary-icon {
        font-size: 48rpx;
        margin-right: 20rpx;
      }
    }

    .anniversary-info {
      flex: 1;
      display: flex;
      flex-direction: column;

      .anniversary-name {
        font-size: 30rpx;
        font-weight: 500;
        color: #333;
      }

      .anniversary-date {
        font-size: 24rpx;
        color: #999;
        margin-top: 6rpx;
      }
    }

    .anniversary-days {
      text-align: right;

      .days {
        font-size: 48rpx;
        font-weight: 700;
        color: #ff4757;
      }

      .unit {
        font-size: 24rpx;
        color: #999;
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

    .type-select {
      display: flex;
      gap: 16rpx;
      margin-bottom: 30rpx;

      .type-item {
        flex: 1;
        height: 80rpx;
        background: #f5f5f5;
        border-radius: 16rpx;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26rpx;
        color: #666;

        &.active {
          background: #fff0f3;
          color: #ff4757;
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
