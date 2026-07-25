import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MoodPulse from '@/components/home/MoodPulse.vue'

const success = data => ({ status: 'success', data })

const mountPulse = (props = {}) => mount(MoodPulse, {
  props: {
    resource: success([]),
    currentUserId: 7,
    reducedMotion: true,
    ...props
  }
})

describe('MoodPulse', () => {
  it('仅显示今天双方最新的安全心情摘要，不渲染描述或用户敏感信息', () => {
    const wrapper = mountPulse({
      resource: success([
        {
          id: 4,
          moodType: 'love',
          description: '我的私密描述',
          sender: { id: 7, nickName: '真实姓名甲', phone: '13800000000' }
        },
        {
          id: 3,
          moodType: 'happy',
          description: '更早的一条',
          sender: { id: 7 }
        },
        {
          id: 2,
          moodType: 'miss_you',
          description: '伴侣私密描述',
          sender: { id: 8, nickName: '真实姓名乙' }
        },
        {
          id: 1,
          moodType: 'sad',
          sender: { id: 8 }
        }
      ])
    })

    expect(wrapper.find('[data-test="mood-self"]').text()).toContain('爱你')
    expect(wrapper.find('[data-test="mood-partner"]').text()).toContain('想你')
    expect(wrapper.text()).not.toMatch(/私密描述|更早的一条|真实姓名|13800000000/)
    expect(wrapper.find('[data-test="mood-choice-love"]').attributes('aria-pressed')).toBe('true')
  })

  it('提供八个 44x44 emoji-only 快捷按钮并发出 send 类型', async () => {
    const wrapper = mountPulse()
    const choices = wrapper.findAll('.mood-pulse__choice')

    expect(choices).toHaveLength(8)
    for (const choice of choices) {
      expect(choice.attributes('aria-label')).toBeTruthy()
      expect(choice.attributes('title')).toBeTruthy()
      expect(choice.attributes('data-selected')).toBe('false')
      expect(choice.text()).toMatch(/^(😊|❤️|🥺|😴|😤|😢|😠|😰)$/u)
    }

    await wrapper.find('[data-test="mood-choice-happy"]').trigger('click')
    expect(wrapper.emitted('send')).toEqual([['happy']])
  })

  it('覆盖 loading、empty、error 和无参数 retry', async () => {
    expect(mountPulse({ resource: { status: 'loading', data: null } })
      .find('[data-test="mood-loading"]').exists()).toBe(true)
    expect(mountPulse({ resource: success([]) })
      .find('[data-test="mood-empty"]').text()).toContain('还没有心情记录')

    const errorWrapper = mountPulse({ resource: { status: 'error', data: null } })
    await errorWrapper.find('[data-test="retry-mood"]').trigger('click')
    expect(errorWrapper.emitted('retry')).toEqual([[]])
  })

  it('submitting 禁用重复发送，submit-error 可重试且 reduced-motion 关闭动画', async () => {
    const submittingWrapper = mountPulse({ submitting: true, reducedMotion: true })
    const button = submittingWrapper.find('[data-test="mood-choice-anxious"]')

    expect(submittingWrapper.attributes('data-motion')).toBe('static')
    expect(submittingWrapper.classes()).toContain('mood-pulse--reduced')
    expect(submittingWrapper.find('[data-test="mood-submitting"]').exists()).toBe(true)
    expect(button.attributes()).toHaveProperty('disabled')
    await button.trigger('click')
    expect(submittingWrapper.emitted('send')).toBeUndefined()

    const errorWrapper = mountPulse({ submitErrorCode: 9001 })
    expect(errorWrapper.find('[data-test="mood-submit-error"]').text()).toContain('发送失败')
    expect(errorWrapper.text()).not.toContain('9001')
  })
})
