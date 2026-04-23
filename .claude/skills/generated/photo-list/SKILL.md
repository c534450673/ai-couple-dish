---
name: photo-list
description: "Skill for the Photo-list area of ai-couple-dish. 6 symbols across 2 files."
---

# Photo-list

6 symbols | 2 files | Cohesion: 90%

## When to Use

- Working with code in `frontend/`
- Understanding how onLoad, onShow, loadPhotos work
- Modifying photo-list-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/pages/photo/photo-list/photo-list.js` | onLoad, onShow, loadPhotos, onDeletePhoto, onPreviewPhoto |
| `frontend/pages/menu/menu-list/menu-list.js` | previewImage |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `onLoad` | Method | `frontend/pages/photo/photo-list/photo-list.js` | 12 |
| `onShow` | Method | `frontend/pages/photo/photo-list/photo-list.js` | 16 |
| `loadPhotos` | Method | `frontend/pages/photo/photo-list/photo-list.js` | 20 |
| `onDeletePhoto` | Method | `frontend/pages/photo/photo-list/photo-list.js` | 57 |
| `onPreviewPhoto` | Method | `frontend/pages/photo/photo-list/photo-list.js` | 37 |
| `previewImage` | Method | `frontend/pages/menu/menu-list/menu-list.js` | 95 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Note-add | 1 calls |

## How to Explore

1. `gitnexus_context({name: "onLoad"})` — see callers and callees
2. `gitnexus_query({query: "photo-list"})` — find related execution flows
3. Read key files listed above for implementation details
