<template>
  <div class="anniversary-page">
    <header class="page-topbar">
      <h1 class="page-title">
        纪念日
      </h1>
    </header>

    <van-pull-refresh
      v-model="refreshing"
      class="anniversary-body"
      @refresh="onRefresh"
    >
      <!-- 恋爱计时 -->
      <div class="love-timer">
        <i class="deco deco-1" />
        <i class="deco deco-2" />
        <div class="timer-main">
          <div class="timer-value">
            {{ timer.days }}
          </div>
          <div class="timer-unit">
            天
          </div>
        </div>
        <div class="timer-secondary">
          {{ timer.hours }} 小时 {{ timer.minutes }} 分 {{ timer.seconds }} 秒
        </div>
        <div class="timer-label">
          在一起的每一天
        </div>
      </div>

      <!-- 即将到来 -->
      <div
        v-if="upcomingList.length > 0"
        class="section"
      >
        <div class="section-title">
          即将到来
        </div>
        <div
          v-for="item in upcomingList"
          :key="item.id"
          class="anniversary-card"
        >
          <span class="icon">
            <van-icon name="underway-o" size="22" />
          </span>
          <div class="info">
            <div class="name">
              {{ item.name }}
            </div>
            <div class="date">
              {{ item.anniversaryDate }}
            </div>
          </div>
          <div class="days">
            <span class="num">{{ item.days }}</span>
            <span class="unit">天后</span>
          </div>
        </div>
      </div>

      <!-- 全部纪念日 -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">全部纪念日</span>
          <van-button
            size="small"
            type="primary"
            round
            icon="plus"
            @click="showAddDialog = true"
          >
            添加
          </van-button>
        </div>

        <div v-if="isSkeleton">
          <div
            v-for="n in 3"
            :key="n"
            class="anniversary-card skeleton"
          >
            <div class="info">
              <div class="sk sk-line sk-name" />
              <div class="sk sk-line sk-date" />
            </div>
            <div class="sk sk-days" />
          </div>
        </div>

        <div v-else>
          <div
            v-for="item in anniversaryList"
            :key="item.id"
            class="anniversary-card"
          >
            <span class="icon soft">
              <van-icon name="gem-o" size="20" />
            </span>
            <div class="info">
              <div class="name">
                {{ item.name }}
              </div>
              <div class="date">
                {{ item.anniversaryDate }}
              </div>
            </div>
            <div class="days">
              <span class="num">{{ item.days }}</span>
              <span class="unit">天</span>
            </div>
          </div>
          <van-empty
            v-if="anniversaryList.length === 0"
            description="暂无纪念日"
          >
            <van-button
              size="small"
              type="primary"
              round
              @click="showAddDialog = true"
            >
              添加纪念日
            </van-button>
          </van-empty>
        </div>
      </div>
    </van-pull-refresh>

    <app-tabbar />

    <!-- 添加弹窗 -->
    <van-popup
      v-model:show="showAddDialog"
      position="bottom"
      round
    >
      <div class="add-dialog">
        <div class="dialog-header">
          <span>添加纪念日</span>
          <van-icon
            name="cross"
            @click="showAddDialog = false"
          />
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
          <van-radio-group
            v-model="addForm.type"
            direction="horizontal"
          >
            <van-radio name="1">
              相识
            </van-radio>
            <van-radio name="2">
              恋爱
            </van-radio>
            <van-radio name="3">
              表白
            </van-radio>
            <van-radio name="4">
              其他
            </van-radio>
          </van-radio-group>
        </div>
        <div class="dialog-footer">
          <van-button
            type="primary"
            block
            round
            @click="handleAdd"
          >
            保存
          </van-button>
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
import AppTabbar from '@/components/AppTabbar.vue'

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
  background: $color-background;
  padding-bottom: 96px;
}

.page-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  @include glass(0.7);

  .page-title { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
}

.anniversary-body { padding: $space-4 $page-padding 0; }

.love-timer {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: $space-8 $space-6;
  border-radius: $radius-xl;
  background: $gradient-primary;
  color: $color-on-primary;
  box-shadow: $shadow-float;
  margin-bottom: $space-6;

  .deco {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.12);
  }
  .deco-1 { width: 120px; height: 120px; top: -40px; right: -30px; }
  .deco-2 { width: 80px; height: 80px; bottom: -30px; left: -20px; }

  .timer-main {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: baseline;
    gap: $space-2;

    .timer-value { font-size: 64px; font-weight: $fw-bold; line-height: 1; }
    .timer-unit { font-size: $fs-headline; }
  }

  .timer-secondary { position: relative; font-size: $fs-body; opacity: 0.92; margin: $space-3 0 $space-1; }
  .timer-label { position: relative; font-size: $fs-caption; opacity: 0.8; }
}

.section {
  margin-bottom: $space-6;

  .section-title { font-size: $fs-label; font-weight: $fw-semibold; color: $color-on-surface; margin-bottom: $space-3; padding: 0 $space-1; }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-3;
    padding: 0 $space-1;
    .section-title { margin-bottom: 0; }
  }
}

.anniversary-card {
  display: flex;
  align-items: center;
  @include card($radius-lg, $space-4);
  margin-bottom: $space-3;

  .icon {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: $color-primary-fixed;
    color: $color-primary;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: $space-3;
    flex-shrink: 0;

    &.soft { background: $color-secondary-container; color: $color-on-secondary-container; }
  }

  .info {
    flex: 1;
    .name { font-size: $fs-label; font-weight: $fw-medium; color: $color-on-surface; }
    .date { font-size: $fs-caption; color: $color-on-surface-variant; margin-top: 2px; }
  }

  .days {
    text-align: right;
    .num { font-size: $fs-headline; font-weight: $fw-bold; color: $color-primary; }
    .unit { font-size: $fs-caption; color: $color-on-surface-variant; margin-left: 2px; }
  }
}

.add-dialog {
  padding: $space-5;

  .dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-4;
    span { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
    .van-icon { color: $color-on-surface-variant; }
  }

  .dialog-content {
    :deep(.van-field) { margin-bottom: $space-3; }
    :deep(.van-radio) { margin: $space-2 $space-4 $space-2 0; }
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
  .sk-line { border-radius: 4px; }
  .sk-name { width: 60%; height: 15px; margin-bottom: 8px; }
  .sk-date { width: 40%; height: 12px; }
  .sk-days { width: 44px; height: 24px; border-radius: 4px; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
