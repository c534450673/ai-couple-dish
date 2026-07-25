<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
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
const activeStep = ref(0)
const pending = computed(() => store.mutationStatus === 'loading')
const isOwner = computed(() => (
  store.detail?.userId !== undefined &&
  String(store.detail.userId) === String(userStore.userInfo?.id)
))
const matchPercent = computed(() => Math.min(99, 82 + (store.detail?.ingredients?.length || 0) * 4))
const servings = computed(() => store.detail?.servings || 2)

const load = async () => {
  coverBroken.value = false
  try {
    await store.fetchDetail(id.value)
    logUiEvent('recipe.detail.loaded', {
      module: 'recipe_detail', operation: 'load', result: 'success', durationMs: 0,
      recipeId: String(id.value)
    })
  } catch (error) {
    logUiEvent('recipe.detail.loaded', {
      module: 'recipe_detail', operation: 'load', result: 'failed', durationMs: 0,
      recipeId: String(id.value), errorCode: String(error?.code || error?.response?.status || 'DETAIL_LOAD_FAILED')
    })
  }
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
  try {
    await store.setLiked(id.value, !store.detail.liked)
    logUiEvent('recipe.like.updated', {
      module: 'recipe_detail', operation: 'toggle_like', result: 'success', durationMs: 0,
      liked: Boolean(store.detail.liked)
    })
  } catch (error) {
    logUiEvent('recipe.like.updated', {
      module: 'recipe_detail', operation: 'toggle_like', result: 'failed', durationMs: 0,
      errorCode: String(error?.code || error?.response?.status || 'LIKE_FAILED')
    })
    showToast('点赞操作失败')
  }
}

const toggleCollect = async () => {
  try {
    await store.setCollected(id.value, !store.detail.collected)
    logUiEvent('recipe.collect.updated', {
      module: 'recipe_detail', operation: 'toggle_collect', result: 'success', durationMs: 0,
      collected: Boolean(store.detail.collected)
    })
  } catch (error) {
    logUiEvent('recipe.collect.updated', {
      module: 'recipe_detail', operation: 'toggle_collect', result: 'failed', durationMs: 0,
      errorCode: String(error?.code || error?.response?.status || 'COLLECT_FAILED')
    })
    showToast('收藏操作失败')
  }
}

const publish = async () => {
  try {
    await store.publish(id.value)
    logUiEvent('recipe.published', { module: 'recipe_detail', operation: 'publish', result: 'success', durationMs: 0 })
    showToast('菜谱已发布')
  } catch (error) {
    logUiEvent('recipe.published', { module: 'recipe_detail', operation: 'publish', result: 'failed', durationMs: 0, errorCode: String(error?.code || error?.response?.status || 'PUBLISH_FAILED') })
    showToast('发布失败')
  }
}

const remove = async () => {
  try {
    await showConfirmDialog({ title: '删除菜谱', message: '删除后无法恢复。' })
    await store.remove(id.value)
    logUiEvent('recipe.deleted', { module: 'recipe_detail', operation: 'delete', result: 'success', durationMs: 0 })
    router.replace('/recipes')
  } catch (error) {
    if (error !== 'cancel') {
      logUiEvent('recipe.deleted', { module: 'recipe_detail', operation: 'delete', result: 'failed', durationMs: 0, errorCode: String(error?.code || error?.response?.status || 'DELETE_FAILED') })
      showToast('删除失败')
    }
  }
}

const activateStep = async (index) => {
  activeStep.value = index
  logUiEvent('recipe.step.activated', {
    module: 'recipe_detail', operation: 'activate_step', result: 'success', durationMs: 0,
    step: index + 1
  })
  await nextTick()
}

