/**
 * AI 助手 API。聊天流必须保持单次 fetch，不接入 request.js 的自动重试。
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export class AiApiError extends Error {
  constructor(message, { code, status = null, unknownResult = false } = {}) {
    super(message)
    this.name = 'AiApiError'
    this.code = code || 'AI_REQUEST_FAILED'
    this.status = status
    this.unknownResult = unknownResult
  }
}

function authHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }
}

async function readErrorMessage(response) {
  try {
    const text = await response.text()
    if (!text) return ''
    try {
      return JSON.parse(text)?.message || ''
    } catch {
      return ''
    }
  } catch {
    return ''
  }
}

const throwHttpError = async (response, unknownResult = false) => {
  const message = await readErrorMessage(response)
  throw new AiApiError(message || `AI 请求失败（HTTP ${response.status}）`, {
    code: `AI_HTTP_${response.status}`,
    status: response.status,
    unknownResult
  })
}

const parseSseEvent = (raw) => {
  let event = 'message'
  const dataLines = []

  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }

  return { event, data: dataLines.join('\n') }
}

const dispatchSseEvent = ({ event, data }, handlers) => {
  switch (event) {
  case 'token':
    handlers.onToken?.(data)
    break
  case 'pending_action':
    try {
      handlers.onPending?.(JSON.parse(data))
    } catch {
      throw new AiApiError('AI 操作预览格式无效', { code: 'AI_PENDING_INVALID' })
    }
    break
  case 'session':
    handlers.onSession?.(data)
    break
  case 'done':
    handlers.onDone?.()
    break
  case 'error':
    throw new AiApiError('AI 流式响应失败', { code: 'AI_SSE_ERROR' })
  default:
    if (data) handlers.onToken?.(data)
  }
}

/**
 * @param {{ message: string, sessionId?: string }} payload
 * @param {{ onToken?, onPending?, onSession?, onDone? }} handlers
 * @param {{ signal?: AbortSignal }} options
 */
export async function streamChat(payload, handlers = {}, { signal } = {}) {
  const response = await fetch(`${BASE_URL}/ai/chat/stream`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
    signal
  })

  if (!response.ok) await throwHttpError(response)
  if (!response.body?.getReader) {
    throw new AiApiError('浏览器不支持流式响应', { code: 'AI_STREAM_UNSUPPORTED' })
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  let streamFinished = false
  while (!streamFinished) {
    const { done, value } = await reader.read()
    streamFinished = done
    if (streamFinished) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''
    events.filter(Boolean).forEach(raw => dispatchSseEvent(parseSseEvent(raw), handlers))
  }

  buffer += decoder.decode()
  if (buffer.trim()) dispatchSseEvent(parseSseEvent(buffer), handlers)
}

async function postJson(path, body, { unknownResult = false } = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body)
    })
  } catch (error) {
    if (unknownResult) error.unknownResult = true
    throw error
  }

  if (!response.ok) await throwHttpError(response, unknownResult)

  let result
  try {
    result = await response.json()
  } catch {
    throw new AiApiError('AI 响应格式无效', {
      code: 'AI_INVALID_JSON',
      status: response.status,
      unknownResult
    })
  }

  if (result?.code !== 200) {
    throw new AiApiError(result?.message || 'AI 业务请求失败', {
      code: `AI_BUSINESS_${result?.code ?? 'UNKNOWN'}`,
      status: response.status
    })
  }
  return result
}

export function confirmAction(sessionId) {
  return postJson('/ai/chat/confirm', { sessionId }, { unknownResult: true })
}

export function rejectAction(sessionId) {
  return postJson('/ai/chat/reject', { sessionId })
}

export function generateForm(type, prompt) {
  return postJson('/ai/generate', { type, prompt })
}
