/**
 * Shared Type Definitions
 *
 * These are JSDoc type definitions for documentation purposes.
 * For full TypeScript support, consider migrating to TypeScript.
 */

/**
 * @typedef {Object} UserInfo
 * @property {number} userId
 * @property {string} nickname
 * @property {string} avatar
 * @property {string} phone
 */

/**
 * @typedef {Object} CoupleInfo
 * @property {number} coupleId
 * @property {UserInfo} maleUser
 * @property {UserInfo} femaleUser
 * @property {string} coupleName
 * @property {string} createdAt
 */

/**
 * @typedef {Object} ApiResponse
 * @property {number} code
 * @property {string} message
 * @property {*} data
 */

/**
 * @typedef {Object} MenuItem
 * @property {number} menuId
 * @property {string} name
 * @property {string} image
 * @property {string} description
 * @property {number} createdBy
 * @property {string} createdAt
 */

/**
 * @typedef {Object} Anniversary
 * @property {number} anniversaryId
 * @property {string} name
 * @property {string} date
 * @property {number} type
 * @property {string} createdAt
 */

/**
 * @typedef {Object} Wish
 * @property {number} wishId
 * @property {string} content
 * @property {number} createdBy
 * @property {boolean} fulfilled
 * @property {string} createdAt
 */

/**
 * @typedef {Object} Feed
 * @property {number} feedId
 * @property {string} content
 * @property {string[]} images
 * @property {number} createdBy
 * @property {string} createdAt
 */
