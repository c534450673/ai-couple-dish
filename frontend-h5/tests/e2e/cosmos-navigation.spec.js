import { expect, test } from './fixtures/auth'

test.describe('Couple Cosmos 导航 @mock', () => {
  test('五栏导航进入对应路由并支持详情返回', async ({ page, auth }) => {
    await auth.authenticated()
    await page.goto('/home')
    const destinations = [
      ['菜单', /\/menu$/],
      ['投喂', /\/feed$/],
      ['回忆', /\/memories$/],
      ['我们', /\/settings$/],
      ['星球', /\/home$/]
    ]
    for (const [label, url] of destinations) {
      await page.locator('.app-tabbar .van-tabbar-item').filter({ hasText: label }).click()
      await expect(page).toHaveURL(url)
    }
    await page.goto('/menu')
    await page.locator('.menu-card').first().click()
    await expect(page).toHaveURL(/\/menu\/101$/)
    await page.goBack()
    await expect(page).toHaveURL(/\/menu$/)
  })

  test('未登录和未绑定访问情侣页面时保留 redirect', async ({ page, auth }) => {
    await auth.unauthenticated()
    await page.goto('/menu')
    await expect(page).toHaveURL(/\/login\?redirect=\/menu/)

    await auth.unbound()
    await page.goto('/menu')
    await expect(page).toHaveURL(/\/bind\?redirect=\/menu/)
  })

  test('非法回忆详情 id 回到笔记列表', async ({ page, auth }) => {
    await auth.authenticated()
    await page.goto('/memories/notes/not-a-number')
    await expect(page).toHaveURL(/\/memories\?type=note/)
  })

  test('未知路由显示明确 404 状态', async ({ page, auth }) => {
    await auth.authenticated()
    await page.goto('/route-that-does-not-exist')
    await expect(page.getByRole('heading', { name: '页面不存在' })).toBeVisible()
    await expect(page.getByRole('link', { name: '返回星球' })).toHaveAttribute('href', '/home')
  })
})
