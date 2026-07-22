<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useRecipeStore } from '@/stores/recipe'
import { useUserStore } from '@/stores/user'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = useRoute()
const router = useRouter()
const store = useRecipeStore()
const userStore = useUserStore()
const id = computed(() => route.params.id)
const coverBroken = ref(false)
const retryUsed = ref(false)
const pending = computed(() => store.mutationStatus === 'loading')
const isOwner = computed(() => (
  store.detail?.userId !== undefined &&
  String(store.detail.userId) === String(userStore.userInfo?.id)
))

const load = async () => {
  try { await store.fetchDetail(id.value) } catch (_) { /* Store 已记录错误态。 */ }
}

const retryOnce = () => {
  if (retryUsed.value) return
  retryUsed.value = true
  logUiEvent('recipe.detail.retry', {
    module: 'recipe_detail', operation: 'retry', result: 'requested', durationMs: 0, attempt: 1
  })
  return load()
}

const markCoverBroken = () => {
  coverBroken.value = true
  logUiEvent('recipe.cover.fallback', {
    module: 'recipe_detail', operation: 'render_cover', result: 'fallback', durationMs: 0,
    errorCode: 'IMAGE_LOAD_FAILED'
  })
}

const toggleLike = async () => {
  try { await store.setLiked(id.value, !store.detail.liked) } catch (_) { showToast('点赞操作失败') }
}
const toggleCollect = async () => {
  try { await store.setCollected(id.value, !store.detail.collected) } catch (_) { showToast('收藏操作失败') }
}
const publish = async () => {
  try { await store.publish(id.value); showToast('菜谱已发布') } catch (_) { showToast('发布失败') }
}
const remove = async () => {
  try {
    await showConfirmDialog({ title: '删除菜谱', message: '删除后无法恢复。' })
    await store.remove(id.value)
    router.replace('/recipes')
  } catch (error) {
    if (error !== 'cancel') showToast('删除失败')
  }
}

onMounted(load)
</script>

<template>
  <main class="recipe-detail">
    <header class="overlay-actions">
      <button type="button" aria-label="返回" @click="router.back()"><van-icon name="arrow-left" /></button>
      <div v-if="isOwner">
        <button data-test="recipe-edit" type="button" aria-label="编辑菜谱" @click="router.push(`/recipes/${id}/edit`)"><van-icon name="edit" /></button>
        <button type="button" aria-label="删除菜谱" :disabled="pending" @click="remove"><van-icon name="delete-o" /></button>
      </div>
    </header>

    <div class="cover-frame">
      <img
        v-if="store.detail?.coverUrl && !coverBroken"
        data-test="recipe-cover-image"
        :src="store.detail.coverUrl"
        :alt="`${store.detail.title} 封面`"
        @error="markCoverBroken"
      >
      <div v-else data-test="recipe-cover-placeholder" class="cover-placeholder cosmos-media cosmos-media--food" role="img" aria-label="本地菜谱占位图" />
    </div>

    <section v-if="store.detailStatus === 'loading'" class="state-panel">正在加载菜谱</section>
    <section v-else-if="store.detailStatus === 'error'" class="state-panel" role="alert">
      <h1>菜谱加载失败</h1><button type="button" :disabled="retryUsed" @click="retryOnce">{{ retryUsed ? '已重试' : '重新加载' }}</button>
    </section>
    <section v-else-if="store.detailStatus === 'empty'" class="state-panel"><h1>菜谱不存在或无权查看</h1></section>

    <template v-else-if="store.detail">
      <section class="recipe-intro">
        <p>{{ store.detail.status === 0 ? '我的草稿' : '已发布菜谱' }}</p>
        <h1>{{ store.detail.title }}</h1>
        <span v-if="store.detail.description">{{ store.detail.description }}</span>
        <div class="meta">
          <b v-if="store.detail.difficultyDesc">{{ store.detail.difficultyDesc }}</b>
          <b v-if="store.detail.cookingTime">{{ store.detail.cookingTime }} 分钟</b>
          <b v-if="store.detail.servings">{{ store.detail.servings }} 人份</b>
        </div>
      </section>

      <section class="content-section">
        <h2>主要食材</h2>
        <ul v-if="store.detail.ingredients?.length" class="ingredients">
          <li v-for="(ingredient, index) in store.detail.ingredients" :key="index"><span>{{ ingredient.name }}</span><b>{{ ingredient.amount }}</b></li>
        </ul>
        <p v-else class="empty-copy">尚未添加食材</p>
      </section>

      <section class="content-section">
        <h2>制作步骤</h2>
        <ol v-if="store.detail.steps?.length" class="steps">
          <li v-for="(step, index) in store.detail.steps" :key="index">
            <span>{{ index + 1 }}</span><p>{{ step.content }}</p>
          </li>
        </ol>
        <p v-else class="empty-copy">尚未添加步骤</p>
      </section>

      <footer class="bottom-actions">
        <button type="button" :disabled="pending" @click="toggleLike"><van-icon :name="store.detail.liked ? 'like' : 'like-o'" /> {{ store.detail.likeCount || 0 }}</button>
        <button type="button" :disabled="pending" @click="toggleCollect"><van-icon :name="store.detail.collected ? 'star' : 'star-o'" /> {{ store.detail.collectCount || 0 }}</button>
        <button v-if="isOwner && store.detail.status === 0" type="button" :disabled="pending" @click="publish">发布</button>
      </footer>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.recipe-detail { min-height: 100vh; padding-bottom: 104px; color: $cosmos-text; background: $cosmos-bg; }
