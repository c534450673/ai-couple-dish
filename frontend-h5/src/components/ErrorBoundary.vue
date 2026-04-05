<template>
  <div class="error-boundary">
    <slot v-if="!hasError"></slot>
    <div v-else class="error-container">
      <div class="error-icon">
        <van-icon name="warning" size="48" color="#ff4757" />
      </div>
      <div class="error-title">{{ title }}</div>
      <div class="error-message">{{ message }}</div>
      <van-button type="primary" round size="small" @click="handleRetry">
        重试
      </van-button>
      <van-button plain round size="small" @click="handleGoBack">
        返回上一页
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  title: {
    type: String,
    default: '出错了'
  },
  message: {
    type: String,
    default: '抱歉，页面发生了一些问题'
  },
  onRetry: {
    type: Function,
    default: null
  }
})

const emit = defineEmits(['retry', 'error'])

const router = useRouter()
const hasError = ref(false)
const errorInfo = ref(null)

onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorInfo.value = {
    err,
    info
  }
  emit('error', { err, info })
  console.error('Error captured by ErrorBoundary:', err, info)
  return false
})

const handleRetry = () => {
  hasError.value = false
  errorInfo.value = null
  if (props.onRetry) {
    props.onRetry()
  } else {
    emit('retry')
  }
}

const handleGoBack = () => {
  hasError.value = false
  errorInfo.value = null
  router.back()
}

// 暴露重置方法
defineExpose({
  reset: () => {
    hasError.value = false
    errorInfo.value = null
  }
})
</script>

<style lang="scss" scoped>
.error-boundary {
  min-height: 100%;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 32px;
  text-align: center;

  .error-icon {
    margin-bottom: 16px;
  }

  .error-title {
    font-size: 18px;
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
  }

  .error-message {
    font-size: 14px;
    color: #999;
    margin-bottom: 24px;
    max-width: 280px;
  }

  .van-button {
    margin: 8px;
  }
}
</style>
