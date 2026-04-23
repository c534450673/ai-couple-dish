---
name: api
description: "Skill for the Api area of ai-couple-dish. 53 symbols across 3 files."
---

# Api

53 symbols | 3 files | Cohesion: 100%

## When to Use

- Working with code in `frontend-uniapp/`
- Understanding how loginByPhone, sendVerifyCode, getUserInfo work
- Modifying api-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend-uniapp/src/api/index.js` | loginByPhone, sendVerifyCode, getUserInfo, updateUserInfo, getCoupleInfo (+42) |
| `frontend-h5/src/api/request.js` | generateRequestKey, addPendingRequest, removePendingRequest, getCache, setCache |
| `frontend-uniapp/src/api/request.js` | request |

## Entry Points

Start here when exploring this area:

- **`loginByPhone`** (Method) — `frontend-uniapp/src/api/index.js:7`
- **`sendVerifyCode`** (Method) — `frontend-uniapp/src/api/index.js:10`
- **`getUserInfo`** (Method) — `frontend-uniapp/src/api/index.js:13`
- **`updateUserInfo`** (Method) — `frontend-uniapp/src/api/index.js:16`
- **`getCoupleInfo`** (Method) — `frontend-uniapp/src/api/index.js:24`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `loginByPhone` | Method | `frontend-uniapp/src/api/index.js` | 7 |
| `sendVerifyCode` | Method | `frontend-uniapp/src/api/index.js` | 10 |
| `getUserInfo` | Method | `frontend-uniapp/src/api/index.js` | 13 |
| `updateUserInfo` | Method | `frontend-uniapp/src/api/index.js` | 16 |
| `getCoupleInfo` | Method | `frontend-uniapp/src/api/index.js` | 24 |
| `getCoupleHome` | Method | `frontend-uniapp/src/api/index.js` | 27 |
| `generateCoupleCode` | Method | `frontend-uniapp/src/api/index.js` | 30 |
| `bindCouple` | Method | `frontend-uniapp/src/api/index.js` | 33 |
| `validateCoupleCode` | Method | `frontend-uniapp/src/api/index.js` | 36 |
| `getLoveTimer` | Method | `frontend-uniapp/src/api/index.js` | 39 |
| `applyUnbind` | Method | `frontend-uniapp/src/api/index.js` | 42 |
| `getMenuList` | Method | `frontend-uniapp/src/api/index.js` | 48 |
| `getMenuDetail` | Method | `frontend-uniapp/src/api/index.js` | 51 |
| `addMenu` | Method | `frontend-uniapp/src/api/index.js` | 54 |
| `updateMenu` | Method | `frontend-uniapp/src/api/index.js` | 57 |
| `deleteMenu` | Method | `frontend-uniapp/src/api/index.js` | 60 |
| `likeMenu` | Method | `frontend-uniapp/src/api/index.js` | 63 |
| `favoriteMenu` | Method | `frontend-uniapp/src/api/index.js` | 66 |
| `getMenuStats` | Method | `frontend-uniapp/src/api/index.js` | 69 |
| `getAnniversaryList` | Method | `frontend-uniapp/src/api/index.js` | 75 |

## How to Explore

1. `gitnexus_context({name: "loginByPhone"})` — see callers and callees
2. `gitnexus_query({query: "api"})` — find related execution flows
3. Read key files listed above for implementation details
