<script setup>
// 统一的底部导航（玻璃态），替换各页重复粘贴的 van-tabbar
</script>

<template>
  <van-tabbar
    route
    class="app-tabbar"
    :border="false"
    safe-area-inset-bottom
  >
    <van-tabbar-item replace to="/home" icon="home-o">
      首页
    </van-tabbar-item>
    <van-tabbar-item replace to="/menu" icon="shop-o">
      餐厅
    </van-tabbar-item>
    <van-tabbar-item replace to="/feed" icon="gift-o">
      投喂
    </van-tabbar-item>
    <van-tabbar-item replace to="/settings" icon="contact">
      我的
    </van-tabbar-item>
  </van-tabbar>
</template>

<style lang="scss" scoped>
.app-tabbar {
  height: 64px;
  border-radius: $radius-xl $radius-xl 0 0;
  box-shadow: $shadow-nav;
  @include glass(0.85);
}

.app-tabbar :deep(.van-tabbar-item) {
  color: $color-on-surface-variant;
  font-size: $fs-caption;
}

.app-tabbar :deep(.van-tabbar-item--active) {
  color: $color-primary;
  background: transparent;
}

.app-tabbar :deep(.van-tabbar-item__icon) {
  font-size: 22px;
}
</style>
