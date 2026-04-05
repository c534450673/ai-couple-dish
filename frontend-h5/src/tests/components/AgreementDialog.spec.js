/**
 * AgreementDialog 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AgreementDialog from '@/components/AgreementDialog.vue'

describe('AgreementDialog 组件测试', () => {
  let wrapper

  const defaultProps = {
    show: false
  }

  const mountComponent = (props = {}) => {
    return mount(AgreementDialog, {
      props: {
        ...defaultProps,
        ...props
      },
      global: {
        mocks: {
          $t: (key) => key
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('组件渲染', () => {
    it('当 show 为 false 时不应该显示对话框', () => {
      wrapper = mountComponent({ show: false })
      const dialog = wrapper.find('.agreement-dialog')
      expect(dialog.exists()).toBe(false)
    })

    it('当 show 为 true 时应该显示对话框', () => {
      wrapper = mountComponent({ show: true })
      const dialog = wrapper.find('.agreement-dialog')
      expect(dialog.exists()).toBe(true)
    })
  })

  describe('协议切换', () => {
    it('默认应该显示用户协议', () => {
      wrapper = mountComponent({ show: true })
      expect(wrapper.vm.activeTab).toBe('user')
    })

    it('点击隐私政策tab应该切换内容', async () => {
      wrapper = mountComponent({ show: true })
      const privacyTab = wrapper.find('.tab-privacy')
      await privacyTab.trigger('click')
      expect(wrapper.vm.activeTab).toBe('privacy')
    })
  })

  describe('事件触发', () => {
    it('点击同意按钮应该触发 agree 事件', async () => {
      wrapper = mountComponent({ show: true })
      const agreeBtn = wrapper.find('.btn-agree')
      await agreeBtn.trigger('click')
      expect(wrapper.emitted('agree')).toBeTruthy()
    })

    it('点击拒绝按钮应该触发 disagree 事件', async () => {
      wrapper = mountComponent({ show: true })
      const disagreeBtn = wrapper.find('.btn-disagree')
      await disagreeBtn.trigger('click')
      expect(wrapper.emitted('disagree')).toBeTruthy()
    })
  })

  describe('内容显示', () => {
    it('应该显示用户协议内容', () => {
      wrapper = mountComponent({ show: true })
      const content = wrapper.find('.agreement-content')
      expect(content.text()).toContain('用户服务协议')
    })

    it('切换到隐私政策后应该显示隐私政策内容', async () => {
      wrapper = mountComponent({ show: true })
      await wrapper.setData({ activeTab: 'privacy' })
      const content = wrapper.find('.agreement-content')
      expect(content.text()).toContain('隐私政策')
    })
  })
})
