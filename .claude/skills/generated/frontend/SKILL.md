---
name: frontend
description: "Skill for the Frontend area of ai-couple-dish. 12 symbols across 2 files."
---

# Frontend

12 symbols | 2 files | Cohesion: 91%

## When to Use

- Working with code in `frontend/`
- Understanding how onLaunch, setupNetworkListener, checkLoginStatus work
- Modifying frontend-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/app.js` | onLaunch, setupNetworkListener, checkLoginStatus, getDemoUserInfo, getDemoCoupleInfo (+6) |
| `frontend/pages/index/index.js` | guestMode |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `onLaunch` | Method | `frontend/app.js` | 13 |
| `setupNetworkListener` | Method | `frontend/app.js` | 22 |
| `checkLoginStatus` | Method | `frontend/app.js` | 55 |
| `getDemoUserInfo` | Method | `frontend/app.js` | 80 |
| `getDemoCoupleInfo` | Method | `frontend/app.js` | 90 |
| `setDemoMode` | Method | `frontend/app.js` | 102 |
| `guestMode` | Method | `frontend/pages/index/index.js` | 130 |
| `exitDemoMode` | Method | `frontend/app.js` | 117 |
| `setLoginInfo` | Method | `frontend/app.js` | 130 |
| `getCoupleInfo` | Method | `frontend/app.js` | 143 |
| `logout` | Method | `frontend/app.js` | 160 |
| `request` | Method | `frontend/app.js` | 177 |

## How to Explore

1. `gitnexus_context({name: "onLaunch"})` — see callers and callees
2. `gitnexus_query({query: "frontend"})` — find related execution flows
3. Read key files listed above for implementation details
