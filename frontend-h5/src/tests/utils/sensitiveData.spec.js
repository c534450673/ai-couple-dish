/**
 * 工具函数测试
 */
import { describe, it, expect } from 'vitest'

/**
 * 敏感数据处理工具函数
 */
const sensitiveData = {
  maskPhone: (phone) => {
    if (!phone || phone.length < 7) return phone
    return phone.substring(0, 3) + '****' + phone.substring(phone.length - 4)
  },
  maskEmail: (email) => {
    if (!email || !email.includes('@')) return email
    const atIndex = email.indexOf('@')
    if (atIndex <= 1) return email
    return email.charAt(0) + '****' + email.substring(atIndex)
  },
  maskName: (name) => {
    if (!name || name.length <= 1) return name
    return name.charAt(0) + '*'.repeat(name.length - 1)
  }
}

/**
 * 日期格式化工具函数
 */
const dateUtils = {
  formatTime: (date) => {
    if (!date) return ''
    const d = new Date(date)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}`
  },
  formatDuration: (days) => {
    if (!days || days < 0) return '0天'
    if (days < 30) return `${days}天`
    if (days < 365) return `${Math.floor(days / 30)}个月${days % 30}天`
    const years = Math.floor(days / 365)
    const remainingDays = days % 365
    const months = Math.floor(remainingDays / 30)
    return `${years}年${months}个月`
  },
  getTimeAgo: (date) => {
    if (!date) return ''
    const now = new Date()
    const past = new Date(date)
    const diffMs = now - past
    const diffMinutes = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMinutes < 1) return '刚刚'
    if (diffMinutes < 60) return `${diffMinutes}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return dateUtils.formatTime(date).split(' ')[0]
  }
}

describe('敏感数据处理工具测试', () => {
  describe('maskPhone', () => {
    it('应该正确脱敏手机号', () => {
      expect(sensitiveData.maskPhone('13812345678')).toBe('138****5678')
      expect(sensitiveData.maskPhone('18600001111')).toBe('186****1111')
    })

    it('短号码应该返回原值', () => {
      expect(sensitiveData.maskPhone('123')).toBe('123')
    })

    it('null或空值应该返回原值', () => {
      expect(sensitiveData.maskPhone(null)).toBe(null)
      expect(sensitiveData.maskPhone('')).toBe('')
    })
  })

  describe('maskEmail', () => {
    it('应该正确脱敏邮箱', () => {
      expect(sensitiveData.maskEmail('test@example.com')).toBe('t****@example.com')
      expect(sensitiveData.maskEmail('admin@mail.com')).toBe('a****@mail.com')
    })

    it('无@符号应该返回原值', () => {
      expect(sensitiveData.maskEmail('testexample.com')).toBe('testexample.com')
    })

    it('单个字符前缀应该返回原值', () => {
      expect(sensitiveData.maskEmail('a@example.com')).toBe('a@example.com')
    })
  })

  describe('maskName', () => {
    it('应该正确脱敏两个字的姓名', () => {
      expect(sensitiveData.maskName('张三')).toBe('张*')
    })

    it('应该正确脱敏三个字的姓名', () => {
      expect(sensitiveData.maskName('王小明')).toBe('王**')
    })

    it('单个字应该返回原值', () => {
      expect(sensitiveData.maskName('李')).toBe('李')
    })
  })
})

describe('日期工具函数测试', () => {
  describe('formatTime', () => {
    it('应该正确格式化日期时间', () => {
      const date = new Date('2024-03-15T10:30:00')
      const result = dateUtils.formatTime(date)
      expect(result).toContain('2024-03-15')
      expect(result).toContain('10:30')
    })

    it('null应该返回空字符串', () => {
      expect(dateUtils.formatTime(null)).toBe('')
    })
  })

  describe('formatDuration', () => {
    it('应该正确格式化天数', () => {
      expect(dateUtils.formatDuration(5)).toBe('5天')
    })

    it('应该正确格式化月数', () => {
      expect(dateUtils.formatDuration(45)).toBe('1个月15天')
    })

    it('应该正确格式化年数', () => {
      expect(dateUtils.formatDuration(400)).toBe('1年1个月')
    })

    it('负数或null应该返回0天', () => {
      expect(dateUtils.formatDuration(null)).toBe('0天')
      expect(dateUtils.formatDuration(-1)).toBe('0天')
    })
  })

  describe('getTimeAgo', () => {
    it('刚刚应该返回"刚刚"', () => {
      const now = new Date()
      expect(dateUtils.getTimeAgo(now)).toBe('刚刚')
    })

    it('几分钟前应该返回"X分钟前"', () => {
      const date = new Date(Date.now() - 5 * 60000)
      expect(dateUtils.getTimeAgo(date)).toBe('5分钟前')
    })

    it('几小时前应该返回"X小时前"', () => {
      const date = new Date(Date.now() - 3 * 60 * 60000)
      expect(dateUtils.getTimeAgo(date)).toBe('3小时前')
    })

    it('几天前应该返回"X天前"', () => {
      const date = new Date(Date.now() - 3 * 24 * 60 * 60000)
      expect(dateUtils.getTimeAgo(date)).toBe('3天前')
    })
  })
})
