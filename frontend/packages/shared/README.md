# @ai-couple-dish/shared

Shared utilities and constants for AI Couple Dish frontend projects.

## Installation

```bash
# From the frontend directory
cd packages/shared
npm link

# Then in your frontend project
npm link @ai-couple-dish/shared
```

## Usage

### Using Constants

```javascript
// Import API endpoints
import { API_ENDPOINTS } from '@ai-couple-dish/shared'

// Use in your API calls
const response = await request.get(API_ENDPOINTS.USER_LOGIN)

// Import response codes
import { RESPONSE_CODES } from '@ai-couple-dish/shared'

if (response.code === RESPONSE_CODES.UNAUTHORIZED) {
  // Handle unauthorized
}
```

### Using Storage Keys

```javascript
import { STORAGE_KEYS } from '@ai-couple-dish/shared'

// Instead of hardcoding strings
localStorage.setItem('token', value)

// Use centralized keys
localStorage.setItem(STORAGE_KEYS.TOKEN, value)
```

## Modules

### Storage Keys (`storage/keys.js`)

Centralized storage key definitions to prevent typos.

### API Endpoints (`constants/api.js`)

Centralized API endpoint paths matching backend controller routes.

### Response Codes (`constants/index.js`)

Standard API response codes for error handling.

### Type Definitions (`types/index.js`)

JSDoc type definitions for documentation and IDE autocomplete.
