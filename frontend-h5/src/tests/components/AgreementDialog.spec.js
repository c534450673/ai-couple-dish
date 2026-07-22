/**
 * AgreementDialog 组件测试
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AgreementDialog from '@/components/AgreementDialog.vue'

const mountComponent = (props = {}) => mount(AgreementDialog, {
  props: {
    show: false,
    type: 'agreement',
    ...props
  },
  global: {
    stubs: {
      'van-dialog': {
        props: ['show', 'title'],
        template: '<section v-if="show" class="agreement-dialog"><h2>{{ title }}</h2><slot /></section>'
      }
    }
  }
})

describe('AgreementDialog 组件测试', () => {
  it('show 为 false 时不渲染协议内容', () => {
    expect(mountComponent().find('.agreement-dialog').exists()).toBe(false)
  })

  it('显示用户服务协议', () => {
    const wrapper = mountComponent({ show: true })

    expect(wrapper.find('.agreement-dialog').text()).toContain('用户服务协议')
    expect(wrapper.find('.agreement-content').text()).toContain('服务条款的确认和接纳')
  })

  it('显示隐私政策', () => {
    const wrapper = mountComponent({ show: true, type: 'privacy' })

    expect(wrapper.find('.agreement-dialog').text()).toContain('隐私政策')
    expect(wrapper.find('.agreement-content').text()).toContain('我们收集的信息')
  })
})
