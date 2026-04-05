<template>
  <view class="login-page">
    <!-- 背景装饰 -->
    <view class="bg-decoration">
      <view class="circle circle-1"></view>
      <view class="circle circle-2"></view>
      <view class="circle circle-3"></view>
    </view>

    <!-- Logo区域 -->
    <view class="logo-section">
      <view class="logo">
        <text class="icon">🍽️</text>
      </view>
      <text class="app-name">情侣私密菜单</text>
      <text class="app-slogan">记录我们的美食之旅</text>
    </view>

    <!-- 登录表单 -->
    <view class="login-form">
      <view class="form-item">
        <view class="input-wrapper">
          <text class="input-icon">📱</text>
          <input
            v-model="phone"
            type="tel"
            maxlength="11"
            placeholder="请输入手机号"
            class="input"
          />
        </view>
      </view>

      <view class="form-item captcha-item">
        <view class="input-wrapper">
          <text class="input-icon">🔐</text>
          <input
            v-model="verifyCode"
            type="digit"
            maxlength="6"
            placeholder="请输入验证码"
            class="input"
          />
        </view>
        <view class="captcha-btn" @click="sendVerifyCode">
          {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
        </view>
      </view>

      <view class="form-item">
        <checkbox-group @change="onAgreeChange">
          <label class="agreement">
            <checkbox value="agree" :checked="agreed" color="#ff4757" />
            <text class="agreement-text">
              我已阅读并同意<text class="link" @click.stop="showAgreement">《用户协议》</text>
              和<text class="link" @click.stop="showPrivacy">《隐私政策》</text>
            </text>
          </label>
        </checkbox-group>
      </view>

      <button class="login-btn" :disabled="!canLogin" @click="handleLogin">
        登录
      </button>

      <!-- 其他登录方式 -->
      <view class="divider">
        <view class="line"></view>
        <text class="divider-text">其他登录方式</text>
        <view class="line"></view>
      </view>

      <view class="other-login">
        <view class="login-icon" @click="wechatLogin">
          <text class="iconfont">🍟</text>
          <text>微信</text>
        </view>
        <view class="login-icon" @click="appleLogin">
          <text class="iconfont">🍎</text>
          <text>Apple</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

const phone = ref('')
const verifyCode = ref('')
const agreed = ref(false)
const countdown = ref(0)
const loading = ref(false)

let countdownTimer = null

const canLogin = computed(() => {
  return phone.value.length === 11 && verifyCode.value.length === 6 && agreed.value
})

const sendVerifyCode = async () => {
  if (countdown.value > 0) return
  if (phone.value.length !== 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }

  try {
    await userStore.sendVerifyCode(phone.value)
    uni.showToast({ title: '验证码已发送', icon: 'success' })
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(countdownTimer)
      }
    }, 1000)
  } catch (error) {
    uni.showToast({ title: '发送失败', icon: 'none' })
  }
}

const handleLogin = async () => {
  if (!agreed.value) {
    uni.showToast({ title: '请先同意用户协议', icon: 'none' })
    return
  }

  loading.value = true
  try {
    await userStore.loginByPhone(phone.value, verifyCode.value)
    // 检查是否已绑定情侣
    if (userStore.coupleInfo) {
      uni.switchTab({ url: '/pages/home/index' })
    } else {
      uni.navigateTo({ url: '/pages/bind/index' })
    }
  } catch (error) {
    uni.showToast({ title: error.message || '登录失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

const onAgreeChange = (e) => {
  agreed.value = e.detail.value.includes('agree')
}

const wechatLogin = () => {
  // #ifdef MP-WEIXIN
  uni.login({
    provider: 'weixin',
    success: (loginRes) => {
      console.log('wechat login', loginRes)
    },
    fail: () => {
      uni.showToast({ title: '微信登录开发中', icon: 'none' })
    }
  })
  // #endif
  // #ifndef MP-WEIXIN
  uni.showToast({ title: '请在微信中使用', icon: 'none' })
  // #endif
}

const appleLogin = () => {
  uni.showToast({ title: 'Apple登录开发中', icon: 'none' })
}

const showAgreement = () => {
  uni.showModal({
    title: '用户协议',
    content: '用户协议内容...',
    showCancel: false
  })
}

const showPrivacy = () => {
  uni.showModal({
    title: '隐私政策',
    content: '隐私政策内容...',
    showCancel: false
  })
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff5f7 0%, #ffffff 100%);
  padding: 0 40rpx;
  position: relative;
  overflow: hidden;
}

.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 400rpx;
  overflow: hidden;

  .circle {
    position: absolute;
    border-radius: 50%;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    opacity: 0.1;

    &.circle-1 {
      width: 300rpx;
      height: 300rpx;
      top: -100rpx;
      right: -50rpx;
    }

    &.circle-2 {
      width: 200rpx;
      height: 200rpx;
      top: 50rpx;
      left: -80rpx;
    }

    &.circle-3 {
      width: 150rpx;
      height: 150rpx;
      top: 150rpx;
      right: 100rpx;
    }
  }
}

.logo-section {
  padding-top: 200rpx;
  display: flex;
  flex-direction: column;
  align-items: center;

  .logo {
    width: 160rpx;
    height: 160rpx;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    border-radius: 40rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 32rpx;
    box-shadow: 0 20rpx 40rpx rgba(255, 71, 87, 0.3);

    .icon {
      font-size: 80rpx;
    }
  }

  .app-name {
    font-size: 48rpx;
    font-weight: 700;
    color: #333;
    margin-bottom: 16rpx;
  }

  .app-slogan {
    font-size: 28rpx;
    color: #999;
  }
}

.login-form {
  margin-top: 80rpx;

  .form-item {
    margin-bottom: 32rpx;
  }

  .input-wrapper {
    display: flex;
    align-items: center;
    background: #fff;
    border-radius: 48rpx;
    padding: 32rpx 40rpx;
    box-shadow: 0 4rpx 20rpx rgba(255, 71, 87, 0.1);

    .input-icon {
      font-size: 40rpx;
      margin-right: 20rpx;
    }

    .input {
      flex: 1;
      font-size: 28rpx;
    }
  }

  .captcha-item {
    display: flex;
    align-items: center;

    .input-wrapper {
      flex: 1;
    }

    .captcha-btn {
      width: 200rpx;
      height: 96rpx;
      background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
      color: #fff;
      border-radius: 48rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24rpx;
      margin-left: 20rpx;
    }
  }

  .agreement {
    display: flex;
    align-items: flex-start;

    .agreement-text {
      font-size: 24rpx;
      color: #999;
      margin-left: 16rpx;
      line-height: 1.5;
    }

    .link {
      color: #ff4757;
    }
  }

  .login-btn {
    width: 100%;
    height: 96rpx;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    color: #fff;
    border-radius: 48rpx;
    font-size: 32rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 40rpx;
    border: none;

    &[disabled] {
      opacity: 0.5;
    }
  }

  .divider {
    display: flex;
    align-items: center;
    margin: 60rpx 0;

    .line {
      flex: 1;
      height: 1px;
      background: #ddd;
    }

    .divider-text {
      padding: 0 30rpx;
      font-size: 24rpx;
      color: #999;
    }
  }

  .other-login {
    display: flex;
    justify-content: center;
    gap: 80rpx;

    .login-icon {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10rpx;

      .iconfont {
        font-size: 60rpx;
      }

      text {
        font-size: 24rpx;
        color: #666;
      }
    }
  }
}
</style>
