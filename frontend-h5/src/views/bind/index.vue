<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { coupleApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const myCoupleCode = ref('')
const partnerCode = ref('')
const generating = ref(false)
const binding = ref(false)

const generateCode = async () => {
  generating.value = true
  try {
    const res = await coupleApi.generateCoupleCode()
    // 接口直接返回情侣码字符串（兼容对象返回）
    myCoupleCode.value = typeof res.data === 'string' ? res.data : (res.data?.coupleCode || '')
    showToast('情侣码已生成')
  } catch (error) {
    showToast('生成失败')
  } finally {
    generating.value = false
  }
}

const handleBind = async () => {
  if (!partnerCode.value || partnerCode.value.length < 6) {
    showToast('请输入正确的情侣码')
    return
  }

  binding.value = true
  showLoadingToast({ message: '绑定中...', forbidClick: true })
  try {
    await coupleApi.bindCouple({ coupleCode: partnerCode.value })
    await userStore.getCoupleInfo()
    closeToast()
    showToast('绑定成功')
    router.replace('/home')
  } catch (error) {
    closeToast()
    showToast(error.message || '绑定失败')
  } finally {
    binding.value = false
  }
}

onMounted(() => {
  generateCode()
})
</script>

<template>
  <div class="bind-page">
    <!-- 渐变头部 -->
    <div class="bind-hero">
      <div class="hero-icon">
        <van-icon
          name="like"
          size="32"
        />
      </div>
      <h1>绑定 TA</h1>
      <p>和亲爱的 TA 开始私密美食之旅</p>
    </div>

    <div class="bind-content">
      <!-- 我的情侣码 -->
      <div class="my-code">
        <div class="code-label">
          我的情侣码
        </div>
        <div
          v-if="myCoupleCode"
          class="code-value"
        >
          {{ myCoupleCode }}
        </div>
        <div
          v-else
          class="code-value loading"
        >
          生成中...
        </div>
        <div class="code-desc">
          让 TA 输入这个码，或扫码绑定
        </div>
        <van-button
          type="primary"
          size="small"
          round
          :loading="generating"
          @click="generateCode"
        >
          {{ myCoupleCode ? '重新生成' : '生成情侣码' }}
        </van-button>
      </div>

      <div class="divider">
        <span>或</span>
      </div>

      <!-- 绑定TA -->
      <div class="bind-form">
        <div class="form-title">
          绑定 TA 的情侣码
        </div>
        <van-field
          v-model="partnerCode"
          class="code-field"
          placeholder="请输入 TA 的情侣码"
          maxlength="8"
          :disabled="binding"
        />
        <van-button
          type="primary"
          block
          round
          :loading="binding"
          :disabled="!partnerCode || partnerCode.length < 6"
          @click="handleBind"
        >
          绑定
        </van-button>
      </div>
    </div>

    <div class="bind-tip">
      <van-icon name="info-o" />
      <span>绑定后你们可以看到彼此的私密菜单和美食笔记</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.bind-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 32px;
}

.bind-hero {
  text-align: center;
  padding: 56px $page-padding 36px;
  background: $gradient-romance;
  border-bottom-left-radius: $radius-xl;
  border-bottom-right-radius: $radius-xl;

  .hero-icon {
    width: 72px;
    height: 72px;
    margin: 0 auto 16px;
    border-radius: $radius-xl;
    background: $color-surface-lowest;
    color: $color-primary;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: $shadow-card;
  }

  h1 { font-size: $fs-headline; font-weight: $fw-bold; color: $color-on-surface; margin-bottom: $space-2; }
  p { font-size: $fs-label; color: $color-on-surface-variant; }
}

.bind-content {
  padding: $space-6 $page-padding 0;
}

.my-code {
  @include card($radius-xl, $space-6);
  text-align: center;

  .code-label { font-size: $fs-label; color: $color-on-surface-variant; margin-bottom: $space-3; }

  .code-value {
    font-size: 38px;
    font-weight: $fw-bold;
    color: $color-primary;
    letter-spacing: 6px;
    margin-bottom: $space-2;

    &.loading { font-size: $fs-body; color: $color-on-surface-variant; letter-spacing: normal; }
  }

  .code-desc { font-size: $fs-caption; color: $color-on-surface-variant; margin-bottom: $space-4; }
}

.divider {
  text-align: center;
  margin: $space-6 0;
  position: relative;

  &::before,
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    width: 38%;
    height: 1px;
    background: $color-outline-variant;
  }
  &::before { left: 0; }
  &::after { right: 0; }

  span {
    background: $color-background;
    padding: 0 $space-4;
    color: $color-on-surface-variant;
    font-size: $fs-caption;
    position: relative;
    z-index: 1;
  }
}

.bind-form {
  @include card($radius-xl, $space-6);

  .form-title { font-size: $fs-label; color: $color-on-surface; font-weight: $fw-medium; margin-bottom: $space-4; }

  .code-field {
    margin-bottom: $space-4;
    background: $color-surface-low;
    border-radius: $radius-md;
    padding: 6px 12px;
  }
}

.bind-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $space-2;
  margin-top: $space-6;
  padding: 0 $page-padding;
  font-size: $fs-caption;
  color: $color-on-surface-variant;
}
</style>
