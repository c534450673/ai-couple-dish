<template>
  <div class="empty-state">
    <div class="empty-icon" v-if="icon">
      <van-icon :name="icon" :size="iconSize" :color="iconColor" />
    </div>
    <div class="empty-image" v-else-if="image">
      <img :src="image" :alt="description" />
    </div>
    <div class="empty-title" v-if="title">{{ title }}</div>
    <div class="empty-description" v-if="description">{{ description }}</div>
    <div class="empty-actions" v-if="$slots.action || actionText">
      <slot name="action">
        <van-button
          v-if="actionText"
          type="primary"
          round
          size="small"
          @click="handleAction"
        >
          {{ actionText }}
        </van-button>
      </slot>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  icon: {
    type: String,
    default: null
  },
  iconSize: {
    type: [Number, String],
    default: 48
  },
  iconColor: {
    type: String,
    default: '#ccc'
  },
  image: {
    type: String,
    default: null
  },
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  actionText: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['action'])

const handleAction = () => {
  emit('action')
}
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;

  .empty-icon {
    margin-bottom: 16px;
  }

  .empty-image {
    margin-bottom: 16px;

    img {
      width: 120px;
      height: 120px;
    }
  }

  .empty-title {
    font-size: 16px;
    font-weight: 500;
    color: #333;
    margin-bottom: 8px;
  }

  .empty-description {
    font-size: 14px;
    color: #999;
    margin-bottom: 24px;
    max-width: 280px;
  }
}
</style>
