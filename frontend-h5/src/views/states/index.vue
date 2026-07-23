<script setup>
import AsyncState from '@/components/cosmos/AsyncState.vue'
</script>

<template>
  <main class="states-page">
    <header>
      <p>Non-production visual sheet</p>
      <h1>系统状态总览</h1>
    </header>
    <section class="state-grid">
      <article><h2>加载</h2><AsyncState status="loading" /></article>
      <article><h2>空数据</h2><AsyncState status="empty" /></article>
      <article><h2>网络错误</h2><AsyncState status="error" /></article>
      <article><h2>未授权</h2><AsyncState status="unauthorized" /></article>
      <article><h2>未绑定</h2><AsyncState status="unbound" /></article>
      <article class="unavailable">
        <h2>能力不可用</h2><p>当前后端未提供对应能力，操作没有被伪造为成功。</p>
      </article>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.states-page { min-height: 100vh; padding: $space-6 $page-padding 96px; color: $cosmos-text; background: $cosmos-bg; }
.states-page > header { max-width: 960px; margin: 0 auto $space-5; }
.states-page > header p { color: $cosmos-secondary; font-size: $fs-caption; }
.states-page h1 { margin-top: $space-1; font-size: $fs-headline; }
.state-grid { display: grid; max-width: 960px; margin: 0 auto; grid-template-columns: repeat(2, minmax(0,1fr)); gap: $space-4; }
.state-grid > article { min-height: 320px; overflow: hidden; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; }
.state-grid > article > h2 { padding: $space-4; border-bottom: 1px solid $cosmos-border; color: $cosmos-text-muted; font-size: $fs-label; }
.unavailable { display: grid; place-items: center; align-content: center; text-align: center; }
.unavailable p { max-width: 280px; padding: $space-4; color: $cosmos-text-muted; }
@media (max-width: 720px) { .state-grid { grid-template-columns: 1fr; } }
</style>
