import { test } from './fixtures/auth'

test.describe('@visual Couple Cosmos 三视口截图矩阵', () => {
  test('关键页面 normal 与 reduced-motion 截图', async ({ page, _apiMock, auth }, testInfo) => {
    await auth.authenticated()
    const routes = ['/home', '/menu', '/recipes', '/feed', '/memories', '/map', '/ai', '/settings', '/notifications', '/legal']
    const pageSelectors = {
      '/home': '.home-emotion',
      '/menu': '.menu-library',
      '/recipes': '.recipe-library',
      '/feed': '.feed-page',
      '/memories': '.memories-page',
      '/map': '.map-page',
      '/ai': '.ai-page',
      '/settings': '.settings-page',
      '/notifications': '.notification-page',
      '/legal': '.legal-page'
    }
    for (const route of routes) {
      await page.goto(route)
      await page.locator(pageSelectors[route]).waitFor({ state: 'visible', timeout: 10_000 })
      await page.screenshot({ path: testInfo.outputPath(`${route.slice(1)}-normal.png`), fullPage: true })
    }

    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/home')
    await page.locator('.home-emotion').waitFor({ state: 'visible', timeout: 10_000 })
    await page.screenshot({ path: testInfo.outputPath('home-reduced-motion.png'), fullPage: true })
  })
})
