import { describe, expect, it, vi } from 'vitest'
import { useAsyncResource } from '@/composables/useAsyncResource'
import { logUiEvent, redactSensitiveFields } from '@/composables/useStructuredLog'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useAsyncResource', () => {
  it('只使用约定状态并区分 success 与 empty', async () => {
    const loader = vi.fn()
      .mockResolvedValueOnce({ id: 1 })
      .mockResolvedValueOnce([])
    const resource = useAsyncResource(loader)

    expect(resource.status.value).toBe('idle')
    await resource.execute()
    expect(resource.status.value).toBe('success')
    expect(resource.data.value).toEqual({ id: 1 })

    await resource.execute()
    expect(resource.status.value).toBe('empty')
    expect(resource.data.value).toEqual([])
  })

  it('将鉴权与未绑定错误映射到统一状态', async () => {
    const loader = vi.fn()
      .mockRejectedValueOnce({ response: { status: 401 }, token: 'never-log-me' })
      .mockRejectedValueOnce({ code: 2006, message: '未绑定情侣关系' })
    const resource = useAsyncResource(loader)

    await resource.execute()
    expect(resource.status.value).toBe('unauthorized')

    await resource.retry()
    expect(resource.status.value).toBe('unbound')
  })

  it('并发执行时旧请求完成不能覆盖新结果', async () => {
    const first = deferred()
    const second = deferred()
    const loader = vi.fn()
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const resource = useAsyncResource(loader)

    const oldRequest = resource.execute('old')
    const latestRequest = resource.execute('latest')
    second.resolve({ id: 'latest' })
    await latestRequest
    first.resolve({ id: 'old' })
    await oldRequest

    expect(resource.status.value).toBe('success')
    expect(resource.data.value).toEqual({ id: 'latest' })
  })

  it('reset 会使进行中的请求失效并恢复 idle', async () => {
    const pending = deferred()
    const resource = useAsyncResource(() => pending.promise)
    const request = resource.execute()

    resource.reset()
    pending.resolve({ id: 1 })
    await request

    expect(resource.status.value).toBe('idle')
    expect(resource.data.value).toBeNull()
    expect(resource.error.value).toBeNull()
  })
})

describe('useStructuredLog', () => {
  it('递归脱敏对象与数组中的敏感字段且保留结构化字段', () => {
    const fields = {
      module: 'router',
      operation: 'guard',
      result: 'redirected',
      durationMs: 3,
      token: 'top-secret',
      nested: {
        authorization: 'Bearer secret',
        rows: [{ phone: '13800138000', errorCode: 2006 }]
      }
    }

    expect(redactSensitiveFields(fields)).toEqual({
      module: 'router',
      operation: 'guard',
      result: 'redirected',
      durationMs: 3,
      token: '[REDACTED]',
      nested: {
        authorization: '[REDACTED]',
        rows: [{ phone: '[REDACTED]', errorCode: 2006 }]
      }
    })
  })

  it('logUiEvent 不向控制台泄露深层敏感值', () => {
    const info = vi.spyOn(console, 'info').mockImplementation(() => {})

    logUiEvent('route_guard_redirected', {
      module: 'router',
      operation: 'authorize',
      result: 'login_required',
      payload: { password: 'secret', cookie: 'session=secret' }
    })

    expect(info).toHaveBeenCalledWith({
      event: 'route_guard_redirected',
      module: 'router',
      operation: 'authorize',
      result: 'login_required',
      payload: { password: '[REDACTED]', cookie: '[REDACTED]' }
    })
    info.mockRestore()
  })
})