const startCooking = async () => {
  logUiEvent('recipe.cooking.started', {
    module: 'recipe_detail', operation: 'start_cooking', result: 'submitted', durationMs: 0,
    recipeId: String(id.value)
  })
  await nextTick()
  document.querySelector('.steps-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(load)
</script>

<template>
  <main class="recipe-detail">
    <header class="overlay-actions">
      <button
        type="button"
        aria-label="返回"
        @click="router.back()"
      >
        <van-icon name="arrow-left" />
      </button>
      <div v-if="isOwner">
        <button
          data-test="recipe-edit"
          type="button"
          aria-label="编辑菜谱"
          @click="router.push(`/recipes/${id}/edit`)"
        >
          <van-icon name="edit" />
        </button>
        <button
          type="button"
          aria-label="删除菜谱"
          :disabled="pending"
          @click="remove"
        >
          <van-icon name="delete-o" />
        </button>
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
      <div
        v-else
        data-test="recipe-cover-placeholder"
        class="cover-placeholder cosmos-media cosmos-media--food"
        role="img"
        aria-label="本地菜谱占位图"
      />
      <div class="cover-shade" />
      <button
        v-if="store.detail"
        type="button"
        class="back-float"
        aria-label="返回菜谱库"
        @click="router.back()"
      >
        <van-icon name="arrow-left" />
      </button>
    </div>

    <section
      v-if="store.detailStatus === 'loading'"
      class="state-panel"
    >
      正在加载菜谱
    </section>
    <section
      v-else-if="store.detailStatus === 'error'"
      class="state-panel"
      role="alert"
    >
      <h1>菜谱加载失败</h1><p>请检查网络后重试。</p><button
        type="button"
        :disabled="retryUsed"
        @click="retryOnce"
      >
        {{ retryUsed ? '已重试' : '重新加载' }}
      </button>
    </section>
    <section
      v-else-if="store.detailStatus === 'empty'"
      class="state-panel"
    >
      <h1>菜谱不存在或无权查看</h1>
    </section>

    <template v-else-if="store.detail">
      <section class="recipe-intro">
        <span class="intro-badge"><van-icon name="star" /> {{ store.detail.status === 0 ? '我的草稿' : '两人共同完成' }}</span>
        <h1>{{ store.detail.title }}</h1>
        <p v-if="store.detail.description">
          {{ store.detail.description }}
        </p>
        <div class="meta">
          <span><van-icon name="clock-o" /> {{ store.detail.cookingTime || 30 }} 分钟</span>
          <span>{{ store.detail.difficultyDesc || '家常' }}</span>
          <span>{{ servings }} 人份</span>
        </div>
      </section>

      <section class="adaptation-card">
        <div class="adaptation-icon">
          <van-icon name="bulb-o" />
        </div>
        <div><h2>AI 智能适配</h2><p>根据你们的口味偏好，建议保留食材原味；也可以在烹饪时让 TA 负责调味。</p></div>
        <strong>{{ matchPercent }}%</strong>
      </section>

      <section class="content-section ingredients-section">
        <div class="section-title">
          <h2>主要食材</h2><button
            type="button"
            aria-label="调整份量"
            @click="showToast(`${servings} 人份食材，可在编辑器调整`)"
          >
            <van-icon name="exchange" /> {{ servings }}人份
          </button>
        </div>
        <ul
          v-if="store.detail.ingredients?.length"
          class="ingredients"
        >
          <li
            v-for="(ingredient, index) in store.detail.ingredients"
            :key="index"
          >
            <span><i>{{ index + 1 }}</i>{{ ingredient.name }}</span><b>{{ ingredient.amount }}</b>
          </li>
        </ul>
        <p
          v-else
          class="empty-copy"
        >
          尚未添加食材
        </p>
      </section>

      <section class="content-section steps-section">
        <div class="section-title">
          <h2>制作步骤</h2><span>{{ store.detail.steps?.length || 0 }} 个步骤</span>
        </div>
        <ol
          v-if="store.detail.steps?.length"
          class="steps"
        >
          <li
            v-for="(step, index) in store.detail.steps"
            :key="index"
            :class="{ active: activeStep === index }"
          >
            <button
              type="button"
              class="step-marker"
              :aria-label="`激活第 ${index + 1} 步`"
              @click="activateStep(index)"
            >
              {{ String(index + 1).padStart(2, '0') }}
            </button>
            <div class="step-content">
              <button
                type="button"
                class="step-heading"
                @click="activateStep(index)"
              >
                第 {{ index + 1 }} 步 <van-icon
                  v-if="activeStep === index"
                  name="play-circle-o"
                />
              </button>
              <p>{{ step.content }}</p>
              <img
                v-if="step.imageUrl"
                :src="step.imageUrl"
                :alt="`第 ${index + 1} 步示意图`"
                class="step-image"
              >
              <div
                v-if="activeStep === index"
                class="step-tip"
              >
                <van-icon name="bulb-o" /><span>AI 微调：两人分工完成，味道会更好。</span>
              </div>
            </div>
          </li>
        </ol>
        <p
          v-else
          class="empty-copy"
        >
          尚未添加步骤
        </p>
      </section>

      <footer class="bottom-actions">
        <button
          type="button"
          class="cook-action"
          @click="startCooking"
        >
          <van-icon name="play-circle-o" /> 开始烹饪
        </button>
        <button
          type="button"
          :disabled="pending"
          :aria-label="store.detail.liked ? '取消点赞' : '点赞'"
          @click="toggleLike"
        >
          <van-icon :name="store.detail.liked ? 'like' : 'like-o'" /> <span>{{ store.detail.likeCount || 0 }}</span>
        </button>
        <button
          type="button"
          :disabled="pending"
          :aria-label="store.detail.collected ? '取消收藏' : '收藏'"
          @click="toggleCollect"
        >
          <van-icon :name="store.detail.collected ? 'star' : 'star-o'" /> <span>{{ store.detail.collectCount || 0 }}</span>
        </button>
        <button
          v-if="isOwner && store.detail.status === 0"
          type="button"
          :disabled="pending"
          class="publish-action"
          @click="publish"
        >
          发布
        </button>
      </footer>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.recipe-detail { min-height: 100vh; padding-bottom: 112px; color: $cosmos-text; background: radial-gradient(circle at 50% -10%, rgba(76,60,142,.45), transparent 38%), $cosmos-bg; }
.overlay-actions { position: absolute; z-index: 3; top: $space-4; right: $page-padding; left: $page-padding; display: flex; justify-content: space-between; pointer-events: none; }
.overlay-actions div { display: flex; gap: $space-2; }
.overlay-actions button, .back-float { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid rgba(255,255,255,.2); border-radius: 50%; background: rgba(13,17,42,.72); color: $cosmos-text; backdrop-filter: blur(14px); pointer-events: auto; }
.cover-frame { position: relative; width: 100%; aspect-ratio: 4 / 5; max-height: 560px; background: $cosmos-surface-raised; }
.cover-frame img, .cover-placeholder { width: 100%; height: 100%; object-fit: cover; }
.cover-shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(13,17,42,.05) 28%, rgba(13,17,42,.1) 48%, $cosmos-bg 100%); pointer-events: none; }
.back-float { position: absolute; top: $space-4; left: $page-padding; }
.state-panel { display: grid; min-height: 320px; gap: $space-4; place-content: center; justify-items: center; padding: $page-padding; text-align: center; }
.state-panel p { color: $cosmos-text-muted; }
.state-panel button { min-height: 44px; padding: 0 $space-5; border: 0; border-radius: 8px; background: $cosmos-primary; color: #67001c; }
.state-panel button:disabled { opacity: .5; }
.recipe-intro { position: relative; z-index: 1; margin-top: -82px; padding: 0 $page-padding $space-6; }
.intro-badge { display: inline-flex; gap: 5px; align-items: center; padding: 6px 10px; border: 1px solid rgba(255,178,183,.3); border-radius: 999px; background: rgba(255,93,115,.2); color: $cosmos-primary; font-size: 11px; font-weight: $fw-semibold; }
.recipe-intro h1 { margin: $space-3 0 $space-2; color: #fff; font-size: 30px; line-height: 1.2; }
.recipe-intro > p { color: rgba(231,222,250,.7); line-height: 1.6; }
.meta { display: flex; flex-wrap: wrap; gap: $space-3; margin-top: $space-4; color: $cosmos-secondary; font-size: $fs-caption; }
.meta span { display: inline-flex; gap: 4px; align-items: center; }
.adaptation-card { display: grid; grid-template-columns: auto 1fr auto; gap: $space-3; align-items: start; margin: 0 $page-padding; padding: $space-4; border: 1px solid rgba(84,232,211,.2); border-radius: 16px; background: rgba(84,232,211,.1); box-shadow: inset 0 1px rgba(255,255,255,.08); backdrop-filter: blur(16px); }
.adaptation-icon { display: grid; width: 40px; height: 40px; place-items: center; border-radius: 12px; background: rgba(84,232,211,.16); color: $cosmos-secondary; font-size: 20px; }
.adaptation-card h2 { color: $cosmos-secondary; font-size: $fs-title; }
.adaptation-card p { margin-top: 4px; color: rgba(231,222,250,.72); font-size: $fs-caption; line-height: 1.6; }
.adaptation-card strong { color: $cosmos-gold; font-size: $fs-caption; }
.content-section { margin: 0 $page-padding; padding: $space-6 0; border-bottom: 1px solid rgba(255,255,255,.1); }
.section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: $space-4; }
.section-title h2 { font-size: $fs-title; }
.section-title > span { color: $cosmos-text-muted; font-size: $fs-caption; }
.section-title button { display: inline-flex; gap: 4px; align-items: center; border: 0; background: transparent; color: $cosmos-secondary; font-size: $fs-caption; }
.ingredients { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: $space-3; padding: 0; list-style: none; }
.ingredients li { display: flex; min-height: 62px; flex-direction: column; justify-content: space-between; padding: $space-3; border: 1px solid rgba(255,255,255,.12); border-radius: 12px; background: rgba(255,255,255,.06); }
.ingredients li span { display: flex; gap: $space-2; align-items: center; font-size: $fs-body; }
.ingredients li i { display: grid; width: 22px; height: 22px; place-items: center; border-radius: 7px; background: rgba(255,178,183,.16); color: $cosmos-primary; font-size: 11px; font-style: normal; }
.ingredients li b { margin-top: $space-2; color: $cosmos-text-muted; font-size: $fs-caption; font-weight: $fw-regular; }
.steps { display: grid; gap: $space-5; padding: 0; list-style: none; }
.steps li { position: relative; display: grid; grid-template-columns: 42px 1fr; gap: $space-3; }
.steps li:not(:last-child)::after { position: absolute; top: 42px; bottom: -24px; left: 20px; width: 2px; background: linear-gradient($cosmos-secondary, rgba(84,232,211,0)); content: ''; opacity: .45; }
.step-marker { position: relative; z-index: 1; display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid rgba(255,255,255,.22); border-radius: 50%; background: $cosmos-bg; color: $cosmos-text-muted; font-size: 12px; }
.steps li.active .step-marker { border-color: $cosmos-secondary; background: rgba(84,232,211,.12); color: $cosmos-secondary; box-shadow: 0 0 18px rgba(84,232,211,.24); }
.step-content { min-width: 0; }
.step-heading { display: inline-flex; gap: $space-2; align-items: center; border: 0; background: transparent; color: $cosmos-text; font-size: $fs-title; font-weight: $fw-semibold; }
.steps li.active .step-heading { color: $cosmos-secondary; }
.step-content p { margin-top: $space-2; color: $cosmos-text-muted; line-height: 1.7; white-space: pre-wrap; }
.step-image { width: 100%; max-height: 180px; margin-top: $space-3; border-radius: 12px; object-fit: cover; }
.step-tip { display: flex; gap: $space-2; align-items: center; margin-top: $space-3; padding: $space-3; border-left: 3px solid $cosmos-secondary; border-radius: 0 8px 8px 0; background: rgba(84,232,211,.1); color: $cosmos-secondary; font-size: $fs-caption; }
.empty-copy { color: $cosmos-text-muted; }
.bottom-actions { position: fixed; z-index: 4; right: 0; bottom: 64px; left: 0; display: grid; grid-template-columns: minmax(0,1.5fr) repeat(2,minmax(44px,.6fr)) auto; gap: $space-2; padding: $space-3 $page-padding; border-top: 1px solid rgba(255,255,255,.14); background: rgba(13,17,42,.9); backdrop-filter: blur(18px); }
.bottom-actions button { display: inline-flex; min-height: 46px; gap: 5px; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,.16); border-radius: 10px; background: rgba(255,255,255,.08); color: $cosmos-text; }
.bottom-actions .cook-action, .bottom-actions .publish-action { border-color: transparent; background: $cosmos-primary; color: #67001c; font-weight: $fw-semibold; }
.bottom-actions button:disabled { opacity: .5; }
@media (min-width: 760px) { .recipe-detail { max-width: 900px; margin: 0 auto; } .bottom-actions { right: 50%; left: 50%; width: 900px; transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .steps li, .step-marker { transition: none; } }
</style>
