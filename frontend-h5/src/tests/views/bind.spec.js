import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BindIndex from '@/views/bind/index.vue'
import { coupleApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = { query: {} }
const router = { replace: vi.fn(), resolve: vi.fn(() => ({ matched: [{ name: 'Home' }] })) }
const userStore = { userInfo: { id: 42 }, setCoupleInfo: vi.fn(), getCoupleInfo: vi.fn() }

vi.mock('vue-router', () => ({ useRouter: () => router, useRoute: () => route }))
vi.mock('@/stores/user', () => ({ useUserStore: () => userStore }))
vi.mock('@/api', () => ({
  coupleApi: {
    getCodeInfo: vi.fn(), generateCoupleCode: vi.fn(), refreshCode: vi.fn(), bindCouple: vi.fn()
  }
}))
vi.mock('vant', () => ({ showToast: vi.fn(), showConfirmDialog: vi.fn(() => Promise.resolve()) }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

const validCodeInfo = {
  coupleCode: 'A1B2C3D4',
  remainingSeconds: 604800,
  createTime: 100,
  expireTime: 200,
  status: 'valid',
  expired: false,
  expiringSoon: false
}

const flush = () => new Promise(resolve => setTimeout(resolve, 0))
const flushMicrotasks = async () => {
  await Promise.resolve()
  await Promise.resolve()
}
const mountBind = () => mount(BindIndex)

describe('情侣绑定页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.query = {}
    coupleApi.getCodeInfo.mockResolvedValue({ data: validCodeInfo })
    userStore.getCoupleInfo.mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue() } })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('展示 8 位邀请码、7 天进度，并支持复制', async () => {
    const wrapper = mountBind()
    await flush()

    expect(wrapper.find('[data-test="invite-code"]').text()).toBe('A1B2C3D4')
    expect(wrapper.text()).toContain('7 天')
    await wrapper.find('[data-test="copy-code"]').trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('A1B2C3D4')
  })

  it('重新生成使用 refreshCode，并保留重置恋爱开始日的确认说明', async () => {
    const wrapper = mountBind()
    await flush()
    coupleApi.refreshCode.mockResolvedValue({ data: 'D4C3B2A1' })

    await wrapper.find('[data-test="refresh-code"]').trigger('click')
    await flush()

    expect(wrapper.text()).toContain('恋爱开始日重置为当天')
    expect(coupleApi.refreshCode).toHaveBeenCalledOnce()
  })

  it('首次读取邀请码失败时显示可重试状态，不改为重新生成', async () => {
    coupleApi.getCodeInfo.mockRejectedValue(new Error('network'))
    const wrapper = mountBind()
    await flush()

    expect(wrapper.find('[data-test="code-state-error"]').text()).toContain('暂时无法获取邀请码')
    expect(coupleApi.generateCoupleCode).not.toHaveBeenCalled()
    await wrapper.find('[data-test="retry-code"]').trigger('click')
    await flush()

    expect(coupleApi.getCodeInfo).toHaveBeenCalledTimes(2)
  })

  it('没有邀请码时显示空状态，生成失败后可重试生成', async () => {
    coupleApi.getCodeInfo.mockResolvedValue({ data: null })
    coupleApi.generateCoupleCode.mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce({ data: 'D4C3B2A1' })
    const wrapper = mountBind()
    await flush()

    expect(wrapper.find('[data-test="code-state-empty"]').exists()).toBe(true)
    await wrapper.find('[data-test="generate-code"]').trigger('click')
    await flush()
    expect(wrapper.find('[data-test="code-state-error"]').exists()).toBe(true)
    await wrapper.find('[data-test="retry-code"]').trigger('click')
    await flush()

    expect(wrapper.find('[data-test="invite-code"]').text()).toBe('D4C3B2A1')
  })

  it('短用户 ID 的结构化日志记录为 anonymous', async () => {
    const rawUserId = 9
    userStore.userInfo = { id: rawUserId }
    coupleApi.getCodeInfo.mockResolvedValue({ data: null })
    coupleApi.generateCoupleCode.mockResolvedValue({ data: 'D4C3B2A1' })
    const wrapper = mountBind()
    await flush()
    await wrapper.find('[data-test="generate-code"]').trigger('click')
    await flush()

    const logFields = logUiEvent.mock.calls.find(([event]) => event === 'couple.code.generate')?.[1]
    expect(logFields.userId).toBe('anonymous')
    expect(logFields.userId).not.toBe(String(rawUserId))
  })

  it('只允许提交恰好 8 位的情侣码，并在错误后保持可再次操作', async () => {
    const wrapper = mountBind()
    await flush()
    await wrapper.findAll('.mode-switch button')[1].trigger('click')
    const input = wrapper.find('[data-test="partner-code-input"]')

    await input.setValue('A1B2')
    expect(wrapper.find('[data-test="bind-submit"]').attributes('disabled')).toBeDefined()

    await input.setValue('A1B2C3D4')
    coupleApi.bindCouple.mockRejectedValue({ code: 2003, message: '情侣码无效或已过期' })
    await wrapper.find('[data-test="bind-submit"]').trigger('click')
    await flush()

    expect(wrapper.find('[data-test="bind-error"]').text()).toContain('情侣码无效或已过期')
    expect(wrapper.find('[data-test="bind-submit"]').attributes('disabled')).toBeUndefined()
  })

  it('绑定成功时先持久化情侣快照，标准动效完成后再拒绝协议相对跳转', async () => {
    vi.useFakeTimers()
    route.query = { redirect: '//external.example' }
    coupleApi.bindCouple.mockResolvedValue({ data: { id: 9, partnerName: 'TA' } })
    const wrapper = mountBind()
    await flushMicrotasks()
    await wrapper.findAll('.mode-switch button')[1].trigger('click')
    await wrapper.find('[data-test="partner-code-input"]').setValue('A1B2C3D4')
    await wrapper.find('[data-test="bind-submit"]').trigger('click')
    await Promise.resolve()

    expect(userStore.setCoupleInfo).toHaveBeenCalledWith({ id: 9, partnerName: 'TA' })
    expect(router.replace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(499)
    expect(router.replace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(userStore.setCoupleInfo.mock.invocationCallOrder[0]).toBeLessThan(router.replace.mock.invocationCallOrder[0])
    expect(router.replace).toHaveBeenCalledWith('/home')
    vi.useRealTimers()
  })

  it('未知站内路径也回退到首页', async () => {
    vi.useFakeTimers()
    route.query = { redirect: '/unknown-route' }
    router.resolve.mockReturnValueOnce({ matched: [] })
    coupleApi.bindCouple.mockResolvedValue({ data: { id: 9 } })
    const wrapper = mountBind()
    await flushMicrotasks()
    await wrapper.findAll('.mode-switch button')[1].trigger('click')
    await wrapper.find('[data-test="partner-code-input"]').setValue('A1B2C3D4')
    await wrapper.find('[data-test="bind-submit"]').trigger('click')
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(500)

    expect(router.replace).toHaveBeenCalledWith('/home')
  })
})
