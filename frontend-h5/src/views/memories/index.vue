<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useMemoriesStore } from '@/stores/memories'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = useRoute()
const router = useRouter()
const store = useMemoriesStore()

const filters = [
  { type: 'all', label: '全部' },
  { type: 'anniversary', label: '纪念日' },
  { type: 'wish', label: '心愿' },
  { type: 'note', label: '笔记' },
  { type: 'map', label: '地点', unavailable: true }
]
const sourceTypes = ['anniversary', 'wish', 'note']
const timeline = computed(() => store.filteredTimeline)
const allSourcesFailed = computed(() => sourceTypes.every(type => store.sourceStatus[type] === 'error'))
const isLoading = computed(() => sourceTypes.some(type => store.sourceStatus[type] === 'loading'))

const syncFilter = (type) => {
  const nextType = ['all', ...sourceTypes].includes(type) ? type : 'all'
  store.setActiveType(nextType)
}

const selectFilter = (filter) => {
  if (filter.unavailable) {
    showToast('地点足迹接口暂不可用，可前往餐厅地图查看')
    logUiEvent('memories.filter.map', {
      module: 'memories_page', operation: 'select_filter', result: 'unavailable',
      durationMs: 0, errorCode: 'MAP_FOOTPRINT_NOT_SUPPORTED'
    })
    return
  }
  syncFilter(filter.type)
  router.replace({ query: filter.type === 'all' ? {} : { ...route.query, type: filter.type }, hash: route.hash })
}

const retry = async (type) => {
  try {
    await store.retrySource(type)
  } catch (error) {
    showToast('该来源仍无法加载，请稍后再试')
  }
}

const openItem = (item) => {
  if (item.type === 'note') router.push(`/memories/notes/${item.id.split(':')[1]}`)
}

watch(() => route.query.type, type => syncFilter(type), { immediate: true })
onMounted(() => store.fetchAll())
</script>

<template>
  <main class="memories-page">
    <header class="memories-header">
      <div>
        <p class="eyebrow">COUPLE ARCHIVE</p>
        <h1>我们的回忆</h1>
      </div>
      <button
        class="icon-button"
        type="button"
        aria-label="新建笔记"
        title="新建笔记"
        @click="router.push('/memories/notes/new')"
      >
        <van-icon name="plus" />
      </button>
    </header>

    <nav class="memory-filters" aria-label="回忆类型">
      <button
        v-for="filter in filters"
        :key="filter.type"
        :data-test="`filter-${filter.type}`"
        :class="{ active: store.activeType === filter.type, unavailable: filter.unavailable }"
        type="button"
        @click="selectFilter(filter)"
      >
        {{ filter.label }}<span v-if="filter.unavailable"> · 暂不可用</span>
      </button>
    </nav>

    <section class="source-statuses" aria-label="来源状态">
      <div
        v-for="type in sourceTypes"
        :key="type"
        class="source-status"
        :data-test="store.sourceStatus[type] === 'error' ? `source-error-${type}` : undefined"
      >
        <span>{{ { anniversary: '纪念日', wish: '心愿', note: '笔记' }[type] }}</span>
        <span v-if="store.sourceStatus[type] === 'loading'">同步中</span>
        <span v-else-if="store.sourceStatus[type] === 'empty'">暂无记录</span>
        <button
          v-else-if="store.sourceStatus[type] === 'error'"
          :data-test="`retry-${type}`"
          type="button"
          @click="retry(type)"
        >
          重试
        </button>
      </div>
      <div class="source-status unavailable">
        <span>地点足迹</span><span>接口暂不可用</span>
      </div>
    </section>

    <p v-if="allSourcesFailed" class="aggregate-message" role="alert">
      所有回忆来源暂时无法加载，请分别重试。
    </p>
    <p v-else-if="isLoading && !timeline.length" class="aggregate-message" role="status">
      正在拼合你们的共同时间线…
    </p>
    <p v-else-if="!timeline.length" class="aggregate-message" role="status">
      这里还在等待第一条共同记录。
    </p>

    <ol v-else class="timeline">
      <li v-for="item in timeline" :key="item.id" class="timeline-item">
        <button v-if="item.type === 'note'" class="timeline-card" type="button" @click="openItem(item)">
          <span class="timeline-dot" :class="`timeline-dot--${item.type}`" />
          <span class="timeline-copy">
            <span class="timeline-meta">{{ { anniversary: '纪念日', wish: '心愿', note: '笔记' }[item.type] }} · {{ item.occurredAt || '日期待补充' }}</span>
            <strong>{{ item.title }}</strong>
            <span v-if="item.summary" class="timeline-summary">{{ item.summary }}</span>
          </span>
          <img v-if="item.media[0]" :src="item.media[0]" alt="回忆图片" loading="lazy">
        </button>
        <article v-else class="timeline-card">
          <span class="timeline-dot" :class="`timeline-dot--${item.type}`" />
          <span class="timeline-copy">
            <span class="timeline-meta">{{ { anniversary: '纪念日', wish: '心愿' }[item.type] }} · {{ item.occurredAt || '日期待补充' }}</span>
            <strong>{{ item.title }}</strong>
            <span v-if="item.summary" class="timeline-summary">{{ item.summary }}</span>
          </span>
          <img v-if="item.media[0]" :src="item.media[0]" alt="回忆图片" loading="lazy">
        </article>
      </li>
    </ol>
  </main>
