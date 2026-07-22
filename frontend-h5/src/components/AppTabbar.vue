<script setup>
// Couple Cosmos 统一底部导航，由 AppShell 单实例挂载。
</script>

<template>
  <van-tabbar
    route
    class="app-tabbar"
    :border="false"
    safe-area-inset-bottom
  >
    <van-tabbar-item
      replace
      to="/home"
      icon="cluster-o"
    >
      星球
    </van-tabbar-item>
    <van-tabbar-item
      replace
      to="/menu"
      icon="orders-o"
    >
      菜单
    </van-tabbar-item>
    <van-tabbar-item
      replace
      to="/feed"
      icon="gift-o"
    >
      投喂
    </van-tabbar-item>
    <van-tabbar-item
      replace
      to="/memories"
      icon="clock-o"
    >
      回忆
    </van-tabbar-item>
    <van-tabbar-item
      replace
      to="/settings"
      icon="friends-o"
    >
      我们
    </van-tabbar-item>
  </van-tabbar>
</template>

<style lang="scss" scoped>
.app-tabbar {
  height: calc(64px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
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
