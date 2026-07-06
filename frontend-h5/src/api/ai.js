/**
 * AI 助手 API（流式 SSE + 表单生成）
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

function authHeaders() {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }
}

/**
 * 流式聊天
 * @param {{ message: string, sessionId?: string }} payload
 * @param {{ onToken?, onPending?, onSession?, onDone?, onError? }} handlers
 */
export async function streamChat(payload, handlers = {}) {
  const response = await fetch(`${BASE_URL}/ai/chat/stream`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    const errText = await response.text()
    handlers.onError?.(errText || `HTTP ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      parseSseEvent(part, handlers)
    }
  }

  if (buffer.trim()) {
    parseSseEvent(buffer, handlers)
  }
}

function parseSseEvent(raw, handlers) {
  let event = 'message'
  let data = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      data += line.slice(5).trim()
    }
  }

  switch (event) {
    case 'token':
      handlers.onToken?.(data)
      break
    case 'pending_action':
      try {
        handlers.onPending?.(JSON.parse(data))
      } catch {
        handlers.onPending?.(data)
      }
      break
    case 'session':
      handlers.onSession?.(data)
      break
    case 'done':
      handlers.onDone?.()
      break
    case 'error':
      handlers.onError?.(data)
      break
    default:
      if (data) handlers.onToken?.(data)
  }
}

export function confirmAction(sessionId) {
  return fetch(`${BASE_URL}/ai/chat/confirm`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ sessionId })
  }).then(r => r.json())
}

export function rejectAction(sessionId) {
  return fetch(`${BASE_URL}/ai/chat/reject`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ sessionId })
  }).then(r => r.json())
}

export function generateForm(type, prompt) {
  return fetch(`${BASE_URL}/ai/generate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ type, prompt })
  }).then(r => r.json())
}
