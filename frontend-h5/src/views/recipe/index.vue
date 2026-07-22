<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRecipeStore } from '@/stores/recipe'
import { logUiEvent } from '@/composables/useStructuredLog'

const router = useRouter()
const store = useRecipeStore()
const source = ref('my')
const keyword = ref('')
const retryUsed = ref(false)
const brokenCovers = ref(new Set())
const pageSize = 10

const sources = [
  { value: 'my', label: '我的草稿', description: '包含我的草稿与已发布菜谱' },
  { value: 'couple', label: '情侣已发布', description: '只展示双方已发布菜谱' },
  { value: 'recommended', label: '全局推荐', description: '全局已发布菜谱' },
  { value: 'collected', label: '我的收藏', description: '本人收藏的已发布菜谱' }
]

const params = (pageNum = 1) => ({
  source: source.value,
  ...(source.value === 'search' ? { keyword: keyword.value.trim() } : {}),
  pageNum,
  pageSize
})

const load = async () => {
  retryUsed.value = false
  await store.fetchList(params())
}

const selectSource = (value) => {
  source.value = value
  keyword.value = ''
  return load()
}

const search = () => {
  if (!keyword.value.trim()) {
    source.value = 'recommended'
  } else {
    source.value = 'search'
  }
  logUiEvent('recipe.search.submitted', {
    module: 'recipe_list', operation: 'search_global', result: 'submitted', durationMs: 0,
    hasKeyword: Boolean(keyword.value.trim())
  })
  return load()
}

const loadMore = async () => {
  if (!store.pagination.hasMore || store.isLoadingMore) return
  try {
    await store.fetchList(params(store.pagination.pageNum + 1), { append: true })
  } catch (error) {
    logUiEvent('recipe.list.load_more', {
      module: 'recipe_list', operation: 'load_more', result: 'failed', durationMs: 0,
      source: source.value,
      page: store.failedPage || store.pagination.pageNum + 1,
      errorCode: String(error?.code || error?.response?.status || 'LOAD_MORE_FAILED')
    })
  }
}

const retryLoadMore = async () => {
  logUiEvent('recipe.list.load_more_retry', {
    module: 'recipe_list', operation: 'retry_load_more', result: 'requested', durationMs: 0,
    source: source.value, page: store.failedPage
  })
  try {
    await store.retryList()
  } catch (error) {
    logUiEvent('recipe.list.load_more_retry', {
      module: 'recipe_list', operation: 'retry_load_more', result: 'failed', durationMs: 0,
      source: source.value, page: store.failedPage,
      errorCode: String(error?.code || error?.response?.status || 'LOAD_MORE_RETRY_FAILED')
    })
  }
}

const retryOnce = () => {
  if (retryUsed.value) return
  retryUsed.value = true
  logUiEvent('recipe.list.retry', {
    module: 'recipe_list', operation: 'retry', result: 'requested', durationMs: 0, attempt: 1,
    source: source.value
  })
  return store.retryList()
}

const markCoverBroken = (id) => {
  brokenCovers.value = new Set([...brokenCovers.value, String(id)])
  logUiEvent('recipe.cover.fallback', {
    module: 'recipe_list', operation: 'render_cover', result: 'fallback', durationMs: 0,
    errorCode: 'IMAGE_LOAD_FAILED'
  })
}

const sourceDescription = () => {
  if (source.value === 'search') return '搜索范围：全局已发布菜谱'
  return sources.find(item => item.value === source.value)?.description || ''
}

onMounted(() => load())
</script>

