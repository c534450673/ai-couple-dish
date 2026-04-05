/**
 * API 配置文件
 * 根据环境自动选择 API 地址
 */

// 开发环境
const DEV_BASE_URL = 'http://localhost:8080/api'

// 生产环境 - 需要替换为实际的生产服务器地址
const PROD_BASE_URL = 'https://api.yourdomain.com/api'

// 根据环境选择
const BASE_URL = import.meta.env.DEV ? DEV_BASE_URL : PROD_BASE_URL

export { BASE_URL, DEV_BASE_URL, PROD_BASE_URL }