import { computed, ref } from 'vue'
import { logUiEvent } from './useStructuredLog'

const VALID_RESOURCES = new Set(['menu', 'recipe', 'note'])
const VALID_ID = /^[A-Za-z0-9_-]+$/
const VALID_RESOURCE_ID = /^[1-9]\d*$/

const validUserId = (userId) => (
  (typeof userId === 'number' && Number.isFinite(userId) && userId > 0) ||
  (typeof userId === 'string' && userId.trim().length > 0 && VALID_ID.test(userId.trim()))
)

const errorCode = (error) => String(error?.name || 'STORAGE_ERROR')

export const useDraft = ({ userId, resource, resourceId } = {}) => {
  if (!VALID_RESOURCES.has(resource)) throw new Error('resource must be menu, recipe or note')
  if (resourceId !== undefined && resourceId !== null && !VALID_RESOURCE_ID.test(String(resourceId))) {
    throw new Error('resourceId is invalid')
  }

  const enabled = validUserId(userId)
  const key = enabled
    ? `couple-cosmos:draft:${String(userId).trim()}:${resource}:${resourceId || 'new'}`
    : null
  const draft = ref(null)
  const hasDraft = computed(() => draft.value !== null)

  const log = (operation, result, startedAt, fields = {}) => logUiEvent(`draft.${operation}`, {
    module: 'draft', operation, result, durationMs: Date.now() - startedAt, resource,
    resourceMode: resourceId ? 'edit' : 'new', ...fields
  })

  const restore = () => {
    const startedAt = Date.now()
    if (!key) {
      log('restore', 'skipped_invalid_user', startedAt, { errorCode: 'INVALID_USER_ID' })
      return null
    }
    try {
      const raw = localStorage.getItem(key)
      draft.value = raw ? JSON.parse(raw) : null
      log('restore', draft.value ? 'restored' : 'empty', startedAt)
      return draft.value
    } catch (error) {
      draft.value = null
      log('restore', 'failed', startedAt, { errorCode: errorCode(error) })
      return null
    }
  }

  const save = (value) => {
    const startedAt = Date.now()
    if (!key) {
      log('save', 'skipped_invalid_user', startedAt, { errorCode: 'INVALID_USER_ID' })
      return false
    }
    try {
      localStorage.setItem(key, JSON.stringify(value))
      draft.value = value
      log('save', 'success', startedAt)
      return true
    } catch (error) {
      log('save', 'failed', startedAt, { errorCode: errorCode(error) })
      return false
    }
  }

  const clear = () => {
    const startedAt = Date.now()
    if (!key) {
      log('clear', 'skipped_invalid_user', startedAt, { errorCode: 'INVALID_USER_ID' })
      return false
    }
    try {
      localStorage.removeItem(key)
      draft.value = null
      log('clear', 'success', startedAt)
      return true
    } catch (error) {
      log('clear', 'failed', startedAt, { errorCode: errorCode(error) })
      return false
    }
  }

  restore()
  return { draft, hasDraft, save, restore, clear }
}
