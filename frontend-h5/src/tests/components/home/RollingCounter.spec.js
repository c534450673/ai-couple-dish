import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import RollingCounter from '@/components/home/RollingCounter.vue'

describe('RollingCounter', () => {
  afterEach(() => vi.useRealTimers())

  it('reduced motion 直接呈现格式化最终值', () => {
    const wrapper = mount(RollingCounter, { props: { value: 1314, reducedMotion: true } })
    expect(wrapper.text()).toBe('1,314')
    expect(wrapper.attributes('data-motion')).toBe('static')
  })

  it('普通动效最终收敛且卸载清理 timer', async () => {
    vi.useFakeTimers()
    const wrapper = mount(RollingCounter, { props: { value: 88, reducedMotion: false } })
    await vi.runAllTimersAsync()
    expect(wrapper.text()).toBe('88')
    wrapper.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
})
