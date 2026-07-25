import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CoupleOrbit from '@/components/home/CoupleOrbit.vue'

const success = (data) => ({ status: 'success', data })

describe('CoupleOrbit', () => {
  afterEach(() => vi.useRealTimers())

  it('显示真实头像、伴侣昵称和唯一可信 loveDays，不出现在线状态', () => {
    const wrapper = mount(CoupleOrbit, {
      props: {
        currentAvatar: '/me.webp',
        couple: success({ partner: { nickName: '星河', avatarUrl: '/partner.webp' } }),
        timer: success({ loveDays: 1314 }),
        reducedMotion: true
      }
    })

    expect(wrapper.find('[data-test="current-avatar"]').attributes('src')).toBe('/me.webp')
    expect(wrapper.find('[data-test="partner-avatar"]').attributes('src')).toBe('/partner.webp')
    expect(wrapper.text()).toContain('星河')
    expect(wrapper.text()).toContain('1,314')
    expect(wrapper.text()).toContain('天')
    expect(wrapper.text()).not.toMatch(/在线|presence|最后上线/)
    expect(wrapper.attributes('data-motion')).toBe('static')
  })

  it('头像缺失使用本地中性占位，错误态不显示 0 天', () => {
    const wrapper = mount(CoupleOrbit, {
      props: {
        currentAvatar: '', couple: success({ partner: { nickName: 'TA', avatarUrl: '' } }),
        timer: { status: 'error', data: null }, reducedMotion: true
      }
    })

    expect(wrapper.find('[data-test="current-avatar"]').attributes('src')).toContain('partner-avatar.webp')
    expect(wrapper.find('[data-test="partner-avatar"]').attributes('src')).toContain('partner-avatar.webp')
    expect(wrapper.find('[data-test="timer-state"]').text()).not.toContain('0 天')
  })

  it('卸载后没有残留 timer', () => {
    vi.useFakeTimers()
    const wrapper = mount(CoupleOrbit, {
      props: {
        currentAvatar: '', couple: { status: 'loading', data: null },
        timer: success({ loveDays: 8 }), reducedMotion: false
      }
    })
    wrapper.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
})
