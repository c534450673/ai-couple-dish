import { ref } from 'vue'
import { logUiEvent } from './useStructuredLog'

const isEmptyResult = (value) => value == null || (Array.isArray(value) && value.length === 0)

const getErrorCode = (error) => error?.code ?? error?.response?.status ?? 'UNKNOWN'

const getErrorStatus = (error) => {
  const code = getErrorCode(error)
  if (code === 401 || code === '401') return 'unauthorized'
  if (code === 2006 || code === '2006' || error?.message?.includes('未绑定')) return 'unbound'
  return 'error'
}

export const useAsyncResource = (loader, options = {}) => {
  const status = ref('idle')
  const data = ref(options.initialData ?? null)
  const error = ref(null)
  const emptyWhen = options.isEmpty || isEmptyResult
  const resource = options.name || 'anonymous'
  let latestRequestId = 0
  let latestArgs = []

  const execute = async (...args) => {
    const requestId = ++latestRequestId
    const startedAt = Date.now()
    latestArgs = args
    status.value = 'loading'
    error.value = null
    logUiEvent('async_resource_transition', {
      module: 'useAsyncResource',
      operation: 'execute',
      requestId,
      resource,
      result: 'loading',
      durationMs: 0
    })

    try {
      const result = await loader(...args)
      const durationMs = Date.now() - startedAt
      if (requestId !== latestRequestId) {
        logUiEvent('async_resource_transition', {
          module: 'useAsyncResource',
          operation: 'execute',
          requestId,
          resource,
          result: 'stale_ignored',
          durationMs
        })
        return result
      }

      data.value = result
      status.value = emptyWhen(result) ? 'empty' : 'success'
      logUiEvent('async_resource_transition', {
        module: 'useAsyncResource',
        operation: 'execute',
        requestId,
        resource,
        result: status.value,
        durationMs
      })
      return result
    } catch (caughtError) {
      const durationMs = Date.now() - startedAt
      if (requestId !== latestRequestId) return null

      error.value = caughtError
      status.value = getErrorStatus(caughtError)
      logUiEvent('async_resource_transition', {
        module: 'useAsyncResource',
        operation: 'execute',
        requestId,
        resource,
        result: status.value,
        durationMs,
        errorCode: getErrorCode(caughtError)
      })
      return null
    }
  }

  const retry = () => execute(...latestArgs)

  const reset = () => {
    latestRequestId++
    latestArgs = []
    status.value = 'idle'
    data.value = options.initialData ?? null
    error.value = null
    logUiEvent('async_resource_transition', {
      module: 'useAsyncResource',
      operation: 'reset',
      resource,
      result: 'idle',
      durationMs: 0
    })
  }

  return { status, data, error, execute, retry, reset }
}
