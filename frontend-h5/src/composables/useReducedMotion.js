import { getCurrentScope, onScopeDispose, ref } from 'vue'
import { logUiEvent } from './useStructuredLog'

export const useReducedMotion = () => {
  const prefersReducedMotion = ref(false)

  if (typeof window === 'undefined' || !window.matchMedia) {
    return prefersReducedMotion
  }

  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  const updatePreference = (event) => {
    prefersReducedMotion.value = event.matches
    logUiEvent('motion_preference_changed', {
      module: 'useReducedMotion',
      operation: 'observe',
      result: event.matches ? 'reduced' : 'standard',
      durationMs: 0
    })
  }

  prefersReducedMotion.value = mediaQuery.matches
  mediaQuery.addEventListener?.('change', updatePreference)

  if (getCurrentScope()) {
    onScopeDispose(() => mediaQuery.removeEventListener?.('change', updatePreference))
  }

  return prefersReducedMotion
}
