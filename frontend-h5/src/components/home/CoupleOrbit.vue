<script setup>
import RollingCounter from './RollingCounter.vue'
import fallbackAvatar from '@/assets/cosmos/partner-avatar.webp'

defineProps({
  currentAvatar: { type: String, default: '' },
  couple: { type: Object, required: true },
  timer: { type: Object, required: true },
  reducedMotion: { type: Boolean, default: false }
})

defineEmits(['retry'])
</script>

<template>
  <section
    class="couple-orbit"
    :class="{ 'couple-orbit--reduced': reducedMotion }"
    :data-motion="reducedMotion ? 'static' : 'animated'"
    aria-labelledby="relationship-title"
  >
    <div class="couple-orbit__avatars">
      <span class="couple-orbit__path" />
      <img
        data-test="current-avatar"
        class="couple-orbit__avatar couple-orbit__avatar--current"
        :src="currentAvatar || fallbackAvatar"
        alt="我的头像"
        width="52"
        height="52"
      >
      <img
        data-test="partner-avatar"
        class="couple-orbit__avatar couple-orbit__avatar--partner"
        :src="couple.data?.partner?.avatarUrl || fallbackAvatar"
        alt="伴侣头像"
        width="52"
        height="52"
      >
    </div>

    <div class="couple-orbit__identity">
      <p class="couple-orbit__eyebrow">
        COUPLE COSMOS
      </p>
      <h1
        id="relationship-title"
        class="couple-orbit__title"
      >
        <template v-if="couple.status === 'success'">
          我和 {{ couple.data.partner.nickName || '伴侣' }}
        </template>
        <template v-else-if="couple.status === 'loading'">
          正在连接彼此
        </template>
        <template v-else-if="couple.status === 'empty'">
          关系信息待完善
        </template>
        <template v-else>
          关系信息暂不可用
        </template>
      </h1>
      <button
        v-if="couple.status === 'error'"
        class="couple-orbit__retry"
        type="button"
        data-test="retry-couple"
        @click="$emit('retry', 'couple')"
      >
        重试关系信息
      </button>
    </div>

    <div
      class="couple-orbit__timer"
      data-test="timer-state"
    >
      <template v-if="timer.status === 'success'">
        <van-icon
          name="like"
          aria-hidden="true"
        />
        <span class="couple-orbit__timer-label">相伴</span>
        <strong><RollingCounter
          :value="timer.data.loveDays"
          :reduced-motion="reducedMotion"
        /></strong>
        <span>天</span>
      </template>
      <span v-else-if="timer.status === 'loading'">天数加载中</span>
      <span v-else-if="timer.status === 'empty'">相伴天数待记录</span>
      <button
        v-else
        type="button"
        data-test="retry-timer"
        @click="$emit('retry', 'timer')"
      >
        重试相伴天数
      </button>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.couple-orbit {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 72px;
  color: #f8f5f7;
}

.couple-orbit__avatars {
  position: relative;
  width: 76px;
  height: 56px;
}

.couple-orbit__path {
  position: absolute;
  inset: 3px 7px;
  border: 1px solid rgba(84, 232, 211, 0.48);
  border-radius: 50%;
  animation: orbit-glow 3.2s ease-in-out infinite;
}

.couple-orbit__avatar {
  position: absolute;
  width: 48px;
  height: 48px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  background: #26242e;
  object-fit: cover;
}

.couple-orbit__avatar--current {
  top: 0;
  left: 0;
  z-index: 1;
}

.couple-orbit__avatar--partner {
  right: 0;
  bottom: 0;
  border-color: #54e8d3;
}

.couple-orbit__identity {
  min-width: 0;
}

.couple-orbit__eyebrow {
  margin: 0 0 4px;
  color: #54e8d3;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0;
}

.couple-orbit__title {
  overflow: hidden;
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.couple-orbit__retry {
  min-height: 44px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #ff9da4;
  font-size: 12px;
}

.couple-orbit__retry:focus-visible,
.couple-orbit__timer button:focus-visible {
  outline: 3px solid #54e8d3;
  outline-offset: 2px;
}

.couple-orbit__timer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 98px;
  min-height: 44px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: #f8f5f7;
  font-size: 11px;
  white-space: nowrap;
  backdrop-filter: blur(10px);

  :deep(.van-icon) {
    color: #ff5d73;
  }

  button {
    min-height: 44px;
    border: 0;
    background: transparent;
    color: #ff9da4;
    font-size: 11px;
  }
}

.couple-orbit__timer-label {
  color: #c7c5ce;
}

@keyframes orbit-glow {
  50% { opacity: 0.45; transform: scale(1.05); }
}

.couple-orbit--reduced .couple-orbit__path {
  animation: none;
}

@media (prefers-reduced-motion: reduce) {
  .couple-orbit__path { animation: none; }
}

@media (max-width: 380px) {
  .couple-orbit {
    gap: 8px;
  }

  .couple-orbit__avatars {
    width: 68px;
  }

  .couple-orbit__timer {
    min-width: 90px;
    padding: 0 8px;
  }
}
</style>
