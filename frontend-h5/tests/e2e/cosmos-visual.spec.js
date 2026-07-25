import { readFile, stat } from 'node:fs/promises'
import { resolve } from 'node:path'
import { expect, test } from './fixtures/auth'

test.describe('@visual Couple Cosmos 三视口截图矩阵', () => {
  test('18 个目标页面 normal/reduced 截图、无溢出且主容器可见', async ({ page, auth }, testInfo) => {
    await auth.authenticated()
    const targets = [
      { name: 'home', path: '/home', selector: '.home-emotion', shell: true },
      { name: 'bind', path: '/bind', selector: '.bind-page', shell: false },
      { name: 'menu-list', path: '/menu', selector: '.menu-library', shell: true },
      { name: 'menu-detail', path: '/menu/101', selector: '.menu-detail', shell: false },
      { name: 'menu-add', path: '/menu/add', selector: '.menu-editor', shell: false },
      { name: 'recipe-list', path: '/recipes', selector: '.recipe-library', shell: true },
      { name: 'recipe-detail', path: '/recipes/201', selector: '.recipe-detail', shell: false },
      { name: 'recipe-edit', path: '/recipes/201/edit', selector: '.recipe-editor', shell: false },
      { name: 'feed', path: '/feed', selector: '.feed-page', shell: true },
      { name: 'memories', path: '/memories', selector: '.memories-page', shell: true },
      { name: 'map', path: '/map', selector: '.map-page', shell: true },
      { name: 'ai', path: '/ai', selector: '.ai-page', shell: true },
      { name: 'settings', path: '/settings', selector: '.settings-page', shell: true },
      { name: 'notifications', path: '/notifications', selector: '.notification-page', shell: true },
      { name: 'note-editor', path: '/memories/notes/new', selector: '.note-editor', shell: false },
      { name: 'note-detail', path: '/memories/notes/801', selector: '.note-detail', shell: false },
      { name: 'states', path: '/states', selector: '.states-page', shell: false },
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

    await auth.unauthenticated()
    await page.goto('/login')
    await page.locator('.login-page').waitFor({ state: 'visible', timeout: 10_000 })
    await expect(page.locator('.login-page')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('login-normal.png'), fullPage: true })

    await auth.authenticated()
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
    await auth.unauthenticated()
    await page.goto('/login')
    await page.locator('.login-page').waitFor({ state: 'visible', timeout: 10_000 })
    await expect(page.locator('.login-page')).toBeVisible()
    const loginReduced = await page.evaluate(() => {
      const values = [...document.querySelectorAll('[class]')].map(node => {
        const style = getComputedStyle(node)
        return Math.max(parseFloat(style.animationDuration) || 0, parseFloat(style.transitionDuration) || 0)
      })
      return { media: matchMedia('(prefers-reduced-motion: reduce)').matches, maxDuration: Math.max(0, ...values) }
    })
    expect(loginReduced.media).toBe(true)
    expect(loginReduced.maxDuration).toBeLessThanOrEqual(0.01)
    await page.screenshot({ path: testInfo.outputPath('login-reduced.png'), fullPage: true })
  })

  test('Stitch 20 屏 manifest 与本地设计资产完整可读', async () => {
    const root = resolve(process.cwd(), '../docs/design/stitch/couple-cosmos')
    const manifest = JSON.parse(await readFile(resolve(root, 'manifest.json'), 'utf8'))
    const expectedIds = [
      'home-base', 'home-emotion', 'home-food', 'home-memory', 'login', 'bind',
      'menu-list', 'menu-detail', 'recipe-list', 'recipe-detail', 'recipe-editor',
      'feed', 'memories', 'note-editor', 'map', 'ai-chat', 'settings',
      'notification-center', 'legal-privacy', 'system-states'
    ]
    expect(manifest.screens.map(screen => screen.localId)).toEqual(expectedIds)
    for (const screen of manifest.screens) {
      const screenshot = await stat(resolve(root, screen.screenshot))
      const html = await stat(resolve(root, screen.html))
      expect(screenshot.size).toBeGreaterThan(1024)
      expect(html.size).toBeGreaterThan(512)
    }
    const loginHtml = await readFile(resolve(root, 'html/login.html'), 'utf8')
    expect(loginHtml).toContain('screenshot-fallback')
  })
})
