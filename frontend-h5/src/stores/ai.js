import { defineStore } from 'pinia'
import { confirmAction, rejectAction, streamChat } from '@/api/ai'
import { logUiEvent } from '@/composables/useStructuredLog'
import { useMenuStore } from '@/stores/menu'
import { useRecipeStore } from '@/stores/recipe'

export const AI_CHAT_STATES = Object.freeze([
  'idle',
  'streaming',
  'interrupted',
  'pending-confirmation',
  'confirming',
  'complete',
  'error'
])

const WRITE_ACTIONS = new Set(['add_menu', 'create_recipe'])
const FIELD_LABELS = {
  restaurantName: '餐厅名称',
  dishName: '菜品名称',
  location: '地点',
  status: '状态',
  rating: '评分',
  price: '价格',
  title: '菜谱名称',
  description: '说明',
  ingredients: '食材',
  steps: '步骤'
}

let requestSequence = 0
let messageSequence = 0

const nextRequestId = () => `ai-${Date.now()}-${++requestSequence}`
const nextMessageId = () => `message-${Date.now()}-${++messageSequence}`

const hashSession = async (sessionId) => {
  if (!sessionId || !globalThis.crypto?.subtle) return undefined
  const bytes = new TextEncoder().encode(sessionId)
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest).slice(0, 8))
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
}

const logAiStage = async (event, fields, sessionId) => {
  const conversationHash = await hashSession(sessionId)
  logUiEvent(event, {
    ...(conversationHash ? { conversationHash } : {}),
    stage: fields.stage,
    requestId: fields.requestId || null,
    firstTokenMs: fields.firstTokenMs ?? null,
    durationMs: fields.durationMs ?? 0,
    cancelReason: fields.cancelReason || null,
    actionType: fields.actionType || null
  })
}

export const buildActionPreview = (action) => {
  if (!action) return null
  const payload = action.payload && typeof action.payload === 'object' ? action.payload : {}
  const supported = WRITE_ACTIONS.has(action.actionType)
  const target = action.actionType === 'add_menu'
    ? '情侣私密菜单'
    : action.actionType === 'create_recipe'
      ? '情侣菜谱库'
      : '不支持的写入对象'

  return {
    actionType: action.actionType || 'unknown',
    title: action.title || 'AI 写操作预览',
    summary: action.summary || '',
    target,
    source: '当前 AI 对话的后端工具调用',
    supported,
    fields: Object.entries(payload).map(([field, value]) => ({
      field,
      label: FIELD_LABELS[field] || field,
      before: '未创建',
      after: Array.isArray(value) ? value.join('、') : String(value ?? '空值')
    }))
  }
}

