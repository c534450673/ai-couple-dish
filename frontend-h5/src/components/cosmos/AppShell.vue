<script setup>
import AppTabbar from '@/components/AppTabbar.vue'
</script>

<template>
  <div class="cosmos-app-shell">
    <header
      v-if="$slots.header"
      class="cosmos-app-shell__header"
    >
      <slot name="header" />
    </header>
    <main class="cosmos-app-shell__content">
      <slot />
    </main>
    <footer class="cosmos-app-shell__navigation">
      <slot name="navigation">
        <AppTabbar />
      </slot>
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.cosmos-app-shell {
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  background: $cosmos-bg;
  color: $cosmos-text;
}

.cosmos-app-shell__header {
  position: relative;
  z-index: 20;
}

.cosmos-app-shell__content {
  min-height: 100vh;
  min-height: 100dvh;
  padding-bottom: calc(72px + env(safe-area-inset-bottom));
}

.cosmos-app-shell__navigation {
  position: relative;
  z-index: 100;
}
</style>
