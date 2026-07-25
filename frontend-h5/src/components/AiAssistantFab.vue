<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import AiChatDrawer from '@/components/AiChatDrawer.vue'

const route = useRoute()
const chatVisible = ref(false)

const showFab = computed(() => {
  const token = localStorage.getItem('token')
  return !!token && route.path !== '/login' && route.path !== '/ai' && !route.meta.hideAiFab
})

const openChat = () => {
  chatVisible.value = true
}
</script>

<template>
  <button
    v-if="showFab"
    class="ai-fab"
    type="button"
    aria-label="打开 AI 助手"
    @click="openChat"
  >
    <van-icon
      name="chat"
      size="22"
    />
  </button>

  <AiChatDrawer v-model:visible="chatVisible" />
</template>

<style lang="scss" scoped>
.ai-fab {
  position: fixed;
  right: 20px;
  bottom: 88px;
  z-index: 999;
  width: 52px;
  height: 52px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, $color-primary, $color-primary-container);
  color: $color-on-primary;
  box-shadow: 0 6px 20px rgba($color-primary, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease;

  &:active {
    transform: scale(0.94);
  }
}
</style>
