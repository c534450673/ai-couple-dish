/**
 * 日期工具函数单元测试
 */
import { describe, it, expect } from 'vitest'
import dayjs from 'dayjs'

describe('日期工具函数测试', () => {
  describe('dayjs 基础功能', () => {
    it('应该正确格式化日期', () => {
      const date = dayjs('2024-01-15')
      expect(date.format('YYYY-MM-DD')).toBe('2024-01-15')
      expect(date.format('YYYY年MM月DD日')).toBe('2024年01月15日')
      expect(date.format('MM/DD/YYYY')).toBe('01/15/2024')
    })

    it('应该正确计算日期差', () => {
      const date1 = dayjs('2024-01-01')
      const date2 = dayjs('2024-01-31')
      expect(date2.diff(date1, 'day')).toBe(30)
    })

    it('应该正确计算恋爱天数', () => {
      const loveStartDate = dayjs('2024-01-01')
      const today = dayjs('2024-03-23')
      const loveDays = today.diff(loveStartDate, 'day') + 1
      expect(loveDays).toBe(83)
    })

    it('应该正确计算相识天数', () => {
      const meetDate = dayjs('2023-06-01')
      const today = dayjs('2024-03-23')
      const days = today.diff(meetDate, 'day') + 1
      expect(days).toBeGreaterThan(0)
    })
  })

  describe('纪念日计算', () => {
    it('应该正确计算下一个周年纪念日', () => {
      const anniversaryDate = dayjs('2024-01-01')
      const today = dayjs('2026-03-23')

      let nextAnniversary = anniversaryDate
      while (nextAnniversary.isBefore(today) || nextAnniversary.isSame(today)) {
        nextAnniversary = nextAnniversary.add(1, 'year')
      }

      expect(nextAnniversary.format('YYYY-MM-DD')).toBe('2027-01-01')
    })

    it('应该正确计算距离纪念日天数', () => {
      const today = dayjs('2026-03-23')
      const nextAnniversary = dayjs('2026-06-01')
      const daysUntil = nextAnniversary.diff(today, 'day')

      expect(daysUntil).toBe(70)
    })

    it('应该正确判断是否是今天', () => {
      const today = dayjs()
      const todayStr = today.format('YYYY-MM-DD')
      const todayFormatted = dayjs(todayStr)

      expect(todayFormatted.isSame(dayjs(), 'day')).toBe(true)
    })

    it('应该正确判断是否已过纪念日', () => {
      const anniversaryDate = dayjs('2024-01-01')
      const today = dayjs('2026-03-23')

      expect(anniversaryDate.isBefore(today)).toBe(true)
    })
  })

  describe('时间戳转换', () => {
    it('应该正确转换时间戳到日期', () => {
      const timestamp = 1711209600000 // 2024-03-24 00:00:00
      const date = dayjs(timestamp)
      expect(date.format('YYYY-MM-DD')).toBe('2024-03-24')
    })

    it('应该正确转换日期到时间戳', () => {
      const date = dayjs('2024-03-24')
      const timestamp = date.valueOf()
      expect(timestamp).toBe(1711209600000)
    })

    it('应该正确获取相对时间', () => {
      const now = dayjs()
      const fiveMinutesAgo = now.subtract(5, 'minute')
      const diffMinutes = now.diff(fiveMinutesAgo, 'minute')
      expect(diffMinutes).toBe(5)
    })
  })

  describe('日期验证', () => {
    it('应该验证有效日期格式', () => {
      const validDate = dayjs('2024-03-23')
      expect(validDate.isValid()).toBe(true)
    })

    it('应该识别无效日期', () => {
      const invalidDate = dayjs('invalid-date')
      expect(invalidDate.isValid()).toBe(false)
    })

    it('应该正确验证手机号格式', () => {
      const phoneRegex = /^1[3-9]\d{9}$/
      expect(phoneRegex.test('13800138000')).toBe(true)
      expect(phoneRegex.test('1380013800')).toBe(false)
      expect(phoneRegex.test('12345678901')).toBe(false)
    })
  })

  describe('恋爱计时器', () => {
    it('应该正确计算完整的恋爱时间', () => {
      const loveStartDate = dayjs('2024-01-01')
      const today = dayjs('2026-03-23')

      const years = today.diff(loveStartDate, 'year')
      const remainingDays = today.diff(loveStartDate.add(years, 'year'), 'day')

      expect(years).toBe(2)
      expect(remainingDays).toBeGreaterThanOrEqual(0)
    })

    it('应该正确计算百日纪念', () => {
      const loveStartDate = dayjs('2024-01-01')
      const hundredDay = loveStartDate.add(99, 'day')

      expect(hundredDay.format('YYYY-MM-DD')).toBe('2024-04-09')
    })

    it('应该正确计算一周年日期', () => {
      const loveStartDate = dayjs('2024-01-01')
      const oneYear = loveStartDate.add(1, 'year').subtract(1, 'day')

      expect(oneYear.format('YYYY-MM-DD')).toBe('2024-12-31')
    })
  })
})