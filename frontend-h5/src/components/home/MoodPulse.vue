<script setup>
import { computed } from 'vue'

const props = defineProps({
  resource: { type: Object, required: true },
  currentUserId: { type: [String, Number], default: '' },
  submitting: { type: Boolean, default: false },
  submitErrorCode: { type: [String, Number], default: null },
  reducedMotion: { type: Boolean, default: false }
})

const emit = defineEmits(['retry', 'send'])

const moodChoices = Object.freeze([
  { type: 'happy', label: '开心', emoji: '😊' },
  { type: 'love', label: '爱你', emoji: '❤️' },
  { type: 'miss_you', label: '想你', emoji: '🥺' },
  { type: 'tired', label: '疲惫', emoji: '😴' },
  { type: 'upset', label: '烦躁', emoji: '😤' },
  { type: 'sad', label: '难过', emoji: '😢' },
  { type: 'angry', label: '生气', emoji: '😠' },
  { type: 'anxious', label: '焦虑', emoji: '😰' }
])

const moodByType = new Map(moodChoices.map(mood => [mood.type, mood]))

const records = computed(() => Array.isArray(props.resource.data) ? props.resource.data : [])
const hasCurrentUser = computed(() => props.currentUserId !== '' && props.currentUserId !== null)
const belongsToCurrentUser = record => hasCurrentUser.value &&
  String(record?.sender?.id) === String(props.currentUserId)

// 今日心情接口按创建时间倒序返回，首条即为双方各自的最新记录。
const myMood = computed(() => records.value.find(belongsToCurrentUser) || null)
const partnerMood = computed(() => records.value.find(record => !belongsToCurrentUser(record)) || null)

const safeMood = record => moodByType.get(record?.moodType) || null
const myMoodMeta = computed(() => safeMood(myMood.value))
const partnerMoodMeta = computed(() => safeMood(partnerMood.value))
const currentMoodType = computed(() => myMoodMeta.value?.type || '')

const sendMood = (moodType) => {
  if (!props.submitting) emit('send', moodType)
}
</script>

<template>
  <section
    class="mood-pulse"
    :class="{ 'mood-pulse--reduced': reducedMotion }"
    :data-motion="reducedMotion ? 'static' : 'animated'"
    data-test="mood-pulse"
    aria-label="今日心情"
    :aria-busy="resource.status === 'loading' || submitting"
  >
    <header class="mood-pulse__header">
      <div>
        <p class="mood-pulse__eyebrow">
          MOOD PULSE
        </p>
        <h2>今天的心情</h2>
      </div>
      <span
        class="mood-pulse__signal"
        aria-hidden="true"
      >
        <i />
        <i />
        <i />
      </span>
    </header>

    <div
      v-if="resource.status === 'success' && records.length"
      class="mood-pulse__snapshot"
      data-test="mood-snapshot"
      aria-live="polite"
    >
      <div
        class="mood-pulse__person"
        data-test="mood-self"
      >
        <span class="mood-pulse__person-label">我</span>
        <span
          class="mood-pulse__current"
          :aria-label="myMoodMeta ? `我的最新心情：${myMoodMeta.label}` : '我今天还未发送心情'"
        >
          <b aria-hidden="true">{{ myMoodMeta?.emoji || '·' }}</b>
          <span>{{ myMoodMeta?.label || '等待记录' }}</span>
        </span>
      </div>
      <span
        class="mood-pulse__divider"
        aria-hidden="true"
      />
      <div
        class="mood-pulse__person mood-pulse__person--partner"
        data-test="mood-partner"
      >
        <span class="mood-pulse__person-label">TA</span>
        <span
          class="mood-pulse__current"
          :aria-label="partnerMoodMeta ? `TA的最新心情：${partnerMoodMeta.label}` : 'TA今天还未发送心情'"
        >
          <b aria-hidden="true">{{ partnerMoodMeta?.emoji || '·' }}</b>
          <span>{{ partnerMoodMeta?.label || '等待回应' }}</span>
        </span>
      </div>
    </div>

    <div
      v-else-if="resource.status === 'loading'"
      class="mood-pulse__state mood-pulse__state--loading"
      data-test="mood-loading"
      aria-live="polite"
    >
      <span
        class="mood-pulse__loading-mark"
        aria-hidden="true"
      />
      <span>正在感应今日心情</span>
    </div>

    <div
      v-else-if="resource.status === 'error'"
      class="mood-pulse__state mood-pulse__state--error"
      data-test="mood-error"
      role="status"
    >
      <span>今日心情暂时无法加载</span>
      <button
        type="button"
        data-test="retry-mood"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>

    <div
      v-else
      class="mood-pulse__state mood-pulse__state--empty"
      data-test="mood-empty"
      aria-live="polite"
    >
      今天还没有心情记录
    </div>

    <div class="mood-pulse__composer">
      <p>我的心情</p>
      <div
        class="mood-pulse__choices"
        aria-label="选择并发送我的心情"
      >
        <button
          v-for="mood in moodChoices"
          :key="mood.type"
          class="mood-pulse__choice"
          :class="{ 'mood-pulse__choice--selected': currentMoodType === mood.type }"
          type="button"
          :data-test="`mood-choice-${mood.type}`"
          :data-selected="currentMoodType === mood.type ? 'true' : 'false'"
          :aria-label="`${currentMoodType === mood.type ? '已选择' : '发送'}${mood.label}心情`"
          :aria-pressed="currentMoodType === mood.type"
          :title="mood.label"
          :disabled="submitting"
          @click="sendMood(mood.type)"
        >
          <span aria-hidden="true">{{ mood.emoji }}</span>
        </button>
      </div>
      <p
        v-if="submitting"
        class="mood-pulse__submit-state"
        data-test="mood-submitting"
        aria-live="polite"
      >
        正在发送心情
      </p>
      <p
        v-else-if="submitErrorCode !== null"
        class="mood-pulse__submit-state mood-pulse__submit-state--error"
        data-test="mood-submit-error"
        role="status"
      >
        心情发送失败，请重试
      </p>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.mood-pulse {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.055);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.18);
  color: #f8f5f7;
}

