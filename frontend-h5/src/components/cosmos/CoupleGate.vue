<script setup>
import AsyncState from './AsyncState.vue'
import { logUiEvent } from '@/composables/useStructuredLog'

defineProps({
  bound: { type: Boolean, required: true }
})

const emit = defineEmits(['bind'])

const requestBind = () => {
  logUiEvent('couple_gate_action', {
    module: 'CoupleGate',
    operation: 'request_bind',
    result: 'emitted',
    durationMs: 0
  })
  emit('bind')
}
</script>

<template>
  <slot v-if="bound" />
  <AsyncState
    v-else
    status="unbound"
    @bind="requestBind"
  />
</template>
