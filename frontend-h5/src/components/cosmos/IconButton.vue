<script setup>
defineProps({
  label: {
    type: String,
    required: true,
    validator: (value) => value.trim().length > 0
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])
</script>

<template>
  <button
    class="cosmos-icon-button"
    type="button"
    :aria-label="label"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style lang="scss" scoped>
.cosmos-icon-button {
  display: inline-grid;
  width: $cosmos-min-touch-target;
  height: $cosmos-min-touch-target;
  min-width: $cosmos-min-touch-target;
  padding: 0;
  place-items: center;
  border: 1px solid $cosmos-glass-border;
  border-radius: 50%;
  background: $cosmos-surface-raised;
  color: $cosmos-text;
  cursor: pointer;
}

.cosmos-icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
</style>
