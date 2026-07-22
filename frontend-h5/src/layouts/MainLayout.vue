<script setup>
import AppShell from '@/components/cosmos/AppShell.vue'
</script>

<template>
  <AppShell>
    <template
      v-if="$slots.header"
      #header
    >
      <slot name="header" />
    </template>
    <slot />
  </AppShell>
</template>
