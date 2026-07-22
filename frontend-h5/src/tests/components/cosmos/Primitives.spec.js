import { effectScope } from 'vue'
import { readFile } from 'node:fs/promises'
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AppHeader from '@/components/cosmos/AppHeader.vue'
import CoupleGate from '@/components/cosmos/CoupleGate.vue'
import GlassCard from '@/components/cosmos/GlassCard.vue'
import MediaCard from '@/components/cosmos/MediaCard.vue'
import StatusChip from '@/components/cosmos/StatusChip.vue'
import { useReducedMotion } from '@/composables/useReducedMotion'

describe('Couple Cosmos 基础组件', () => {
  it('AppHeader 提供标题、副标题与操作区', () => {
    const wrapper = mount(AppHeader, {
      props: { title: '回忆', subtitle: '共同时间线' },
      slots: { actions: '<button>新建</button>' }
    })

    expect(wrapper.get('h1').text()).toBe('回忆')
    expect(wrapper.text()).toContain('共同时间线')
    expect(wrapper.get('button').text()).toBe('新建')
  })

  it('CoupleGate 绑定时渲染内容，未绑定时发出 bind', async () => {
    const bound = mount(CoupleGate, {
      props: { bound: true },
      slots: { default: '<div data-couple-content>共享内容</div>' }
    })
    expect(bound.get('[data-couple-content]').text()).toBe('共享内容')

    const unbound = mount(CoupleGate, { props: { bound: false } })
    await unbound.get('[data-action="bind"]').trigger('click')
    expect(unbound.emitted('bind')).toHaveLength(1)
  })

  it('卡片、媒体卡片与状态标签保留语义和内容', () => {
    const glass = mount(GlassCard, { slots: { default: '玻璃卡片' } })
    expect(glass.get('article').text()).toBe('玻璃卡片')

    const media = mount(MediaCard, {
      props: { src: '/dish.webp', alt: '番茄牛腩' },
      slots: { default: '晚餐记录' }
    })
    expect(media.get('img').attributes()).toMatchObject({ src: '/dish.webp', alt: '番茄牛腩' })
    expect(media.text()).toContain('晚餐记录')

    const chip = mount(StatusChip, {
      props: { tone: 'success' },
      slots: { default: '已同步' }
    })
    expect(chip.get('[role="status"]').classes()).toContain('status-chip--success')
  })

  it('主卡统一使用 24px 圆角且页面过渡使用 500ms 令牌', async () => {
    const [glassCard, mediaCard, app] = await Promise.all([
      readFile('src/components/cosmos/GlassCard.vue', 'utf8'),
      readFile('src/components/cosmos/MediaCard.vue', 'utf8'),
      readFile('src/App.vue', 'utf8')
    ])

    expect(glassCard).toContain('border-radius: $cosmos-card-radius')
    expect(mediaCard).toContain('border-radius: $cosmos-card-radius')
    expect(app).toContain('transition: opacity $cosmos-duration-slow')
  })
})

describe('useReducedMotion', () => {
  it('响应系统减少动态效果偏好并在作用域销毁时解绑', () => {
    let changeHandler
    const removeEventListener = vi.fn()
    const matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn((event, handler) => {
        changeHandler = handler
      }),
      removeEventListener
    }))
    vi.stubGlobal('matchMedia', matchMedia)
    const scope = effectScope()
    let reducedMotion

    scope.run(() => {
      reducedMotion = useReducedMotion()
    })
    expect(reducedMotion.value).toBe(true)

    changeHandler({ matches: false })
    expect(reducedMotion.value).toBe(false)
    scope.stop()
    expect(removeEventListener).toHaveBeenCalledWith('change', changeHandler)
    vi.unstubAllGlobals()
  })
})
