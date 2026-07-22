import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginIndex from '@/views/login/index.vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const userStore = vi.hoisted(() => ({ login: vi.fn(), register: vi.fn() }))
vi.mock('@/stores/user', () => ({ useUserStore: vi.fn(() => userStore) }))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    resolve: vi.fn(() => ({ matched: [{ name: 'Home' }] }))
  })),
  useRoute: vi.fn(() => ({ query: {} }))
}))

vi.mock('vant', () => ({ showToast: vi.fn() }))
vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

const mountLogin = () => mount(LoginIndex, {
  global: { stubs: { AgreementDialog: true } }
})

describe('密码认证页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('只提供账号密码入口，不显示短信、微信或 Apple 登录', () => {
    const wrapper = mountLogin()

    expect(wrapper.text()).toContain('账号')
    expect(wrapper.text()).toContain('密码')
    expect(wrapper.text()).not.toContain('验证码')
    expect(wrapper.text()).not.toContain('微信')
    expect(wrapper.text()).not.toContain('Apple')
  })

  it('在字段旁显示账号和密码校验错误', async () => {
    const wrapper = mountLogin()
    await wrapper.find('[data-test="auth-submit"]').trigger('click')

    expect(wrapper.find('[data-test="account-error"]').text()).toBe('请输入账号')
    expect(wrapper.find('[data-test="password-error"]').text()).toBe('请输入密码')
  })

  it('密码能力未开放时不发请求、不写会话也不跳转', async () => {
    const store = useUserStore()
    const router = useRouter()
    store.login.mockResolvedValue({
      status: 'unavailable',
      reason: 'PASSWORD_AUTH_NOT_SUPPORTED'
    })
    const wrapper = mountLogin()

    await wrapper.find('[data-test="account-input"]').setValue('cosmos-user')
    await wrapper.find('[data-test="password-input"]').setValue('secret')
    await wrapper.find('[data-test="agreement-input"]').setValue(true)
    await wrapper.find('[data-test="auth-submit"]').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(store.login).toHaveBeenCalledWith({ account: 'cosmos-user', password: 'secret' })
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('userInfo')).toBeNull()
    expect(router.push).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="auth-unavailable"]').text()).toContain('密码登录/注册暂不可用')
  })
})
