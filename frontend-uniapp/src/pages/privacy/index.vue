<template>
  <view class="privacy-page">
    <view class="nav-bar">
      <text class="back-btn" @click="goBack">‹</text>
      <text class="title">隐私政策</text>
    </view>
    <view class="content">
      <view class="section">
        <text class="section-title">一、信息收集</text>
        <text class="section-content">我们收集您提供的信息，包括但不限于手机号码、昵称、头像等，以便为您提供更好的服务。</text>
      </view>
      <view class="section">
        <text class="section-title">二、信息使用</text>
        <text class="section-content">您的信息将用于提供、维护和改进我们的服务，以及向您推送个性化的内容和推荐。</text>
      </view>
      <view class="section">
        <text class="section-title">三、信息共享</text>
        <text class="section-content">未经您的同意，我们不会与任何第三方共享您的个人信息，但法律法规要求的情况除外。</text>
      </view>
      <view class="section">
        <text class="section-title">四、信息安全</text>
        <text class="section-content">我们采用行业标准的安全措施来保护您的个人信息，防止未经授权的访问、使用或泄露。</text>
      </view>
      <view class="section">
        <text class="section-title">五、联系我们</text>
        <text class="section-content">如果您对本隐私政策有任何疑问，请通过我们的客服渠道联系我们。</text>
      </view>
    </view>
  </view>
</template>

<script setup>
const goBack = () => uni.navigateBack()
</script>

<style lang="scss" scoped>
.privacy-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.nav-bar {
  display: flex;
  align-items: center;
  padding: 40rpx 24rpx;
  background: #fff;

  .back-btn {
    font-size: 48rpx;
    color: #333;
    margin-right: 24rpx;
  }

  .title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
  }
}

.content {
  padding: 24rpx;
}

.section {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;

  .section-title {
    display: block;
    font-size: 30rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 16rpx;
  }

  .section-content {
    display: block;
    font-size: 28rpx;
    color: #666;
    line-height: 1.6;
  }
}
</style>