import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() }
const route = { params: {}, query: {} }
const recipeStore = vi.hoisted(() => ({
  items: [], detail: null, pagination: { hasMore: false }, activeSource: 'my',
  listStatus: 'empty', loadMoreError: null, failedPage: null, isLoadingMore: false,
  detailStatus: 'idle', mutationStatus: 'idle', error: null,
  fetchList: vi.fn(), retryList: vi.fn(), fetchDetail: vi.fn(), create: vi.fn(), update: vi.fn(),
  remove: vi.fn(), publish: vi.fn(), setLiked: vi.fn(), setCollected: vi.fn()
}))
const draftState = vi.hoisted(() => ({
  draft: { value: null }, hasDraft: { value: false }, save: vi.fn(), restore: vi.fn(), clear: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => router,
  useRoute: () => route,
  onBeforeRouteLeave: vi.fn()
}))
vi.mock('@/stores/recipe', () => ({ useRecipeStore: () => recipeStore }))
vi.mock('@/stores/user', () => ({ useUserStore: () => ({ userInfo: { id: 42 } }) }))
vi.mock('@/composables/useDraft', () => ({ useDraft: () => draftState }))
vi.mock('@/api', () => ({ uploadApi: { uploadImage: vi.fn() } }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))
vi.mock('vant', () => ({ showToast: vi.fn(), showConfirmDialog: vi.fn(() => Promise.resolve()) }))

import RecipeIndex from '@/views/recipe/index.vue'
import RecipeDetail from '@/views/recipe/detail.vue'
import RecipeEditor from '@/views/recipe/add.vue'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))

