import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  request: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  },
  router: { push: vi.fn(), replace: vi.fn() },
  userStore: {
    token: 'local-session',
    userInfo: null,
    coupleInfo: { id: 17, partnerName: 'TA' },
    fetchUserInfo: vi.fn(),
    updateUserInfo: vi.fn(),
    getCoupleInfo: vi.fn(),
    logout: vi.fn()
  },
  confirm: vi.fn(),
  toast: vi.fn(),
  logUiEvent: vi.fn()
}))

vi.mock('@/api/request', () => ({ default: mocks.request }))
vi.mock('vue-router', () => ({ useRouter: () => mocks.router }))
vi.mock('@/stores/user', () => ({ useUserStore: () => mocks.userStore }))
vi.mock('vant', () => ({
  showConfirmDialog: mocks.confirm,
  showToast: mocks.toast
}))
vi.mock('@/composables/useStructuredLog', async () => {
  const actual = await vi.importActual('@/composables/useStructuredLog')
  return { ...actual, logUiEvent: mocks.logUiEvent }
})

import SettingsView from '@/views/settings/index.vue'
import { uploadApi, userApi } from '@/api'
import { useThemeStore } from '@/stores/theme'

const flush = () => new Promise(resolve => setTimeout(resolve, 0))
const profile = {
  id: 42,
  nickName: '星河',
  avatarUrl: '/avatar.webp',
  memberLevel: 1,
  phone: '13800138000'
}

const mountSettings = () => mount(SettingsView, {
  global: {
    stubs: {
      RouterLink: { template: '<a><slot /></a>' },
      AsyncState: false
    }
  }
})

