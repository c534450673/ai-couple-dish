/**
 * Response Codes
 */
export const RESPONSE_CODES = {
  SUCCESS: 200,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  SERVER_ERROR: 500
}

/**
 * Error Messages
 */
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error, please try again later',
  UNAUTHORIZED: 'Please login first',
  SESSION_EXPIRED: 'Session expired, please login again',
  SERVER_ERROR: 'Server error, please try again later',
  UNKNOWN_ERROR: 'Unknown error occurred'
}

export * from './api.js'