</template>

<style lang="scss" scoped>
.memories-page { min-height: 100%; padding: $space-5 $page-padding $space-8; color: $cosmos-text; }
.memories-header { display: flex; align-items: center; justify-content: space-between; gap: $space-4; }
.eyebrow { color: $cosmos-secondary; font-size: $fs-caption; letter-spacing: 0; }
h1 { margin-top: $space-1; font-size: $fs-display; line-height: $lh-display; }
.icon-button { width: 44px; height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-elevated; color: $cosmos-primary; font-size: 20px; }
.memory-filters { display: flex; margin: $space-5 calc(-1 * $page-padding) 0; padding: 0 $page-padding $space-2; gap: $space-2; overflow-x: auto; }
.memory-filters button { min-height: 38px; flex: 0 0 auto; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: $radius-pill; background: transparent; color: $cosmos-text-muted; }
.memory-filters button.active { border-color: $cosmos-secondary; background: rgba(84, 232, 211, 0.12); color: $cosmos-secondary; }
.memory-filters button.unavailable { border-style: dashed; opacity: 0.72; }
.source-statuses { display: grid; margin-top: $space-3; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $space-2; }
.source-status { display: flex; min-height: 36px; padding: 0 $space-3; align-items: center; justify-content: space-between; gap: $space-2; border-left: 2px solid $cosmos-secondary; background: rgba(255, 255, 255, 0.04); color: $cosmos-text-muted; font-size: $fs-caption; }
.source-status button { min-height: 32px; border: 0; background: transparent; color: $cosmos-primary; }
.source-status.unavailable { border-left-color: $cosmos-gold; }
.aggregate-message { padding: $space-8 0; color: $cosmos-text-muted; text-align: center; }
.timeline { position: relative; margin-top: $space-6; padding-left: $space-5; list-style: none; }
.timeline::before { position: absolute; top: 12px; bottom: 12px; left: 4px; width: 1px; background: $cosmos-border; content: ''; }
.timeline-item + .timeline-item { margin-top: $space-4; }
.timeline-card { position: relative; display: grid; width: 100%; min-height: 104px; padding: $space-4; grid-template-columns: minmax(0, 1fr) 72px; gap: $space-3; border: 1px solid $cosmos-border; border-radius: $radius-md; background: $cosmos-surface-elevated; color: inherit; text-align: left; }
.timeline-dot { position: absolute; top: 20px; left: calc(-1 * $space-5 - 1px); width: 9px; height: 9px; border-radius: 50%; background: $cosmos-primary; box-shadow: 0 0 12px rgba(255, 93, 115, 0.7); }
.timeline-dot--wish { background: $cosmos-secondary; }.timeline-dot--anniversary { background: $cosmos-gold; }
.timeline-copy { display: flex; min-width: 0; flex-direction: column; gap: $space-2; }
.timeline-meta { color: $cosmos-secondary; font-size: $fs-caption; }.timeline-copy strong { font-size: $fs-title; }
.timeline-summary { display: -webkit-box; overflow: hidden; color: $cosmos-text-muted; font-size: $fs-label; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.timeline-card img { width: 72px; height: 72px; border-radius: $radius-sm; object-fit: cover; }
@media (max-width: 360px) { .source-statuses { grid-template-columns: 1fr; } .timeline-card { grid-template-columns: 1fr; } .timeline-card img { width: 100%; height: auto; aspect-ratio: 16 / 9; } }
</style>