.mood-pulse::before {
  position: absolute;
  top: 0;
  right: 18px;
  left: 18px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(84, 232, 211, 0.62), transparent);
  content: '';
}

.mood-pulse__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.mood-pulse__eyebrow {
  margin: 0 0 4px;
  color: #54e8d3;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0;
}

.mood-pulse h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: 0;
}

.mood-pulse__signal {
  display: flex;
  align-items: center;
  gap: 3px;
  width: 34px;
  height: 24px;
}

.mood-pulse__signal i {
  display: block;
  width: 3px;
  border-radius: 999px;
  background: #ff5d73;
  animation: mood-signal 1.15s ease-in-out infinite alternate;
}

.mood-pulse__signal i:nth-child(1) { height: 8px; }
.mood-pulse__signal i:nth-child(2) { height: 20px; animation-delay: 140ms; }
.mood-pulse__signal i:nth-child(3) { height: 12px; animation-delay: 280ms; }

.mood-pulse__snapshot {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1px minmax(0, 1fr);
  align-items: stretch;
  min-height: 70px;
  margin-bottom: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.mood-pulse__person {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  min-width: 0;
  padding: 10px 12px 10px 0;
}

.mood-pulse__person--partner {
  padding-right: 0;
  padding-left: 12px;
}

.mood-pulse__person-label {
  color: #aaa8b1;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.mood-pulse__current {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
  font-weight: 700;
}

.mood-pulse__current b {
  flex: 0 0 auto;
  font-size: 23px;
  font-weight: 400;
  line-height: 1;
}

.mood-pulse__current span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mood-pulse__divider {
  width: 1px;
  margin: 12px 0;
  background: rgba(255, 255, 255, 0.1);
}

.mood-pulse__state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 70px;
  margin-bottom: 16px;
  padding: 10px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #aaa8b1;
  font-size: 12px;
}

.mood-pulse__state--loading {
  justify-content: flex-start;
}

.mood-pulse__loading-mark {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(84, 232, 211, 0.25);
  border-top-color: #54e8d3;
  border-radius: 50%;
  animation: mood-spin 700ms linear infinite;
}

.mood-pulse__state button {
  min-width: 58px;
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  background: rgba(255, 93, 115, 0.14);
  color: #ff9da4;
  font-size: 12px;
  font-weight: 800;
}

.mood-pulse__composer > p:first-child {
  margin: 0 0 10px;
  color: #c7c5ce;
  font-size: 11px;
  font-weight: 700;
}

.mood-pulse__choices {
  display: flex;
  gap: 8px;
  width: 100%;
  overflow-x: auto;
  padding: 2px 0 5px;
  scrollbar-width: none;
  overscroll-behavior-x: contain;
}

.mood-pulse__choices::-webkit-scrollbar {
  display: none;
}

.mood-pulse__choice {
  display: inline-flex;
  flex: 0 0 44px;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  background: rgba(10, 10, 16, 0.42);
  color: #f8f5f7;
  font: inherit;
  transition: border-color 180ms ease, background-color 180ms ease, transform 180ms ease;
}

.mood-pulse__choice span {
  font-size: 21px;
  line-height: 1;
}

.mood-pulse__choice--selected {
  border-color: #54e8d3;
  background: rgba(84, 232, 211, 0.14);
  box-shadow: inset 0 0 0 1px rgba(84, 232, 211, 0.22);
}

.mood-pulse__choice:active:not(:disabled) {
  transform: scale(0.94);
}

.mood-pulse__choice:disabled {
  cursor: wait;
  opacity: 0.5;
}

.mood-pulse__choice:focus-visible,
.mood-pulse__state button:focus-visible {
  outline: 3px solid #54e8d3;
  outline-offset: 2px;
}

.mood-pulse__submit-state {
  min-height: 16px;
  margin: 7px 0 0;
  color: #54e8d3;
  font-size: 10px;
  line-height: 1.4;
}

.mood-pulse__submit-state--error {
  color: #ff9da4;
}

[data-motion='animated'].mood-pulse {
  animation: mood-enter 380ms ease both;
}

@keyframes mood-enter {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes mood-signal {
  to { transform: scaleY(0.48); opacity: 0.55; }
}

@keyframes mood-spin {
  to { transform: rotate(360deg); }
}

.mood-pulse--reduced,
.mood-pulse--reduced *,
.mood-pulse--reduced *::before,
.mood-pulse--reduced *::after {
  scroll-behavior: auto !important;
  animation: none !important;
  transition: none !important;
}

@media (prefers-reduced-motion: reduce) {
  .mood-pulse,
  .mood-pulse *,
  .mood-pulse *::before,
  .mood-pulse *::after {
    scroll-behavior: auto !important;
    animation: none !important;
    transition: none !important;
  }
}
</style>
