<script setup>
defineProps({
  resourceKey: { type: String, required: true },
  title: { type: String, required: true },
  to: { type: [String, Object], required: true },
  icon: { type: String, required: true },
  resource: { type: Object, required: true },
  accent: { type: String, default: 'mint' },
  linkTest: { type: String, default: '' },
  unavailableText: { type: String, default: '当前不可用' }
})

defineEmits(['retry', 'navigate'])
</script>

<template>
  <article
    class="home-bento"
    :class="`home-bento--${accent}`"
  >
    <router-link
      class="home-bento__link"
      :to="to"
      :data-test="linkTest || undefined"
      @click="$emit('navigate', to)"
    >
      <span class="home-bento__header">
        <van-icon
          :name="icon"
          aria-hidden="true"
        />
        <span class="home-bento__title">{{ title }}</span>
      </span>
      <span
        :data-test="`${resourceKey}-state`"
        class="home-bento__body"
      >
        <slot v-if="resource.status === 'success'" />
        <span
          v-else-if="resource.status === 'loading'"
          class="home-bento__state"
        >正在加载</span>
        <span
          v-else-if="resource.status === 'empty'"
          class="home-bento__state"
        >暂无数据</span>
        <span
          v-else-if="resource.status === 'unavailable'"
          class="home-bento__state"
        >{{ unavailableText }}</span>
        <span
          v-else
          class="home-bento__state"
        >暂时无法加载</span>
      </span>
      <van-icon
        class="home-bento__arrow"
        name="arrow"
        aria-hidden="true"
      />
    </router-link>
    <button
      v-if="resource.status === 'error'"
      class="home-bento__retry"
      type="button"
      :data-test="`retry-${resourceKey}`"
      @click="$emit('retry', resourceKey)"
    >
      重试
    </button>
  </article>
</template>

<style lang="scss" scoped>
.home-bento {
  position: relative;
  min-width: 0;
  height: 154px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.16);
}

.home-bento::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  background: #54e8d3;
  content: '';
}

.home-bento--gold::before { background: #ffc857; }
.home-bento--coral::before { background: #ff5d73; }
.home-bento--violet::before { background: #c1c4e6; }

.home-bento__link {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  min-height: 44px;
  padding: 16px;
  color: #f8f5f7;
  text-decoration: none;
}

.home-bento__link:focus-visible,
.home-bento__retry:focus-visible {
  outline: 3px solid #54e8d3;
  outline-offset: -3px;
}

.home-bento__header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #c7c5ce;
}

.home-bento__header :deep(.van-icon) {
  flex: 0 0 auto;
  color: #54e8d3;
  font-size: 20px;
}

.home-bento--gold .home-bento__header :deep(.van-icon) { color: #ffc857; }
.home-bento--coral .home-bento__header :deep(.van-icon) { color: #ff9da4; }
.home-bento--violet .home-bento__header :deep(.van-icon) { color: #c1c4e6; }

.home-bento__title {
  overflow-wrap: anywhere;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.35;
}

.home-bento__body {
  display: -webkit-box;
  overflow: hidden;
  padding-right: 18px;
  color: #f8f5f7;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.35;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.home-bento__state {
  color: #aaa8b1;
  font-size: 12px;
  font-weight: 500;
}

.home-bento__arrow {
  position: absolute;
  right: 14px;
  bottom: 16px;
  color: #919098;
}

.home-bento__retry {
  position: absolute;
  right: 10px;
  bottom: 8px;
  z-index: 2;
  min-width: 52px;
  min-height: 44px;
  border: 0;
  background: transparent;
  color: #ff9da4;
  font-size: 12px;
  font-weight: 700;
}
</style>
