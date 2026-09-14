import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginIndex from '@/views/login/index.vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = vi.hoisted(() => ({
  loginByPhone: vi.fn(), registerByPhone: vi.fn(), sendVerifyCode: vi.fn(), userInfo: { id: 1 }
}))
const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
  resolve: vi.fn(() => ({ matched: [{ name: 'Home' }] }))
}))
vi.mock('@/stores/user', () => ({ useUserStore: vi.fn(() => userStore) }))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => routerMock),
  useRoute: vi.fn(() => ({ query: {} }))
}))

vi.mock('vant', () => ({ showToast: vi.fn() }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

const mountLogin = () => mount(LoginIndex, {
  global: { stubs: { AgreementDialog: true } }
})

describe('手机号认证页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('提供手机号验证码入口，不显示密码、微信或 Apple 登录', () => {
    const wrapper = mountLogin()

    expect(wrapper.text()).toContain('手机号')
    expect(wrapper.text()).toContain('验证码')
    expect(wrapper.text()).not.toContain('密码')
    expect(wrapper.text()).not.toContain('微信')
    expect(wrapper.text()).not.toContain('Apple')
  })

  it('在字段旁显示账号和密码校验错误', async () => {
    const wrapper = mountLogin()
    await wrapper.find('[data-test="auth-submit"]').trigger('click')

    expect(wrapper.find('[data-test="phone-error"]').text()).toBe('请输入正确的手机号')
    expect(wrapper.find('[data-test="verify-code-error"]').text()).toBe('请输入验证码')
  })

  it('发送验证码并完成手机号注册后跳转', async () => {
    const store = useUserStore()
    store.sendVerifyCode.mockResolvedValue({ data: { devCode: '123456' } })
    store.registerByPhone.mockResolvedValue({ data: { token: 'token' } })
    const wrapper = mountLogin()

    await wrapper.find('[role="tab"]:nth-child(2)').trigger('click')
    await wrapper.find('[data-test="phone-input"]').setValue('13800138000')
    await wrapper.find('[data-test="send-code"]').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(wrapper.find('[data-test="dev-code"]').text()).toContain('123456')
    await wrapper.find('[data-test="verify-code-input"]').setValue('123456')
    await wrapper.find('[data-test="agreement-input"]').setValue(true)
    await wrapper.find('[data-test="auth-submit"]').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(store.sendVerifyCode).toHaveBeenCalledWith('13800138000')
    expect(store.registerByPhone).toHaveBeenCalledWith('13800138000', '123456')
    expect(routerMock.push).toHaveBeenCalled()
  })
})
