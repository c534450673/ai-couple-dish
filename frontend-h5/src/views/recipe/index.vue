<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRecipeStore } from '@/stores/recipe'
import { logUiEvent } from '@/composables/useStructuredLog'

const router = useRouter()
const store = useRecipeStore()
const source = ref('recommended')
const keyword = ref('')
const retryUsed = ref(false)
const brokenCovers = ref(new Set())
const featuredBroken = ref(false)
const pageSize = 10

const filters = [
  { value: 'recommended', label: '想做', description: '探索适合今晚的全局推荐' },
  { value: 'collected', label: '已做', description: '回看你收藏过的灵感菜谱' },
  { value: 'my', label: '我的', description: '包含我的草稿与已发布菜谱' },
  { value: 'couple', label: 'TA的', description: '查看情侣共同发布的菜谱' }
]

const featuredRecipe = computed(() => store.items[0] || null)
const libraryItems = computed(() => store.items.slice(1))

const params = (pageNum = 1) => ({
  source: source.value,
  ...(source.value === 'search' ? { keyword: keyword.value.trim() } : {}),
  pageNum,
  pageSize
})

const load = async () => {
  retryUsed.value = false
  featuredBroken.value = false
  try {
    await store.fetchList(params())
    logUiEvent('recipe.list.loaded', {
      module: 'recipe_list', operation: 'load', result: 'success', durationMs: 0,
      source: source.value, itemCount: store.items.length
    })
  } catch (error) {
    logUiEvent('recipe.list.loaded', {
      module: 'recipe_list', operation: 'load', result: 'failed', durationMs: 0,
      source: source.value, errorCode: String(error?.code || error?.response?.status || 'LOAD_FAILED')
    })
  }
}

const selectSource = (value) => {
  source.value = value
  keyword.value = ''
  logUiEvent('recipe.filter.selected', {
    module: 'recipe_list', operation: 'select_filter', result: 'submitted', durationMs: 0,
    source: value
  })
  return load()
}

const search = () => {
  if (!keyword.value.trim()) source.value = 'recommended'
  else source.value = 'search'
  logUiEvent('recipe.search.submitted', {
    module: 'recipe_list', operation: 'search_global', result: 'submitted', durationMs: 0,
    hasKeyword: Boolean(keyword.value.trim())
  })
  return load()
}

const openRecipe = (recipe, placement = 'card') => {
  logUiEvent('recipe.opened', {
    module: 'recipe_list', operation: 'open_detail', result: 'submitted', durationMs: 0,
    placement, recipeId: String(recipe?.id || '')
  })
  return router.push(`/recipes/${recipe.id}`)
}

const startCooking = () => {
  if (!featuredRecipe.value) return
  logUiEvent('recipe.cooking.started', {
    module: 'recipe_list', operation: 'start_cooking', result: 'submitted', durationMs: 0,
    recipeId: String(featuredRecipe.value.id)
  })
  return openRecipe(featuredRecipe.value, 'featured')
}

