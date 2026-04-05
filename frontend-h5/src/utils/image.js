/**
 * 图片处理工具
 */

/**
 * 压缩图片
 * @param {File} file - 图片文件
 * @param {Object} options - 压缩选项
 * @param {number} options.maxWidth - 最大宽度
 * @param {number} options.maxHeight - 最大高度
 * @param {number} options.quality - 压缩质量 (0-1)
 * @param {string} options.mimeType - 输出格式
 * @returns {Promise<Blob>} - 压缩后的图片Blob
 */
export const compressImage = (file, options = {}) => {
  const {
    maxWidth = 1920,
    maxHeight = 1920,
    quality = 0.8,
    mimeType = 'image/jpeg'
  } = options

  return new Promise((resolve, reject) => {
    // 如果不是图片，直接返回原文件
    if (!file.type.startsWith('image/')) {
      resolve(file)
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        let { width, height } = img

        // 计算缩放比例
        if (width > maxWidth) {
          height = (height * maxWidth) / width
          width = maxWidth
        }
        if (height > maxHeight) {
          width = (width * maxHeight) / height
          height = maxHeight
        }

        canvas.width = width
        canvas.height = height

        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)

        canvas.toBlob(
          (blob) => {
            if (blob) {
              // 如果压缩后比原文件大，使用原文件
              if (blob.size > file.size) {
                resolve(file)
              } else {
                resolve(blob)
              }
            } else {
              resolve(file)
            }
          },
          mimeType,
          quality
        )
      }
      img.onerror = () => reject(new Error('图片加载失败'))
      img.src = e.target.result
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

/**
 * 获取图片方向
 * @param {File} file - 图片文件
 * @returns {Promise<number>} - 图片方向 (1-8)
 */
export const getImageOrientation = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const view = new DataView(e.target.result)
      if (view.getUint16(0, false) !== 0xffd8) {
        resolve(1)
        return
      }
      const length = view.byteLength
      let offset = 2
      while (offset < length) {
        const marker = view.getUint16(offset, false)
        offset += 2
        if (marker === 0xffe1) {
          const little = view.getUint16(offset + 1, false) === 0x4949
          const tags = view.getUint16(offset + 2, !little)
          if (tags !== 0x0112) {
            resolve(1)
            return
          }
          const orientation = view.getUint16(offset + 9, !little)
          resolve(orientation)
          return
        } else if ((marker & 0xff00) !== 0xff00) {
          break
        } else {
          offset += view.getUint16(offset, false)
        }
      }
      resolve(1)
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsArrayBuffer(file.slice(0, 65536))
  })
}

/**
 * 修正图片方向
 * @param {HTMLCanvasElement} canvas - 画布
 * @param {CanvasRenderingContext2D} ctx - 画布上下文
 * @param {number} orientation - 图片方向
 * @param {HTMLImageElement} img - 图片对象
 */
const correctOrientation = (canvas, ctx, orientation, img) => {
  const { width, height } = canvas

  switch (orientation) {
    case 2:
      ctx.translate(width, 0)
      ctx.scale(-1, 1)
      break
    case 3:
      ctx.translate(width, height)
      ctx.rotate(Math.PI)
      break
    case 4:
      ctx.translate(0, height)
      ctx.scale(1, -1)
      break
    case 5:
      canvas.width = height
      canvas.height = width
      ctx.translate(height, 0)
      ctx.rotate(Math.PI / 2)
      break
    case 6:
      canvas.width = height
      canvas.height = width
      ctx.translate(height, 0)
      ctx.rotate(Math.PI / 2)
      break
    case 7:
      canvas.width = height
      canvas.height = width
      ctx.translate(0, width)
      ctx.rotate(-Math.PI / 2)
      break
    case 8:
      canvas.width = height
      canvas.height = width
      ctx.translate(0, width)
      ctx.rotate(-Math.PI / 2)
      break
    default:
      break
  }

  ctx.drawImage(img, 0, 0)
}

/**
 * 创建缩略图
 * @param {File} file - 图片文件
 * @param {number} size - 缩略图大小
 * @returns {Promise<Blob>} - 缩略图Blob
 */
export const createThumbnail = (file, size = 200) => {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      resolve(file)
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')

        // 计算裁剪区域 (正方形)
        const minDim = Math.min(img.width, img.height)
        const sx = (img.width - minDim) / 2
        const sy = (img.height - minDim) / 2

        canvas.width = size
        canvas.height = size

        ctx.drawImage(img, sx, sy, minDim, minDim, 0, 0, size, size)

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob)
            } else {
              resolve(file)
            }
          },
          'image/jpeg',
          0.7
        )
      }
      img.onerror = () => reject(new Error('图片加载失败'))
      img.src = e.target.result
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

/**
 * 获取文件大小显示
 * @param {number} bytes - 字节数
 * @returns {string} - 格式化的大小字符串
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 检查文件类型
 * @param {File} file - 文件
 * @param {string[]} allowedTypes - 允许的文件类型
 * @returns {boolean}
 */
export const isAllowedFileType = (file, allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']) => {
  return allowedTypes.includes(file.type)
}

/**
 * 检查文件大小
 * @param {File} file - 文件
 * @param {number} maxSize - 最大大小（字节）
 * @returns {boolean}
 */
export const isAllowedFileSize = (file, maxSize = 10 * 1024 * 1024) => {
  return file.size <= maxSize
}

export default {
  compressImage,
  getImageOrientation,
  createThumbnail,
  formatFileSize,
  isAllowedFileType,
  isAllowedFileSize
}
