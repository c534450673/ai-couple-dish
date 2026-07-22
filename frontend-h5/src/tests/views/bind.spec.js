import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BindIndex from '@/views/bind/index.vue'
import { coupleApi } from '@/api'

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
const mountBind = () => mount(BindIndex)

describe('情侣绑定页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.query = {}
    coupleApi.getCodeInfo.mockResolvedValue({ data: validCodeInfo })
    userStore.getCoupleInfo.mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue() } })
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

  it('绑定成功时先持久化情侣快照，再拒绝协议相对跳转', async () => {
    route.query = { redirect: '//external.example' }
    coupleApi.bindCouple.mockResolvedValue({ data: { id: 9, partnerName: 'TA' } })
    const wrapper = mountBind()
    await flush()
    await wrapper.findAll('.mode-switch button')[1].trigger('click')
    await wrapper.find('[data-test="partner-code-input"]').setValue('A1B2C3D4')
    await wrapper.find('[data-test="bind-submit"]').trigger('click')
    await flush()

    expect(userStore.setCoupleInfo).toHaveBeenCalledWith({ id: 9, partnerName: 'TA' })
    expect(userStore.setCoupleInfo.mock.invocationCallOrder[0]).toBeLessThan(router.replace.mock.invocationCallOrder[0])
    expect(router.replace).toHaveBeenCalledWith('/home')
  })

  it('未知站内路径也回退到首页', async () => {
    route.query = { redirect: '/unknown-route' }
    router.resolve.mockReturnValueOnce({ matched: [] })
    coupleApi.bindCouple.mockResolvedValue({ data: { id: 9 } })
    const wrapper = mountBind()
    await flush()
    await wrapper.findAll('.mode-switch button')[1].trigger('click')
    await wrapper.find('[data-test="partner-code-input"]').setValue('A1B2C3D4')
    await wrapper.find('[data-test="bind-submit"]').trigger('click')
    await flush()

    expect(router.replace).toHaveBeenCalledWith('/home')
  })
})
