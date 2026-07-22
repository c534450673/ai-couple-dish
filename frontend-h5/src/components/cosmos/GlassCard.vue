<template>
  <article class="glass-card">
    <slot />
  </article>
</template>

<style lang="scss" scoped>
.glass-card {
  padding: $space-4;
  border: 1px solid $cosmos-glass-border;
  border-radius: $cosmos-card-radius;
  background: rgba(20, 27, 51, 0.82);
  box-shadow: $shadow-card;
  backdrop-filter: blur(12px);
}
</style>