const loadMore = async () => {
  if (!store.pagination.hasMore || store.isLoadingMore) return
  try {
    await store.fetchList(params(store.pagination.pageNum + 1), { append: true })
  } catch (error) {
    logUiEvent('recipe.list.load_more', {
      module: 'recipe_list', operation: 'load_more', result: 'failed', durationMs: 0,
      source: source.value, page: store.failedPage || store.pagination.pageNum + 1,
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
  return load()
}

const markCoverBroken = (id) => {
  brokenCovers.value = new Set([...brokenCovers.value, String(id)])
  logUiEvent('recipe.cover.fallback', {
    module: 'recipe_list', operation: 'render_cover', result: 'fallback', durationMs: 0,
    errorCode: 'IMAGE_LOAD_FAILED'
  })
}

const markFeaturedBroken = () => {
  featuredBroken.value = true
  logUiEvent('recipe.cover.fallback', {
    module: 'recipe_list', operation: 'render_featured_cover', result: 'fallback', durationMs: 0,
    errorCode: 'IMAGE_LOAD_FAILED'
  })
}

const imageAvailable = (recipe) => recipe?.coverUrl && !brokenCovers.value.has(String(recipe.id))
const recipeMatch = (recipe) => Math.min(99, 82 + (recipe?.ingredients?.length || 0) * 4)
const filterDescription = computed(() => {
  if (source.value === 'search') return '搜索范围：全局已发布菜谱'
  return filters.find(item => item.value === source.value)?.description || ''
})

onMounted(load)
</script>

<template>
  <main class="recipe-library">
    <header class="page-heading">
      <div class="heading-copy">
        <p class="eyebrow">
          COUPLE COSMOS
        </p>
        <h1>我们的食谱库</h1>
        <span>把下一顿饭，变成你们的共同记忆。</span>
      </div>
      <button
        type="button"
        aria-label="新建菜谱"
        @click="router.push('/recipes/new')"
      >
        <van-icon name="plus" />
      </button>
    </header>

    <form
      class="search-row"
      @submit.prevent="search"
    >
      <van-icon
        name="search"
        aria-hidden="true"
      />
      <input
        v-model="keyword"
        type="search"
        placeholder="寻找星球上的美味..."
        aria-label="搜索全局已发布菜谱"
      >
      <button
        type="submit"
        aria-label="提交搜索"
      >
        搜索
      </button>
    </form>

    <nav
      class="segments"
      aria-label="菜谱数据范围"
    >
      <button
        v-for="item in filters"
        :key="item.value"
        type="button"
        :class="{ active: source === item.value }"
        @click="selectSource(item.value)"
      >
        {{ item.label }}
      </button>
    </nav>
    <p class="scope-copy">
      <van-icon name="info-o" /> {{ filterDescription }}
    </p>
    <p class="sr-only">
      搜索范围：全局已发布菜谱。我的草稿、情侣已发布、全局推荐、我的收藏。
    </p>

    <section
      v-if="store.listStatus === 'loading' && !store.items.length"
      class="state-panel"
      role="status"
    >
      <span
        class="spinner"
        aria-hidden="true"
      /><p>正在同步你们的星系菜单</p>
    </section>
    <section
      v-else-if="store.listStatus === 'error'"
      class="state-panel"
      role="alert"
    >
      <h2>星系暂时失联</h2><p>请稍后重试，本页只允许一次显式重试。</p>
      <button
        type="button"
        :disabled="retryUsed"
        @click="retryOnce"
      >
        {{ retryUsed ? '已重试' : '重新连接' }}
      </button>
    </section>
    <section
      v-else-if="store.listStatus === 'empty'"
      class="state-panel"
    >
      <h2>{{ source === 'my' ? '还没有我的菜谱' : '当前星系暂无菜谱' }}</h2>
      <p>{{ source === 'my' ? '从一份可恢复草稿开始。' : '切换数据范围或搜索其他关键词。' }}</p>
      <button
        v-if="source === 'my'"
        type="button"
        @click="router.push('/recipes/new')"
      >
        新建菜谱
      </button>
    </section>

    <template v-else-if="featuredRecipe">
      <section
        class="featured-card"
        @click="openRecipe(featuredRecipe, 'featured-card')"
      >
        <img
          v-if="imageAvailable(featuredRecipe) && !featuredBroken"
          class="featured-image"
          :src="featuredRecipe.coverUrl"
          :alt="`${featuredRecipe.title} 封面`"
          @error="markFeaturedBroken"
        >
        <div
          v-else
          class="featured-image cosmos-media cosmos-media--food"
          role="img"
          :aria-label="`${featuredRecipe.title} 本地菜谱占位图`"
        />
        <div class="featured-shade" />
        <div class="featured-content">
          <span class="featured-badge"><van-icon name="star" /> 今日星选</span>
          <h2>{{ featuredRecipe.title }}</h2>
          <div class="featured-meta">
            <span><van-icon name="clock-o" /> {{ featuredRecipe.cookingTime || 30 }} 分钟</span>
            <span>{{ featuredRecipe.difficultyDesc || '简单' }}</span>
            <strong>食材匹配 {{ recipeMatch(featuredRecipe) }}%</strong>
          </div>
          <p>{{ featuredRecipe.description || '为你们挑选的一道值得一起完成的美味。' }}</p>
          <button
            type="button"
            class="primary-action"
            @click.stop="startCooking"
          >
            开始烹饪 <van-icon name="arrow" />
          </button>
        </div>
      </section>

      <section
        class="library-section"
        aria-live="polite"
      >
        <div class="section-heading">
          <h2><i />星系菜单</h2><span>{{ store.pagination.total || store.items.length }} 道灵感</span>
        </div>
        <div
          v-if="libraryItems.length"
          class="recipe-grid"
        >
          <article
            v-for="recipe in libraryItems"
            :key="recipe.id"
            class="recipe-card"
            tabindex="0"
            @click="openRecipe(recipe)"
            @keydown.enter="openRecipe(recipe)"
          >
            <div class="cover-frame">
              <img
                v-if="imageAvailable(recipe)"
                :src="recipe.coverUrl"
                :alt="`${recipe.title} 封面`"
                @error="markCoverBroken(recipe.id)"
              >
              <div
                v-else
                class="cover-placeholder cosmos-media cosmos-media--food"
                role="img"
                :aria-label="`${recipe.title} 本地菜谱占位图`"
              />
              <span
                v-if="recipe.status === 0"
                class="status-chip"
              >草稿</span>
              <span
                v-else
                class="status-chip status-chip--published"
              ><van-icon name="star" /> 已发布</span>
            </div>
            <div class="recipe-card__body">
              <h3>{{ recipe.title }}</h3>
              <p v-if="recipe.description">
                {{ recipe.description }}
              </p>
              <div class="meta">
                <span v-if="recipe.cookingTime"><van-icon name="clock-o" /> {{ recipe.cookingTime }} 分钟</span>
                <span>{{ recipe.difficultyDesc || '家常' }}</span>
                <span>{{ recipe.likeCount || 0 }} 赞</span>
              </div>
            </div>
          </article>
        </div>
        <p
          v-else
          class="library-hint"
        >
          继续添加菜谱，下一颗星球就会亮起来。
        </p>
      </section>

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
    </template>
  </main>
</template>

<style lang="scss" scoped>
.recipe-library { min-height: 100vh; padding: $space-6 $page-padding 112px; color: $cosmos-text; background: radial-gradient(circle at 50% -12%, rgba(88, 63, 151, .5), transparent 42%), $cosmos-bg; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: $space-5; }
.heading-copy { min-width: 0; }
.eyebrow { color: $cosmos-secondary; font-size: 11px; font-weight: $fw-semibold; letter-spacing: .14em; }
.page-heading h1 { margin-top: $space-1; color: $cosmos-primary; font-size: 28px; line-height: 36px; }
.heading-copy > span { display: block; margin-top: $space-2; color: $cosmos-text-muted; font-size: $fs-caption; }
.page-heading button { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid rgba(255,255,255,.16); border-radius: 50%; background: rgba(255,255,255,.08); color: $cosmos-primary; box-shadow: 0 8px 24px rgba(0,0,0,.2); }
.search-row { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: $space-2; align-items: center; padding: $space-2 $space-3; border: 1px solid rgba(255,255,255,.13); border-radius: 16px; background: rgba(255,255,255,.07); box-shadow: inset 0 1px rgba(255,255,255,.08); backdrop-filter: blur(18px); }
.search-row > .van-icon { color: $cosmos-text-muted; font-size: 20px; }
.search-row input { min-width: 0; min-height: 40px; border: 0; outline: 0; background: transparent; color: $cosmos-text; font-size: $fs-body; }
.search-row input::placeholder { color: rgba(231,222,250,.5); }
.search-row button { min-height: 36px; padding: 0 $space-3; border: 0; border-radius: 10px; background: rgba(84,232,211,.18); color: $cosmos-secondary; font-size: $fs-caption; }
.segments { display: flex; gap: $space-2; margin: $space-4 0 $space-2; overflow-x: auto; scrollbar-width: none; }
.segments::-webkit-scrollbar { display: none; }
.segments button { min-height: 40px; padding: 0 $space-4; white-space: nowrap; border: 1px solid rgba(255,255,255,.12); border-radius: 999px; background: rgba(255,255,255,.06); color: $cosmos-text-muted; }
.segments button.active { border-color: transparent; background: $cosmos-primary; color: #67001c; box-shadow: 0 8px 20px rgba(255,93,115,.25); }
.scope-copy { display: flex; gap: $space-2; align-items: center; color: $cosmos-text-muted; font-size: $fs-caption; }
.scope-copy .van-icon { color: $cosmos-secondary; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.featured-card { position: relative; min-height: 420px; margin-top: $space-5; overflow: hidden; border: 1px solid rgba(255,255,255,.16); border-radius: 24px; background: $cosmos-surface; box-shadow: 0 24px 60px rgba(0,0,0,.28); cursor: pointer; }
.featured-image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; background-position: center; background-size: cover; transition: transform .7s ease; }
.featured-card:hover .featured-image { transform: scale(1.04); }
.featured-shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(13,17,42,.05) 10%, rgba(13,17,42,.25) 35%, rgba(13,17,42,.98) 100%); }
.featured-content { position: relative; z-index: 1; display: flex; min-height: 420px; flex-direction: column; justify-content: flex-end; padding: $space-6; }
.featured-badge { display: inline-flex; width: fit-content; gap: $space-1; align-items: center; padding: 5px 10px; border: 1px solid rgba(244,190,78,.45); border-radius: 999px; background: rgba(244,190,78,.16); color: $cosmos-gold; font-size: 11px; font-weight: $fw-semibold; letter-spacing: .08em; }
.featured-content h2 { margin-top: $space-3; color: #fff; font-size: 24px; line-height: 1.3; }
.featured-meta { display: flex; flex-wrap: wrap; gap: $space-3; align-items: center; margin-top: $space-3; color: rgba(255,255,255,.78); font-size: $fs-caption; }
.featured-meta span { display: inline-flex; gap: 4px; align-items: center; }
.featured-meta strong { padding: 4px 8px; border: 1px solid rgba(84,232,211,.25); border-radius: 8px; background: rgba(84,232,211,.16); color: $cosmos-secondary; font-size: 11px; }
.featured-content > p { display: -webkit-box; margin-top: $space-3; overflow: hidden; color: rgba(255,255,255,.64); line-height: 1.6; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.primary-action { display: flex; min-height: 44px; gap: $space-2; align-items: center; justify-content: center; margin-top: $space-4; border: 0; border-radius: 12px; background: $cosmos-primary; color: #67001c; font-weight: $fw-semibold; box-shadow: 0 12px 28px rgba(255,93,115,.25); }
.library-section { margin-top: $space-6; }
.section-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: $space-4; }
.section-heading h2 { display: flex; gap: $space-2; align-items: center; font-size: $fs-title; }
.section-heading h2 i { display: block; width: 4px; height: 22px; border-radius: 4px; background: $cosmos-secondary; box-shadow: 0 0 12px rgba(84,232,211,.5); }
.section-heading span { color: $cosmos-secondary; font-size: $fs-caption; }
.recipe-grid { display: grid; gap: $space-4; }
.recipe-card { overflow: hidden; border: 1px solid rgba(255,255,255,.12); border-radius: 16px; background: rgba(255,255,255,.06); cursor: pointer; transition: transform .2s ease, border-color .2s ease; }
.recipe-card:hover, .recipe-card:focus-visible { border-color: rgba(84,232,211,.45); outline: 0; transform: translateY(-2px); }
.cover-frame { position: relative; aspect-ratio: 16 / 9; background: rgba(255,255,255,.08); }
.cover-frame img, .cover-placeholder { width: 100%; height: 100%; object-fit: cover; }
.status-chip { position: absolute; top: $space-3; left: $space-3; display: inline-flex; gap: 3px; align-items: center; padding: 4px 8px; border-radius: 6px; background: rgba(8,12,37,.82); color: $cosmos-secondary; font-size: 11px; }
.status-chip--published { color: $cosmos-gold; }
.recipe-card__body { padding: $space-4; }
.recipe-card__body h3 { font-size: $fs-title; }
.recipe-card__body p { display: -webkit-box; margin-top: $space-2; overflow: hidden; color: $cosmos-text-muted; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.meta { display: flex; flex-wrap: wrap; gap: $space-3; margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.meta span { display: inline-flex; gap: 3px; align-items: center; }
.library-hint { padding: $space-5; border: 1px dashed rgba(255,255,255,.15); border-radius: 12px; color: $cosmos-text-muted; text-align: center; }
.state-panel { display: grid; min-height: 300px; gap: $space-3; place-content: center; justify-items: center; padding: $space-6; text-align: center; }
.state-panel p { max-width: 300px; color: $cosmos-text-muted; }
.state-panel button { min-height: 40px; padding: 0 $space-4; border: 0; border-radius: 8px; background: $cosmos-primary; color: #67001c; }
.state-panel button:disabled { opacity: .5; }
.spinner { width: 30px; height: 30px; border: 3px solid rgba(255,255,255,.16); border-top-color: $cosmos-secondary; border-radius: 50%; animation: cosmos-orbit $cosmos-duration-slow linear infinite; }
.load-more { width: 100%; min-height: 44px; margin-top: $space-5; border: 1px solid rgba(255,255,255,.15); border-radius: 10px; background: rgba(255,255,255,.06); color: $cosmos-text; }
.load-more:disabled { opacity: .5; }
@media (min-width: 720px) { .recipe-library { max-width: 980px; margin: 0 auto; } .recipe-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media (prefers-reduced-motion: reduce) { .featured-image, .recipe-card { transition: none; } .featured-card:hover .featured-image { transform: none; } }
</style>
