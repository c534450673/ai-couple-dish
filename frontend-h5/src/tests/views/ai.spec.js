import { readFile } from 'node:fs/promises'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const aiApi = vi.hoisted(() => ({
  streamChat: vi.fn(),
  confirmAction: vi.fn(),
  rejectAction: vi.fn()
}))
const resourceStores = vi.hoisted(() => ({
  menu: { fetchList: vi.fn() },
  recipe: { fetchList: vi.fn() }
}))

vi.mock('@/api/ai', () => aiApi)
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))
vi.mock('@/stores/menu', () => ({ useMenuStore: () => resourceStores.menu }))
vi.mock('@/stores/recipe', () => ({ useRecipeStore: () => resourceStores.recipe }))

import { AI_CHAT_STATES, buildActionPreview, useAiChatStore } from '@/stores/ai'

const deferred = () => Promise.withResolvers()

describe('AI 完整页与共享会话合同', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    resourceStores.menu.fetchList.mockResolvedValue(undefined)
    resourceStores.recipe.fetchList.mockResolvedValue(undefined)
  })

  it('/ai 路由加载真实页面而不是 UnavailableView', async () => {
    const router = await readFile('src/router/index.js', 'utf8')
    expect(router).toMatch(/path:\s*['"]\/ai['"][\s\S]*views\/ai\/index\.vue/)
  })

  it('抽屉与完整页复用同一个 AI Store 和聊天面板', async () => {
    const [drawer, page] = await Promise.all([
      readFile('src/components/AiChatDrawer.vue', 'utf8'),
      readFile('src/views/ai/index.vue', 'utf8')
    ])

    expect(drawer).toContain('useAiChatStore')
    expect(page).toContain('useAiChatStore')
    expect(drawer).toContain('AiChatPanel')
    expect(page).toContain('AiChatPanel')
    expect(drawer).toContain('打开完整页')
  })

  it('只展示真实运行期会话，不宣称历史、分页或断点续传', async () => {
    const page = await readFile('src/views/ai/index.vue', 'utf8')
    expect(page).toContain('历史与分页暂不可用')
    expect(page).not.toContain('断点继续')
    expect(page).toContain('重新发送')
  })

  it('写工具预览展示操作类型、字段 diff、影响对象与来源', async () => {
    const panel = await readFile('src/components/AiChatPanel.vue', 'utf8')
    expect(panel).toContain('操作类型')
    expect(panel).toContain('字段变更')
    expect(panel).toContain('影响对象')
    expect(panel).toContain('来源')
  })

  it('状态集合精确，token/pending/session/done 落入同一运行期 Store', async () => {
    expect(AI_CHAT_STATES).toEqual([
      'idle', 'streaming', 'interrupted', 'pending-confirmation', 'confirming', 'complete', 'error'
    ])
    aiApi.streamChat.mockImplementation(async (payload, handlers) => {
      handlers.onPending({
        actionId: 'action-1',
        actionType: 'add_menu',
        payload: { restaurantName: '星港餐厅' }
      })
      handlers.onToken('第一段')
      handlers.onToken('第二段')
      handlers.onSession('server-session')
      handlers.onDone()
    })
    const store = useAiChatStore()
    store.draft = '添加餐厅'

    await store.sendMessage()

    expect(store.sessionId).toBe('server-session')
    expect(store.messages.at(-1).content).toBe('第一段第二段')
    expect(store.state).toBe('pending-confirmation')
    expect(store.canSend).toBe(false)
    expect(store.canConfirm).toBe(true)
  })

  it('显式停止进入 interrupted，迟到旧流不能污染重新发送的新请求', async () => {
    const first = deferred()
    let oldHandlers
    aiApi.streamChat
      .mockImplementationOnce((payload, handlers, { signal }) => {
        oldHandlers = handlers
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
          first.promise.then(resolve)
        })
      })
      .mockImplementationOnce(async (payload, handlers) => {
        handlers.onToken('新回复')
        handlers.onSession('new-session')
        handlers.onDone()
      })
    const store = useAiChatStore()
    const oldRequest = store.sendMessage('原问题')
    expect(store.state).toBe('streaming')
    expect(store.stopStreaming()).toBe(true)
    expect(store.state).toBe('interrupted')

    await store.retryLastMessage()
    oldHandlers.onToken('迟到内容')
    oldHandlers.onSession('old-session')
    oldHandlers.onDone()
    await oldRequest

    expect(store.sessionId).toBe('new-session')
    expect(store.messages.at(-1).content).toBe('新回复')
    expect(store.messages.some(message => message.content.includes('迟到内容'))).toBe(false)
    expect(store.state).toBe('complete')
  })

  it('新会话 pending 在 session 前中断时不可确认，只能清预览后重新发送', async () => {
    aiApi.streamChat.mockImplementationOnce((payload, handlers, { signal }) => {
      handlers.onPending({ actionId: 'a2', actionType: 'create_recipe', payload: { title: '星云汤' } })
      return new Promise((resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
      })
    }).mockImplementationOnce(async (payload, handlers) => {
      handlers.onToken('请再次核对')
      handlers.onDone()
    })
    const store = useAiChatStore()
    const request = store.sendMessage('创建菜谱')
    await Promise.resolve()

    expect(store.pendingAction).toBeTruthy()
    expect(store.canConfirm).toBe(false)
    expect(store.canSend).toBe(false)
    store.stopStreaming()
    await request
    expect(store.state).toBe('interrupted')
    expect(store.canRetry).toBe(true)

    await store.retryLastMessage()
    expect(store.pendingAction).toBeNull()
    expect(aiApi.streamChat).toHaveBeenCalledTimes(2)
  })

  it('确认严格单飞，成功后才清 pending', async () => {
    const confirmation = deferred()
    aiApi.confirmAction.mockReturnValue(confirmation.promise)
    const store = useAiChatStore()
    store.sessionId = 'sid'
    store.pendingAction = { actionType: 'add_menu', payload: { restaurantName: '星港' } }
    store.state = 'pending-confirmation'

    const first = store.confirmPending()
    const second = store.confirmPending()
    expect(aiApi.confirmAction).toHaveBeenCalledOnce()
    expect(await second).toBe(false)
    expect(store.pendingAction).toBeTruthy()
    confirmation.resolve({ code: 200, data: { message: '已创建' } })
    expect(await first).toBe(true)
    expect(store.pendingAction).toBeNull()
    expect(store.state).toBe('complete')
  })

  it('确认结果未知时不自动重试也不允许再次确认', async () => {
    const error = Object.assign(new Error('network'), { unknownResult: true, code: 'AI_HTTP_500' })
    aiApi.confirmAction.mockRejectedValue(error)
    const store = useAiChatStore()
    store.sessionId = 'sid'
    store.pendingAction = { actionType: 'create_recipe', payload: { title: '星云汤' } }
    store.state = 'pending-confirmation'

    expect(await store.confirmPending()).toBe(false)
    expect(store.confirmationOutcomeUnknown).toBe(true)
    expect(store.canConfirm).toBe(false)
    expect(resourceStores.recipe.fetchList).toHaveBeenCalledWith({
      source: 'couple', pageNum: 1, pageSize: 10
    })
    expect(await store.confirmPending()).toBe(false)
    expect(aiApi.confirmAction).toHaveBeenCalledOnce()
  })

  it('拒绝调用真实接口并仅清除 pending，不执行 confirm', async () => {
    aiApi.rejectAction.mockResolvedValue({ code: 200, data: null })
    const store = useAiChatStore()
    store.sessionId = 'sid'
    store.pendingAction = { actionType: 'add_menu', payload: { restaurantName: '星港' } }
    store.state = 'pending-confirmation'

    expect(await store.rejectPending()).toBe(true)
    expect(aiApi.rejectAction).toHaveBeenCalledWith('sid')
    expect(aiApi.confirmAction).not.toHaveBeenCalled()
    expect(store.pendingAction).toBeNull()
  })

  it('未知写操作预览明确 unavailable', () => {
    const preview = buildActionPreview({ actionType: 'delete_menu', payload: { id: 9 } })
    expect(preview.supported).toBe(false)
    expect(preview.target).toBe('不支持的写入对象')
  })
})
