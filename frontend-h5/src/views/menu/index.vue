<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMenuStore } from '@/stores/menu'
import { logUiEvent } from '@/composables/useStructuredLog'

const router = useRouter()
const store = useMenuStore()
const keyword = ref('')
const status = ref('')
const retryUsed = ref(false)
const pageSize = 10

const statusOptions = [
  { label: '全部', value: '' },
  { label: '想去', value: 0 },
  { label: '去过', value: 1 },
  { label: '种草', value: 2 }
]

const statusText = (value) => ({ 0: '想去', 1: '去过', 2: '种草' }[value] || '未分类')

const listParams = (page = 1) => ({
  ...(status.value !== '' ? { status: status.value } : {}),
  ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
  sortBy: 'time',
  sortOrder: 'desc',
  page,
  pageSize
})

const loadList = async () => {
  retryUsed.value = false
  await store.fetchList(listParams())
}

const handleSearch = () => {
  logUiEvent('menu.search.submitted', {
    module: 'menu_list', operation: 'search', result: 'submitted', durationMs: 0,
    hasKeyword: Boolean(keyword.value.trim())
  })
  return loadList()
}

const selectStatus = (value) => {
  status.value = value
  return loadList()
}

const loadMore = async () => {
  if (!store.pagination.hasMore || store.isLoadingMore) return
  try {
    await store.fetchList(listParams(store.pagination.page + 1), { append: true })
  } catch (error) {
    logUiEvent('menu.list.load_more', {
      module: 'menu_list', operation: 'load_more', result: 'failed', durationMs: 0,
      page: store.failedPage || store.pagination.page + 1,
      errorCode: String(error?.code || error?.response?.status || 'LOAD_MORE_FAILED')
    })
  }
}

const retryLoadMore = async () => {
  logUiEvent('menu.list.load_more_retry', {
    module: 'menu_list', operation: 'retry_load_more', result: 'requested', durationMs: 0,
    page: store.failedPage
  })
  try {
    await store.retryList()
  } catch (error) {
    logUiEvent('menu.list.load_more_retry', {
      module: 'menu_list', operation: 'retry_load_more', result: 'failed', durationMs: 0,
      page: store.failedPage,
      errorCode: String(error?.code || error?.response?.status || 'LOAD_MORE_RETRY_FAILED')
    })
  }
}

const retryOnce = () => {
  if (retryUsed.value) return
  retryUsed.value = true
  logUiEvent('menu.list.retry', {
    module: 'menu_list', operation: 'retry', result: 'requested', durationMs: 0,
    attempt: 1
  })
  return store.retryList()
}

onMounted(() => {
  Promise.allSettled([loadList(), store.fetchStats()])
})
</script>

<template>
  <main class="menu-library">
    <header class="page-heading">
      <div>
        <p class="eyebrow">COUPLE COSMOS</p>
        <h1>我们的美食库</h1>
      </div>
      <button
        class="icon-action"
        type="button"
        aria-label="添加餐厅"
        @click="router.push('/menu/add')"
      >
        <van-icon name="plus" />
      </button>
    </header>

    <form class="search-row" @submit.prevent="handleSearch">
      <van-icon name="search" aria-hidden="true" />
      <input v-model="keyword" type="search" placeholder="按餐厅名搜索" aria-label="按餐厅名搜索">
      <button type="submit">搜索</button>
    </form>

    <nav class="segments" aria-label="菜单状态">
      <button
        v-for="option in statusOptions"
        :key="String(option.value)"
        type="button"
        :class="{ active: status === option.value }"
        @click="selectStatus(option.value)"
      >
        {{ option.label }}
      </button>
    </nav>

    <p class="contract-note">
      <van-icon name="info-o" /> 收藏筛选暂不可用；后端图片合同缺失，列表统一显示本地占位。
    </p>

    <section class="stats-band" aria-label="菜单统计">
      <div><span>全部</span><strong>{{ store.stats.totalCount || 0 }}</strong></div>
      <div><span>想去</span><strong>{{ store.stats.wantToGoCount || 0 }}</strong></div>
      <div><span>去过</span><strong>{{ store.stats.visitedCount || 0 }}</strong></div>
      <div><span>种草</span><strong>{{ store.stats.seededCount || 0 }}</strong></div>
    </section>

    <section v-if="store.listStatus === 'loading' && !store.items.length" class="state-panel" role="status">
      <span class="spinner" aria-hidden="true" />
      <p>正在同步美食记录</p>
    </section>

    <section v-else-if="store.listStatus === 'error'" class="state-panel" role="alert">
      <h2>{{ store.error?.code === 2006 ? '需要先绑定情侣关系' : '美食库加载失败' }}</h2>
      <p>请检查网络后重试，本页只允许一次显式重试。</p>
      <button data-test="menu-retry" type="button" :disabled="retryUsed" @click="retryOnce">
        {{ retryUsed ? '已重试' : '重新加载' }}
      </button>
    </section>

    <section v-else-if="store.listStatus === 'empty'" class="state-panel">
      <h2>还没有餐厅记录</h2>
      <p>把下一次约会想去的地方放进这里。</p>
      <button data-test="menu-empty-add" type="button" @click="router.push('/menu/add')">添加餐厅</button>
    </section>

    <section v-else class="menu-grid" aria-live="polite">
      <article
        v-for="item in store.items"
        :key="item.id"
        class="menu-card"
        tabindex="0"
        @click="router.push(`/menu/${item.id}`)"
        @keydown.enter="router.push(`/menu/${item.id}`)"
      >
        <div
          :data-test="`menu-placeholder-${item.id}`"
          class="menu-placeholder cosmos-media cosmos-media--place"
          data-contract="backend-image-missing"
          role="img"
          :aria-label="`${item.restaurantName} 本地餐厅占位图`"
        >
          <span>本地占位</span>
        </div>
        <div class="menu-card__body">
          <div class="card-title-row">
            <div>
              <span class="status-chip">{{ statusText(item.status) }}</span>
              <h2>{{ item.restaurantName }}</h2>
            </div>
            <strong v-if="item.rating" class="rating"><van-icon name="star" /> {{ item.rating }}</strong>
          </div>
          <p v-if="item.dishName" class="dish-name">{{ item.dishName }}</p>
          <div class="card-meta">
            <span v-if="item.dishCategory">{{ item.dishCategory }}</span>
            <span v-if="item.price">¥{{ item.price }}</span>
            <span>{{ item.likeCount || 0 }} 赞</span>
          </div>
        </div>
      </article>
      <button
        v-if="store.loadMoreError"
        data-test="menu-load-more-retry"
        class="load-more"
        type="button"
        :disabled="store.isLoadingMore"
        @click="retryLoadMore"
      >
        {{ store.isLoadingMore ? '重试中' : '加载失败，重试本页' }}
      </button>
      <button
        v-else-if="store.pagination.hasMore"
        class="load-more"
        type="button"
        :disabled="store.isLoadingMore"
        @click="loadMore"
      >
        {{ store.isLoadingMore ? '加载中' : '加载更多' }}
      </button>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.menu-library { min-height: 100vh; padding: $space-6 $page-padding 112px; color: $cosmos-text; background: $cosmos-bg; }
