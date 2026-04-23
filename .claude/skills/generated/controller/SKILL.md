---
name: controller
description: "Skill for the Controller area of ai-couple-dish. 66 symbols across 37 files."
---

# Controller

66 symbols | 37 files | Cohesion: 56%

## When to Use

- Working with code in `backend/`
- Understanding how WishController, UserController, UploadController work
- Modifying controller-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/controller/WishController.java` | updateWish, deleteWish, fulfillWish, WishController, getWishList (+2) |
| `backend/src/main/java/com/aicoupledish/service/WishService.java` | updateWish, deleteWish, fulfillWish, getWishList, getWishDetail (+1) |
| `backend/src/main/java/com/aicoupledish/controller/UploadController.java` | UploadController, uploadImage, uploadImages, isAllowedImageType, isAllowedMimeType (+1) |
| `backend/src/main/java/com/aicoupledish/controller/UserController.java` | sendVerifyCode, logout, UserController |
| `backend/src/main/java/com/aicoupledish/controller/PosterController.java` | deletePoster, PosterController, getMyPosters |
| `backend/src/main/java/com/aicoupledish/service/PosterService.java` | deletePoster, getMyPosters |
| `backend/src/main/java/com/aicoupledish/service/CartService.java` | batchRemove, clearCart |
| `backend/src/main/java/com/aicoupledish/controller/HeartMomentController.java` | deleteHeartMoment, HeartMomentController |
| `backend/src/main/java/com/aicoupledish/controller/CartController.java` | batchRemove, clearCart |
| `backend/src/main/java/com/aicoupledish/service/impl/PosterServiceImpl.java` | deletePoster, getMyPosters |

## Entry Points

Start here when exploring this area:

- **`WishController`** (Class) — `backend/src/main/java/com/aicoupledish/controller/WishController.java:20`
- **`UserController`** (Class) — `backend/src/main/java/com/aicoupledish/controller/UserController.java:22`
- **`UploadController`** (Class) — `backend/src/main/java/com/aicoupledish/controller/UploadController.java:27`
- **`TimeCapsuleController`** (Class) — `backend/src/main/java/com/aicoupledish/controller/TimeCapsuleController.java:20`
- **`SweetBombController`** (Class) — `backend/src/main/java/com/aicoupledish/controller/SweetBombController.java:19`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `WishController` | Class | `backend/src/main/java/com/aicoupledish/controller/WishController.java` | 20 |
| `UserController` | Class | `backend/src/main/java/com/aicoupledish/controller/UserController.java` | 22 |
| `UploadController` | Class | `backend/src/main/java/com/aicoupledish/controller/UploadController.java` | 27 |
| `TimeCapsuleController` | Class | `backend/src/main/java/com/aicoupledish/controller/TimeCapsuleController.java` | 20 |
| `SweetBombController` | Class | `backend/src/main/java/com/aicoupledish/controller/SweetBombController.java` | 19 |
| `RelationshipWeatherController` | Class | `backend/src/main/java/com/aicoupledish/controller/RelationshipWeatherController.java` | 19 |
| `PosterController` | Class | `backend/src/main/java/com/aicoupledish/controller/PosterController.java` | 19 |
| `NotificationController` | Class | `backend/src/main/java/com/aicoupledish/controller/NotificationController.java` | 17 |
| `NoteController` | Class | `backend/src/main/java/com/aicoupledish/controller/NoteController.java` | 19 |
| `MoodRecordController` | Class | `backend/src/main/java/com/aicoupledish/controller/MoodRecordController.java` | 21 |
| `MenuController` | Class | `backend/src/main/java/com/aicoupledish/controller/MenuController.java` | 20 |
| `LoveCalendarController` | Class | `backend/src/main/java/com/aicoupledish/controller/LoveCalendarController.java` | 21 |
| `InviteController` | Class | `backend/src/main/java/com/aicoupledish/controller/InviteController.java` | 21 |
| `HeartMomentController` | Class | `backend/src/main/java/com/aicoupledish/controller/HeartMomentController.java` | 20 |
| `FeedController` | Class | `backend/src/main/java/com/aicoupledish/controller/FeedController.java` | 20 |
| `DeepQaController` | Class | `backend/src/main/java/com/aicoupledish/controller/DeepQaController.java` | 19 |
| `DailyTaskController` | Class | `backend/src/main/java/com/aicoupledish/controller/DailyTaskController.java` | 19 |
| `DailyGreetingController` | Class | `backend/src/main/java/com/aicoupledish/controller/DailyGreetingController.java` | 22 |
| `CoupleTreeController` | Class | `backend/src/main/java/com/aicoupledish/controller/CoupleTreeController.java` | 21 |
| `CoupleRankController` | Class | `backend/src/main/java/com/aicoupledish/controller/CoupleRankController.java` | 19 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `CreateTimeCapsule → GetSigningKey` | cross_community | 5 |
| `CreateHeartMoment → GetSigningKey` | cross_community | 5 |
| `GenerateCoupleCode → GetSigningKey` | cross_community | 5 |
| `ApplyUnbind → GetSigningKey` | cross_community | 5 |
| `FulfillWish → GetSigningKey` | cross_community | 5 |
| `UnlockTimeCapsule → GetSigningKey` | cross_community | 5 |
| `GenerateBomb → GetSigningKey` | cross_community | 5 |
| `MarkAsRead → GetSigningKey` | cross_community | 5 |
| `AnswerBomb → GetSigningKey` | cross_community | 5 |
| `GeneratePoster → GetSigningKey` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Aicoupledish | 6 calls |
| Exception | 2 calls |
| Interceptor | 1 calls |
| Impl | 1 calls |

## How to Explore

1. `gitnexus_context({name: "WishController"})` — see callers and callees
2. `gitnexus_query({query: "controller"})` — find related execution flows
3. Read key files listed above for implementation details
