import { expect, test } from './fixtures/auth'

const seedDraft = async (page, userId, resource, value, resourceId = 'new') => {
  await page.addInitScript(({ resourceName, draftValue, id }) => {
    localStorage.setItem(`couple-cosmos:draft:${id.userId}:${resourceName}:${id.resourceId}`, JSON.stringify(draftValue))
  }, { resourceName: resource, draftValue: value, id: { userId, resourceId } })
}

const useDraftUser = async (page, userId) => {
  await page.addInitScript((id) => {
    localStorage.setItem('userInfo', JSON.stringify({ id, nickName: `测试用户${id}`, nickname: `测试用户${id}`, avatarUrl: '' }))
  }, userId)
  await page.reload()
}

test.describe('Couple Cosmos 表单草稿与防重复 @mock', () => {
  test('菜单草稿按 user1/user2 隔离并可恢复，重复提交只发一次', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await seedDraft(page, 1, 'menu', { restaurantName: '用户一的草稿', note: '本地备注' })
    await seedDraft(page, 2, 'menu', { restaurantName: '用户二的草稿', note: '另一份本地备注' })
    await page.goto('/menu/add')
    await expect(page.getByTestId('restore-menu-draft')).toBeVisible()
    await page.getByTestId('restore-menu-draft').click()
    await expect(page.getByTestId('restaurant-name')).toHaveValue('用户一的草稿')

    await useDraftUser(page, 2)
    await expect(page.getByTestId('restore-menu-draft')).toBeVisible()
    await page.getByTestId('restore-menu-draft').click()
    await expect(page.getByTestId('restaurant-name')).toHaveValue('用户二的草稿')

    apiMock.setReply('POST', '/api/menu/add', { status: 200, delayMs: 120, body: { code: 200, message: 'mock', data: 102 }, businessCode: 200 })
    await page.getByTestId('menu-submit').dblclick()
    await expect(page).toHaveURL(/\/menu\/102$/)
    expect(apiMock.calls.filter(call => call.pathname === '/api/menu/add')).toHaveLength(1)
  })

  test('菜谱实际提交 Long 合同且笔记双击只写入一次', async ({ page, apiMock, auth }) => {
    await auth.authenticated()
    await seedDraft(page, 1, 'recipe', { title: '草稿菜谱', ingredients: [{ name: '番茄', amount: '1 个' }], steps: [{ content: '切好', imageUrl: null }] })
    await page.goto('/recipes/new')
    await expect(page.getByTestId('restore-draft')).toBeVisible()
    await page.getByTestId('restore-draft').click()
    await expect(page.getByTestId('recipe-title')).toHaveValue('草稿菜谱')
    apiMock.setReply('POST', '/api/recipe/create', { status: 200, delayMs: 120, body: { code: 200, message: 'mock', data: 202 }, businessCode: 200 })
    await page.getByTestId('recipe-publish').dblclick()
    await expect(page).toHaveURL(/\/recipes\/202$/)
    expect(apiMock.calls.filter(call => call.pathname === '/api/recipe/create')).toHaveLength(1)

    await seedDraft(page, 1, 'note', { title: '草稿回忆', content: '草稿内容', location: '草稿地点', photoUrls: [] })
    await page.goto('/memories/notes/new')
    await expect(page.getByTestId('restore-note-draft')).toBeVisible()
    await page.getByTestId('restore-note-draft').click()
    await expect(page.getByTestId('note-title')).toHaveValue('草稿回忆')
    await expect(page.getByTestId('note-content')).toHaveValue('草稿内容')

    apiMock.setReply('POST', '/api/note/add', { status: 200, delayMs: 120, body: { code: 200, message: 'mock', data: 802 }, businessCode: 200 })
    await page.getByTestId('note-submit').dblclick()
    await expect(page).toHaveURL(/\/memories\/notes\/802$/)
    expect(apiMock.calls.filter(call => call.pathname === '/api/note/add')).toHaveLength(1)
  })
})