.overlay-actions { position: absolute; z-index: 2; top: $space-4; right: $page-padding; left: $page-padding; display: flex; justify-content: space-between; }
.overlay-actions div { display: flex; gap: $space-2; }
.overlay-actions button { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: rgba(13,17,42,.82); color: $cosmos-text; }
.cover-frame { width: 100%; aspect-ratio: 16 / 9; max-height: 520px; background: $cosmos-surface-raised; }
.cover-frame img, .cover-placeholder { width: 100%; height: 100%; object-fit: cover; }
.state-panel { display: grid; min-height: 320px; gap: $space-4; place-content: center; justify-items: center; padding: $page-padding; text-align: center; }
.state-panel button { min-height: 44px; padding: 0 $space-5; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; }
.recipe-intro, .content-section { margin: 0 $page-padding; padding: $space-6 0; border-bottom: 1px solid $cosmos-border; }
.recipe-intro > p { color: $cosmos-secondary; font-size: $fs-label; }
.recipe-intro h1 { margin: $space-2 0; font-size: 30px; line-height: 38px; }
.recipe-intro > span { color: $cosmos-text-muted; line-height: 1.6; }
.meta { display: flex; gap: $space-3; margin-top: $space-4; }
.meta b { color: $cosmos-gold; font-size: $fs-caption; }
.content-section h2 { margin-bottom: $space-5; font-size: $fs-title; }
.ingredients { display: grid; gap: $space-2; padding: 0; list-style: none; }
.ingredients li { display: flex; justify-content: space-between; padding: $space-3; border-bottom: 1px solid $cosmos-border; }
.ingredients b { color: $cosmos-secondary; }
.steps { display: grid; gap: $space-5; padding: 0; list-style: none; }
.steps li { display: grid; grid-template-columns: 36px 1fr; gap: $space-3; align-items: start; }
.steps li > span { display: grid; width: 32px; height: 32px; place-items: center; border: 1px solid $cosmos-secondary; border-radius: 50%; color: $cosmos-secondary; }
.steps p { color: $cosmos-text-muted; line-height: 1.7; white-space: pre-wrap; }
.empty-copy { color: $cosmos-text-muted; }
.bottom-actions { position: fixed; z-index: 3; right: 0; bottom: 64px; left: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; padding: $space-3 $page-padding; border-top: 1px solid $cosmos-border; background: rgba(13,17,42,.92); backdrop-filter: blur(18px); }
.bottom-actions button { min-height: 48px; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
.bottom-actions button:last-child { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.bottom-actions button:disabled { opacity: .5; }
@media (min-width: 760px) { .recipe-detail { max-width: 900px; margin: 0 auto; } .bottom-actions { right: 50%; left: 50%; width: 900px; transform: translateX(-50%); } }
</style>
