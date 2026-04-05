import { vi } from 'vitest'

// Mock uni API
vi.mock('uni', () => ({
  showToast: vi.fn(),
  showLoadingToast: vi.fn(),
  hideLoading: vi.fn(),
  showModal: vi.fn(),
  showActionSheet: vi.fn(),
  navigateTo: vi.fn(),
  redirectTo: vi.fn(),
  reLaunch: vi.fn(),
  switchTab: vi.fn(),
  navigateBack: vi.fn(),
  getStorageSync: vi.fn(),
  setStorageSync: vi.fn(),
  removeStorageSync: vi.fn(),
  getLocation: vi.fn(),
  chooseImage: vi.fn(),
  previewImage: vi.fn(),
  uploadFile: vi.fn(),
  request: vi.fn(),
  login: vi.fn(),
  getUserProfile: vi.fn(),
  getProvider: vi.fn(),
  chooseMultiImage: vi.fn(),
  compressImage: vi.fn(),
  saveImageToPhotosAlbum: vi.fn(),
  getImageInfo: vi.fn(),
  getSystemInfo: vi.fn(),
  getSystemInfoSync: vi.fn(),
  setNavigationBarTitle: vi.fn(),
  setNavigationBarColor: vi.fn(),
  showNavigationBarLoading: vi.fn(),
  hideNavigationBarLoading: vi.fn(),
  pageScrollTo: vi.fn(),
  $on: vi.fn(),
  $off: vi.fn(),
  $emit: vi.fn(),
  $once: vi.fn()
}))

// Mock Vue
vi.mock('vue', async () => {
  const actual = await vi.importActual('vue')
  return {
    ...actual,
    ref: (val) => ({ value: val }),
    reactive: (obj) => obj,
    computed: (fn) => ({ value: fn() }),
    watch: vi.fn()
  }
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
vi.stubGlobal('localStorage', localStorageMock)

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
vi.stubGlobal('sessionStorage', sessionStorageMock)

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: vi.fn(),
  error: vi.fn()
}