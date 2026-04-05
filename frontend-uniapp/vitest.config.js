import { defineConfig } from 'vitest/config'
import uni from '@dcloudio/vite-plugin-uni'
import { resolve } from 'path'

export default defineConfig({
  plugins: [uni()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'dist/**',
        '**/*.spec.js',
        '**/*.test.js',
        'src/tests/**'
      ]
    },
    include: ['src/**/*.{test,spec}.{js,ts}'],
    exclude: ['node_modules/**', 'dist/**']
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
})