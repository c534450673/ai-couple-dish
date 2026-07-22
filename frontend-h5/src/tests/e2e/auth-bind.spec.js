import { describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api'

vi.mock('@/api', () => ({
  userApi: { loginByPhone: vi.fn(), registerByPhone: vi.fn(), logout: vi.fn() },
  coupleApi: { getCoupleInfo: vi.fn() }
}))

describe('认证到绑定主链路', () => {
  it('密码登录和注册均在请求前返回固定不可用合同', async () => {
    setActivePinia(createPinia())
    const userStore = useUserStore()

    await expect(userStore.login({ account: 'cosmos-user', password: 'secret' })).resolves.toEqual({
      status: 'unavailable', reason: 'PASSWORD_AUTH_NOT_SUPPORTED'
    })
    await expect(userStore.register({ account: 'cosmos-user', password: 'secret' })).resolves.toEqual({
      status: 'unavailable', reason: 'PASSWORD_AUTH_NOT_SUPPORTED'
    })
    expect(userApi.loginByPhone).not.toHaveBeenCalled()
    expect(userApi.registerByPhone).not.toHaveBeenCalled()
    expect(localStorage.getItem('token')).toBeNull()
  })
})
