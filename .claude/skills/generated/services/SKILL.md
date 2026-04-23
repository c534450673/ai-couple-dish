---
name: services
description: "Skill for the Services area of ai-couple-dish. 60 symbols across 1 files."
---

# Services

60 symbols | 1 files | Cohesion: 46%

## When to Use

- Working with code in `frontend/`
- Understanding how bindCouple, getCoupleInfo, getCoupleHome work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/services/api.js` | bindCouple, getCoupleInfo, getCoupleHome, validateCoupleCode, getLoveTimer (+55) |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `delay` | Function | `frontend/services/api.js` | 69 |
| `saveDemoData` | Function | `frontend/services/api.js` | 62 |
| `bindCouple` | Method | `frontend/services/api.js` | 88 |
| `getCoupleInfo` | Method | `frontend/services/api.js` | 91 |
| `getCoupleHome` | Method | `frontend/services/api.js` | 94 |
| `validateCoupleCode` | Method | `frontend/services/api.js` | 112 |
| `getLoveTimer` | Method | `frontend/services/api.js` | 115 |
| `getMenuDetail` | Method | `frontend/services/api.js` | 123 |
| `favoriteMenu` | Method | `frontend/services/api.js` | 166 |
| `getAnniversaryList` | Method | `frontend/services/api.js` | 177 |
| `getNextAnniversary` | Method | `frontend/services/api.js` | 183 |
| `getReceivedFeeds` | Method | `frontend/services/api.js` | 219 |
| `getNoteList` | Method | `frontend/services/api.js` | 244 |
| `likeNote` | Method | `frontend/services/api.js` | 273 |
| `getNotificationList` | Method | `frontend/services/api.js` | 281 |
| `markAsRead` | Method | `frontend/services/api.js` | 287 |
| `getWishList` | Method | `frontend/services/api.js` | 295 |
| `uploadPhotos` | Method | `frontend/services/api.js` | 325 |
| `getRecipeList` | Method | `frontend/services/api.js` | 333 |
| `processChefOrder` | Method | `frontend/services/api.js` | 341 |

## How to Explore

1. `gitnexus_context({name: "bindCouple"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
