# Frontend Architecture Guide

## Current State

The project has two frontend versions:
- **frontend-h5**: Vue 3 + Vite + Vant (for H5 browsers)
- **frontend-uniapp**: UniApp (cross-platform including Mini Programs)

## Architecture Overview

```
frontend/
├── packages/
│   └── shared/                 # Shared utilities and types
│       ├── src/
│       │   ├── storage/        # Platform-agnostic storage interface
│       │   ├── constants/      # Shared constants (API endpoints, etc.)
│       │   └── types/         # TypeScript type definitions
│       └── package.json
├── frontend-h5/              # H5-specific implementation
└── frontend-uniapp/          # UniApp-specific implementation
```

## Shared Storage Interface

### Problem
- H5 uses `localStorage`
- UniApp uses `uni.getStorageSync` / `uni.setStorageSync`

### Solution
Create a platform-agnostic storage interface that both frontends implement.

### Implementation

**packages/shared/src/storage/index.js**
```javascript
/**
 * Platform-agnostic storage interface
 * Implement this interface in each platform-specific project
 */

export const storage = {
  getItem(key) {
    // Platform-specific implementation
  },
  setItem(key, value) {
    // Platform-specific implementation
  },
  removeItem(key) {
    // Platform-specific implementation
  },
  clear() {
    // Platform-specific implementation
  }
}
```

## API Request Unification

### Current Differences

| Feature | H5 | UniApp |
|---------|-----|--------|
| HTTP Client | axios | uni.request |
| Request deduplication | Yes | No |
| Response caching | Yes | No |
| Retry mechanism | Yes | No |
| Token storage | localStorage | uni.getStorageSync |

### Unified API Structure

Both frontends should expose the same API methods:

```javascript
// shared/src/api/config.js
export const API_ENDPOINTS = {
  USER_LOGIN: '/user/login',
  USER_PHONE_LOGIN: '/user/phoneLogin',
  // ... other endpoints
}

// shared/src/constants/index.js
export const RESPONSE_CODES = {
  SUCCESS: 200,
  UNAUTHORIZED: 401,
  // ...
}
```

## Recommended Refactoring Steps

1. **Phase 1**: Extract shared constants and types
   - Create `packages/shared`
   - Move API endpoints and constants
   - Define response type interfaces

2. **Phase 2**: Create storage abstraction
   - Define storage interface in shared
   - Implement platform-specific adapters

3. **Phase 3**: Unify API request structure
   - Extract common error handling logic
   - Keep platform-specific HTTP clients
   - Share interceptors where possible

## Key Principles

1. **DRY**: Shared logic goes to `packages/shared`
2. **Platform-specific**: UI components and platform APIs stay in each project
3. **Interface-driven**: Define contracts in shared, implement in platforms
4. **Gradual migration**: Refactor incrementally, don't rewrite

## File Structure After Refactoring

```
frontend/
├── packages/
│   └── shared/
│       ├── package.json
│       ├── src/
│       │   ├── constants/
│       │   │   ├── api.js      # API endpoints
│       │   │   └── index.js
│       │   ├── storage/
│       │   │   ├── index.js    # Storage interface
│       │   │   └── keys.js     # Storage keys
│       │   └── types/          # Type definitions
│       └── index.js
├── frontend-h5/
│   ├── src/
│   │   ├── adapter/            # Platform adapters
│   │   │   └── storage.js      # H5 storage implementation
│   │   └── ...
│   └── ...
└── frontend-uniapp/
    ├── src/
    │   ├── adapter/            # Platform adapters
    │   │   └── storage.js      # UniApp storage implementation
    │   └── ...
    └── ...
```

## Migration Checklist

- [ ] Create `packages/shared` directory structure
- [ ] Extract API endpoints to shared constants
- [ ] Define storage interface
- [ ] Implement H5 storage adapter
- [ ] Implement UniApp storage adapter
- [ ] Update H5 to use shared storage
- [ ] Update UniApp to use shared storage
- [ ] Add ESLint/Prettier to shared package
- [ ] Document contribution guidelines
