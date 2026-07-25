import { expect, test as base } from '@playwright/test'

const json = (data, { code = 200, message = 'mock', status = 200, delayMs = 0 } = {}) => ({
  status,
  contentType: 'application/json; charset=utf-8',
  body: { code, message, data },
  businessCode: code,
  delayMs
})

const httpError = (status, message = 'mock http failure', delayMs = 0) => json(null, { status, code: status, message, delayMs })

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

const recipeItem = {
  id: 201,
  userId: 1,
  title: '测试菜谱',
  description: '测试菜谱简介',
  coverUrl: '',
  status: 0,
  ingredients: [{ name: '番茄', amount: '1 个' }],
  steps: [{ content: '切好食材', imageUrl: null }]
}

const feedItems = [
  { id: 401, status: 0, feedType: 'meal', feedTypeName: '正餐', content: '今晚吃火锅', message: '下班见', senderName: 'TA', createTime: '2026-07-25T10:00:00+08:00', expireTime: '2099-07-25T10:00:00+08:00' }
]

const streamReply = ({ token = '已生成预览', pending = true, session = 'mock-session', done = true } = {}) => ({
  status: 200,
  contentType: 'text/event-stream; charset=utf-8',
  body: [
    token ? `event: token\ndata: ${token}` : '',
    pending ? 'event: pending_action\ndata: {"actionType":"add_menu","title":"AI 写入预览","payload":{"restaurantName":"测试餐厅"}}' : '',
    session ? `event: session\ndata: ${session}` : '',
    done ? 'event: done\ndata: done' : ''
  ].filter(Boolean).join('\n\n') + '\n\n'
})

const is = (method, expectedMethod, pathname, expectedPath) => method === expectedMethod && pathname === expectedPath

const sanitizeBusinessCode = (code) => {
  const value = String(code)
  return /^[A-Za-z0-9_-]{1,32}$/.test(value) ? `BUSINESS_${value}` : 'BUSINESS_REDACTED'
}

