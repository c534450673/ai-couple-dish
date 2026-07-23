const REDACTED = '[REDACTED]'
const SENSITIVE_KEY_PATTERN = /(?:authorization|cookie|openid|password|phone|secret|session|token|verify.?code)/i

const redactValue = (value, seen) => {
  if (value === null || typeof value !== 'object') return value
  if (seen.has(value)) return '[CIRCULAR]'

  seen.add(value)
  if (Array.isArray(value)) {
    return value.map((item) => redactValue(item, seen))
  }

  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key,
    SENSITIVE_KEY_PATTERN.test(key) ? REDACTED : redactValue(item, seen)
  ]))
}

export const redactSensitiveFields = (fields) => redactValue(fields, new WeakSet())

export const normalizeUiErrorCode = (error, fallback = 'UNKNOWN_ERROR') => {
  const candidate = error?.code ?? error?.response?.data?.code ?? error?.response?.status
  const normalized = String(candidate ?? '').trim()
  return /^[A-Za-z0-9_.-]{1,64}$/.test(normalized) ? normalized : fallback
}

export const logUiEvent = (event, fields = {}) => {
  console.info({
    event,
    ...redactSensitiveFields(fields)
  })
}

export const useStructuredLog = () => ({ logUiEvent })
