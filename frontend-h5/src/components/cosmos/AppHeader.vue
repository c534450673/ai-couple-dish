<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})
</script>

<template>
  <header class="app-header">
    <div class="app-header__copy">
      <h1>{{ title }}</h1>
      <p v-if="subtitle">
        {{ subtitle }}
      </p>
    </div>
    <div
      v-if="$slots.actions"
      class="app-header__actions"
    >
      <slot name="actions" />
    </div>
  </header>
</template>

<style lang="scss" scoped>
.app-header {
  display: flex;
  min-height: 64px;
  padding: calc($space-3 + env(safe-area-inset-top)) $page-padding $space-3;
  align-items: center;
  justify-content: space-between;
  gap: $space-3;
  background: rgba(11, 16, 32, 0.9);
  border-bottom: 1px solid $cosmos-border;
  backdrop-filter: blur(12px);
}

.app-header h1 {
  color: $cosmos-text;
  font-size: $fs-title;
  font-weight: $fw-semibold;
  line-height: $lh-title;
}

.app-header p {
  margin-top: $space-1;
  color: $cosmos-text-muted;
  font-size: $fs-caption;
  line-height: $lh-caption;
}

.app-header__copy {
  min-width: 0;
}

.app-header__actions {
  display: flex;
  flex: 0 0 auto;
  gap: $space-2;
}
</style>
