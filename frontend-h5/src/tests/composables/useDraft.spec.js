import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/composables/useStructuredLog', () => ({ logUiEvent: vi.fn() }))

import { useDraft } from '@/composables/useDraft'

describe('useDraft', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem.mockClear()
  })

  it('使用精确 key 并隔离用户、资源与编辑 ID', () => {
    const draft = useDraft({ userId: 7, resource: 'recipe', resourceId: 9 })
    const other = useDraft({ userId: 7, resource: 'menu', resourceId: 9 })

    draft.save({ title: '本地草稿' })

    expect(localStorage.getItem('couple-cosmos:draft:7:recipe:9')).toBe(JSON.stringify({ title: '本地草稿' }))
    expect(other.restore()).toBeNull()
    expect(draft.restore()).toEqual({ title: '本地草稿' })
    expect(draft.hasDraft.value).toBe(true)
  })

  it('新建使用 new，成功清理只移除当前草稿', () => {
    const current = useDraft({ userId: 'user-1', resource: 'menu' })
    const retained = useDraft({ userId: 'user-1', resource: 'recipe' })
    current.save({ restaurantName: 'A' })
    retained.save({ title: 'B' })

    current.clear()

    expect(localStorage.getItem('couple-cosmos:draft:user-1:menu:new')).toBeNull()
    expect(retained.restore()).toEqual({ title: 'B' })
  })

  it.each([null, undefined, '', 0, '   '])('无效用户 ID %s 不落盘', (userId) => {
    const draft = useDraft({ userId, resource: 'recipe' })

    expect(draft.save({ title: '不可写入' })).toBe(false)
    expect(draft.restore()).toBeNull()
    expect(localStorage.setItem).not.toHaveBeenCalled()
  })

  it('拒绝未知资源与无效编辑 ID', () => {
    expect(() => useDraft({ userId: 1, resource: 'note' })).toThrow('resource')
    expect(() => useDraft({ userId: 1, resource: 'menu', resourceId: '../all' })).toThrow('resourceId')
    expect(() => useDraft({ userId: 1, resource: 'menu', resourceId: 0 })).toThrow('resourceId')
  })
})
