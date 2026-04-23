<template>
  <div class="login-page">
    <div class="login-header">
      <div class="logo">
        <span class="logo-text">美食</span>
      </div>
      <h1 class="title">情侣私密菜单</h1>
      <p class="subtitle">记录我们的美食之旅</p>
    </div>

    <div class="login-form">
      <div class="form-item">
        <van-field
          v-model="phone"
          type="tel"
          maxlength="11"
          placeholder="请输入手机号"
          :border="false"
        >
          <template #left-icon>
            <van-icon name="phone-o" />
          </template>
        </van-field>
      </div>

      <div class="form-item captcha-item">
        <van-field
          v-model="verifyCode"
          type="digit"
          maxlength="6"
          placeholder="请输入验证码"
          :border="false"
        >
          <template #left-icon>
            <van-icon name="shield-o" />
          </template>
        </van-field>
        <van-button
          size="small"
          type="primary"
          :disabled="countdown > 0"
          @click="sendVerifyCode"
        >
          {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
        </van-button>
      </div>

      <div class="form-item">
        <van-button
          type="primary"
          size="large"
          :loading="loading"
          class="login-btn"
          @click="handleLogin"
        >
          登录/注册
        </van-button>
      </div>

      <div class="协议">
        <van-checkbox v-model="agreed" shape="round" icon-size="14">
          我已阅读并同意<a href="#" @click.prevent="showAgreement">《用户协议》</a>和<a href="#" @click.prevent="showPrivacy">《隐私政策》</a>
        </van-checkbox>
      </div>
    </div>

    <div class="login-footer">
      <div class="第三方登录">
        <span class="line"></span>
        <span class="text">其他登录方式</span>
        <span class="line"></span>
      </div>
      <div class="第三方图标">
        <img src="@/assets/images/icon-wechat.png" alt="微信" @click="wechatLogin" />
        <img src="@/assets/images/icon-apple.png" alt="Apple" @click="appleLogin" />
      </div>
    </div>

    <AgreementDialog v-model:show="showAgreementDialog" type="agreement" />
    <AgreementDialog v-model:show="showPrivacyDialog" type="privacy" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api'
import AgreementDialog from '@/components/AgreementDialog.vue'

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
    // 注册（会自动降级为登录如果手机号已注册）
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

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffd6e0 0%, #ffb3c1 50%, #ff8fa3 100%);
  padding: 80px 32px 60px;
  display: flex;
  flex-direction: column;
}

.login-header {
  text-align: center;
  margin-bottom: 60px;

  .logo {
    width: 100px;
    height: 100px;
    margin: 0 auto 20px;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    border-radius: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 24px rgba(255, 71, 87, 0.3);

    .logo-text {
      font-size: 28px;
      font-weight: 700;
      color: #fff;
    }
  }

  .title {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 8px;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .subtitle {
    font-size: 16px;
    color: rgba(255, 255, 255, 0.9);
  }
}

.login-form {
  flex: 1;

  .form-item {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    margin-bottom: 16px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(255, 71, 87, 0.15);

    :deep(.van-field) {
      padding: 16px 20px;
      background: transparent;

      .van-field__left-icon {
        color: #ff6b9d;
      }

      .van-field__control {
        color: #333;
        &::placeholder {
          color: #999;
        }
      }
    }
  }

  .captcha-item {
    display: flex;
    align-items: center;

    :deep(.van-field) {
      flex: 1;
    }

    .van-button {
      margin-right: 12px;
      height: 36px;
      background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
      border: none;
      border-radius: 18px;
      font-size: 13px;
      color: #fff;
    }
  }

  .login-btn {
    height: 50px;
    border-radius: 25px;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    border: none;
    font-size: 17px;
    font-weight: 600;
    color: #fff;
    box-shadow: 0 4px 16px rgba(255, 71, 87, 0.4);
  }

  .协议 {
    margin-top: 20px;
    text-align: center;

    :deep(.van-checkbox) {
      .van-checkbox__label {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.9);
        line-height: 1.4;
      }

      .van-checkbox__icon--checked .van-icon {
        background: #ff4757;
        border-color: #ff4757;
      }
    }

    a {
      color: #fff;
      text-decoration: underline;
    }
  }
}

.login-footer {
  margin-top: auto;
  padding-top: 40px;

  .第三方登录 {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;

    .line {
      width: 50px;
      height: 1px;
      background: rgba(255, 255, 255, 0.5);
    }

    .text {
      margin: 0 16px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.9);
    }
  }

  .第三方图标 {
    display: flex;
    justify-content: center;
    gap: 48px;

    img {
      width: 48px;
      height: 48px;
      cursor: pointer;
      opacity: 0.95;
    }
  }
}

.dialog-content {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