const defaultReply = ({ method, pathname }) => {
  if (is(method, 'GET', pathname, '/api/user/info')) return json({ id: 1, nickName: '测试用户', nickname: '测试用户', avatarUrl: '' })
  if (is(method, 'GET', pathname, '/api/couple/info')) return json({ id: 2, partner: { nickName: '测试伴侣', nickname: '测试伴侣', avatarUrl: '' } })
  if (is(method, 'GET', pathname, '/api/couple/home')) return json({})
  if (is(method, 'GET', pathname, '/api/couple/loveTimer')) return json({ loveDays: 365 })
  if (is(method, 'GET', pathname, '/api/mood/today')) return json([
    { id: 901, moodType: 'happy', moodTypeName: '开心', moodIcon: '😊', sender: { id: 1 } },
    { id: 902, moodType: 'love', moodTypeName: '爱你', moodIcon: '❤️', sender: { id: 2 } }
  ])
  if (is(method, 'POST', pathname, '/api/mood/send')) return json(903)
  if (is(method, 'GET', pathname, '/api/couple/codeInfo')) return json({ coupleCode: 'AB12CD34', expiresAt: '2099-01-01T00:00:00Z' })
  if (is(method, 'POST', pathname, '/api/couple/generateCode')) return json('AB12CD34')
  if (is(method, 'POST', pathname, '/api/couple/bind')) return json({ id: 2 })
  if (is(method, 'GET', pathname, '/api/couple/validateCode')) return json(true)
  if (is(method, 'GET', pathname, '/api/anniversary/next')) return json({ name: '纪念日', daysUntil: 10 })
  if (is(method, 'GET', pathname, '/api/anniversary/list')) return json([{ id: 601, anniversaryDate: '2026-08-01', name: '纪念日' }])
  if (is(method, 'GET', pathname, '/api/wish/list')) return json([{ id: 701, title: '一起吃火锅', statusName: '想去', createTime: '2026-07-20T10:00:00+08:00' }])
  if (is(method, 'GET', pathname, '/api/note/list')) return json([{ id: 801, title: '第一次约会', content: '测试回忆', location: '测试地点', createTime: '2026-07-19T10:00:00+08:00', photoUrls: [] }])
  if (is(method, 'GET', pathname, '/api/note/detail/:id')) return json({ id: 801, title: '第一次约会', content: '测试回忆', location: '测试地点', photoUrls: [] })
  if (is(method, 'POST', pathname, '/api/note/add')) return json(802)
  if (is(method, 'PUT', pathname, '/api/note/update/:id')) return json(null)
  if (is(method, 'DELETE', pathname, '/api/note/delete/:id')) return json(null)
  if (is(method, 'GET', pathname, '/api/menu/list')) return json({ list: [menuItem], page: 1, pageSize: 10, total: 1, totalPages: 1, hasMore: false })
  if (is(method, 'GET', pathname, '/api/menu/stats')) return json({ totalCount: 1, wantToGoCount: 1, visitedCount: 0, seededCount: 0 })
  if (is(method, 'GET', pathname, '/api/menu/map') || is(method, 'GET', pathname, '/api/menu/nearby')) return json([menuItem])
  if (is(method, 'GET', pathname, '/api/menu/detail/:id')) return json(menuItem)
  if (is(method, 'POST', pathname, '/api/menu/add')) return json(102)
  if (is(method, 'PUT', pathname, '/api/menu/update/:id')) return json(null)
  if (is(method, 'DELETE', pathname, '/api/menu/delete/:id')) return json(null)
  if (is(method, 'POST', pathname, '/api/menu/like/:id') || is(method, 'DELETE', pathname, '/api/menu/unlike/:id')) return json(null)
  if (is(method, 'POST', pathname, '/api/menu/favorite/:id') || is(method, 'DELETE', pathname, '/api/menu/unfavorite/:id')) return json(null)
  if (is(method, 'GET', pathname, '/api/recipe/my') || is(method, 'GET', pathname, '/api/recipe/couple') || is(method, 'GET', pathname, '/api/recipe/recommended') || is(method, 'GET', pathname, '/api/recipe/search') || is(method, 'GET', pathname, '/api/recipe/collected')) return json({ records: [recipeItem], current: 1, size: 10, total: 1, pages: 1 })
  if (is(method, 'GET', pathname, '/api/recipe/detail/:id')) return json(recipeItem)
  if (is(method, 'POST', pathname, '/api/recipe/create')) return json(202)
  if (is(method, 'PUT', pathname, '/api/recipe/update/:id')) return json(null)
  if (is(method, 'DELETE', pathname, '/api/recipe/delete/:id')) return json(null)
  if (is(method, 'POST', pathname, '/api/recipe/publish/:id')) return json(null)
  if (is(method, 'POST', pathname, '/api/recipe/like/:id') || is(method, 'DELETE', pathname, '/api/recipe/like/:id') || is(method, 'POST', pathname, '/api/recipe/collect/:id') || is(method, 'DELETE', pathname, '/api/recipe/collect/:id')) return json(null)
  if (is(method, 'GET', pathname, '/api/feed/today')) return json({ remainingCount: 1, sent: false, received: false })
  if (is(method, 'GET', pathname, '/api/feed/received')) return json(feedItems)
  if (is(method, 'GET', pathname, '/api/feed/sent')) return json([])
  if (is(method, 'POST', pathname, '/api/feed/send')) return json(402)
  if (is(method, 'POST', pathname, '/api/feed/accept/:id') || is(method, 'POST', pathname, '/api/feed/reject/:id')) return json(null)
  if (is(method, 'GET', pathname, '/api/notification/list')) return json([{ id: 301, type: 2, title: '测试提醒', content: '测试通知内容', isRead: 0, createTime: '2026-07-22T12:00:00+08:00' }])
  if (is(method, 'GET', pathname, '/api/notification/unreadCount')) return json(1)
  if (is(method, 'PUT', pathname, '/api/notification/read/:id') || is(method, 'PUT', pathname, '/api/notification/readAll')) return json(null)
  if (is(method, 'POST', pathname, '/api/upload/image')) return json({ url: '/local/mock-image.webp' })
  if (is(method, 'POST', pathname, '/api/ai/chat/stream')) return streamReply()
  if (is(method, 'POST', pathname, '/api/ai/chat/confirm')) return json({ actionType: 'add_menu', resourceId: 102, message: '操作已确认完成' })
  if (is(method, 'POST', pathname, '/api/ai/chat/reject')) return json(null)
  return null
}

