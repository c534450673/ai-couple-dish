import { defineConfig } from '@playwright/test'

const mobileProjects = [
  { name: '375x812', viewport: { width: 375, height: 812 } },
  { name: '390x844', viewport: { width: 390, height: 844 } },
  { name: '430x932', viewport: { width: 430, height: 932 } }
]

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: 'test-results',
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [['line'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:3000',
    testIdAttribute: 'data-test',
    locale: 'zh-CN',
    trace: 'off',
    video: 'off',
    screenshot: 'off'
  },
  projects: mobileProjects.map(({ name, viewport }) => ({
    name,
    use: { browserName: 'chromium', viewport }
  })),
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 3000 --strictPort',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      PLAYWRIGHT_TEST: 'true',
      VITE_API_BASE_URL: ''
    }
  }
})
