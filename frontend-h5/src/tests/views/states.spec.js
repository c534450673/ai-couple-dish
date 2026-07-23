import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StatesView from '@/views/states/index.vue'

describe('非生产系统状态总览', () => {
  it('同时展示真实组件的加载、空、错误、未授权、未绑定和不可用状态', () => {
    const wrapper = mount(StatesView)

    expect(wrapper.text()).toContain('加载')
    expect(wrapper.text()).toContain('空数据')
    expect(wrapper.text()).toContain('网络错误')
    expect(wrapper.text()).toContain('未授权')
    expect(wrapper.text()).toContain('未绑定')
    expect(wrapper.text()).toContain('能力不可用')
    expect(wrapper.text()).not.toContain('实时同步')
  })
})
