<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user'
import ErrorBoundary from './components/ErrorBoundary.vue'
import AiAssistantFab from './components/AiAssistantFab.vue'
import MainLayout from './layouts/MainLayout.vue'

const userStore = useUserStore()

onMounted(() => {
  userStore.checkLoginStatus()
})
</script>

<template>
  <div id="app">
    <router-view v-slot="{ Component }">
      <transition
        name="fade"
        mode="out-in"
      >
        <error-boundary>
          <MainLayout v-if="$route.meta.shell">
            <component :is="Component" />
          </MainLayout>
          <component
            :is="Component"
            v-else
          />
        </error-boundary>
      </transition>
    </router-view>
    <AiAssistantFab />
  </div>
</template>

<style lang="scss">
#app {
  width: 100%;
  min-height: 100vh;
  background: $color-background;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity $cosmos-duration-slow $ease-standard;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
