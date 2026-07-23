import { defineStore } from 'pinia'
import { logUiEvent } from '@/composables/useStructuredLog'

export const THEME_STORAGE_KEY = 'couple-cosmos:theme'
export const THEME_VALUES = ['cosmos', 'system-contrast']

const normalizeTheme = (value) => THEME_VALUES.includes(value) ? value : 'cosmos'

const applyTheme = (theme) => {
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = theme
  }
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: normalizeTheme(globalThis.localStorage?.getItem(THEME_STORAGE_KEY))
  }),

  actions: {
    initializeTheme() {
      const rawTheme = globalThis.localStorage?.getItem(THEME_STORAGE_KEY)
      const theme = normalizeTheme(rawTheme)
      this.theme = theme
      globalThis.localStorage?.setItem(THEME_STORAGE_KEY, theme)
      applyTheme(theme)
      logUiEvent('settings.theme.change', {
        module: 'settings',
        operation: 'theme_initialize',
        result: 'success',
        durationMs: 0,
        errorCode: 'NONE',
        theme,
        migrated: rawTheme !== null && rawTheme !== theme
      })
    },

    setTheme(value) {
      const startedAt = Date.now()
      const theme = normalizeTheme(value)
      this.theme = theme
      globalThis.localStorage?.setItem(THEME_STORAGE_KEY, theme)
      applyTheme(theme)
      logUiEvent('settings.theme.change', {
        module: 'settings',
        operation: 'theme_change',
        result: 'success',
        durationMs: Date.now() - startedAt,
        errorCode: 'NONE',
        theme
      })
    }
  }
})
