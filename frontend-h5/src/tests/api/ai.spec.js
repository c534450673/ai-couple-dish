import { beforeEach, describe, expect, it, vi } from 'vitest'
import { confirmAction, generateForm, rejectAction, streamChat } from '@/api/ai'

const encoder = new TextEncoder()

const streamResponse = (chunks, overrides = {}) => {
  let index = 0
  return {
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: vi.fn(async () => index < chunks.length
          ? { done: false, value: encoder.encode(chunks[index++]) }
          : { done: true, value: undefined })
      })
    },
    ...overrides
  }
}

const jsonResponse = (body, { ok = true, status = 200 } = {}) => ({
  ok,
  status,
  json: vi.fn().mockResolvedValue(body),
  text: vi.fn().mockResolvedValue(JSON.stringify(body))
})

describe('AI API 真实合同', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    localStorage.setItem('token', 'secret-jwt')
  })

  it('跨网络分块解析 token、pending、session、done 和尾 buffer', async () => {
    const handlers = {
      onToken: vi.fn(),
      onPending: vi.fn(),
      onSession: vi.fn(),
      onDone: vi.fn()
    }
    const pending = { actionId: 'a1', actionType: 'add_menu', payload: { restaurantName: '星港' } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse([
      'event: token\ndata: 你',
      '好\n\nevent: pending_action\ndata: {"actionId":"a1","actionType":"add_menu",',
      '"payload":{"restaurantName":"星港"}}\n\nevent: session\ndata: u7-private\n\n',
      'event: done\ndata: ok'
    ])))

    await streamChat({ message: '敏感输入' }, handlers)

    expect(handlers.onToken).toHaveBeenCalledWith('你好')
    expect(handlers.onPending).toHaveBeenCalledWith(pending)
    expect(handlers.onSession).toHaveBeenCalledWith('u7-private')
    expect(handlers.onDone).toHaveBeenCalledOnce()
  })

  it.each([401, 429, 500])('HTTP %s 直接失败且不伪装为 SSE 成功', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(
      { code: status, message: '服务失败' },
      { ok: false, status }
    )))

    await expect(streamChat({ message: 'hello' })).rejects.toMatchObject({
      status,
      code: `AI_HTTP_${status}`
    })
  })

  it('SSE error 事件终止当前流并返回脱敏错误码', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse([
      'event: token\ndata: partial\n\n',
      'event: error\ndata: upstream detail\n\n'
    ])))

    await expect(streamChat({ message: 'hello' })).rejects.toMatchObject({ code: 'AI_SSE_ERROR' })
  })

  it('把 AbortController signal 传给单次流请求', async () => {
    const controller = new AbortController()
    const fetchMock = vi.fn().mockResolvedValue(streamResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    await streamChat({ message: 'hello' }, {}, { signal: controller.signal })

    expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal)
  })

  it('confirm/reject/generate 统一拒绝非 2xx 与业务 code 错误', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(jsonResponse({ code: 500, message: '未知结果' }, { ok: false, status: 500 }))
      .mockResolvedValueOnce(jsonResponse({ code: 4001, message: 'pending 已失效' }))
      .mockResolvedValueOnce(jsonResponse({ code: 429, message: '限流' }, { ok: false, status: 429 })))

    await expect(confirmAction('sid')).rejects.toMatchObject({ code: 'AI_HTTP_500', unknownResult: true })
    await expect(rejectAction('sid')).rejects.toMatchObject({ code: 'AI_BUSINESS_4001' })
    await expect(generateForm('menu', 'prompt')).rejects.toMatchObject({ code: 'AI_HTTP_429' })
  })
})
