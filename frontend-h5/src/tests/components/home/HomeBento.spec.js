import { describe, expect, it } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import HomeBento from '@/components/home/HomeBento.vue'

const mountBento = props => mount(HomeBento, {
  props,
  slots: { default: '<strong data-test="slot-content">最长业务文案保持稳定</strong>' },
  global: { stubs: { RouterLink: RouterLinkStub, 'van-icon': { template: '<i />' } } }
})

describe('HomeBento', () => {
  it('整卡使用精确 router-link 并承载成功内容', () => {
    const wrapper = mountBento({
      resourceKey: 'recipe', title: '双方已发布菜谱', to: '/recipes', icon: 'orders-o',
      resource: { status: 'success', data: { total: 12 } }
    })

    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/recipes')
    expect(wrapper.find('[data-test="slot-content"]').exists()).toBe(true)
  })

  it('error 提供独立 button 重试，empty 与 unavailable 文案可区分', async () => {
    const errorWrapper = mountBento({
      resourceKey: 'recipe', title: '双方已发布菜谱', to: '/recipes', icon: 'orders-o',
      resource: { status: 'error', data: null }
    })
    await errorWrapper.find('[data-test="retry-recipe"]').trigger('click')
    expect(errorWrapper.emitted('retry')).toHaveLength(1)

    const emptyWrapper = mountBento({
      resourceKey: 'wish', title: '心愿', to: '/memories', icon: 'like-o',
      resource: { status: 'empty', data: null }
    })
    expect(emptyWrapper.find('[data-test="wish-state"]').text()).toContain('暂无数据')

    const unavailableWrapper = mountBento({
      resourceKey: 'footprint', title: '餐厅地图', to: '/map', icon: 'location-o',
      resource: { status: 'unavailable', data: null }, unavailableText: '不提供到访记录，可打开地图'
    })
    expect(unavailableWrapper.find('[data-test="footprint-state"]').text()).toContain('不提供到访记录')
  })
})
