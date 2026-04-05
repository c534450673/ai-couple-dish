<template>
  <view class="agreement-page">
    <view class="nav-bar">
      <text class="back-btn" @click="goBack">‹</text>
      <text class="title">用户协议</text>
    </view>
    <view class="content">
      <view class="section">
        <text class="section-title">一、服务说明</text>
        <text class="section-content">情侣私密菜单是一个帮助情侣记录和分享美食体验的应用。我们保留随时修改或中断服务的权利。</text>
      </view>
      <view class="section">
        <text class="section-title">二、用户注册</text>
        <text class="section-content">您需要提供真实、准确的个人信息进行注册，并负责维护您的账户安全。</text>
      </view>
      <view class="section">
        <text class="section-title">三、使用规则</text>
        <text class="section-content">您同意不利用本服务从事任何违法活动，不发布侵犯他人权益的内容。</text>
      </view>
      <view class="section">
        <text class="section-title">四、知识产权</text>
        <text class="section-content">本应用的所有内容，包括但不限于文字、图片、标识等，均受知识产权保护。</text>
      </view>
      <view class="section">
        <text class="section-title">五、免责声明</text>
        <text class="section-content">对于因不可抗力或第三方原因导致的服务中断，我们不承担责任。</text>
      </view>
      <view class="section">
        <text class="section-title">六、协议修改</text>
        <text class="section-content">我们有权随时修改本协议，修改后的协议一经公布即生效。</text>
      </view>
    </view>
  </view>
</template>

<script setup>
const goBack = () => uni.navigateBack()
</script>

<style lang="scss" scoped>
.agreement-page {
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