<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import AiChatPanel from '@/components/AiChatPanel.vue'
import { useAiChatStore } from '@/stores/ai'

const props = defineProps({
  visible: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible'])
const router = useRouter()
const aiStore = useAiChatStore()

const show = computed({
  get: () => props.visible,
  set: value => emit('update:visible', value)
})

const openFullPage = () => {
  show.value = false
  router.push('/ai')
}

watch(show, (visible) => {
  if (visible) aiStore.logSurface('drawer-open')
})
</script>

<template>
  <van-popup
    v-model:show="show"
    position="bottom"
    :style="{ height: '82vh' }"
    class="ai-drawer"
    teleport="body"
  >
    <section
      class="drawer-content"
      aria-label="AI 助手抽屉"
    >
      <header>
        <div>
          <p>COUPLE COSMOS</p>
          <h2>AI 恋爱助手</h2>
        </div>
        <div class="drawer-actions">
          <button
            type="button"
            @click="openFullPage"
          >
            打开完整页
          </button>
          <button
            type="button"
            aria-label="关闭 AI 助手"
            @click="show = false"
          >
            <van-icon name="cross" />
          </button>
        </div>
      </header>
      <AiChatPanel compact />
    </section>
  </van-popup>
</template>

<style lang="scss" scoped>
.ai-drawer { border-radius: 28px 28px 0 0; background: $cosmos-bg; }
.drawer-content { display: flex; height: 100%; flex-direction: column; padding: $space-4 $page-padding calc($space-4 + env(safe-area-inset-bottom)); color: $cosmos-text; }
.drawer-content > header { display: flex; gap: $space-3; align-items: center; justify-content: space-between; padding-bottom: $space-3; border-bottom: 1px solid $cosmos-border; }
.drawer-content > header p { color: $cosmos-secondary; font-size: $fs-caption; }
.drawer-content h2 { font-size: $fs-title; }
.drawer-actions { display: flex; gap: $space-2; align-items: center; }
.drawer-actions button { min-height: 42px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: 6px; background: transparent; color: $cosmos-text; }
.drawer-actions button:last-child { width: 42px; padding: 0; }
</style>
