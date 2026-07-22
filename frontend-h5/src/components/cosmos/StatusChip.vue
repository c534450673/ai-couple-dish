<script setup>
defineProps({
  tone: {
    type: String,
    default: 'neutral',
    validator: (value) => ['neutral', 'success', 'warning', 'danger'].includes(value)
  }
})
</script>

<template>
  <span
    class="status-chip"
    :class="`status-chip--${tone}`"
    role="status"
  >
    <slot />
  </span>
</template>

<style lang="scss" scoped>
.status-chip {
  display: inline-flex;
  min-height: 24px;
  padding: 2px $space-2;
  align-items: center;
  border: 1px solid $cosmos-border;
  border-radius: $radius-pill;
  background: $cosmos-surface-elevated;
  color: $cosmos-text-muted;
  font-size: $fs-caption;
  line-height: $lh-caption;
}

.status-chip--success { border-color: $cosmos-secondary; color: $cosmos-secondary; }
.status-chip--warning { border-color: $cosmos-gold; color: $cosmos-gold; }
.status-chip--danger { border-color: $cosmos-primary; color: $cosmos-primary; }
</style>
