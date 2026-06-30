<template>
  <div id="app">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <error-boundary>
          <component :is="Component" />
        </error-boundary>
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user'
import ErrorBoundary from './components/ErrorBoundary.vue'

const userStore = useUserStore()

onMounted(() => {
  userStore.checkLoginStatus()
})
</script>

<style lang="scss">
#app {
  width: 100%;
  min-height: 100vh;
  background: $color-background;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
