<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMenuStore } from '@/stores/menu'
import { logUiEvent } from '@/composables/useStructuredLog'
import placeRestaurant from '@/assets/cosmos/place-restaurant.webp'
import foodHero from '@/assets/cosmos/food-hero.webp'

const router = useRouter()
const store = useMenuStore()
const keyword = ref('')
const status = ref('')
const retryUsed = ref(false)
const pageSize = 10

const discoveryTab = ref('explore')

const itemImage = item => item?.photoUrl || item?.imageUrl || item?.coverUrl || placeRestaurant
const recommended = computed(() => store.items[0] || null)
const groupedItems = computed(() => ({
  want: store.items.filter(item => Number(item.status) === 0).slice(0, 1),
  visited: store.items.filter(item => Number(item.status) === 1).slice(0, 1),
  recommended: store.items.filter(item => Number(item.status) === 2).slice(0, 1),
  favorite: store.items.filter(item => item.isFavorite || item.favorite).slice(0, 1)
}))

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

const selectDiscoveryTab = (tab) => {
  discoveryTab.value = tab
  if (tab === 'recipes') return router.push('/recipes')
  if (tab === 'map') return router.push('/map')
  return undefined
}

const openItem = item => item?.id ? router.push(`/menu/${item.id}`) : undefined

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
  <main class="menu-library menu-library--discovery">
    <header class="page-heading discovery-header">
      <div>
        <p class="eyebrow">COUPLE COSMOS</p>
        <h1>探索星系</h1>
        <p class="discovery-subtitle">为你们发现下一次约会的浪漫坐标</p>
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

    <form class="search-row search-row--discovery" @submit.prevent="handleSearch">
      <van-icon name="search" aria-hidden="true" />
      <input v-model="keyword" type="search" placeholder="搜索餐厅、食谱或地点..." aria-label="搜索餐厅、食谱或地点">
      <button type="submit" aria-label="提交搜索"><van-icon name="search" /></button>
    </form>

    <nav class="segments discovery-tabs" aria-label="探索类别">
      <button type="button" :class="{ active: discoveryTab === 'explore' }" @click="selectDiscoveryTab('explore')">探店</button>
      <button type="button" :class="{ active: discoveryTab === 'recipes' }" @click="selectDiscoveryTab('recipes')">食谱</button>
      <button type="button" :class="{ active: discoveryTab === 'map' }" @click="selectDiscoveryTab('map')">地图</button>
    </nav>

    <section v-if="store.listStatus === 'success' && recommended" class="chef-feature" aria-labelledby="chef-feature-title">
      <img :src="itemImage(recommended)" alt="主厨推荐料理" width="1280" height="720">
      <div class="chef-feature__shade" aria-hidden="true" />
      <div class="chef-feature__copy">
        <span class="feature-kicker">CHEF SIGNATURE</span>
        <h2 id="chef-feature-title">{{ recommended.restaurantName }}</h2>
        <p>{{ recommended.dishName || '为今晚挑一处值得奔赴的味觉坐标' }}</p>
        <button type="button" @click="openItem(recommended)">查看这颗星</button>
      </div>
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

    <section v-else class="menu-grid discovery-grid" aria-live="polite">
      <article
        v-for="group in [
          { key: 'want', label: '想去' },
          { key: 'visited', label: '已去' },
          { key: 'recommended', label: '推荐' },
          { key: 'favorite', label: '收藏' }
        ]"
        :key="group.key"
        class="discovery-group"
      >
        <div class="discovery-group__heading"><h2>{{ group.label }}</h2><span aria-hidden="true">›</span></div>
        <button
          v-if="groupedItems[group.key][0]"
          class="discovery-card"
          type="button"
          @click="openItem(groupedItems[group.key][0])"
        >
          <img :src="itemImage(groupedItems[group.key][0])" :alt="`${groupedItems[group.key][0].restaurantName} 餐厅`" width="480" height="600">
          <span class="discovery-card__shade" aria-hidden="true" />
          <span class="discovery-card__name">{{ groupedItems[group.key][0].restaurantName }}</span>
        </button>
        <div v-else class="discovery-card discovery-card--empty" data-test="discovery-empty">等待下一次记录</div>
      </article>
      <article class="nearby-galaxy">
        <img :src="foodHero" alt="附近星系中的料理" width="1280" height="871">
        <div class="nearby-galaxy__copy"><h2>寻找附近的星系</h2><p>在你们的区域发现新的约会坐标</p><button type="button" @click="selectDiscoveryTab('map')">开启定位</button></div>
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
.menu-library--discovery { background: radial-gradient(circle at 50% 0, rgba(92, 66, 145, .22), transparent 34%), $cosmos-bg; }
.discovery-header { align-items: flex-start; }
.discovery-subtitle { margin-top: $space-1; color: $cosmos-text-muted; font-size: $fs-caption; }
.search-row--discovery { border-radius: 999px; background: rgba(255, 255, 255, .06); backdrop-filter: blur(16px); }
.search-row--discovery button { display: inline-grid; width: 40px; min-width: 40px; padding: 0; place-items: center; border-radius: 50%; }
.discovery-tabs { gap: $space-3; margin-top: $space-5; }
.discovery-tabs button { min-width: 82px; }
.chef-feature { position: relative; min-height: 220px; margin: $space-5 0 $space-6; overflow: hidden; border: 1px solid $cosmos-border; border-radius: 24px; background: $cosmos-surface; }
.chef-feature img, .chef-feature__shade { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.chef-feature__shade { background: linear-gradient(180deg, transparent 25%, rgba(6, 8, 25, .92)); }
.chef-feature__copy { position: relative; display: grid; min-height: 220px; align-content: end; gap: $space-2; padding: $space-5; }
.feature-kicker { color: $cosmos-gold; font-size: 10px; font-weight: $fw-bold; letter-spacing: .08em; }
.chef-feature h2 { max-width: 90%; font-size: 24px; line-height: 30px; }
.chef-feature p { color: $cosmos-text-muted; font-size: $fs-caption; }
.chef-feature button, .nearby-galaxy button { width: fit-content; min-height: 40px; padding: 0 $space-4; border: 0; border-radius: 999px; background: $cosmos-primary; color: #fff; font-weight: $fw-semibold; }
.discovery-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $space-4 $space-3; }
.discovery-group { min-width: 0; }
.discovery-group__heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: $space-2; }
.discovery-group__heading h2 { font-size: $fs-label; }
.discovery-group__heading span { color: $cosmos-text-muted; font-size: 22px; }
.discovery-card { position: relative; display: block; width: 100%; aspect-ratio: 4 / 5; overflow: hidden; border: 1px solid $cosmos-border; border-radius: 20px; background: $cosmos-surface; color: #fff; text-align: left; }
.discovery-card img, .discovery-card__shade { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.discovery-card__shade { background: linear-gradient(180deg, transparent 42%, rgba(6, 8, 25, .82)); }
.discovery-card__name { position: absolute; right: $space-3; bottom: $space-3; left: $space-3; overflow: hidden; font-size: $fs-caption; font-weight: $fw-semibold; text-overflow: ellipsis; white-space: nowrap; }
.discovery-card--empty { display: grid; padding: $space-3; place-items: center; color: $cosmos-text-muted; font-size: $fs-caption; text-align: center; }
.nearby-galaxy { position: relative; grid-column: 1 / -1; min-height: 190px; margin-top: $space-2; overflow: hidden; border: 1px solid $cosmos-border; border-radius: 24px; }
.nearby-galaxy img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; filter: brightness(.48) saturate(.8); }
.nearby-galaxy__copy { position: relative; display: grid; min-height: 190px; align-content: end; gap: $space-2; padding: $space-5; }
.nearby-galaxy__copy h2 { font-size: 22px; }
.nearby-galaxy__copy p { color: $cosmos-text-muted; font-size: $fs-caption; }
@media (prefers-reduced-motion: reduce) { .chef-feature img, .discovery-card img { transition: none; } }
@media (min-width: 720px) { .menu-library { max-width: 980px; margin: 0 auto; } .menu-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .load-more { grid-column: 1 / -1; } }
</style>