<template>
  <main class="recipe-library">
    <header class="page-heading">
      <div><p>COUPLE COSMOS</p><h1>我们的食谱库</h1></div>
      <button type="button" aria-label="新建菜谱" @click="router.push('/recipes/new')"><van-icon name="plus" /></button>
    </header>

    <form class="search-row" @submit.prevent="search">
      <van-icon name="search" aria-hidden="true" />
      <input v-model="keyword" type="search" placeholder="寻找已发布菜谱" aria-label="搜索全局已发布菜谱">
      <button type="submit">搜索</button>
    </form>
    <p class="search-scope">搜索范围：全局已发布菜谱</p>
    <p class="scope-copy">{{ sourceDescription() }}</p>

    <nav class="segments" aria-label="菜谱数据范围">
      <button
        v-for="item in sources"
        :key="item.value"
        type="button"
        :class="{ active: source === item.value }"
        @click="selectSource(item.value)"
      >
        {{ item.label }}
      </button>
    </nav>
    <p class="unavailable-note"><van-icon name="info-o" /> 难度、食材、收藏状态与自选排序筛选暂不可用。</p>

    <section v-if="store.listStatus === 'loading' && !store.items.length" class="state-panel" role="status">
      <span class="spinner" aria-hidden="true" /><p>正在同步菜谱</p>
    </section>
    <section v-else-if="store.listStatus === 'error'" class="state-panel" role="alert">
      <h2>菜谱加载失败</h2><p>请稍后重试，本页只允许一次显式重试。</p>
      <button type="button" :disabled="retryUsed" @click="retryOnce">{{ retryUsed ? '已重试' : '重新加载' }}</button>
    </section>
    <section v-else-if="store.listStatus === 'empty'" class="state-panel">
      <h2>{{ source === 'my' ? '还没有我的菜谱' : '当前范围暂无菜谱' }}</h2>
      <p>{{ source === 'my' ? '从一份可恢复草稿开始。' : '切换数据范围或搜索其他关键词。' }}</p>
      <button v-if="source === 'my'" type="button" @click="router.push('/recipes/new')">新建菜谱</button>
    </section>

    <section v-else class="recipe-grid" aria-live="polite">
      <article
        v-for="recipe in store.items"
        :key="recipe.id"
        class="recipe-card"
        tabindex="0"
        @click="router.push(`/recipes/${recipe.id}`)"
        @keydown.enter="router.push(`/recipes/${recipe.id}`)"
      >
        <div class="cover-frame">
          <img
            v-if="recipe.coverUrl && !brokenCovers.has(String(recipe.id))"
            :src="recipe.coverUrl"
            :alt="`${recipe.title} 封面`"
            @error="markCoverBroken(recipe.id)"
          >
          <div v-else class="cover-placeholder cosmos-media cosmos-media--food" role="img" :aria-label="`${recipe.title} 本地菜谱占位图`" />
          <span class="status-chip">{{ recipe.status === 0 ? '草稿' : '已发布' }}</span>
        </div>
        <div class="recipe-card__body">
          <h2>{{ recipe.title }}</h2>
          <p v-if="recipe.description">{{ recipe.description }}</p>
          <div class="meta">
            <span v-if="recipe.cookingTime"><van-icon name="clock-o" /> {{ recipe.cookingTime }} 分钟</span>
            <span v-if="recipe.difficultyDesc">{{ recipe.difficultyDesc }}</span>
            <span>{{ recipe.likeCount || 0 }} 赞</span>
          </div>
        </div>
      </article>
      <button
        v-if="store.loadMoreError"
        data-test="recipe-load-more-retry"
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
.recipe-library { min-height: 100vh; padding: $space-6 $page-padding 112px; color: $cosmos-text; background: $cosmos-bg; }
.page-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: $space-5; }
.page-heading p { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; }
.page-heading h1 { margin-top: $space-1; font-size: 28px; line-height: 36px; }
.page-heading button { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-primary; }
.search-row { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: $space-2; align-items: center; padding: $space-2 $space-3; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface-raised; }
.search-row input { min-width: 0; min-height: 40px; border: 0; outline: 0; background: transparent; color: $cosmos-text; font-size: $fs-body; }
.search-row button, .state-panel button { min-height: 40px; padding: 0 $space-4; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; }
.search-scope, .scope-copy { margin-top: $space-2; font-size: $fs-caption; }
.search-scope { color: $cosmos-gold; }
.scope-copy { color: $cosmos-secondary; }
.segments { display: flex; gap: $space-2; margin: $space-4 0; overflow-x: auto; }
.segments button { min-height: 40px; padding: 0 $space-4; white-space: nowrap; border: 1px solid $cosmos-border; border-radius: 999px; background: transparent; color: $cosmos-text-muted; }
.segments button.active { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.unavailable-note { display: flex; gap: $space-2; align-items: center; color: $cosmos-text-muted; font-size: $fs-caption; }
.state-panel { display: grid; min-height: 300px; gap: $space-3; place-content: center; justify-items: center; padding: $space-6; text-align: center; }
.state-panel p { max-width: 300px; color: $cosmos-text-muted; }
.state-panel button:disabled { opacity: .5; }
.spinner { width: 30px; height: 30px; border: 3px solid $cosmos-border; border-top-color: $cosmos-secondary; border-radius: 50%; animation: cosmos-orbit $cosmos-duration-slow linear infinite; }
.recipe-grid { display: grid; gap: $space-4; margin-top: $space-5; }
.recipe-card { overflow: hidden; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; cursor: pointer; }
.cover-frame { position: relative; aspect-ratio: 16 / 9; background: $cosmos-surface-raised; }
.cover-frame img, .cover-placeholder { width: 100%; height: 100%; object-fit: cover; }
.status-chip { position: absolute; top: $space-3; left: $space-3; padding: $space-1 $space-2; border-radius: 4px; background: rgba(8,12,37,.82); color: $cosmos-secondary; font-size: $fs-caption; }
.recipe-card__body { padding: $space-4; }
.recipe-card__body h2 { font-size: $fs-title; }
.recipe-card__body p { display: -webkit-box; margin-top: $space-2; overflow: hidden; color: $cosmos-text-muted; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.meta { display: flex; gap: $space-3; margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.load-more { width: 100%; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
@media (min-width: 720px) { .recipe-library { max-width: 980px; margin: 0 auto; } .recipe-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } .load-more { grid-column: 1 / -1; } }
</style>
