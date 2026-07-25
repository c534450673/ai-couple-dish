import { expect, test } from './fixtures/auth'

test.describe('@visual Couple Cosmos 三视口截图矩阵', () => {
  test('14 个目标页面 normal/reduced 截图、无溢出且主容器可见', async ({ page, auth }, testInfo) => {
    await auth.authenticated()
    const targets = [
      { name: 'home', path: '/home', selector: '.home-emotion', shell: true },
      { name: 'bind', path: '/bind', selector: '.bind-page', shell: false },
      { name: 'menu-list', path: '/menu', selector: '.menu-library', shell: true },
      { name: 'menu-detail', path: '/menu/101', selector: '.menu-detail', shell: false },
      { name: 'recipe-list', path: '/recipes', selector: '.recipe-library', shell: true },
      { name: 'recipe-detail', path: '/recipes/201', selector: '.recipe-detail', shell: false },
      { name: 'recipe-edit', path: '/recipes/201/edit', selector: '.recipe-editor', shell: false },
      { name: 'feed', path: '/feed', selector: '.feed-page', shell: true },
      { name: 'memories', path: '/memories', selector: '.memories-page', shell: true },
      { name: 'map', path: '/map', selector: '.map-page', shell: true },
      { name: 'ai', path: '/ai', selector: '.ai-page', shell: true },
      { name: 'settings', path: '/settings', selector: '.settings-page', shell: true },
      { name: 'notifications', path: '/notifications', selector: '.notification-page', shell: true },
      { name: 'legal', path: '/legal', selector: '.legal-page', shell: false }
    ]
    for (const target of targets) {
      await page.goto(target.path)
      await page.locator(target.selector).waitFor({ state: 'visible', timeout: 10_000 })
      await expect(page.locator(target.selector)).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true)
      if (target.shell) await expect(page.locator('.app-tabbar')).toBeVisible()
      if (target.name === 'menu-detail' || target.name === 'recipe-detail' || target.name === 'recipe-edit') {
        await expect(page.locator('.ai-fab')).toHaveCount(0)
      }
      await page.screenshot({ path: testInfo.outputPath(`${target.name}-normal.png`), fullPage: true })
    }

    await page.emulateMedia({ reducedMotion: 'reduce' })
    for (const target of targets) {
      await page.goto(target.path)
      await page.locator(target.selector).waitFor({ state: 'visible', timeout: 10_000 })
      await expect(page.locator(target.selector)).toBeVisible()
      const reduced = await page.evaluate(() => {
        const values = [...document.querySelectorAll('[class]')].map(node => {
          const style = getComputedStyle(node)
          return Math.max(parseFloat(style.animationDuration) || 0, parseFloat(style.transitionDuration) || 0)
        })
        return { media: matchMedia('(prefers-reduced-motion: reduce)').matches, maxDuration: Math.max(0, ...values) }
      })
      expect(reduced.media).toBe(true)
      expect(reduced.maxDuration).toBeLessThanOrEqual(0.01)
      if (target.name === 'menu-detail' || target.name === 'recipe-detail' || target.name === 'recipe-edit') {
        await expect(page.locator('.ai-fab')).toHaveCount(0)
      }
      await page.screenshot({ path: testInfo.outputPath(`${target.name}-reduced.png`), fullPage: true })
    }
  })
})