describe('Couple Cosmos 设置页', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.userStore.token = 'local-session'
    mocks.userStore.userInfo = null
    mocks.userStore.coupleInfo = { id: 17, partnerName: 'TA' }
    mocks.userStore.fetchUserInfo.mockResolvedValue({ data: profile })
    mocks.userStore.updateUserInfo.mockResolvedValue({ data: null })
    mocks.userStore.getCoupleInfo.mockResolvedValue({ status: 'success' })
    mocks.userStore.logout.mockResolvedValue(undefined)
    mocks.confirm.mockResolvedValue(undefined)
    mocks.request.put.mockResolvedValue({ data: null })
    mocks.request.post.mockResolvedValue({ data: null })
  })

  it('资料 API 只发送一次 JSON body，不拆为 query', async () => {
    const body = { nickName: '新名字', avatarUrl: '/new-avatar.webp' }

    await userApi.updateUserInfo(body)

    expect(mocks.request.put).toHaveBeenCalledOnce()
    expect(mocks.request.put).toHaveBeenCalledWith('/user/update', body, {
      retryConfig: { retries: 0 }
    })
  })

  it('资料保存单飞且只由 Store 提交昵称和头像，失败保留编辑输入', async () => {
    mocks.userStore.updateUserInfo.mockRejectedValueOnce({ code: 500 })
    const wrapper = mountSettings()
    await flush()
    await wrapper.find('[data-test="profile-edit"]').trigger('click')
    await wrapper.find('[data-test="nickname-input"]').setValue('保留的名字')
    await wrapper.find('[data-test="profile-save"]').trigger('click')
    await flush()

    expect(mocks.userStore.updateUserInfo).toHaveBeenCalledOnce()
    expect(mocks.userStore.updateUserInfo).toHaveBeenCalledWith({
      nickName: '保留的名字',
      avatarUrl: '/avatar.webp'
    })
    expect(wrapper.find('[data-test="nickname-input"]').element.value).toBe('保留的名字')
    expect(wrapper.find('[data-test="profile-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="profile-save"]').attributes('disabled')).toBeUndefined()
  })

  it('头像上传固定使用 file 字段，上传完成仍等待资料保存', async () => {
    const image = new File(['image'], 'avatar.png', { type: 'image/png' })
    mocks.request.post.mockResolvedValue({ data: { url: '/uploaded.webp' } })

    await uploadApi.uploadImage(image)

    const [, formData] = mocks.request.post.mock.calls[0]
    expect(mocks.request.post.mock.calls[0][0]).toBe('/upload/image')
    expect(formData).toBeInstanceOf(FormData)
    expect(formData.get('file')).toBe(image)
    expect(mocks.userStore.updateUserInfo).not.toHaveBeenCalled()
  })

  it('旧 cream 和未知主题迁移为 cosmos，主题值域不会返回旧主题', () => {
    localStorage.setItem('couple-cosmos:theme', 'cream')
    const store = useThemeStore()

    store.initializeTheme()
    expect(store.theme).toBe('cosmos')
    expect(localStorage.getItem('couple-cosmos:theme')).toBe('cosmos')

    store.setTheme('system-contrast')
    expect(store.theme).toBe('system-contrast')
    store.setTheme('unknown')
    expect(store.theme).toBe('cosmos')
  })

  it('通知偏好只写本机专用 key，不发网络请求', async () => {
    const wrapper = mountSettings()
    await flush()
    await wrapper.find('[data-test="notification-preference"]').setValue(false)

    expect(localStorage.getItem('couple-cosmos:notification-display')).toBe('disabled')
    expect(mocks.request.post).not.toHaveBeenCalled()
    expect(mocks.request.put).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('仅影响本机显示')
  })

  it('解绑不传 coupleId 或删除 option，成功只显示待对方处理并刷新真实状态', async () => {
    const wrapper = mountSettings()
    await flush()
    await wrapper.find('[data-test="unbind-action"]').trigger('click')
    await flush()

    expect(mocks.request.post).toHaveBeenCalledWith('/couple/unbind/apply', {})
    expect(mocks.request.post.mock.calls.flat().join(' ')).not.toContain('delete')
    expect(mocks.userStore.getCoupleInfo).toHaveBeenCalledOnce()
    expect(mocks.toast).toHaveBeenCalledWith(expect.stringContaining('等待对方处理'))
    expect(mocks.userStore.coupleInfo).not.toBeNull()
  })

  it('解绑申请成功但状态刷新失败时保留旧快照并暴露未确认状态', async () => {
    mocks.userStore.getCoupleInfo.mockResolvedValueOnce({ status: 'error', errorCode: '503' })
    const wrapper = mountSettings()
    await flush()

    await wrapper.find('[data-test="unbind-action"]').trigger('click')
    await flush()

    expect(mocks.request.post).toHaveBeenCalledWith('/couple/unbind/apply', {})
    expect(wrapper.find('[data-test="unbind-refresh-warning"]').text()).toContain('保留原关系信息')
    expect(wrapper.find('[data-test="unbind-unbound"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('已绑定')
    expect(mocks.toast).not.toHaveBeenCalledWith(expect.stringContaining('已解绑'))
    expect(mocks.logUiEvent).toHaveBeenCalledWith(
      'settings.couple.unbind.apply',
      expect.objectContaining({ result: 'refresh_error', errorCode: '503' })
    )
  })

  it('未绑定时进入 unbound 状态且不发解绑请求', async () => {
    mocks.userStore.coupleInfo = null
    const wrapper = mountSettings()
    await flush()
    await wrapper.find('[data-test="unbind-action"]').trigger('click')

    expect(wrapper.find('[data-test="unbind-unbound"]').exists()).toBe(true)
    expect(mocks.request.post).not.toHaveBeenCalled()
  })

  it('退出只承诺本机清理边界，并且只跳转一次', async () => {
    const wrapper = mountSettings()
    await flush()
    expect(wrapper.text()).toContain('仅退出当前设备上的本地会话')

    await wrapper.find('[data-test="logout-action"]').trigger('click')
    await flush()

    expect(mocks.userStore.logout).toHaveBeenCalledOnce()
    expect(mocks.router.replace).toHaveBeenCalledOnce()
    expect(mocks.router.replace).toHaveBeenCalledWith('/login')
    expect(wrapper.text()).not.toContain('已退出所有设备')
    expect(wrapper.text()).not.toContain('令牌已吊销')
  })

  it('会员只读展示且升级入口 unavailable，不模拟支付或等级变更', async () => {
    const wrapper = mountSettings()
    await flush()

    expect(wrapper.find('[data-test="member-level"]').text()).toContain('黄金')
    await wrapper.find('[data-test="member-action"]').trigger('click')
    expect(wrapper.find('[data-test="member-unavailable"]').exists()).toBe(true)
    expect(mocks.request.post).not.toHaveBeenCalled()
    expect(mocks.userStore.userInfo).toBeNull()
  })

  it('六个法律与数据权利入口都指向统一 legal anchor', async () => {
    const wrapper = mountSettings()
    await flush()
    const hrefs = wrapper.findAll('[data-test="legal-link"]').map(link => link.attributes('to'))

    expect(hrefs).toEqual([
      '/legal#privacy', '/legal#terms', '/legal#third-party',
      '/legal#export', '/legal#deletion', '/legal#couple-data'
    ])
  })

  it('资料读取 unauthorized 时进入登录流程，不展示缓存资料', async () => {
    mocks.userStore.userInfo = { nickName: '缓存昵称' }
    mocks.userStore.fetchUserInfo.mockRejectedValue({ code: 401 })
    const wrapper = mountSettings()
    await flush()

    expect(wrapper.find('[data-test="settings-unauthorized"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('缓存昵称')
    expect(mocks.router.replace).toHaveBeenCalledWith('/login')
  })
})
