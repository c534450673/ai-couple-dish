---
name: note-add
description: "Skill for the Note-add area of ai-couple-dish. 16 symbols across 11 files."
---

# Note-add

16 symbols | 11 files | Cohesion: 77%

## When to Use

- Working with code in `frontend/`
- Understanding how showSuccess, onUnbind, onBindCouple work
- Modifying note-add-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/pages/note/note-add/note-add.js` | onSave, uploadImages, saveNote |
| `frontend/pages/feed/feed-send/feed-send.js` | onSend, uploadImages, sendFeedRequest |
| `frontend/pages/my/settings/settings.js` | onToggleCouple, onClearCache |
| `frontend/app.js` | showSuccess |
| `frontend/pages/couple-home/couple-home.js` | onUnbind |
| `frontend/pages/couple-bind/couple-bind.js` | onBindCouple |
| `frontend/pages/photo/photo-upload/photo-upload.js` | onUpload |
| `frontend/pages/note/note-detail/note-detail.js` | onDelete |
| `frontend/pages/menu/menu-detail/menu-detail.js` | onDelete |
| `frontend/pages/menu/menu-add/menu-add.js` | onSave |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `showSuccess` | Method | `frontend/app.js` | 262 |
| `onUnbind` | Method | `frontend/pages/couple-home/couple-home.js` | 105 |
| `onBindCouple` | Method | `frontend/pages/couple-bind/couple-bind.js` | 74 |
| `onUpload` | Method | `frontend/pages/photo/photo-upload/photo-upload.js` | 35 |
| `onDelete` | Method | `frontend/pages/note/note-detail/note-detail.js` | 32 |
| `onSave` | Method | `frontend/pages/note/note-add/note-add.js` | 45 |
| `uploadImages` | Method | `frontend/pages/note/note-add/note-add.js` | 72 |
| `saveNote` | Method | `frontend/pages/note/note-add/note-add.js` | 115 |
| `onToggleCouple` | Method | `frontend/pages/my/settings/settings.js` | 15 |
| `onClearCache` | Method | `frontend/pages/my/settings/settings.js` | 48 |
| `onDelete` | Method | `frontend/pages/menu/menu-detail/menu-detail.js` | 40 |
| `onSave` | Method | `frontend/pages/menu/menu-add/menu-add.js` | 148 |
| `onSend` | Method | `frontend/pages/feed/feed-send/feed-send.js` | 64 |
| `uploadImages` | Method | `frontend/pages/feed/feed-send/feed-send.js` | 89 |
| `sendFeedRequest` | Method | `frontend/pages/feed/feed-send/feed-send.js` | 132 |
| `onSave` | Method | `frontend/pages/anniversary/anniversary-add/anniversary-add.js` | 21 |

## How to Explore

1. `gitnexus_context({name: "showSuccess"})` — see callers and callees
2. `gitnexus_query({query: "note-add"})` — find related execution flows
3. Read key files listed above for implementation details
