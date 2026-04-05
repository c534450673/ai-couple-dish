/**
 * 表单验证工具
 */

/**
 * 验证手机号
 */
export const validatePhone = (phone) => {
  const reg = /^1[3-9]\d{9}$/
  return reg.test(phone)
}

/**
 * 验证邮箱
 */
export const validateEmail = (email) => {
  const reg = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/
  return reg.test(email)
}

/**
 * 验证验证码
 */
export const validateVerifyCode = (code) => {
  const reg = /^\d{4,6}$/
  return reg.test(code)
}

/**
 * 验证昵称
 */
export const validateNickName = (name) => {
  return name && name.length >= 2 && name.length <= 20
}

/**
 * 验证密码
 */
export const validatePassword = (password) => {
  return password && password.length >= 6 && password.length <= 20
}

/**
 * 验证必填项
 */
export const validateRequired = (value) => {
  if (typeof value === 'string') {
    return value.trim().length > 0
  }
  return value !== null && value !== undefined
}

/**
 * 验证URL
 */
export const validateUrl = (url) => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/**
 * 验证价格
 */
export const validatePrice = (price) => {
  const reg = /^\d+(\.\d{1,2})?$/
  return reg.test(price)
}

/**
 * 通用验证器
 */
export const validators = {
  phone: validatePhone,
  email: validateEmail,
  verifyCode: validateVerifyCode,
  nickName: validateNickName,
  password: validatePassword,
  required: validateRequired,
  url: validateUrl,
  price: validatePrice
}

/**
 * 验证表单字段
 * @param {Object} data - 表单数据
 * @param {Object} rules - 验证规则 { fieldName: ['required', 'phone', ...] }
 * @returns {Object} - { valid: boolean, errors: { fieldName: '错误信息' } }
 */
export const validateForm = (data, rules) => {
  const errors = {}

  for (const [field, fieldRules] of Object.entries(rules)) {
    const value = data[field]

    for (const rule of fieldRules) {
      let isValid = true
      let errorMsg = ''

      switch (rule) {
        case 'required':
          isValid = validateRequired(value)
          errorMsg = '此项为必填'
          break
        case 'phone':
          if (value) {
            isValid = validatePhone(value)
            errorMsg = '手机号格式不正确'
          }
          break
        case 'email':
          if (value) {
            isValid = validateEmail(value)
            errorMsg = '邮箱格式不正确'
          }
          break
        case 'verifyCode':
          if (value) {
            isValid = validateVerifyCode(value)
            errorMsg = '验证码格式不正确'
          }
          break
        case 'nickName':
          if (value) {
            isValid = validateNickName(value)
            errorMsg = '昵称长度需在2-20字之间'
          }
          break
        case 'password':
          if (value) {
            isValid = validatePassword(value)
            errorMsg = '密码长度需在6-20位'
          }
          break
        case 'url':
          if (value) {
            isValid = validateUrl(value)
            errorMsg = 'URL格式不正确'
          }
          break
        case 'price':
          if (value) {
            isValid = validatePrice(value)
            errorMsg = '价格格式不正确'
          }
          break
        default:
          // 自定义验证函数
          if (typeof rule === 'function') {
            isValid = rule(value)
            errorMsg = '验证失败'
          }
      }

      if (!isValid) {
        errors[field] = errorMsg
        break
      }
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  }
}

export default {
  validatePhone,
  validateEmail,
  validateVerifyCode,
  validateNickName,
  validatePassword,
  validateRequired,
  validateUrl,
  validatePrice,
  validateForm,
  validators
}