export const test = base.extend({
  apiMock: async ({ page }, use) => {
    const calls = []
    const runtimeErrors = []
    const overrides = new Map()
    const expectedHttpErrors = new Map()
    const expectedRequestFailures = new Map()
    const keyFor = (method, pathname) => `${method.toUpperCase()} ${pathname}`
    const errorKey = (method, pathname, status) => `${keyFor(method, pathname)} ${status}`
    const requestFailureKey = (method, pathname, errorText) => `${keyFor(method, pathname)} ${errorText}`

    const setReply = (method, pathname, reply) => {
      const queue = Array.isArray(reply) ? [...reply] : [reply]
      overrides.set(keyFor(method, pathname), queue)
      queue.filter(item => item?.status >= 400).forEach(item => {
        const key = errorKey(method, pathname, item.status)
        expectedHttpErrors.set(key, (expectedHttpErrors.get(key) || 0) + 1)
      })
    }

    const expectRequestFailure = (method, pathname, errorText = 'net::ERR_ABORTED') => {
      const key = requestFailureKey(method, pathname, errorText)
      expectedRequestFailures.set(key, (expectedRequestFailures.get(key) || 0) + 1)
    }

    page.on('console', (message) => {
      if (message.type() === 'error') {
        // Chromium mirrors expected HTTP failures as console errors; response
        // validation below already records whether those statuses are allowed.
        if (/^Failed to load resource: the server responded with a status of \d+/.test(message.text())) return
        runtimeErrors.push({ source: 'console', errorCode: 'CONSOLE_ERROR', durationMs: 0 })
      }
    })
    page.on('pageerror', () => runtimeErrors.push({ source: 'pageerror', errorCode: 'PAGE_ERROR', durationMs: 0 }))
    page.on('requestfailed', (request) => {
      const pathname = normalizePathname(new URL(request.url()).pathname)
      const errorText = request.failure()?.errorText || 'REQUEST_FAILURE_UNKNOWN'
      const key = requestFailureKey(request.method(), pathname, errorText)
      const remaining = expectedRequestFailures.get(key) || 0
      if (remaining > 0) {
        expectedRequestFailures.set(key, remaining - 1)
        return
      }
      runtimeErrors.push({
        source: 'requestfailed',
        errorCode: errorText === 'net::ERR_ABORTED' ? 'REQUEST_ABORTED' : 'REQUEST_FAILED',
        pathname,
        errorText,
        durationMs: 0
      })
    })
    page.on('response', (response) => {
      if (response.status() < 400) return
      const request = response.request()
      const pathname = normalizePathname(new URL(response.url()).pathname)
      const key = errorKey(request.method(), pathname, response.status())
      const remaining = expectedHttpErrors.get(key) || 0
      if (remaining > 0) expectedHttpErrors.set(key, remaining - 1)
      else runtimeErrors.push({ source: 'response', errorCode: `HTTP_${response.status()}`, durationMs: 0 })
    })

    await page.route(/^https?:\/\/127\.0\.0\.1:3000\/api\//, async (route) => {
      const startedAt = Date.now()
      const request = route.request()
      const method = request.method().toUpperCase()
      const pathname = normalizePathname(new URL(request.url()).pathname)
      const queue = overrides.get(keyFor(method, pathname))
      const reply = queue?.length ? queue.shift() : defaultReply({ method, pathname })
      const status = reply?.status ?? 501
      const handled = Boolean(reply)
      if (reply?.delayMs) await new Promise(resolve => setTimeout(resolve, reply.delayMs))
      const errorCode = !handled
        ? 'UNHANDLED_API'
        : status >= 400
          ? `HTTP_${status}`
          : reply.businessCode !== undefined && reply.businessCode !== 200
            ? sanitizeBusinessCode(reply.businessCode)
            : 'NONE'
      const record = { method, pathname, status, handled, durationMs: Date.now() - startedAt, errorCode }
      calls.push(record)
      console.info('[e2e.api]', record)
      await route.fulfill({
        status,
        contentType: reply?.contentType || 'application/json; charset=utf-8',
        body: typeof reply?.body === 'string' ? reply.body : JSON.stringify(reply?.body ?? { code: 501, message: 'mock handler missing', data: null })
      })
    })

    await use({
      calls,
      setReply,
      expectRequestFailure,
      streamReply,
      businessError: (code, message = 'mock business failure') => json(null, { code, message }),
      httpError,
      expectedContract: (method, pathname) => Boolean(defaultReply({ method, pathname }))
    })

    expect(calls.filter(call => !call.handled), '所有 /api 请求必须由精确 mock 合同处理').toEqual([])
    expect([...expectedHttpErrors.entries()].filter(([, remaining]) => remaining > 0), '显式允许的 HTTP 错误必须全部发生').toEqual([])
    expect([...expectedRequestFailures.entries()].filter(([, remaining]) => remaining > 0), '显式允许的请求失败必须全部发生').toEqual([])
    expect(runtimeErrors, '浏览器 console/pageerror/requestfailed/非白名单 HTTP 错误必须为 0').toEqual([])
  }
})

export { expect }