describe('菜谱页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.params = {}
    route.query = {}
    Object.assign(recipeStore, {
      items: [], detail: null, pagination: { hasMore: false }, activeSource: 'my',
      listStatus: 'empty', loadMoreError: null, failedPage: null, isLoadingMore: false,
      detailStatus: 'idle', mutationStatus: 'idle', error: null
    })
    Object.assign(draftState, {
      draft: { value: null }, hasDraft: { value: false },
      save: vi.fn(), restore: vi.fn(), clear: vi.fn()
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('清楚区分我的草稿、情侣已发布、全局推荐，搜索标明全局范围', async () => {
    const wrapper = mount(RecipeIndex)
    await flush()

    expect(wrapper.text()).toContain('我的草稿')
    expect(wrapper.text()).toContain('情侣已发布')
    expect(wrapper.text()).toContain('全局推荐')
    expect(wrapper.text()).toContain('搜索范围：全局已发布菜谱')
    expect(wrapper.text()).not.toContain('情侣推荐')
  })

  it('追加失败时保留已有菜谱并提供失败页重试', async () => {
    recipeStore.items = [{ id: 1, title: '已有菜谱', status: 1 }]
    recipeStore.listStatus = 'success'
    recipeStore.loadMoreError = { code: 'NETWORK_ERROR' }
    recipeStore.failedPage = 2
    const wrapper = mount(RecipeIndex)

    expect(wrapper.text()).toContain('已有菜谱')
    await wrapper.find('[data-test="recipe-load-more-retry"]').trigger('click')

    expect(recipeStore.retryList).toHaveBeenCalledOnce()
  })

  it('详情展示结构化食材与步骤，并为坏图提供固定比例占位', async () => {
    route.params = { id: '5' }
    recipeStore.detail = {
      id: 5, userId: 42, title: '星空汤', coverUrl: 'bad://cover',
      ingredients: [{ name: '水', amount: '500ml' }], steps: [{ content: '加热', imageUrl: null }]
    }
    recipeStore.detailStatus = 'success'
    const wrapper = mount(RecipeDetail)
    await flush()
    await wrapper.find('[data-test="recipe-cover-image"]').trigger('error')

    expect(wrapper.find('[data-test="recipe-cover-placeholder"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('水')
    expect(wrapper.text()).toContain('加热')
    expect(wrapper.find('[data-test="recipe-edit"]').exists()).toBe(true)
  })

  it('编辑器以可排序结构化列表编辑食材/步骤并使用图标删除按钮', async () => {
    const wrapper = mount(RecipeEditor)

    await wrapper.find('[data-test="add-ingredient"]').trigger('click')
    await wrapper.find('[data-test="add-ingredient"]').trigger('click')
    await wrapper.find('[data-test="ingredient-name-0"]').setValue('盐')
    await wrapper.find('[data-test="ingredient-name-1"]').setValue('水')
    await wrapper.find('[data-test="ingredient-move-up-1"]').trigger('click')

    expect(wrapper.find('[data-test="ingredient-name-0"]').element.value).toBe('水')
    expect(wrapper.find('[data-test="ingredient-remove-0"]').attributes('aria-label')).toBe('删除食材')
    expect(wrapper.find('[data-test="step-remove-0"]').attributes('aria-label')).toBe('删除步骤')
  })

  it('防止重复提交并在成功后只清理当前草稿', async () => {
    let resolveCreate
    recipeStore.create.mockReturnValue(new Promise(resolve => { resolveCreate = resolve }))
    const wrapper = mount(RecipeEditor)
    await wrapper.find('[data-test="recipe-title"]').setValue('星空汤')

    await wrapper.find('[data-test="recipe-save-draft"]').trigger('click')
    await wrapper.find('[data-test="recipe-save-draft"]').trigger('click')
    expect(recipeStore.create).toHaveBeenCalledOnce()
    expect(recipeStore.create.mock.calls[0][0]).toMatchObject({ difficulty: 'easy', publish: false })
    expect(wrapper.find('[data-test="recipe-publish"]').attributes('disabled')).toBeDefined()
    resolveCreate({ id: 10 })
    await flush()
    expect(draftState.clear).toHaveBeenCalledOnce()
  })

  it('脏表单注册离开提醒并可恢复草稿', async () => {
    draftState.hasDraft.value = true
    draftState.restore.mockReturnValue({ title: '恢复的菜谱', ingredients: [], steps: [] })
    const { onBeforeRouteLeave } = await import('vue-router')
    const wrapper = mount(RecipeEditor)
    await wrapper.find('[data-test="restore-draft"]').trigger('click')

    expect(wrapper.find('[data-test="recipe-title"]').element.value).toBe('恢复的菜谱')
    expect(onBeforeRouteLeave).toHaveBeenCalledOnce()
  })

  it('编辑已发布菜谱只允许真实更新，合法字符串难度和 null 列表保持原语义', async () => {
    route.params = { id: '7' }
    recipeStore.detail = {
      id: 7, title: '旧标题', status: 1, difficulty: 'hard', ingredients: null, steps: null
    }
    recipeStore.fetchDetail.mockResolvedValue()
    recipeStore.update.mockResolvedValue({ id: 7 })
    const wrapper = mount(RecipeEditor)
    await flush()

    expect(wrapper.find('[data-test="recipe-save-draft"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="recipe-publish"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="recipe-save-edit"]').text()).toContain('保存修改')
    await wrapper.find('[data-test="recipe-title"]').setValue('只改标题')
    await wrapper.find('[data-test="recipe-save-edit"]').trigger('click')
    await flush()

    expect(recipeStore.update).toHaveBeenCalledWith('7', expect.objectContaining({
      title: '只改标题', difficulty: 'hard', ingredients: null, steps: null
    }))
    expect(recipeStore.update.mock.calls[0][1]).not.toHaveProperty('publish')
    expect(recipeStore.publish).not.toHaveBeenCalled()
  })

  it('显式编辑结构列表时过滤全空项，显式删除全部才发送空数组', async () => {
    route.params = { id: '8' }
    recipeStore.detail = {
      id: 8, title: '旧标题', status: 0, difficulty: 'medium', ingredients: null, steps: null
    }
    recipeStore.fetchDetail.mockResolvedValue()
    recipeStore.update.mockResolvedValue({ id: 8 })
    const wrapper = mount(RecipeEditor)
    await flush()

    await wrapper.find('[data-test="add-ingredient"]').trigger('click')
    await wrapper.find('[data-test="add-ingredient"]').trigger('click')
    await wrapper.find('[data-test="ingredient-name-1"]').setValue('盐')
    await wrapper.find('[data-test="add-step"]').trigger('click')
    await wrapper.find('[data-test="add-step"]').trigger('click')
    await wrapper.find('[data-test="step-content-1"]').setValue('加盐')
    await wrapper.find('[data-test="recipe-save-edit"]').trigger('click')
    await flush()

    expect(recipeStore.update.mock.calls[0][1]).toMatchObject({
      difficulty: 'medium',
      ingredients: [{ name: '盐', amount: '' }],
      steps: [{ content: '加盐', imageUrl: null }]
    })

    recipeStore.update.mockClear()
    await wrapper.find('[data-test="ingredient-remove-0"]').trigger('click')
    await wrapper.find('[data-test="ingredient-remove-0"]').trigger('click')
    await wrapper.find('[data-test="step-remove-0"]').trigger('click')
    await wrapper.find('[data-test="step-remove-0"]').trigger('click')
    await wrapper.find('[data-test="recipe-save-edit"]').trigger('click')
    await flush()
    expect(recipeStore.update.mock.calls[0][1]).toMatchObject({ ingredients: [], steps: [] })
  })

  it('脏菜谱表单真实阻止路由/浏览器离开，并允许确认后继续', async () => {
    const { onBeforeRouteLeave } = await import('vue-router')
    const wrapper = mount(RecipeEditor)
    await wrapper.find('[data-test="recipe-title"]').setValue('未保存菜谱')
    await flush()
    const guard = onBeforeRouteLeave.mock.calls.at(-1)[0]
    const next = vi.fn()
    const confirm = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true)
    vi.stubGlobal('confirm', confirm)

    guard({}, {}, next)
    expect(next).toHaveBeenLastCalledWith(false)
    guard({}, {}, next)
    expect(next).toHaveBeenLastCalledWith()

    const event = new Event('beforeunload', { cancelable: true })
    globalThis.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })
})
