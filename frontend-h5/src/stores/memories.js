import { defineStore } from 'pinia'
import { anniversaryApi, noteApi, wishApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const SOURCE_TYPES = ['anniversary', 'wish', 'note']
const initialStatuses = () => ({ anniversary: 'idle', wish: 'idle', note: 'idle', map: 'unavailable' })
const initialErrors = () => ({ anniversary: null, wish: null, note: null, map: null })
const initialItems = () => ({ anniversary: [], wish: [], note: [] })
const errorCode = error => String(error?.code || error?.response?.status || 'UNKNOWN')

const logMemory = (operation, result, startedAt, fields = {}) => logUiEvent(`memories.${operation}`, {
  module: 'memories_store',
  operation,
  result,
  durationMs: Date.now() - startedAt,
  ...fields
})

export const normalizeTimelineItem = (type, item) => {
  if (type === 'anniversary') {
    return {
      id: `anniversary:${item.id}`,
      type,
      occurredAt: item.anniversaryDate || null,
      creatorId: null,
      title: item.name || '',
      summary: item.typeName || '',
      media: []
    }
  }
  if (type === 'wish') {
    return {
      id: `wish:${item.id}`,
      type,
      occurredAt: item.achievedDate || item.targetDate || item.createTime || null,
      creatorId: item.creatorId ?? null,
      title: item.title || '',
      summary: item.description || item.statusName || '',
      media: item.imageUrl ? [item.imageUrl] : []
    }
  }
  if (type === 'note') {
    return {
      id: `note:${item.id}`,
      type,
      occurredAt: item.createTime || null,
      creatorId: item.authorId ?? null,
      title: item.title || '',
      summary: item.content || '',
      media: Array.isArray(item.photoUrls) ? item.photoUrls : []
    }
  }
  return null
}

const sourceRequest = type => {
  if (type === 'anniversary') return anniversaryApi.getAnniversaryList()
  if (type === 'wish') return wishApi.getWishList()
  return noteApi.getNoteList()
}

const stableTimelineSort = (items) => items
  .map((item, index) => ({ item, index, timestamp: Date.parse(item.occurredAt || '') }))
  .sort((left, right) => {
    const leftValid = Number.isFinite(left.timestamp)
    const rightValid = Number.isFinite(right.timestamp)
    if (leftValid && rightValid && left.timestamp !== right.timestamp) return right.timestamp - left.timestamp
    if (leftValid !== rightValid) return leftValid ? -1 : 1
    return left.index - right.index
  })
  .map(entry => entry.item)

export const useMemoriesStore = defineStore('memories', {
  state: () => ({
    timeline: [],
    sourceItems: initialItems(),
    sourceStatus: initialStatuses(),
    sourceErrors: initialErrors(),
    activeType: 'all',
    aggregateRequestId: 0,
    sourceRequestIds: { anniversary: 0, wish: 0, note: 0 },
    noteDetail: null,
    noteDetailStatus: 'idle',
    noteDetailRequestId: 0,
    noteMutationRequestId: 0,
    mutationStatus: 'idle',
    error: null
  }),
  getters: {
    filteredTimeline: state => state.activeType === 'all'
      ? state.timeline
      : state.timeline.filter(item => item.type === state.activeType)
  },
  actions: {
    rebuildTimeline() {
      this.timeline = stableTimelineSort(SOURCE_TYPES.flatMap(type => this.sourceItems[type]))
    },
    setActiveType(type) {
      this.activeType = ['all', ...SOURCE_TYPES].includes(type) ? type : 'all'
    },
    applySourceSuccess(type, response, startedAt, requestId) {
      const raw = Array.isArray(response?.data) ? response.data : []
      this.sourceItems[type] = raw.map(item => normalizeTimelineItem(type, item)).filter(Boolean)
      this.sourceStatus[type] = raw.length ? 'success' : 'empty'
      this.sourceErrors[type] = null
      logMemory(`source.${type}`, this.sourceStatus[type], startedAt, {
        requestId,
        itemCount: raw.length
      })
    },
    applySourceError(type, error, startedAt, requestId) {
      this.sourceItems[type] = []
      this.sourceStatus[type] = 'error'
      this.sourceErrors[type] = error
      logMemory(`source.${type}`, 'error', startedAt, {
        requestId,
        itemCount: 0,
        errorCode: errorCode(error)
      })
    },
    async fetchAll() {
      const startedAt = Date.now()
      const aggregateRequestId = ++this.aggregateRequestId
      const requestIds = Object.fromEntries(SOURCE_TYPES.map(type => [
        type,
        ++this.sourceRequestIds[type]
      ]))
      SOURCE_TYPES.forEach((type) => {
        this.sourceStatus[type] = 'loading'
        this.sourceErrors[type] = null
        logMemory(`source.${type}`, 'loading', startedAt, {
          requestId: requestIds[type],
          aggregateRequestId
        })
      })
      this.sourceStatus.map = 'unavailable'
      logMemory('source.map', 'unavailable', startedAt, {
        requestId: aggregateRequestId,
        errorCode: 'MAP_FOOTPRINT_NOT_SUPPORTED',
        itemCount: 0
      })
      const results = await Promise.allSettled([
        sourceRequest('anniversary'),
        sourceRequest('wish'),
        sourceRequest('note'),
        Promise.resolve({ status: 'unavailable' })
      ])
      if (aggregateRequestId !== this.aggregateRequestId) {
        logMemory('aggregate', 'stale_ignored', startedAt, { requestId: aggregateRequestId })
        return results
      }
      SOURCE_TYPES.forEach((type, index) => {
        if (requestIds[type] !== this.sourceRequestIds[type]) {
          logMemory(`source.${type}`, 'stale_ignored', startedAt, { requestId: requestIds[type] })
          return
        }
        const result = results[index]
        if (result.status === 'fulfilled') this.applySourceSuccess(type, result.value, startedAt, requestIds[type])
        else this.applySourceError(type, result.reason, startedAt, requestIds[type])
      })
      this.rebuildTimeline()
      const allSourcesFailed = SOURCE_TYPES.every(type => this.sourceStatus[type] === 'error')
      const aggregateResult = allSourcesFailed ? 'error' : (this.timeline.length ? 'success' : 'empty')
      logMemory('aggregate', aggregateResult, startedAt, {
        requestId: aggregateRequestId,
        itemCount: this.timeline.length,
        ...(allSourcesFailed ? { errorCode: 'ALL_SOURCES_FAILED' } : {})
      })
      return results
    },
    async retrySource(type) {
      if (!SOURCE_TYPES.includes(type)) {
        logMemory('source.map', 'unavailable', Date.now(), { errorCode: 'MAP_FOOTPRINT_NOT_SUPPORTED', itemCount: 0 })
        return { status: 'unavailable', reason: 'MAP_FOOTPRINT_NOT_SUPPORTED' }
      }
      const startedAt = Date.now()
      const requestId = ++this.sourceRequestIds[type]
      this.sourceStatus[type] = 'loading'
      this.sourceErrors[type] = null
      logMemory(`source.${type}`, 'loading', startedAt, { requestId })
      try {
        const response = await sourceRequest(type)
        if (requestId !== this.sourceRequestIds[type]) {
          logMemory(`source.${type}`, 'stale_ignored', startedAt, { requestId })
          return response
        }
        this.applySourceSuccess(type, response, startedAt, requestId)
        this.rebuildTimeline()
        return response
      } catch (error) {
        if (requestId === this.sourceRequestIds[type]) {
          this.applySourceError(type, error, startedAt, requestId)
          this.rebuildTimeline()
        }
        throw error
      }
    },
    async fetchNoteDetail(id) {
      const startedAt = Date.now()
      const requestId = ++this.noteDetailRequestId
      this.noteDetailStatus = 'loading'
      this.noteDetail = null
      logMemory('note.detail', 'loading', startedAt, { requestId })
      try {
        const response = await noteApi.getNoteDetail(id)
        if (requestId !== this.noteDetailRequestId) {
          logMemory('note.detail', 'stale_ignored', startedAt, { requestId })
          return null
        }
        this.noteDetail = response?.data || null
        this.noteDetailStatus = this.noteDetail ? 'success' : 'empty'
        logMemory('note.detail', this.noteDetailStatus, startedAt, { requestId, itemCount: this.noteDetail ? 1 : 0 })
        return this.noteDetail
      } catch (error) {
        if (requestId === this.noteDetailRequestId) {
          this.noteDetailStatus = 'error'
          this.error = error
        }
        logMemory('note.detail', 'error', startedAt, { requestId, errorCode: errorCode(error) })
        throw error
      }
    },
    async saveNote(id, payload) {
      const startedAt = Date.now()
      const requestId = ++this.noteMutationRequestId
      const operation = id ? 'note.update' : 'note.create'
      const notePayload = { ...payload }
      delete notePayload.anniversaryName
      const isAnniversaryLinked = Number(notePayload.isAnniversaryLinked) ? 1 : 0
      const apiPayload = {
        ...notePayload,
        isAnniversaryLinked,
        anniversaryId: isAnniversaryLinked ? (notePayload.anniversaryId ?? null) : null
      }
      this.mutationStatus = 'loading'
      logMemory(operation, 'loading', startedAt, { requestId })
      try {
        const response = id ? await noteApi.updateNote(id, apiPayload) : await noteApi.addNote(apiPayload)
        this.mutationStatus = 'success'
        logMemory(operation, 'success', startedAt, { requestId, itemCount: 1 })
        const savedNote = {
          id: id || response?.data,
          ...apiPayload,
          anniversaryName: isAnniversaryLinked ? (payload.anniversaryName ?? null) : null
        }
        return savedNote
      } catch (error) {
        this.mutationStatus = 'error'
        this.error = error
        logMemory(operation, 'error', startedAt, { requestId, errorCode: errorCode(error) })
        throw error
      }
    },
    async removeNote(id) {
      const startedAt = Date.now()
      const requestId = ++this.noteMutationRequestId
      this.mutationStatus = 'loading'
      logMemory('note.delete', 'loading', startedAt, { requestId })
      try {
        await noteApi.deleteNote(id)
        this.sourceItems.note = this.sourceItems.note.filter(item => item.id !== `note:${id}`)
        this.rebuildTimeline()
        this.mutationStatus = 'success'
        logMemory('note.delete', 'success', startedAt, { requestId, itemCount: 1 })
      } catch (error) {
        this.mutationStatus = 'error'
        logMemory('note.delete', 'error', startedAt, { requestId, errorCode: errorCode(error) })
        throw error
      }
    }
  }
})
