import { expect, test } from './fixtures/auth'

test.describe('Couple Cosmos 状态与降级 @mock', () => {
  test('开发态状态总览保留全部状态文案和 reduced motion', async ({ page, auth }) => {
    await auth.authenticated()
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/states')
    await expect(page.getByRole('heading', { name: '系统状态总览' })).toBeVisible()
    for (const text of ['正在加载', '暂无内容', '加载失败', '登录状态已失效', '还没有绑定伴侣']) {
      await expect(page.getByText(text, { exact: true })).toBeVisible()
    }
    await expect(page.getByText('当前后端未提供对应能力，操作没有被伪造为成功。')).toBeVisible()
    await expect(page.locator('.async-state__spinner').first()).toHaveCSS('animation-duration', '1e-05s')
  })

  test('菜单业务错误可显式重试一次并恢复为空态', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('GET', '/api/menu/list', [
      apiMock.businessError(500),
      { status: 200, body: { code: 200, message: 'mock', data: { list: [], page: 1, pageSize: 10, total: 0, totalPages: 0, hasMore: false } } }
    ])
    await page.goto('/menu')
    await expect(page.getByTestId('menu-retry')).toBeVisible()
    await page.getByTestId('menu-retry').click()
    await expect(page.getByRole('heading', { name: '还没有餐厅记录' })).toBeVisible()
    await expect(page.getByTestId('menu-retry')).toHaveCount(0)
  })

  test('地图 SDK 不可用时保留地点列表降级', async ({ page, auth }) => {
    await auth.authenticated()
    await auth.denyGeolocation()
    await page.goto('/map')
    await expect(page.getByText('地图密钥未配置，已切换地点列表')).toBeVisible()
    await expect(page.getByTestId('map-mode-list')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('map-item-101')).toBeVisible()
  })

  test('通知单条已读失败回滚乐观状态', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('PUT', '/api/notification/read/:id', apiMock.businessError(500))
    await page.goto('/notifications')
    const notification = page.locator('.notification-card')
    await expect(notification).toHaveClass(/unread/)
    await notification.click()
    await expect(notification).toHaveClass(/unread/)
    await expect(page.locator('.summary-row strong')).toHaveText('1')
  })

  test('通知筛选 AI 显示不可用合同且不发列表请求', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await page.goto('/notifications')
    await expect(page.locator('.notification-card')).toBeVisible()
    const before = apiMock.calls.filter(call => call.pathname === '/api/notification/list').length
    await page.getByTestId('filter-ai').click()
    await expect(page.getByText('暂不支持 AI 通知筛选')).toBeVisible()
    expect(apiMock.calls.filter(call => call.pathname === '/api/notification/list').length).toBe(before)
  })

  test('通知 HTTP 401/429/500 均有明确恢复行为', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('GET', '/api/notification/list', apiMock.httpError(401))
    await page.goto('/notifications')
    await expect(page).toHaveURL(/\/login$/)

    await auth.authenticated()
    apiMock.setReply('PUT', '/api/notification/read/:id', apiMock.httpError(429))
    await page.goto('/notifications')
    const notification = page.locator('.notification-card')
    await expect(notification).toBeVisible()
    await notification.click()
    await expect.poll(() => apiMock.calls.filter(call => call.pathname === '/api/notification/read/:id')).toHaveLength(1)
    await expect(notification).toHaveClass(/unread/)

    apiMock.setReply('PUT', '/api/notification/readAll', apiMock.httpError(500))
    await expect(page.getByTestId('read-all')).toBeEnabled()
    const readAllResponse = page.waitForResponse((response) => {
      const request = response.request()
      return request.method() === 'PUT' && new URL(response.url()).pathname === '/api/notification/readAll'
    })
    await page.getByTestId('read-all').click()
    await readAllResponse
    await expect.poll(() => apiMock.calls.filter(call => call.pathname === '/api/notification/readAll')).toHaveLength(1)
    await expect(notification).toHaveClass(/unread/)
  })

  test('严格合同拒绝未知路径和错误 method', async ({ apiMock }) => {
    expect(apiMock.expectedContract('GET', '/api/menu/list')).toBe(true)
    expect(apiMock.expectedContract('GET', '/api/menu/detail/:id')).toBe(true)
    expect(apiMock.expectedContract('POST', '/api/menu/list')).toBe(false)
    expect(apiMock.expectedContract('GET', '/api/menu/unknown')).toBe(false)
  })

  test('投喂发送和接受主流程只提交一次', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('POST', '/api/feed/send', { status: 200, delayMs: 150, body: { code: 200, message: 'mock', data: 402 } })
    await page.goto('/feed')
    await page.getByLabel('想投喂什么').fill('今晚吃火锅')
    await page.getByTestId('feed-send').click()
    await page.locator('[data-test="feed-send"]').dispatchEvent('click')
    await expect(page.getByTestId('feed-success')).toBeVisible()
    expect(apiMock.calls.filter(call => call.pathname === '/api/feed/send')).toHaveLength(1)
    await page.locator('.feed-card').first().getByRole('button', { name: '接受' }).click()
    expect(apiMock.calls.filter(call => call.pathname === '/api/feed/accept/:id')).toHaveLength(1)
  })

  test('回忆来源可筛选并打开笔记详情', async ({ page, auth }) => {
    await auth.authenticated()
    await page.goto('/memories')
    await page.getByTestId('filter-note').click()
    await expect(page.locator('.timeline-card').first()).toBeVisible()
    await page.locator('.timeline-card').first().click()
    await expect(page).toHaveURL(/\/memories\/notes\/801$/)
  })
})