export const useAiChatStore = defineStore('ai-chat', {
  state: () => ({
    sessionId: '',
    messages: [],
    pendingAction: null,
    state: 'idle',
    draft: '',
    lastPrompt: '',
    activeRequestId: null,
    activeController: null,
    confirmationInFlight: false,
    confirmationOutcomeUnknown: false,
    errorCode: null,
    cancelReason: null
  }),

  getters: {
    pendingPreview: state => buildActionPreview(state.pendingAction),
    canSend: state => Boolean(state.draft.trim())
      && !state.pendingAction
      && !['streaming', 'confirming'].includes(state.state),
    canStop: state => Boolean(state.activeController)
      && ['streaming', 'pending-confirmation'].includes(state.state),
    canConfirm: state => Boolean(
      state.pendingAction
      && state.sessionId
      && WRITE_ACTIONS.has(state.pendingAction.actionType)
      && !state.confirmationInFlight
      && !state.confirmationOutcomeUnknown
      && !state.activeController
    ),
    canReject: state => Boolean(state.pendingAction)
      && !state.confirmationInFlight
      && !state.activeController,
    canRetry: state => ['interrupted', 'error'].includes(state.state)
      && Boolean(state.lastPrompt)
      && !state.confirmationInFlight
      && !state.confirmationOutcomeUnknown
  },

  actions: {
    logSurface(stage) {
      logAiStage('ai.surface.opened', { stage }, this.sessionId)
    },

    isCurrentRequest(requestId) {
      return this.activeRequestId === requestId
    },

    async sendMessage(message = this.draft) {
      const prompt = String(message || '').trim()
      if (!prompt || this.pendingAction || ['streaming', 'confirming'].includes(this.state)) return false

      const requestId = nextRequestId()
      const controller = new AbortController()
      const startedAt = performance.now()
      let firstTokenAt = null
      let receivedDone = false
      this.lastPrompt = prompt
      this.draft = ''
      this.errorCode = null
      this.cancelReason = null
      this.confirmationOutcomeUnknown = false
      this.activeRequestId = requestId
      this.activeController = controller
      this.state = 'streaming'

      const assistant = {
        id: nextMessageId(),
        role: 'assistant',
        content: '',
        streaming: true,
        requestId
      }
      this.messages.push({ id: nextMessageId(), role: 'user', content: prompt })
      this.messages.push(assistant)
      logAiStage('ai.chat.request', { stage: 'started', requestId }, this.sessionId)

      try {
        await streamChat(
          { message: prompt, ...(this.sessionId ? { sessionId: this.sessionId } : {}) },
          {
            onToken: (token) => {
              if (!this.isCurrentRequest(requestId)) return
              if (firstTokenAt === null) firstTokenAt = performance.now()
              assistant.content += token
            },
            onPending: (action) => {
              if (!this.isCurrentRequest(requestId)) return
              this.pendingAction = action
              this.state = 'pending-confirmation'
              logAiStage('ai.chat.pending', {
                stage: 'pending-confirmation',
                requestId,
                firstTokenMs: firstTokenAt === null ? null : Math.round(firstTokenAt - startedAt),
                durationMs: Math.round(performance.now() - startedAt),
                actionType: action?.actionType
              }, this.sessionId)
            },
            onSession: (sessionId) => {
              if (!this.isCurrentRequest(requestId)) return
              this.sessionId = sessionId
            },
            onDone: () => {
              if (!this.isCurrentRequest(requestId)) return
              receivedDone = true
            }
          },
          { signal: controller.signal }
        )

        if (!this.isCurrentRequest(requestId)) return false
        if (!receivedDone) {
          const error = new Error('AI 流在完成事件前结束')
          error.code = 'AI_STREAM_INCOMPLETE'
          throw error
        }
        assistant.streaming = false
        this.state = this.pendingAction ? 'pending-confirmation' : 'complete'
        logAiStage('ai.chat.request', {
          stage: this.state,
          requestId,
          firstTokenMs: firstTokenAt === null ? null : Math.round(firstTokenAt - startedAt),
          durationMs: Math.round(performance.now() - startedAt),
          actionType: this.pendingAction?.actionType
        }, this.sessionId)
        return true
      } catch (error) {
        if (!this.isCurrentRequest(requestId)) return false
        assistant.streaming = false
        this.draft = prompt
        this.errorCode = error?.code || (error?.name === 'AbortError' ? 'AI_ABORTED' : 'AI_REQUEST_FAILED')
        const interrupted = error?.name === 'AbortError'
          || error?.code === 'AI_STREAM_INCOMPLETE'
          || Boolean(assistant.content)
        this.state = interrupted ? 'interrupted' : 'error'
        this.cancelReason = error?.name === 'AbortError' ? 'explicit-stop' : interrupted ? 'stream-lost' : null
        logAiStage('ai.chat.request', {
          stage: this.state,
          requestId,
          firstTokenMs: firstTokenAt === null ? null : Math.round(firstTokenAt - startedAt),
          durationMs: Math.round(performance.now() - startedAt),
          cancelReason: this.cancelReason,
          actionType: this.pendingAction?.actionType
        }, this.sessionId)
        return false
      } finally {
        if (this.isCurrentRequest(requestId)) {
          this.activeRequestId = null
          this.activeController = null
        }
      }
    },

    stopStreaming() {
      if (!this.activeController || !['streaming', 'pending-confirmation'].includes(this.state)) return false
      const requestId = this.activeRequestId
      const controller = this.activeController
      this.activeRequestId = null
      this.activeController = null
      const assistant = this.messages.find(message => message.requestId === requestId)
      if (assistant) assistant.streaming = false
      this.state = 'interrupted'
      this.draft = this.lastPrompt
      this.cancelReason = 'explicit-stop'
      controller.abort()
      logAiStage('ai.chat.request', {
        stage: 'interrupted',
        requestId,
        cancelReason: this.cancelReason,
        actionType: this.pendingAction?.actionType
      }, this.sessionId)
      return true
    },

    async retryLastMessage() {
      if (!this.canRetry) return false
      if (this.pendingAction && !this.sessionId) this.pendingAction = null
      if (this.pendingAction) return false
      return this.sendMessage(this.lastPrompt)
    },

    async refreshAffectedResource(actionType) {
      try {
        if (actionType === 'add_menu') {
          await useMenuStore().fetchList({ page: 1, pageSize: 10 })
        } else if (actionType === 'create_recipe') {
          await useRecipeStore().fetchList({ source: 'couple', pageNum: 1, pageSize: 10 })
        }
        logAiStage('ai.chat.resource-refresh', { stage: 'complete', actionType }, this.sessionId)
      } catch {
        logAiStage('ai.chat.resource-refresh', { stage: 'error', actionType }, this.sessionId)
      }
    },

    async confirmPending() {
      if (!this.canConfirm) return false
      this.confirmationInFlight = true
      this.state = 'confirming'
      const actionType = this.pendingAction.actionType
      const startedAt = performance.now()
      logAiStage('ai.chat.confirm', { stage: 'started', actionType }, this.sessionId)

      try {
        const result = await confirmAction(this.sessionId)
        this.messages.push({
          id: nextMessageId(),
          role: 'assistant',
          content: result.data?.message || '操作已确认完成'
        })
        this.pendingAction = null
        this.state = 'complete'
        logAiStage('ai.chat.confirm', {
          stage: 'complete',
          durationMs: Math.round(performance.now() - startedAt),
          actionType
        }, this.sessionId)
        return true
      } catch (error) {
        this.confirmationOutcomeUnknown = Boolean(error?.unknownResult)
        this.errorCode = error?.code || 'AI_CONFIRM_FAILED'
        this.state = 'error'
        if (this.confirmationOutcomeUnknown) await this.refreshAffectedResource(actionType)
        logAiStage('ai.chat.confirm', {
          stage: this.confirmationOutcomeUnknown ? 'outcome-unknown' : 'error',
          durationMs: Math.round(performance.now() - startedAt),
          actionType
        }, this.sessionId)
        return false
      } finally {
        this.confirmationInFlight = false
      }
    },

    async rejectPending() {
      if (!this.canReject) return false
      const actionType = this.pendingAction.actionType
      if (!this.sessionId) {
        this.pendingAction = null
        this.state = this.lastPrompt ? 'interrupted' : 'idle'
        logAiStage('ai.chat.reject', { stage: 'local-only', actionType }, this.sessionId)
        return true
      }

      this.confirmationInFlight = true
      const startedAt = performance.now()
      try {
        await rejectAction(this.sessionId)
        this.pendingAction = null
        this.state = 'complete'
        logAiStage('ai.chat.reject', {
          stage: 'complete',
          durationMs: Math.round(performance.now() - startedAt),
          actionType
        }, this.sessionId)
        return true
      } catch (error) {
        this.errorCode = error?.code || 'AI_REJECT_FAILED'
        this.state = 'error'
        logAiStage('ai.chat.reject', {
          stage: 'error',
          durationMs: Math.round(performance.now() - startedAt),
          actionType
        }, this.sessionId)
        return false
      } finally {
        this.confirmationInFlight = false
      }
    }
  }
})
