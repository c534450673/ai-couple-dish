# API Design Specification

## Overview

This document defines the API design and request/response conventions for the AI Couple Dish project.

## Base URL

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8080/api` |
| Production | `https://api.aicoupledish.com/api` |

## Request Format

### Headers

All requests should include:

```javascript
{
  'Content-Type': 'application/json',
  'Authorization': 'Bearer {token}'  // If authenticated
}
```

### Request Methods

| Method | Usage |
|--------|-------|
| GET | Retrieve data |
| POST | Create new resource |
| PUT | Update existing resource |
| DELETE | Delete resource |

### Standard Request Structure

```javascript
// H5 (axios)
api.get('/endpoint', { params: { key: value } })
api.post('/endpoint', data)
api.put('/endpoint', data)
api.delete('/endpoint')

// UniApp (uni.request)
request({ url: '/endpoint', method: 'GET', data: { key: value } })
request({ url: '/endpoint', method: 'POST', data })
```

## Response Format

### Success Response

```javascript
{
  "code": 200,      // HTTP status or business code
  "message": "Success",
  "data": { ... }   // Response payload
}
```

### Error Response

```javascript
{
  "code": 400,      // Error code
  "message": "Error description",
  "data": null
}
```

### Standard Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | - |
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show permission error |
| 404 | Not Found | Show not found error |
| 500 | Server Error | Show generic error |

## API Module Structure

### File Organization

```
src/api/
├── index.js      # Export all APIs
├── config.js     # Base URL and config
├── request.js    # HTTP client wrapper
├── user.js       # User related APIs
├── couple.js     # Couple related APIs
├── menu.js       # Menu related APIs
└── ...
```

### API Definition Pattern

```javascript
// H5 Pattern (uses axios methods directly)
export const userApi = {
  login(phone, code) {
    return api.post('/user/login', null, { params: { phone, code } })
  },
  getInfo() {
    return api.get('/user/info')
  }
}

// UniApp Pattern (uses options object)
export const userApi = {
  login(data) {
    return request({ url: '/user/login', method: 'POST', data })
  },
  getInfo() {
    return request({ url: '/user/info' })
  }
}
```

## API Endpoints

### User APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /user/phoneLogin | Phone login with verify code |
| POST | /user/sendCode | Send verify code |
| GET | /user/info | Get current user info |
| PUT | /user/update | Update user info |

### Couple APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /couple/home | Get couple home data |
| POST | /couple/generateCode | Generate couple code |
| POST | /couple/bind | Bind with partner |
| GET | /couple/validateCode | Validate couple code |
| POST | /couple/unbind/apply | Apply for unbind |
| POST | /couple/unbind/confirm | Confirm unbind |

### Menu APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /menu/list | Get menu list |
| GET | /menu/detail/{id} | Get menu detail |
| POST | /menu/add | Add new menu |
| PUT | /menu/update/{id} | Update menu |
| DELETE | /menu/delete/{id} | Delete menu |

### Anniversary APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /anniversary/list | Get anniversary list |
| GET | /anniversary/upcoming | Get upcoming anniversaries |
| POST | /anniversary/add | Add anniversary |
| PUT | /anniversary/update/{id} | Update anniversary |
| DELETE | /anniversary/delete/{id} | Delete anniversary |

### Feed APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /feed/today | Get today's feed status |
| POST | /feed/send | Send feed to partner |
| GET | /feed/received | Get received feeds |
| GET | /feed/sent | Get sent feeds |
| POST | /feed/accept/{id} | Accept feed |
| POST | /feed/reject/{id} | Reject feed |

### Wish APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /wish/list | Get wish list |
| POST | /wish/add | Add new wish |
| POST | /wish/fulfill/{id} | Mark wish as fulfilled |
| DELETE | /wish/delete/{id} | Delete wish |

### Note APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /note/list | Get note list |
| GET | /note/detail/{id} | Get note detail |
| POST | /note/add | Add new note |
| PUT | /note/update/{id} | Update note |
| DELETE | /note/delete/{id} | Delete note |

### Upload APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /upload/image | Upload image file |

## Error Handling

### Client-side Error Handling Pattern

```javascript
// H5 (axios interceptor)
api.interceptors.response.use(
  (response) => {
    if (response.data.code === 200) {
      return response.data
    } else if (response.data.code === 401) {
      // Handle unauthorized
      redirectToLogin()
    }
    return Promise.reject(response.data)
  },
  (error) => {
    // Handle network errors
    showToast('Network error')
    return Promise.reject(error)
  }
)

// UniApp (in request wrapper)
success: (res) => {
  if (res.statusCode === 200) {
    if (res.data.code === 200) {
      resolve(res.data)
    } else if (res.data.code === 401) {
      // Handle unauthorized
      uni.reLaunch({ url: '/pages/index/index' })
      reject(res.data)
    }
  }
}
```

### Best Practices

1. **Always handle errors**: Use try-catch or .catch() for all API calls
2. **Show user-friendly messages**: Use toast/notification for errors
3. **Redirect on auth errors**: Redirect to login when 401 is received
4. **Log errors for debugging**: Console log errors in development
5. **Retry failed requests**: Implement retry for transient failures

## Pagination

### Request Parameters

```javascript
{
  page: 1,      // Page number (1-indexed)
  pageSize: 20  // Items per page
}
```

### Response Format

```javascript
{
  "code": 200,
  "message": "Success",
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "pageSize": 20
  }
}
```

## File Upload

### Request Format

```
Content-Type: multipart/form-data
```

### Response Format

```javascript
{
  "code": 200,
  "message": "Success",
  "data": {
    "url": "https://cdn.example.com/uploads/image.png",
    "filename": "image.png",
    "size": 102400
  }
}
```
