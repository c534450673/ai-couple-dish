<script setup>
import { onMounted } from 'vue'
import AiChatPanel from '@/components/AiChatPanel.vue'
import { useAiChatStore } from '@/stores/ai'

const aiStore = useAiChatStore()

onMounted(() => aiStore.logSurface('full-page-open'))
</script>

<template>
  <main class="ai-page">
    <header class="ai-header">
      <div>
        <p>SHARED ASSISTANT</p>
        <h1>我们的 AI 对话</h1>
      </div>
      <span :data-state="aiStore.state">{{ aiStore.state }}</span>
    </header>
    <p class="runtime-note">
      当前仅共享本次运行期会话；历史与分页暂不可用，刷新后无法恢复。
    </p>
    <AiChatPanel />
    <span class="retry-contract">中断后仅支持重新发送，不提供服务端续传。</span>
  </main>
</template>

<style lang="scss" scoped>
.ai-page { display: flex; min-height: calc(100vh - 64px); flex-direction: column; padding: $space-5 $page-padding 96px; color: $cosmos-text; background: $cosmos-bg; }
.ai-header { display: flex; gap: $space-4; align-items: center; justify-content: space-between; }
.ai-header p { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; }
.ai-header h1 { font-size: $fs-headline; letter-spacing: 0; }
.ai-header > span { padding: $space-1 $space-2; border: 1px solid $cosmos-border; border-radius: 4px; color: $cosmos-text-muted; font-size: $fs-caption; }
.runtime-note { margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.retry-contract { margin-top: $space-2; color: $cosmos-text-muted; font-size: $fs-caption; text-align: center; }
</style>
