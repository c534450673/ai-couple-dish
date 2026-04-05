/**
 * 时光胶囊和心动时刻 API 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'

// 创建时光胶囊API
const timeCapsuleApi = {
  getList: () => axios.get('/api/timeCapsule/list'),
  getDetail: (id) => axios.get(`/api/timeCapsule/detail/${id}`),
  create: (data) => axios.post('/api/timeCapsule/create', data),
  unlock: (id) => axios.post(`/api/timeCapsule/unlock/${id}`),
  delete: (id) => axios.delete(`/api/timeCapsule/delete/${id}`),
  getPending: () => axios.get('/api/timeCapsule/pending')
}

// 创建心动时刻API
const heartMomentApi = {
  getList: (params) => axios.get('/api/heartMoment/list', { params }),
  create: (data) => axios.post('/api/heartMoment/create', data),
  delete: (id) => axios.delete(`/api/heartMoment/delete/${id}`),
  getRandom: () => axios.get('/api/heartMoment/random')
}

describe('时光胶囊 API 测试', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(axios)
  })

  afterEach(() => {
    mock.restore()
  })

  describe('getList', () => {
    it('应该获取时光胶囊列表', async () => {
      const mockResponse = {
        data: [
          { id: 1, title: '测试胶囊', status: 0 },
          { id: 2, title: '已解锁胶囊', status: 1 }
        ]
      }
      mock.onGet('/api/timeCapsule/list').reply(200, mockResponse)

      const result = await timeCapsuleApi.getList()
      expect(result.data).toHaveLength(2)
      expect(result.data[0].title).toBe('测试胶囊')
    })
  })

  describe('getDetail', () => {
    it('应该获取指定ID的胶囊详情', async () => {
      const mockResponse = {
        data: { id: 1, title: '测试胶囊', content: '内容' }
      }
      mock.onGet('/api/timeCapsule/detail/1').reply(200, mockResponse)

      const result = await timeCapsuleApi.getDetail(1)
      expect(result.data.id).toBe(1)
      expect(result.data.content).toBe('内容')
    })
  })

  describe('create', () => {
    it('应该创建新的时光胶囊', async () => {
      const createData = {
        capsuleType: 'text',
        title: '新胶囊',
        content: '测试内容',
        unlockDate: '2024-12-31'
      }
      const mockResponse = { data: 1 }
      mock.onPost('/api/timeCapsule/create', createData).reply(200, mockResponse)

      const result = await timeCapsuleApi.create(createData)
      expect(result.data).toBe(1)
    })
  })

  describe('unlock', () => {
    it('应该解锁时光胶囊', async () => {
      const mockResponse = {
        data: { id: 1, status: 1, content: '解锁的内容' }
      }
      mock.onPost('/api/timeCapsule/unlock/1').reply(200, mockResponse)

      const result = await timeCapsuleApi.unlock(1)
      expect(result.data.status).toBe(1)
    })
  })

  describe('delete', () => {
    it('应该删除时光胶囊', async () => {
      mock.onDelete('/api/timeCapsule/delete/1').reply(200, { data: { success: true } })

      const result = await timeCapsuleApi.delete(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('getPending', () => {
    it('应该获取可解锁的胶囊列表', async () => {
      const mockResponse = {
        data: [{ id: 1, title: '可解锁胶囊' }]
      }
      mock.onGet('/api/timeCapsule/pending').reply(200, mockResponse)

      const result = await timeCapsuleApi.getPending()
      expect(result.data).toHaveLength(1)
    })
  })
})

describe('心动时刻 API 测试', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(axios)
  })

  afterEach(() => {
    mock.restore()
  })

  describe('getList', () => {
    it('应该获取心动时刻列表', async () => {
      const mockResponse = {
        data: [
          { id: 1, content: '今天心情很好', momentType: 'text' },
          { id: 2, content: '照片描述', momentType: 'photo' }
        ]
      }
      mock.onGet('/api/heartMoment/list').reply(200, mockResponse)

      const result = await heartMomentApi.getList()
      expect(result.data).toHaveLength(2)
    })

    it('应该支持分页参数', async () => {
      const mockResponse = { data: [] }
      mock.onGet('/api/heartMoment/list', { params: { page: 2, pageSize: 10 } }).reply(200, mockResponse)

      const result = await heartMomentApi.getList({ page: 2, pageSize: 10 })
      expect(result.data).toEqual([])
    })
  })

  describe('create', () => {
    it('应该创建文本类型心动时刻', async () => {
      const createData = {
        momentType: 'text',
        content: '今天和TA一起吃饭很开心'
      }
      const mockResponse = { data: 1 }
      mock.onPost('/api/heartMoment/create', createData).reply(200, mockResponse)

      const result = await heartMomentApi.create(createData)
      expect(result.data).toBe(1)
    })

    it('应该创建照片类型心动时刻', async () => {
      const createData = {
        momentType: 'photo',
        content: '我们的合影',
        mediaUrl: 'https://example.com/photo.jpg'
      }
      const mockResponse = { data: 2 }
      mock.onPost('/api/heartMoment/create', createData).reply(200, mockResponse)

      const result = await heartMomentApi.create(createData)
      expect(result.data).toBe(2)
    })
  })

  describe('delete', () => {
    it('应该删除心动时刻', async () => {
      mock.onDelete('/api/heartMoment/delete/1').reply(200, { data: { success: true } })

      const result = await heartMomentApi.delete(1)
      expect(result.data.success).toBe(true)
    })
  })

  describe('getRandom', () => {
    it('应该获取随机心动时刻', async () => {
      const mockResponse = {
        data: { id: 1, content: '随机的心动时刻', timeDesc: '3天前' }
      }
      mock.onGet('/api/heartMoment/random').reply(200, mockResponse)

      const result = await heartMomentApi.getRandom()
      expect(result.data.content).toBe('随机的心动时刻')
      expect(result.data.timeDesc).toBe('3天前')
    })

    it('没有数据时应该返回null', async () => {
      mock.onGet('/api/heartMoment/random').reply(200, { data: null })

      const result = await heartMomentApi.getRandom()
      expect(result.data).toBeNull()
    })
  })
})