.page-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: $space-5; }
.eyebrow { margin-bottom: $space-1; color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; }
h1 { font-size: 28px; line-height: 36px; }
.icon-action { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-primary; font-size: 20px; }
.search-row { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: $space-2; align-items: center; padding: $space-2 $space-3; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface-raised; }
.search-row input { min-width: 0; min-height: 40px; border: 0; outline: 0; background: transparent; color: $cosmos-text; font-size: $fs-body; }
.search-row button, .state-panel button { min-height: 40px; padding: 0 $space-4; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; }
.segments { display: flex; gap: $space-2; margin: $space-4 0; overflow-x: auto; }
.segments button { min-height: 40px; padding: 0 $space-4; white-space: nowrap; border: 1px solid $cosmos-border; border-radius: 999px; background: transparent; color: $cosmos-text-muted; }
.segments button.active { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.contract-note { display: flex; gap: $space-2; align-items: flex-start; padding: $space-3; border-left: 3px solid $cosmos-gold; color: $cosmos-text-muted; background: rgba(255, 200, 87, .08); font-size: $fs-caption; line-height: 20px; }
.stats-band { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; margin: $space-5 0; overflow: hidden; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-border; }
.stats-band div { display: grid; gap: 2px; padding: $space-3 $space-1; text-align: center; background: $cosmos-surface; }
.stats-band span { color: $cosmos-text-muted; font-size: $fs-caption; }
.stats-band strong { font-size: $fs-title; }
.state-panel { display: grid; min-height: 280px; gap: $space-3; place-content: center; justify-items: center; padding: $space-6; text-align: center; }
.state-panel h2 { font-size: $fs-title; }
.state-panel p { max-width: 300px; color: $cosmos-text-muted; }
.state-panel button:disabled { opacity: .5; }
.spinner { width: 30px; height: 30px; border: 3px solid $cosmos-border; border-top-color: $cosmos-secondary; border-radius: 50%; animation: cosmos-orbit $cosmos-duration-slow linear infinite; }
.menu-grid { display: grid; gap: $space-4; }
.menu-card { overflow: hidden; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; cursor: pointer; }
.menu-placeholder { position: relative; aspect-ratio: 16 / 9; }
.menu-placeholder span { position: absolute; right: $space-3; bottom: $space-3; padding: 3px $space-2; border-radius: 4px; background: rgba(8, 12, 37, .78); color: $cosmos-text-muted; font-size: $fs-caption; }
.menu-card__body { padding: $space-4; }
.card-title-row { display: flex; gap: $space-3; align-items: flex-start; justify-content: space-between; }
.card-title-row h2 { margin-top: $space-2; font-size: $fs-title; }
.status-chip { color: $cosmos-secondary; font-size: $fs-caption; }
.rating { color: $cosmos-gold; white-space: nowrap; font-size: $fs-label; }
.dish-name { margin-top: $space-3; color: $cosmos-text; }
.card-meta { display: flex; gap: $space-3; margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.load-more { width: 100%; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
@media (min-width: 720px) { .menu-library { max-width: 980px; margin: 0 auto; } .menu-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .load-more { grid-column: 1 / -1; } }
</style>
