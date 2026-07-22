<script setup>
import AsyncState from '@/components/cosmos/AsyncState.vue'
</script>

<template>
  <div class="unavailable-view">
    <AsyncState
      status="empty"
      message="这片星域正在建设中"
    />
  </div>
</template>

<style lang="scss" scoped>
.unavailable-view {
  display: grid;
  min-height: calc(100vh - 64px - env(safe-area-inset-bottom));
  min-height: calc(100dvh - 64px - env(safe-area-inset-bottom));
  place-items: center;
  padding: $page-padding;
}
</style>
