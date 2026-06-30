<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api'
import AgreementDialog from '@/components/AgreementDialog.vue'
import wechatIcon from '@/assets/images/wechat.svg'
import appleIcon from '@/assets/images/apple.svg'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const phone = ref('')
const verifyCode = ref('')
const countdown = ref(0)
const loading = ref(false)
const agreed = ref(false)
const showAgreementDialog = ref(false)
const showPrivacyDialog = ref(false)

let countdownTimer = null

const sendVerifyCode = async () => {
  if (!phone.value || phone.value.length !== 11) {
    showToast('请输入正确的手机号')
    return
  }

  try {
    await userApi.sendVerifyCode(phone.value)
    showToast('验证码已发送')
    countdown.value = 60
    startCountdown()
  } catch (error) {
    showToast(error.message || '发送失败')
  }
}

const startCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

const handleLogin = async () => {
  if (!agreed.value) {
    showToast('请先同意用户协议')
    return
  }

  if (!phone.value || phone.value.length !== 11) {
    showToast('请输入正确的手机号')
    return
  }

  if (!verifyCode.value || verifyCode.value.length !== 6) {
    showToast('请输入6位验证码')
    return
  }

  loading.value = true
  try {
    await userStore.registerByPhone(phone.value, verifyCode.value)
    const redirect = route.query.redirect || '/home'
    router.push(redirect)
  } catch (error) {
    showToast(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}

const wechatLogin = () => {
  showToast('请在微信中打开')
}

const appleLogin = () => {
  showToast('Apple登录开发中')
}

const showAgreement = () => {
  showAgreementDialog.value = true
}

const showPrivacy = () => {
  showPrivacyDialog.value = true
}
</script>

<template>
  <div class="login-page">
    <!-- 顶部 Logo -->
    <div class="login-hero">
      <div class="logo">
        <van-icon
          name="like"
          size="40"
        />
      </div>
      <h1 class="title">
        情侣私密菜单
      </h1>
      <p class="subtitle">
        记录我们的美食之旅
      </p>
    </div>

    <!-- 表单卡片 -->
    <div class="login-card">
      <van-field
        v-model="phone"
        class="field"
        type="tel"
        maxlength="11"
        placeholder="请输入手机号"
        :border="false"
      >
        <template #left-icon>
          <van-icon name="phone-o" />
        </template>
      </van-field>

      <div class="code-row">
        <van-field
          v-model="verifyCode"
          class="field"
          type="digit"
          maxlength="6"
          placeholder="请输入验证码"
          :border="false"
        >
          <template #left-icon>
            <van-icon name="shield-o" />
          </template>
        </van-field>
        <button
          class="code-btn"
          :disabled="countdown > 0"
          @click="sendVerifyCode"
        >
          {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
        </button>
      </div>

      <button
        class="submit-btn"
        :class="{ loading }"
        @click="handleLogin"
      >
        登录 / 注册
      </button>

      <div class="agree">
        <van-checkbox
          v-model="agreed"
          shape="round"
          icon-size="14"
        >
          我已阅读并同意<a
            href="#"
            @click.prevent="showAgreement"
          >《用户协议》</a>和<a
            href="#"
            @click.prevent="showPrivacy"
          >《隐私政策》</a>
        </van-checkbox>
      </div>
    </div>

    <!-- 第三方登录 -->
    <div class="third-party">
      <div class="divider">
        <span>其他登录方式</span>
      </div>
      <div class="icons">
        <button
          class="icon-btn"
          @click="wechatLogin"
        >
          <img
            :src="wechatIcon"
            alt="微信"
          >
        </button>
        <button
          class="icon-btn"
          @click="appleLogin"
        >
          <img
            :src="appleIcon"
            alt="Apple"
          >
        </button>
      </div>
    </div>

    <AgreementDialog
      v-model:show="showAgreementDialog"
      type="agreement"
    />
    <AgreementDialog
      v-model:show="showPrivacyDialog"
      type="privacy"
    />
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: $gradient-romance;
  padding: 72px $page-padding 48px;
  display: flex;
  flex-direction: column;
}

.login-hero {
  text-align: center;
  margin-bottom: 40px;

  .logo {
    width: 84px;
    height: 84px;
    margin: 0 auto 20px;
    border-radius: $radius-xl;
    background: $color-surface-lowest;
    color: $color-primary;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: $shadow-card;
  }

  .title {
    font-size: $fs-headline;
    font-weight: $fw-bold;
    color: $color-on-surface;
    letter-spacing: -0.01em;
    margin-bottom: $space-2;
  }

  .subtitle {
    font-size: $fs-label;
    color: $color-on-surface-variant;
  }
}

.login-card {
  @include card($radius-xl, $space-6);

  .field {
    background: $color-surface-low;
    border-radius: $radius-md;
    margin-bottom: $space-3;
    padding: 6px 12px;

    :deep(.van-field__left-icon) { color: $color-primary; margin-right: 8px; }
  }

  .code-row {
    display: flex;
    align-items: center;
    gap: $space-3;
    margin-bottom: $space-5;

    .field { flex: 1; margin-bottom: 0; }

    .code-btn {
      flex-shrink: 0;
      height: 40px;
      padding: 0 14px;
      border: none;
      border-radius: $radius-pill;
      background: $color-primary-container;
      color: $color-on-primary-container;
      font-size: $fs-caption;
      font-weight: $fw-semibold;
      cursor: pointer;

      &:disabled { opacity: 0.6; }
    }
  }

  .submit-btn {
    width: 100%;
    height: 50px;
    @include btn-primary;
    font-size: $fs-body;
    box-shadow: $shadow-float;
    cursor: pointer;
    transition: opacity $transition-base;

    &:active { opacity: 0.9; }
    &.loading { opacity: 0.7; pointer-events: none; }
  }

  .agree {
    margin-top: $space-4;
    display: flex;
    justify-content: center;

    :deep(.van-checkbox__label) {
      font-size: $fs-caption;
      color: $color-on-surface-variant;
    }

    a { color: $color-primary; }
  }
}

.third-party {
  margin-top: auto;
  padding-top: 40px;

  .divider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $space-4;
    margin-bottom: $space-5;
    color: $color-on-surface-variant;
    font-size: $fs-caption;

    &::before,
    &::after {
      content: '';
      width: 48px;
      height: 1px;
      background: $color-outline-variant;
    }
  }

  .icons {
    display: flex;
    justify-content: center;
    gap: 32px;

    .icon-btn {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      border: none;
      background: $color-surface-lowest;
      box-shadow: $shadow-card;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;

      img { width: 26px; height: 26px; }
    }
  }
}
</style>
