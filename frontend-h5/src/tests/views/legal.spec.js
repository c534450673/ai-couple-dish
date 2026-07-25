import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  router: { back: vi.fn(), push: vi.fn() },
  logUiEvent: vi.fn(),
  request: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
  userStore: { logout: vi.fn() }
}))

vi.mock('vue-router', () => ({ useRouter: () => mocks.router }))
vi.mock('@/api/request', () => ({ default: mocks.request }))
vi.mock('@/stores/user', () => ({ useUserStore: () => mocks.userStore }))
vi.mock('@/composables/useStructuredLog', async () => {
  const actual = await vi.importActual('@/composables/useStructuredLog')
  return { ...actual, logUiEvent: mocks.logUiEvent }
})

import LegalView from '@/views/legal/index.vue'

const mountLegal = () => mount(LegalView, {
  global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } }
})

describe('法律、隐私与数据权利页', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('访客可直接阅读六个稳定锚点，情侣数据明确确认解绑后保留 30 天', () => {
    const wrapper = mountLegal()
    const anchors = ['privacy', 'terms', 'third-party', 'export', 'deletion', 'couple-data']

    expect(anchors.every(id => wrapper.find(`#${id}`).exists())).toBe(true)
    expect(wrapper.find('#couple-data').text()).toContain('确认解绑')
    expect(wrapper.find('#couple-data').text()).toContain('30 天')
    expect(wrapper.text()).not.toContain('立即删除')
    expect(wrapper.text()).not.toContain('永久删除')
  })

  it('导出确认取消回到 idle，不产生网络、下载或存储副作用', async () => {
    localStorage.setItem('token', 'local-session')
    const originalCreateObjectUrl = URL.createObjectURL
    URL.createObjectURL = vi.fn()
    const before = localStorage.getItem('token')
    const wrapper = mountLegal()

    await wrapper.find('[data-test="export-action"]').trigger('click')
    expect(wrapper.find('[data-test="export-confirming"]').exists()).toBe(true)
    await wrapper.find('[data-test="export-cancel"]').trigger('click')

    expect(wrapper.find('[data-test="export-confirming"]').exists()).toBe(false)
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    expect(localStorage.getItem('token')).toBe(before)
    expect(mocks.logUiEvent).toHaveBeenCalledWith('legal.export', expect.objectContaining({ result: 'cancelled' }))
    URL.createObjectURL = originalCreateObjectUrl
  })

  it('已登录确认导出后固定 unavailable，零下载且不伪造进度或成功', async () => {
    localStorage.setItem('token', 'local-session')
    const wrapper = mountLegal()

    await wrapper.find('[data-test="export-action"]').trigger('click')
    await wrapper.find('[data-test="export-confirm"]').trigger('click')

    expect(wrapper.find('[data-test="export-unavailable"]').text()).toContain('暂未提供数据导出接口')
    expect(wrapper.text()).not.toContain('导出成功')
    expect(wrapper.text()).not.toContain('预计完成')
    expect(localStorage.getItem('token')).toBe('local-session')
  })

  it('访客确认个人数据动作进入 unauthorized 并提供登录引导', async () => {
    const wrapper = mountLegal()

    await wrapper.find('[data-test="export-action"]').trigger('click')
    await wrapper.find('[data-test="export-confirm"]').trigger('click')

    expect(wrapper.find('[data-test="export-unauthorized"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('登录后检查此数据权利入口')
    expect(mocks.logUiEvent).toHaveBeenCalledWith('legal.export', expect.objectContaining({ result: 'unauthorized' }))
  })

  it('账号删除状态机独立且确认后 unavailable，绝不调用 logout 或清会话', async () => {
    localStorage.setItem('token', 'local-session')
    localStorage.setItem('userInfo', JSON.stringify({ nickName: '本地用户' }))
    const snapshot = {
      token: localStorage.getItem('token'),
      userInfo: localStorage.getItem('userInfo')
    }
    const wrapper = mountLegal()

    await wrapper.find('[data-test="deletion-action"]').trigger('click')
    await wrapper.find('[data-test="deletion-confirm"]').trigger('click')

    expect(wrapper.find('[data-test="deletion-unavailable"]').text()).toContain('暂未提供账号删除接口')
    expect(wrapper.text()).not.toContain('删除成功')
    expect(wrapper.text()).not.toContain('申请已提交')
    expect(localStorage.getItem('token')).toBe(snapshot.token)
    expect(localStorage.getItem('userInfo')).toBe(snapshot.userInfo)
    expect(mocks.userStore.logout).not.toHaveBeenCalled()
    expect(Object.values(mocks.request).every(method => method.mock.calls.length === 0)).toBe(true)
  })

  it('导出与删号完整交互保持零网络，并从开始检查累计日志耗时', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-25T10:00:00Z'))
    localStorage.setItem('token', 'local-session')
    const wrapper = mountLegal()

    await wrapper.find('[data-test="export-action"]').trigger('click')
    vi.advanceTimersByTime(240)
    await wrapper.find('[data-test="export-confirm"]').trigger('click')
    await wrapper.find('[data-test="deletion-action"]').trigger('click')
    vi.advanceTimersByTime(360)
    await wrapper.find('[data-test="deletion-confirm"]').trigger('click')

    expect(Object.values(mocks.request).every(method => method.mock.calls.length === 0)).toBe(true)
    expect(mocks.userStore.logout).not.toHaveBeenCalled()
    expect(mocks.logUiEvent).toHaveBeenCalledWith(
      'legal.export',
      expect.objectContaining({ result: 'unavailable', durationMs: 240 })
    )
    expect(mocks.logUiEvent).toHaveBeenCalledWith(
      'legal.account.deletion',
      expect.objectContaining({ result: 'unavailable', durationMs: 360 })
    )
    vi.useRealTimers()
  })

  it('不保留 Stitch 的原型状态切换器', () => {
    const wrapper = mountLegal()

    expect(wrapper.find('#state-controls').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Normal')
    expect(wrapper.text()).not.toContain('Loading')
  })
})
