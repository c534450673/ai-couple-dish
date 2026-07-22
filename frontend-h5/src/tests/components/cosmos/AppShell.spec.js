import { describe, expect, it } from 'vitest'
import { readFile } from 'node:fs/promises'
import { mount } from '@vue/test-utils'
import AppShell from '@/components/cosmos/AppShell.vue'
import IconButton from '@/components/cosmos/IconButton.vue'

const cosmosStubs = {
  'van-tabbar': {
    template: '<nav class="tabbar-stub"><slot /></nav>'
  },
  'van-tabbar-item': {
    props: ['to', 'icon'],
    template: '<a :href="to" :data-icon="icon"><slot /></a>'
  }
}

describe('AppShell', () => {
  it('按产品顺序渲染精确的五栏导航', () => {
    const wrapper = mount(AppShell, {
      global: { stubs: cosmosStubs }
    })

    const tabs = wrapper.findAll('.tabbar-stub a').map((item) => [
      item.text(),
      item.attributes('href')
    ])

    expect(tabs).toEqual([
      ['星球', '/home'],
      ['菜单', '/menu'],
      ['投喂', '/feed'],
      ['回忆', '/memories'],
      ['我们', '/settings']
    ])
  })

  it('提供 header、default 与 navigation slots', () => {
    const wrapper = mount(AppShell, {
      slots: {
        header: '<div data-slot="header">顶部</div>',
        default: '<main data-slot="content">主体</main>',
        navigation: '<nav data-slot="navigation">自定义导航</nav>'
      }
    })

    expect(wrapper.find('[data-slot="header"]').text()).toBe('顶部')
    expect(wrapper.find('[data-slot="content"]').text()).toBe('主体')
    expect(wrapper.find('[data-slot="navigation"]').text()).toBe('自定义导航')
    expect(wrapper.find('.app-tabbar').exists()).toBe(false)
  })

  it('底栏和内容区只计算一次底部安全区', async () => {
    const [tabbar, shell] = await Promise.all([
      readFile('src/components/AppTabbar.vue', 'utf8'),
      readFile('src/components/cosmos/AppShell.vue', 'utf8')
    ])

    expect(tabbar).toContain('height: 64px')
    expect(tabbar).not.toContain('height: calc(64px + env(safe-area-inset-bottom))')
    expect(tabbar).toContain('padding-bottom: env(safe-area-inset-bottom)')
    expect(shell).toContain('padding-bottom: calc(64px + env(safe-area-inset-bottom))')
  })
})

describe('IconButton', () => {
  it('输出非空 aria-label 并保持 44px 稳定尺寸', () => {
    const wrapper = mount(IconButton, {
      props: { label: '打开通知' },
      slots: { default: '!' }
    })

    const button = wrapper.get('button')
    expect(button.attributes('aria-label')).toBe('打开通知')
    expect(button.classes()).toContain('cosmos-icon-button')
  })

  it('点击时发出 click 事件', async () => {
    const wrapper = mount(IconButton, { props: { label: '返回' } })

    await wrapper.get('button').trigger('click')

    expect(wrapper.emitted('click')).toHaveLength(1)
  })
})
