import { expect, test } from './fixtures/auth'

test.describe('Couple Cosmos AI 确认流 @mock', () => {
  const openPreview = async (page, prompt) => {
    await page.goto('/ai')
    await page.getByPlaceholder('给我们的星球留言').fill(prompt)
    await page.getByRole('button', { name: '发送消息' }).click()
    await expect(page.getByTestId('ai-action-preview')).toBeVisible()
  }

  test('AI 写入预览确认双击只提交一次', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await openPreview(page, '创建测试餐厅')
    apiMock.setReply('POST', '/api/ai/chat/confirm', { status: 200, delayMs: 120, body: { code: 200, message: 'mock', data: { actionType: 'add_menu', resourceId: 102, message: '操作已确认完成' } }, businessCode: 200 })
    await page.getByTestId('ai-confirm').dblclick()
    await expect(page.getByTestId('ai-action-preview')).toHaveCount(0)
    expect(apiMock.calls.filter(call => call.pathname === '/api/ai/chat/confirm')).toHaveLength(1)
  })

  test('AI 写入预览可拒绝', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await openPreview(page, '拒绝测试预览')
    await page.getByTestId('ai-reject').click()
    await expect(page.getByTestId('ai-action-preview')).toHaveCount(0)
    expect(apiMock.calls.filter(call => call.pathname === '/api/ai/chat/reject')).toHaveLength(1)
  })

  test('无 session 的 pending 只能本地拒绝，确认不可用', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('POST', '/api/ai/chat/stream', apiMock.streamReply({ session: '' }))
    await openPreview(page, '无会话预览')
    await expect(page.getByTestId('ai-confirm')).toBeDisabled()
    await page.getByTestId('ai-reject').click()
    await expect(page.getByTestId('ai-action-preview')).toHaveCount(0)
    expect(apiMock.calls.filter(call => call.pathname === '/api/ai/chat/reject')).toHaveLength(0)
  })

  test('SSE 在 done 前中断会保留输入并进入中断态', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('POST', '/api/ai/chat/stream', apiMock.streamReply({ done: false, pending: false }))
    await page.goto('/ai')
    await page.getByPlaceholder('给我们的星球留言').fill('中断测试')
    await page.getByRole('button', { name: '发送消息' }).click()
    await expect(page.getByText('回复已中断，当前片段仅保存在本机，服务端不支持续传。')).toBeVisible()
    await expect(page.getByTestId('ai-retry')).toBeVisible()
  })

  test('确认按钮双击遇到未知结果不会自动重试', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('POST', '/api/ai/chat/confirm', apiMock.httpError(500))
    await openPreview(page, '未知结果测试')
    await page.getByTestId('ai-confirm').dblclick()
    await expect(page.getByText('确认结果未知，请先刷新相关菜单或菜谱核对，不要重复确认。')).toBeVisible()
    expect(apiMock.calls.filter(call => call.pathname === '/api/ai/chat/confirm')).toHaveLength(1)
  })

  test('流式请求未完成时阻止第二次发送', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    apiMock.setReply('POST', '/api/ai/chat/stream', { ...apiMock.streamReply({ done: false, token: '第一条流' }), delayMs: 250 })
    await page.goto('/ai')
    await page.getByPlaceholder('给我们的星球留言').fill('第一条')
    await page.getByRole('button', { name: '发送消息' }).click()
    await expect(page.getByRole('button', { name: '停止生成' })).toBeVisible()
    await page.getByPlaceholder('给我们的星球留言').fill('第二条不应发送')
    await expect(page.getByRole('button', { name: '发送消息' })).toHaveCount(0)
    await expect.poll(() => apiMock.calls.filter(call => call.pathname === '/api/ai/chat/stream')).toHaveLength(1)
  })

  for (const status of [429, 500]) {
    test(`流式请求 HTTP ${status} 后可保留输入并恢复`, async ({ page, apiMock, auth }) => {
      await auth.authenticated()
      apiMock.setReply('POST', '/api/ai/chat/stream', [apiMock.httpError(status), apiMock.streamReply()])
      await page.goto('/ai')
      await page.getByPlaceholder('给我们的星球留言').fill(`恢复 ${status}`)
      await page.getByRole('button', { name: '发送消息' }).click()
      await expect(page.getByText('AI 请求失败，输入和已有消息已保留。')).toBeVisible()
      await expect(page.getByPlaceholder('给我们的星球留言')).toHaveValue(`恢复 ${status}`)
      await page.getByTestId('ai-retry').click()
      await expect(page.getByTestId('ai-action-preview')).toBeVisible()
      expect(apiMock.calls.filter(call => call.pathname === '/api/ai/chat/stream')).toHaveLength(2)
    })
  }
})
