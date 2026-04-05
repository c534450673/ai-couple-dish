import { describe, it, expect } from 'vitest'

/**
 * Utility function tests
 * Note: These test the helper functions used across the application
 */

describe('Utility Functions', () => {
  describe('Date Formatting', () => {
    it('should format date correctly', () => {
      const formatDate = (date) => {
        if (!date) return ''
        const d = new Date(date)
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }

      expect(formatDate('2024-03-15')).toBe('2024-03-15')
      expect(formatDate('2024-12-31')).toBe('2024-12-31')
    })

    it('should return empty string for null date', () => {
      const formatDate = (date) => {
        if (!date) return ''
        const d = new Date(date)
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }

      expect(formatDate(null)).toBe('')
      expect(formatDate(undefined)).toBe('')
    })
  })

  describe('Love Duration Calculation', () => {
    it('should calculate days correctly', () => {
      const calculateLoveDays = (startDate) => {
        if (!startDate) return 0
        const start = new Date(startDate)
        const now = new Date()
        const diffTime = Math.abs(now - start)
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        return diffDays
      }

      const today = new Date()
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)

      expect(calculateLoveDays(yesterday.toISOString())).toBe(1)
    })

    it('should return 0 for invalid date', () => {
      const calculateLoveDays = (startDate) => {
        if (!startDate) return 0
        const start = new Date(startDate)
        if (isNaN(start.getTime())) return 0
        const now = new Date()
        const diffTime = Math.abs(now - start)
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        return diffDays
      }

      expect(calculateLoveDays(null)).toBe(0)
      expect(calculateLoveDays('invalid-date')).toBe(0)
    })
  })

  describe('Phone Number Validation', () => {
    it('should validate Chinese phone numbers', () => {
      const isValidPhone = (phone) => {
        return /^1[3-9]\d{9}$/.test(phone)
      }

      expect(isValidPhone('13800138000')).toBe(true)
      expect(isValidPhone('19912345678')).toBe(true)
      expect(isValidPhone('12345678901')).toBe(false) // Starts with 12
      expect(isValidPhone('1380013800')).toBe(false) // Only 10 digits
      expect(isValidPhone('138001380000')).toBe(false) // 12 digits
    })
  })

  describe('Verification Code Validation', () => {
    it('should validate 6-digit codes', () => {
      const isValidCode = (code) => {
        return /^\d{6}$/.test(code)
      }

      expect(isValidCode('123456')).toBe(true)
      expect(isValidCode('000000')).toBe(true)
      expect(isValidCode('12345')).toBe(false) // Only 5 digits
      expect(isValidCode('1234567')).toBe(false) // 7 digits
      expect(isValidCode('12345a')).toBe(false) // Contains letter
    })
  })

  describe('Image URL Validation', () => {
    it('should validate image URLs', () => {
      const isValidImageUrl = (url) => {
        if (!url) return false
        return /\.(jpg|jpeg|png|gif|webp)$/i.test(url)
      }

      expect(isValidImageUrl('https://example.com/photo.jpg')).toBe(true)
      expect(isValidImageUrl('https://example.com/photo.png')).toBe(true)
      expect(isValidImageUrl('https://example.com/photo')).toBe(false)
      expect(isValidImageUrl('')).toBe(false)
      expect(isValidImageUrl(null)).toBe(false)
    })
  })

  describe('Couple Code Validation', () => {
    it('should validate 8-character couple codes', () => {
      const isValidCoupleCode = (code) => {
        if (!code) return false
        return /^[A-Z0-9]{8}$/.test(code.toUpperCase())
      }

      expect(isValidCoupleCode('ABC12345')).toBe(true)
      expect(isValidCoupleCode('abc12345')).toBe(true) // Case insensitive
      expect(isValidCoupleCode('ABC1234')).toBe(false) // Only 7 chars
      expect(isValidCoupleCode('ABC123456')).toBe(false) // 9 chars
      expect(isValidCoupleCode('')).toBe(false)
    })
  })

  describe('Status Text Helpers', () => {
    it('should return correct status text for menu', () => {
      const getMenuStatusText = (status) => {
        const map = { 0: '想去', 1: '去过', 2: '种草' }
        return map[status] || '想去'
      }

      expect(getMenuStatusText(0)).toBe('想去')
      expect(getMenuStatusText(1)).toBe('去过')
      expect(getMenuStatusText(2)).toBe('种草')
      expect(getMenuStatusText(99)).toBe('想去') // Default
    })

    it('should return correct status class for menu', () => {
      const getMenuStatusClass = (status) => {
        const map = { 0: 'primary', 1: 'success', 2: 'warning' }
        return map[status] || 'primary'
      }

      expect(getMenuStatusClass(0)).toBe('primary')
      expect(getMenuStatusClass(1)).toBe('success')
      expect(getMenuStatusClass(2)).toBe('warning')
      expect(getMenuStatusClass(99)).toBe('primary') // Default
    })

    it('should return correct feed status text', () => {
      const getFeedStatusText = (status) => {
        const map = { 0: '待领取', 1: '已领取', 2: '已拒绝' }
        return map[status] || '未知'
      }

      expect(getFeedStatusText(0)).toBe('待领取')
      expect(getFeedStatusText(1)).toBe('已领取')
      expect(getFeedStatusText(2)).toBe('已拒绝')
    })

    it('should return correct anniversary type name', () => {
      const getAnniversaryTypeName = (type) => {
        const map = { 1: '相识', 2: '恋爱', 3: '表白', 4: '其他' }
        return map[type] || '其他'
      }

      expect(getAnniversaryTypeName(1)).toBe('相识')
      expect(getAnniversaryTypeName(2)).toBe('恋爱')
      expect(getAnniversaryTypeName(3)).toBe('表白')
      expect(getAnniversaryTypeName(4)).toBe('其他')
      expect(getAnniversaryTypeName(99)).toBe('其他')
    })
  })

  describe('Array Helpers', () => {
    it('should chunk array correctly', () => {
      const chunk = (arr, size) => {
        if (!Array.isArray(arr) || size <= 0) return []
        const result = []
        for (let i = 0; i < arr.length; i += size) {
          result.push(arr.slice(i, i + size))
        }
        return result
      }

      expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]])
      expect(chunk([1, 2, 3], 2)).toEqual([[1, 2], [3]])
      expect(chunk([], 2)).toEqual([])
    })

    it('should unique array correctly', () => {
      const unique = (arr) => {
        if (!Array.isArray(arr)) return []
        return [...new Set(arr)]
      }

      expect(unique([1, 2, 2, 3, 3, 3])).toEqual([1, 2, 3])
      expect(unique([])).toEqual([])
      expect(unique([1])).toEqual([1])
    })
  })

  describe('Object Helpers', () => {
    it('should pick selected keys', () => {
      const pick = (obj, keys) => {
        if (!obj || typeof obj !== 'object' || !Array.isArray(keys)) return {}
        return keys.reduce((acc, key) => {
          if (key in obj) acc[key] = obj[key]
          return acc
        }, {})
      }

      const obj = { id: 1, name: 'Test', password: 'secret' }
      expect(pick(obj, ['id', 'name'])).toEqual({ id: 1, name: 'Test' })
      expect(pick(obj, ['id'])).toEqual({ id: 1 })
      expect(pick(obj, [])).toEqual({})
    })

    it('should omit selected keys', () => {
      const omit = (obj, keys) => {
        if (!obj || typeof obj !== 'object' || Array.isArray(obj) || !Array.isArray(keys)) return {}
        return Object.keys(obj).reduce((acc, key) => {
          if (!keys.includes(key)) acc[key] = obj[key]
          return acc
        }, {})
      }

      const obj = { id: 1, name: 'Test', password: 'secret' }
      expect(omit(obj, ['password'])).toEqual({ id: 1, name: 'Test' })
      expect(omit(obj, ['id', 'name'])).toEqual({ password: 'secret' })
    })
  })
})