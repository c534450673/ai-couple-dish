<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => ['idle', 'loading', 'success', 'empty', 'error', 'unauthorized', 'unbound'].includes(value)
  },
  message: {
    type: String,
    default: ''
  }
})

defineEmits(['retry', 'bind'])

const stateCopy = {
  loading: { title: '正在加载', description: '正在同步你们的专属内容' },
  empty: { title: '暂无内容', description: '这里还在等待第一条共同记录' },
  error: { title: '加载失败', description: '网络开了小差，请稍后重试' },
  unauthorized: { title: '登录状态已失效', description: '请重新登录后继续' },
  unbound: { title: '还没有绑定伴侣', description: '完成绑定后即可解锁情侣空间' }
}
</script>

<template>
  <slot v-if="props.status === 'success'" />
  <section
    v-else-if="props.status !== 'idle'"
    class="async-state"
    :class="`async-state--${props.status}`"
    :role="['error', 'unauthorized'].includes(props.status) ? 'alert' : 'status'"
    :aria-live="['error', 'unauthorized'].includes(props.status) ? 'assertive' : 'polite'"
  >
    <span
      v-if="props.status === 'loading'"
      class="async-state__spinner"
      aria-hidden="true"
    />
    <h2 class="async-state__title">
      {{ stateCopy[props.status].title }}
    </h2>
    <p class="async-state__description">
      {{ props.message || stateCopy[props.status].description }}
    </p>
    <button
      v-if="props.status === 'error'"
      class="async-state__action"
      data-action="retry"
      type="button"
      @click="$emit('retry')"
    >
      重新加载
    </button>
    <button
      v-if="props.status === 'unbound'"
      class="async-state__action"
      data-action="bind"
      type="button"
      @click="$emit('bind')"
    >
      去绑定
    </button>
  </section>
</template>

<style lang="scss" scoped>
.async-state {
  display: flex;
  min-height: 280px;
  padding: $space-8 $space-5;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.async-state__spinner {
  width: 32px;
  height: 32px;
  margin-bottom: $space-4;
  border: 3px solid $cosmos-border;
  border-top-color: $cosmos-secondary;
  border-radius: 50%;
  animation: cosmos-orbit $cosmos-duration-slow linear infinite;
}

.async-state__title {
  color: $cosmos-text;
  font-size: $fs-title;
  font-weight: $fw-semibold;
}

.async-state__description {
  max-width: 280px;
  margin-top: $space-2;
  color: $cosmos-text-muted;
  font-size: $fs-label;
}

.async-state__action {
  min-width: 120px;
  min-height: $cosmos-min-touch-target;
  margin-top: $space-5;
  padding: 0 $space-5;
  border: 0;
  border-radius: $radius-pill;
  background: $cosmos-primary;
  color: $color-on-primary;
  cursor: pointer;
  font-size: $fs-label;
  font-weight: $fw-semibold;
}
</style>
