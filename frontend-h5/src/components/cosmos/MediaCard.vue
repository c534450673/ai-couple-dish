<script setup>
defineProps({
  src: { type: String, required: true },
  alt: { type: String, required: true }
})
</script>

<template>
  <article class="media-card">
    <img
      class="media-card__image"
      :src="src"
      :alt="alt"
    >
    <div class="media-card__content">
      <slot />
    </div>
  </article>
</template>

<style lang="scss" scoped>
.media-card {
  overflow: hidden;
  border: 1px solid $cosmos-glass-border;
  border-radius: $cosmos-card-radius;
  background: $cosmos-surface;
  box-shadow: $shadow-card;
}

.media-card__image {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.media-card__content {
  padding: $space-4;
}
</style>
