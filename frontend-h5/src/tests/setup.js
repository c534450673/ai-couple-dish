import { vi } from 'vitest'

// Mock Vue router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn()
  }),
  useRoute: () => ({
    path: '/',
    name: 'home',
    params: {},
    query: {}
  }),
  createRouter: vi.fn(() => ({
    beforeEach: vi.fn(),
    afterEach: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn()
  })),
  createWebHistory: vi.fn()
}))

// Mock the router module
vi.mock('@/router', () => ({
  default: {
    beforeEach: vi.fn(),
    afterEach: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn()
  }
}))

// Mock localStorage with actual storage behavior
const localStorageStore = {}
const localStorageMock = {
  getItem: vi.fn((key) => localStorageStore[key] || null),
  setItem: vi.fn((key, value) => {
    localStorageStore[key] = value
  }),
  removeItem: vi.fn((key) => {
    delete localStorageStore[key]
  }),
  clear: vi.fn(() => {
    Object.keys(localStorageStore).forEach(key => delete localStorageStore[key])
  })
}
vi.stubGlobal('localStorage', localStorageMock)

// Mock sessionStorage
const sessionStorageStore = {}
const sessionStorageMock = {
  getItem: vi.fn((key) => sessionStorageStore[key] || null),
  setItem: vi.fn((key, value) => {
    sessionStorageStore[key] = value
  }),
  removeItem: vi.fn((key) => {
    delete sessionStorageStore[key]
  }),
  clear: vi.fn(() => {
    Object.keys(sessionStorageStore).forEach(key => delete sessionStorageStore[key])
  })
}
vi.stubGlobal('sessionStorage', sessionStorageMock)

// Mock window.location
vi.stubGlobal('location', {
  href: 'http://localhost:3000',
  pathname: '/',
  search: '',
  hash: ''
})

// Mock document
vi.stubGlobal('document', {
  ...document,
  querySelector: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  createElement: vi.fn(() => ({
    style: {},
    classList: { add: vi.fn(), remove: vi.fn() },
    appendChild: vi.fn(),
    removeChild: vi.fn()
  })),
  getElementById: vi.fn()
})

// Mock Vant components
vi.mock('vant', async () => {
  const actual = await vi.importActual('vant')
  return {
    ...actual,
    showToast: vi.fn(),
    showLoadingToast: vi.fn(),
    closeToast: vi.fn(),
    showDialog: vi.fn(),
    showConfirmDialog: vi.fn()
  }
})

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: vi.fn(),
  error: vi.fn()
}