<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useMenuStore } from '@/stores/menu'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = useRoute()
const router = useRouter()
const store = useMenuStore()
const retryUsed = ref(false)
const id = computed(() => route.params.id)
const pending = computed(() => store.mutationStatus === 'loading')
const statusText = value => ({ 0: '想去', 1: '去过', 2: '种草' }[value] || '未分类')

const load = async () => {
  try {
    await store.fetchDetail(id.value)
  } catch (_) {
    // Store 已记录脱敏错误与错误态。
  }
}

const retryOnce = () => {
  if (retryUsed.value) return
  retryUsed.value = true
  logUiEvent('menu.detail.retry', {
    module: 'menu_detail', operation: 'retry', result: 'requested', durationMs: 0, attempt: 1
  })
  return load()
}

const toggleFavorite = async () => {
  try {
    await store.setFavorite(id.value, !store.detail.isFavorite)
    showToast(store.detail.isFavorite ? '已收藏' : '已取消收藏')
  } catch (_) {
    showToast('收藏操作失败')
  }
}

const like = async () => {
  try {
    await store.setLiked(id.value, true)
    showToast('点赞成功')
  } catch (_) {
    showToast('点赞失败或已点赞')
  }
}

const remove = async () => {
  try {
    await showConfirmDialog({ title: '删除餐厅', message: '删除后不会再出现在菜单列表中。' })
    await store.remove(id.value)
    showToast('已删除')
    router.replace('/menu')
  } catch (error) {
    if (error !== 'cancel') showToast('删除失败')
  }
}

onMounted(load)
</script>

<template>
  <main class="menu-detail">
    <header class="detail-actions">
      <button type="button" aria-label="返回" @click="router.back()"><van-icon name="arrow-left" /></button>
      <div>
        <button data-test="menu-edit" type="button" aria-label="编辑餐厅" @click="router.push(`/menu/${id}/edit`)">
          <van-icon name="edit" />
        </button>
        <button type="button" aria-label="删除餐厅" :disabled="pending" @click="remove"><van-icon name="delete-o" /></button>
      </div>
    </header>

    <div
      data-test="menu-detail-placeholder"
      data-contract="backend-image-missing"
      class="hero-placeholder cosmos-media cosmos-media--place"
      role="img"
      aria-label="餐厅本地占位图"
    >
      <span>后端图片合同缺失 · 本地占位</span>
    </div>

    <section v-if="store.detailStatus === 'loading'" class="detail-state" role="status">正在加载餐厅详情</section>
    <section v-else-if="store.detailStatus === 'error'" class="detail-state" role="alert">
      <h1>详情加载失败</h1>
      <button type="button" :disabled="retryUsed" @click="retryOnce">{{ retryUsed ? '已重试' : '重新加载' }}</button>
    </section>
    <section v-else-if="store.detailStatus === 'empty'" class="detail-state">
      <h1>餐厅不存在或已删除</h1>
      <button type="button" @click="router.replace('/menu')">返回美食库</button>
    </section>

    <template v-else-if="store.detail">
      <section class="identity-section">
        <div>
          <span class="status">{{ statusText(store.detail.status) }}</span>
          <h1>{{ store.detail.restaurantName }}</h1>
          <p v-if="store.detail.dishName">{{ store.detail.dishName }}</p>
        </div>
        <strong v-if="store.detail.rating"><van-icon name="star" /> {{ store.detail.rating }}</strong>
      </section>

      <section class="facts" aria-label="餐厅信息">
        <div v-if="store.detail.dishCategory"><span>分类</span><b>{{ store.detail.dishCategory }}</b></div>
        <div v-if="store.detail.price"><span>人均</span><b>¥{{ store.detail.price }}</b></div>
        <div v-if="store.detail.eatenDate"><span>记录日期</span><b>{{ store.detail.eatenDate }}</b></div>
      </section>

      <section v-if="store.detail.location" class="content-section">
        <h2>位置</h2>
        <p>{{ store.detail.location }}</p>
      </section>
      <section v-if="store.detail.note" class="content-section">
        <h2>我们的记录</h2>
        <p>{{ store.detail.note }}</p>
      </section>

      <footer class="bottom-actions">
        <button data-test="menu-like" type="button" :disabled="pending" @click="like">
          <van-icon name="like-o" /> {{ store.detail.likeCount || 0 }} 赞
        </button>
        <button type="button" :disabled="pending" @click="toggleFavorite">
          <van-icon :name="store.detail.isFavorite ? 'star' : 'star-o'" />
          {{ store.detail.isFavorite ? '取消收藏' : '收藏' }}
        </button>
      </footer>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.menu-detail { min-height: 100vh; padding-bottom: 100px; color: $cosmos-text; background: $cosmos-bg; }
.detail-actions { position: absolute; z-index: 2; top: $space-4; right: $page-padding; left: $page-padding; display: flex; justify-content: space-between; }
.detail-actions div { display: flex; gap: $space-2; }
.detail-actions button { width: 44px; min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: rgba(13, 17, 42, .82); color: $cosmos-text; }
.hero-placeholder { position: relative; width: 100%; aspect-ratio: 16 / 9; max-height: 520px; }
.hero-placeholder::after { position: absolute; inset: 0; content: ''; background: linear-gradient(transparent 50%, $cosmos-bg); }
.hero-placeholder span { position: absolute; z-index: 1; right: $page-padding; bottom: $space-5; padding: $space-1 $space-2; border-radius: 4px; background: rgba(8, 12, 37, .82); color: $cosmos-text-muted; font-size: $fs-caption; }
.detail-state { display: grid; min-height: 320px; gap: $space-4; place-content: center; justify-items: center; padding: $page-padding; text-align: center; }
.detail-state button { min-height: 44px; padding: 0 $space-5; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; }
.identity-section, .facts, .content-section { margin: 0 $page-padding; }
.identity-section { display: flex; gap: $space-4; align-items: flex-start; justify-content: space-between; padding: $space-5 0; border-bottom: 1px solid $cosmos-border; }
.identity-section h1 { margin-top: $space-2; font-size: 28px; line-height: 36px; }
.identity-section p { margin-top: $space-2; color: $cosmos-text-muted; }
.identity-section strong { color: $cosmos-gold; white-space: nowrap; }
.status { color: $cosmos-secondary; font-size: $fs-label; }
.facts { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: $space-5; border: 1px solid $cosmos-border; border-radius: 8px; }
.facts div { display: grid; gap: $space-1; padding: $space-4 $space-2; text-align: center; }
.facts span { color: $cosmos-text-muted; font-size: $fs-caption; }
.content-section { padding: $space-6 0; border-bottom: 1px solid $cosmos-border; }
.content-section h2 { margin-bottom: $space-3; color: $cosmos-primary; font-size: $fs-title; }
.content-section p { color: $cosmos-text-muted; line-height: 1.7; white-space: pre-wrap; }
.bottom-actions { position: fixed; z-index: 3; right: 0; bottom: 64px; left: 0; display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; padding: $space-3 $page-padding; border-top: 1px solid $cosmos-border; background: rgba(13, 17, 42, .92); backdrop-filter: blur(18px); }
.bottom-actions button { min-height: 48px; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
.bottom-actions button:last-child { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.bottom-actions button:disabled { opacity: .5; }
@media (min-width: 760px) { .menu-detail { max-width: 900px; margin: 0 auto; } .bottom-actions { right: 50%; left: 50%; width: 900px; transform: translateX(-50%); } }
</style>
