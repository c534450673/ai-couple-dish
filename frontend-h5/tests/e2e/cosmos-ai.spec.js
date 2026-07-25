import { expect, test } from './fixtures/auth'

test.describe('Couple Cosmos AI 确认流 @mock', () => {
  const openPreview = async (page, prompt) => {
    await page.goto('/ai')
    await page.getByPlaceholder('给我们的星球留言').fill(prompt)
    await page.getByRole('button', { name: '发送消息' }).click()
    await expect(page.getByTestId('ai-action-preview')).toBeVisible()
  }

  test('AI 写入预览可确认且不会自动重试', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await openPreview(page, '创建测试餐厅')
    await page.getByTestId('ai-confirm').click()
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
})
