/**
 * API Endpoints
 *
 * Centralized API endpoint definitions.
 */
export const API_ENDPOINTS = {
  // User endpoints
  USER_LOGIN: '/user/login',
  USER_PHONE_LOGIN: '/user/phoneLogin',
  USER_SEND_CODE: '/user/sendVerifyCode',
  USER_INFO: '/user/info',
  USER_UPDATE: '/user/update',

  // Couple endpoints
  COUPLE_GET: '/couple/get',
  COUPLE_BIND: '/couple/bind',
  COUPLE_UNBIND: '/couple/unbind',

  // Menu endpoints
  MENU_LIST: '/menu/list',
  MENU_DETAIL: '/menu/detail',
  MENU_ADD: '/menu/add',
  MENU_DELETE: '/menu/delete',
  MENU_UPDATE: '/menu/update',

  // Feed endpoints
  FEED_LIST: '/feed/list',
  FEED_SEND: '/feed/send',

  // Anniversary endpoints
  ANNIVERSARY_LIST: '/anniversary/list',
  ANNIVERSARY_ADD: '/anniversary/add',
  ANNIVERSARY_DELETE: '/anniversary/delete',

  // Wish endpoints
  WISH_LIST: '/wish/list',
  WISH_ADD: '/wish/add',
  WISH_FULFILL: '/wish/fulfill',
  WISH_DELETE: '/wish/delete',

  // Notification endpoints
  NOTIFICATION_LIST: '/notification/list',
  NOTIFICATION_READ: '/notification/read',

  // Note endpoints
  NOTE_LIST: '/note/list',
  NOTE_ADD: '/note/add',
  NOTE_DELETE: '/note/delete'
}
