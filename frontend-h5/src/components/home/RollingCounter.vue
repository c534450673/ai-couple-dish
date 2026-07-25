<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
  reducedMotion: { type: Boolean, default: false }
})

const renderedValue = ref(0)
let animationTimer = null

const stopAnimation = () => {
  if (animationTimer) window.clearInterval(animationTimer)
  animationTimer = null
}

const renderValue = () => {
  stopAnimation()
  const target = Number.isFinite(props.value) ? Math.max(0, props.value) : 0
  if (props.reducedMotion || target === 0 || typeof window === 'undefined') {
    renderedValue.value = target
    return
  }

  const steps = 12
  let step = 0
  renderedValue.value = 0
  animationTimer = window.setInterval(() => {
    step += 1
    renderedValue.value = step === steps ? target : Math.round(target * (step / steps))
    if (step === steps) stopAnimation()
  }, 24)
}

const formattedValue = computed(() => new Intl.NumberFormat('zh-CN').format(renderedValue.value))

watch(() => [props.value, props.reducedMotion], renderValue, { immediate: true })
onUnmounted(stopAnimation)
</script>

<template>
  <span :data-motion="reducedMotion ? 'static' : 'animated'">{{ formattedValue }}</span>
</template>
