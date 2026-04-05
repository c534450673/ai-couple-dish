<template>
  <view class="bind-page">
    <view class="bind-header">
      <text class="title">绑定TA</text>
      <text class="subtitle">和亲爱的TA开始私密美食之旅</text>
    </view>

    <!-- 我的情侣码 -->
    <view class="my-code-section">
      <text class="label">我的情侣码</text>
      <text class="code" v-if="myCoupleCode">{{ myCoupleCode }}</text>
      <text class="code loading" v-else>生成中...</text>
      <text class="desc">让TA扫码绑定，或告诉TA这个码</text>
      <button class="regenerate-btn" :loading="generating" @click="generateCode">
        {{ myCoupleCode ? '重新生成' : '生成情侣码' }}
      </button>
    </view>

    <view class="divider">
      <view class="line"></view>
      <text>或</text>
      <view class="line"></view>
    </view>

    <!-- 绑定TA -->
    <view class="bind-form">
      <text class="form-title">绑定TA的情侣码</text>
      <input v-model="partnerCode" class="code-input" placeholder="请输入TA的情侣码" maxlength="8" />
      <button class="bind-btn" :disabled="!partnerCode || partnerCode.length < 6" :loading="binding" @click="handleBind">
        绑定
      </button>
    </view>

    <view class="tip">
      <text>💡 绑定后你们可以看到彼此的私密菜单和美食笔记</text>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { coupleApi } from '@/api'

const userStore = useUserStore()

const myCoupleCode = ref('')
const partnerCode = ref('')
const generating = ref(false)
const binding = ref(false)

const generateCode = async () => {
  generating.value = true
  try {
    const res = await coupleApi.generateCoupleCode()
    myCoupleCode.value = res.data.coupleCode
  } catch (error) {
    uni.showToast({ title: '生成失败', icon: 'none' })
  } finally {
    generating.value = false
  }
}

const handleBind = async () => {
  if (!partnerCode.value || partnerCode.value.length < 6) {
    uni.showToast({ title: '请输入正确的情侣码', icon: 'none' })
    return
  }

  binding.value = true
  uni.showLoading({ title: '绑定中...', mask: true })
  try {
    await coupleApi.bindCouple({ coupleCode: partnerCode.value })
    await userStore.getCoupleInfo()
    uni.hideLoading()
    uni.showToast({ title: '绑定成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/home/index' })
    }, 1500)
  } catch (error) {
    uni.hideLoading()
    uni.showToast({ title: error.message || '绑定失败', icon: 'none' })
  } finally {
    binding.value = false
  }
}

onMounted(() => {
  generateCode()
})
</script>

<style lang="scss" scoped>
.bind-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 60rpx 40rpx;
}

.bind-header {
  text-align: center;
  margin-bottom: 80rpx;

  .title {
    display: block;
    font-size: 48rpx;
    font-weight: 700;
    color: #333;
    margin-bottom: 16rpx;
  }

  .subtitle {
    font-size: 28rpx;
    color: #999;
  }
}

.my-code-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #fff;
  border-radius: 32rpx;
  padding: 60rpx;

  .label {
    font-size: 28rpx;
    color: #999;
    margin-bottom: 24rpx;
  }

  .code {
    font-size: 72rpx;
    font-weight: 700;
    color: #ff4757;
    letter-spacing: 8rpx;
    margin-bottom: 16rpx;

    &.loading {
      font-size: 32rpx;
      color: #999;
    }
  }

  .desc {
    font-size: 24rpx;
    color: #999;
    margin-bottom: 32rpx;
  }

  .regenerate-btn {
    padding: 16rpx 40rpx;
    background: linear-gradient(135deg, #ff6b9d, #ff4757);
    color: #fff;
    border-radius: 40rpx;
    font-size: 28rpx;
    border: none;
  }
}

.divider {
  display: flex;
  align-items: center;
  margin: 60rpx 0;

  .line {
    flex: 1;
    height: 2rpx;
    background: #ddd;
  }

  text {
    padding: 0 30rpx;
    font-size: 24rpx;
    color: #999;
  }
}

.bind-form {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 32rpx;
  padding: 40rpx;

  .form-title {
    font-size: 28rpx;
    color: #666;
    margin-bottom: 24rpx;
  }

  .code-input {
    width: 100%;
    height: 100rpx;
    background: #f5f5f5;
    border-radius: 16rpx;
    padding: 0 30rpx;
    font-size: 32rpx;
    text-align: center;
    letter-spacing: 4rpx;
    box-sizing: border-box;
  }

  .bind-btn {
    width: 100%;
    height: 96rpx;
    background: linear-gradient(135deg, #ff6b9d, #ff4757);
    color: #fff;
    border-radius: 48rpx;
    font-size: 32rpx;
    margin-top: 30rpx;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;

    &[disabled] {
      opacity: 0.5;
    }
  }
}

.tip {
  text-align: center;
  margin-top: 40rpx;

  text {
    font-size: 24rpx;
    color: #999;
  }
}
</style>
