import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AsyncState from '@/components/cosmos/AsyncState.vue'

const stateCases = [
  ['loading', 'status', '正在加载'],
  ['empty', 'status', '暂无内容'],
  ['error', 'alert', '加载失败'],
  ['unauthorized', 'alert', '登录状态已失效'],
  ['unbound', 'status', '还没有绑定伴侣']
]

describe('AsyncState', () => {
  it.each(stateCases)('%s 只渲染一个明确的可访问状态', (status, role, text) => {
    const wrapper = mount(AsyncState, { props: { status } })

    expect(wrapper.findAll('[role="status"], [role="alert"]')).toHaveLength(1)
    expect(wrapper.get(`[role="${role}"]`).text()).toContain(text)
  })

  it('error 状态通过 retry 事件请求重试', async () => {
    const wrapper = mount(AsyncState, { props: { status: 'error' } })

    await wrapper.get('[data-action="retry"]').trigger('click')

    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('unbound 状态通过 bind 事件进入绑定流程', async () => {
    const wrapper = mount(AsyncState, { props: { status: 'unbound' } })

    await wrapper.get('[data-action="bind"]').trigger('click')

    expect(wrapper.emitted('bind')).toHaveLength(1)
  })

  it('success 状态只渲染业务内容', () => {
    const wrapper = mount(AsyncState, {
      props: { status: 'success' },
      slots: { default: '<article data-content>业务内容</article>' }
    })

    expect(wrapper.get('[data-content]').text()).toBe('业务内容')
    expect(wrapper.find('[role="status"], [role="alert"]').exists()).toBe(false)
  })
})
