<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { showToast } from 'vant'
import { useFeedStore } from '@/stores/feed'
import { useReducedMotion } from '@/composables/useReducedMotion'

const store = useFeedStore()
const prefersReducedMotion = useReducedMotion()
const successVisible = ref(false)
const unavailableMessage = ref('')
const rejectReasons = ref({})
const nowMs = ref(Date.now())
let expiryTimer = null
const feedTypes = [
  { value: 'meal', label: '正餐', icon: 'shop-o' },
  { value: 'dessert', label: '甜点', icon: 'smile-o' },
  { value: 'snack', label: '零食', icon: 'bag-o' },
  { value: 'drink', label: '饮品', icon: 'coupon-o' }
]
const canSend = computed(() => Boolean(store.draft.feedType?.trim()) && Number(store.today?.remainingCount ?? 1) > 0 && !store.isMutationPending)

const expiryTimestamp = item => Date.parse(item.expireTime || '')
const isLocallyExpired = (item) => {
  if (Number(item.status) === 3) return true
  const expiresAt = expiryTimestamp(item)
  return Number(item.status) === 0 && Number.isFinite(expiresAt) && expiresAt <= nowMs.value
}
const isPending = item => Number(item.status) === 0 && !isLocallyExpired(item)
const expiryText = (item) => {
  if (isLocallyExpired(item)) return '已过期'
  const remainingSeconds = Math.ceil((expiryTimestamp(item) - nowMs.value) / 1000)
  if (!Number.isFinite(remainingSeconds)) return '有效期未知'
  const minutes = Math.floor(remainingSeconds / 60)
  const seconds = remainingSeconds % 60
  return `剩余 ${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

const updateDraft = (field, value) => store.updateDraft({ [field]: value })
const send = async () => {
  if (!canSend.value) return
  successVisible.value = false
  unavailableMessage.value = ''
  try {
    const result = await store.sendDraft()
    if (result?.status === 'success') {
      successVisible.value = true
      unavailableMessage.value = ''
    } else if (result?.status === 'unavailable') {
      unavailableMessage.value = result.reason === 'DAILY_LIMIT_REACHED' ? '今天的投喂次数已用完，输入已保留。' : '当前操作暂不可用，输入已保留。'
    }
  } catch (error) {
    showToast('发送失败，输入已保留')
  }
}
const accept = async (item) => {
  try {
    await store.accept(item)
  } catch (error) {
    showToast('投喂状态已变化，已同步最新结果')
  }
}
const reject = async (item) => {
  try {
    await store.reject(item, rejectReasons.value[item.id] || '')
  } catch (error) {
    showToast('投喂状态已变化，已同步最新结果')
  }
}
const unsupported = async (action) => {
  successVisible.value = false
  const actions = {
    counter: store.requestCounter,
    completion: store.requestCompletion,
    withdraw: store.requestWithdraw
  }
  const result = await actions[action].call(store)
  if (result?.status === 'unavailable') unavailableMessage.value = '后端尚不支持此动作，你的输入和当前状态都没有改变。'
}
const statusText = item => isLocallyExpired(item)
  ? '已过期'
  : ({ 0: '待领取', 1: '已接受', 2: '已拒绝', 3: '已过期' })[Number(item.status)] || '状态未知'

onMounted(() => {
  expiryTimer = window.setInterval(() => { nowMs.value = Date.now() }, 1000)
  store.fetchAll().catch(() => showToast('投喂记录加载失败，请下拉重试'))
})
onUnmounted(() => {
  if (expiryTimer !== null) window.clearInterval(expiryTimer)
})
</script>

<template>
  <main class="feed-page">
    <header class="feed-header">
      <p class="eyebrow">TODAY'S SIGNAL</p>
      <h1>投喂 TA</h1>
      <p>用一份小小的期待，约定今天的味道。</p>
    </header>

    <section class="composer" aria-labelledby="feed-compose-title">
      <div class="composer-heading">
        <div>
          <span>今日剩余</span>
          <strong>{{ store.today?.remainingCount ?? '—' }}</strong>
        </div>
        <p v-if="store.today?.remainingCount === 0">次数已用完，草稿仍会保留。</p>
      </div>
      <h2 id="feed-compose-title">选择投喂</h2>
      <div class="feed-types" role="radiogroup" aria-label="投喂类型">
        <button
          v-for="type in feedTypes"
          :key="type.value"
          type="button"
          :class="{ active: store.draft.feedType === type.value }"
          :aria-pressed="store.draft.feedType === type.value"
          :disabled="store.isMutationPending"
          @click="updateDraft('feedType', type.value)"
        >
          <van-icon :name="type.icon" /><span>{{ type.label }}</span>
        </button>
      </div>
      <label for="feed-content">想投喂什么</label>
      <input
        id="feed-content"
        :value="store.draft.content"
        maxlength="120"
        placeholder="例如：下班一起吃火锅"
        :disabled="store.isMutationPending"
        @input="updateDraft('content', $event.target.value)"
      >
      <label for="feed-message">留句话（可选）</label>
      <textarea
        id="feed-message"
        :value="store.draft.message"
        maxlength="300"
        rows="3"
        placeholder="只在这次投喂中发送"
        :disabled="store.isMutationPending"
        @input="updateDraft('message', $event.target.value)"
      />
      <p class="image-contract">投喂专属图片上传暂不可用；不会调用不存在的端点。</p>
      <button class="send-button" data-test="feed-send" type="button" :disabled="!canSend" @click="send">
        <van-icon name="guide-o" /> {{ store.isMutationPending ? '正在发送…' : '发送投喂' }}
      </button>
      <button class="text-action" data-test="feed-counter" type="button" :disabled="store.isMutationPending" @click="unsupported('counter')">
        换一种投喂（暂不可用）
      </button>
    </section>

    <p v-if="unavailableMessage" class="unavailable-notice" role="status">{{ unavailableMessage }}</p>
    <div
      v-if="successVisible"
      class="success-feedback"
      data-test="feed-success"
      :data-motion="prefersReducedMotion ? 'static' : 'animated'"
      role="status"
    >
      <van-icon name="passed" />
      <span>投喂已送达</span>
    </div>

    <section class="feed-list" aria-labelledby="received-title">
      <div class="section-heading"><h2 id="received-title">TA 发来的投喂</h2><span>{{ store.received.length }}</span></div>
      <p v-if="store.loadStatus === 'loading' && !store.received.length" class="list-state">正在接收信号…</p>
      <p v-else-if="store.loadStatus === 'error' && !store.received.length" class="list-state">暂时无法读取投喂记录。</p>
      <p v-else-if="!store.received.length" class="list-state">今天还没有收到投喂。</p>
      <article v-for="item in store.received" :key="item.id" class="feed-card">
        <div class="card-head">
          <div>
            <span>{{ item.senderName || 'TA' }}</span>
            <small>{{ item.createTime }}</small>
            <small v-if="item.expireTime && Number(item.status) === 0" :data-test="`feed-countdown-${item.id}`">{{ expiryText(item) }}</small>
          </div>
          <strong :class="`status-${item.status}`">{{ statusText(item) }}</strong>
        </div>
        <h3>{{ item.feedTypeName || feedTypes.find(type => type.value === item.feedType)?.label || '投喂' }}</h3>
        <p>{{ item.content }}</p>
        <p v-if="item.message" class="feed-message">{{ item.message }}</p>
        <div v-if="isPending(item)" class="receive-actions">
          <input v-model="rejectReasons[item.id]" maxlength="100" placeholder="拒绝原因（可选）" :disabled="store.isMutationPending">
          <button type="button" :disabled="store.isMutationPending" @click="reject(item)">拒绝</button>
          <button type="button" :disabled="store.isMutationPending" @click="accept(item)">接受</button>
        </div>
        <button v-if="Number(item.status) === 1" class="text-action" type="button" @click="unsupported('completion')">完成确认（暂不可用）</button>
      </article>
    </section>

    <section class="feed-list" aria-labelledby="sent-title">
      <div class="section-heading"><h2 id="sent-title">我发出的投喂</h2><span>{{ store.sent.length }}</span></div>
      <p v-if="!store.sent.length" class="list-state">还没有发出的投喂。</p>
      <article v-for="item in store.sent" :key="item.id" class="feed-card compact">
        <div><strong>{{ item.content }}</strong><small>{{ item.createTime }}</small></div>
        <span>{{ statusText(item) }}</span>
        <button v-if="Number(item.status) === 0" class="text-action" type="button" @click="unsupported('withdraw')">撤回（暂不可用）</button>
      </article>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.feed-page { min-height: 100%; padding: $space-5 $page-padding $space-8; color: $cosmos-text; }.feed-header { padding: $space-2 0 $space-5; }.eyebrow { color: $cosmos-secondary; font-size: $fs-caption; }.feed-header h1 { margin-top: $space-1; font-size: $fs-display; }.feed-header > p:last-child { margin-top: $space-2; color: $cosmos-text-muted; }
.composer { padding: $space-4; border: 1px solid $cosmos-border; border-radius: $radius-md; background: $cosmos-surface-elevated; }.composer-heading { display: flex; align-items: center; justify-content: space-between; gap: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }.composer-heading div { display: flex; align-items: baseline; gap: $space-2; }.composer-heading strong { color: $cosmos-gold; font-size: $fs-title; }.composer h2 { margin-top: $space-4; font-size: $fs-title; }
.feed-types { display: grid; margin-top: $space-3; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: $space-2; }.feed-types button { display: flex; min-height: 64px; padding: $space-2; flex-direction: column; align-items: center; justify-content: center; gap: $space-1; border: 1px solid $cosmos-border; border-radius: $radius-sm; background: rgba(255,255,255,.03); color: $cosmos-text-muted; }.feed-types button.active { border-color: $cosmos-secondary; background: rgba(84,232,211,.1); color: $cosmos-secondary; }
.composer label { display: block; margin: $space-4 0 $space-2; color: $cosmos-gold; font-size: $fs-label; }.composer input, .composer textarea, .receive-actions input { width: 100%; padding: $space-3; border: 1px solid $cosmos-border; border-radius: $radius-sm; outline: 0; background: rgba(255,255,255,.04); color: $cosmos-text; font: inherit; }.composer textarea { resize: vertical; }.image-contract { margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.send-button { width: 100%; min-height: 52px; margin-top: $space-4; border: 0; border-radius: $radius-sm; background: $cosmos-primary; color: white; font-size: 16px; font-weight: $fw-semibold; }.send-button:disabled, button:disabled { cursor: not-allowed; opacity: .48; }.text-action { min-height: 40px; border: 0; background: transparent; color: $cosmos-text-muted; text-decoration: underline; }
.unavailable-notice, .success-feedback { margin-top: $space-3; padding: $space-3; border-left: 3px solid $cosmos-gold; background: rgba(255,200,87,.08); color: $cosmos-gold; }.success-feedback { display: flex; align-items: center; gap: $space-2; border-left-color: $cosmos-secondary; color: $cosmos-secondary; }.success-feedback[data-motion='animated'] { animation: success-pulse 480ms ease-out; }
.feed-list { margin-top: $space-6; }.section-heading { display: flex; align-items: center; justify-content: space-between; }.section-heading h2 { font-size: $fs-title; }.section-heading span { color: $cosmos-secondary; }.list-state { padding: $space-5 0; color: $cosmos-text-muted; text-align: center; }
.feed-card { margin-top: $space-3; padding: $space-4; border: 1px solid $cosmos-border; border-radius: $radius-md; background: rgba(255,255,255,.04); }.card-head, .compact { display: flex; align-items: center; justify-content: space-between; gap: $space-3; }.card-head div, .compact div { display: flex; min-width: 0; flex-direction: column; gap: $space-1; }.card-head small, .compact small { color: $cosmos-text-muted; }.card-head > strong { flex: 0 0 auto; color: $cosmos-gold; font-size: $fs-caption; }.card-head .status-1 { color: $cosmos-secondary; }.card-head .status-2, .card-head .status-3 { color: $cosmos-text-muted; }.feed-card h3 { margin-top: $space-3; font-size: $fs-title; }.feed-card > p { margin-top: $space-2; overflow-wrap: anywhere; }.feed-message { padding: $space-3; background: rgba(255,255,255,.04); color: $cosmos-text-muted; }.receive-actions { display: grid; margin-top: $space-4; grid-template-columns: 1fr auto auto; gap: $space-2; }.receive-actions button { min-width: 60px; border: 1px solid $cosmos-border; border-radius: $radius-sm; background: transparent; color: $cosmos-text; }.receive-actions button:last-child { border-color: $cosmos-secondary; color: $cosmos-secondary; }
@keyframes success-pulse { 0% { opacity: 0; transform: translateY(8px); } 100% { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .success-feedback[data-motion='animated'] { animation: none; } }
@media (max-width: 360px) { .feed-types { grid-template-columns: repeat(2, minmax(0,1fr)); }.receive-actions { grid-template-columns: 1fr 1fr; }.receive-actions input { grid-column: 1 / -1; } }
</style>
