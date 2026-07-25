import { expect, test as base } from '@playwright/test'

const json = (data, { code = 200, message = 'mock' } = {}) => ({
  status: 200,
  contentType: 'application/json; charset=utf-8',
  body: { code, message, data }
})

const normalizePathname = (pathname) => pathname
  .replace(/\/[0-9]+(?=\/|$)/g, '/:id')
  .replace(/\/[a-f0-9]{8,}(?=\/|$)/gi, '/:id')

const menuItem = {
  id: 101,
  restaurantName: '测试餐厅',
  dishName: '测试菜品',
  dishCategory: '中餐',
  status: 0,
  rating: 4.5,
  price: 88,
  likeCount: 1,
  latitude: 31.2,
  longitude: 121.5,
  location: '测试地点'
}

const recipePage = { records: [{ id: 201, title: '测试菜谱', coverUrl: '', status: 1 }], current: 1, size: 10, total: 1, pages: 1 }

const streamReply = () => ({
  status: 200,
  contentType: 'text/event-stream; charset=utf-8',
  body: [
    'event: token\ndata: 已生成预览',
    'event: pending_action\ndata: {"actionType":"add_menu","title":"AI 写入预览","payload":{"restaurantName":"测试餐厅"}}',
    'event: session\ndata: mock-session',
    'event: done\ndata: done'
  ].join('\n\n') + '\n\n'
})

const defaultReply = ({ pathname }) => {
  if (pathname === '/api/user/info') return json({ id: 1, nickName: '测试用户', nickname: '测试用户', avatarUrl: '' })
  if (pathname === '/api/couple/info') return json({ id: 2, partner: { nickName: '测试伴侣', nickname: '测试伴侣', avatarUrl: '' } })
  if (pathname === '/api/couple/home') return json({})
  if (pathname === '/api/couple/loveTimer') return json({ loveDays: 365 })
  if (pathname === '/api/anniversary/next') return json({ name: '纪念日', daysUntil: 10 })
  if (pathname === '/api/anniversary/list' || pathname === '/api/wish/list') return json([])
  if (pathname === '/api/note/list') return json([])
  if (pathname === '/api/menu/list') {
    return json({ list: [menuItem], page: 1, pageSize: 10, total: 1, totalPages: 1, hasMore: false })
  }
  if (pathname === '/api/menu/stats') return json({ totalCount: 1, wantToGoCount: 1, visitedCount: 0, seededCount: 0 })
  if (pathname === '/api/menu/map' || pathname === '/api/menu/nearby') return json([menuItem])
  if (pathname.startsWith('/api/menu/detail/')) return json(menuItem)
  if (pathname.startsWith('/api/recipe/detail/')) return json({ id: 201, title: '测试菜谱', ingredients: [], steps: [] })
  if (pathname.startsWith('/api/recipe/')) return json(recipePage)
  if (pathname === '/api/feed/today') return json({ sent: false, received: false })
  if (pathname === '/api/feed/received' || pathname === '/api/feed/sent') return json([])
  if (pathname === '/api/notification/list') {
    return json([{ id: 301, type: 2, title: '测试提醒', content: '测试通知内容', isRead: 0, createTime: '2026-07-22T12:00:00+08:00' }])
  }
  if (pathname === '/api/notification/unreadCount') return json(1)
  if (pathname === '/api/ai/chat/stream') return streamReply()
  if (pathname === '/api/ai/chat/confirm' || pathname === '/api/ai/chat/reject') return json({ accepted: true, message: '操作已确认完成' })
  return null
}

export const test = base.extend({
  apiMock: async ({ page }, use) => {
    const calls = []
    const runtimeErrors = []
    const overrides = new Map()
    const keyFor = (method, pathname) => `${method.toUpperCase()} ${pathname}`

    const setReply = (method, pathname, reply) => {
      overrides.set(keyFor(method, pathname), Array.isArray(reply) ? [...reply] : [reply])
    }

    page.on('console', (message) => {
      if (message.type() === 'error') runtimeErrors.push({ source: 'console' })
    })
    page.on('pageerror', () => runtimeErrors.push({ source: 'pageerror' }))
    page.on('requestfailed', (request) => {
      if (new URL(request.url()).pathname.startsWith('/api/')) runtimeErrors.push({ source: 'api-requestfailed' })
    })

    await page.route(/^https?:\/\/127\.0\.0\.1:3000\/api\//, async (route) => {
      const request = route.request()
      const method = request.method().toUpperCase()
      const pathname = normalizePathname(new URL(request.url()).pathname)
      const queue = overrides.get(keyFor(method, pathname))
      const reply = queue?.length ? queue.shift() : defaultReply({ method, pathname })
      const status = reply?.status ?? 500
      const handled = Boolean(reply)
      const record = { method, pathname, status, handled }
      calls.push(record)
      // Deliberately log only the contract allowlist: method/path/status/handled.
      console.info('[e2e.api]', record)
      await route.fulfill({
        status,
        contentType: reply?.contentType || 'application/json; charset=utf-8',
        body: typeof reply?.body === 'string' ? reply.body : JSON.stringify(reply?.body || { code: 500, message: 'mock handler missing', data: null })
      })
    })

    await use({
      calls,
      setReply,
      businessError: (code, message = 'mock business failure') => json(null, { code, message }),
      httpError: (status, message = 'mock http failure') => ({ status, contentType: 'application/json; charset=utf-8', body: { code: status, message, data: null } })
    })

    expect(calls.filter(call => !call.handled), '所有 /api 请求必须由脱敏 mock 合同处理').toEqual([])
    expect(runtimeErrors, '浏览器 console/pageerror/API 请求失败必须为 0').toEqual([])
  }
})

export { expect }
