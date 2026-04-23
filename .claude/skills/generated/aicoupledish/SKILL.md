---
name: aicoupledish
description: "Skill for the Aicoupledish area of ai-couple-dish. 458 symbols across 72 files."
---

# Aicoupledish

458 symbols | 72 files | Cohesion: 80%

## When to Use

- Working with code in `backend/`
- Understanding how CoupleMenu, LoginRespDTO, BindCoupleReq work
- Modifying aicoupledish-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/test/java/com/aicoupledish/MenuServiceTest.java` | setUp, getMenuList_NotBindCouple_ShouldThrowException, getMenuList_WithMenus_ShouldReturnList, getMenuList_FilterByStatusWant_ShouldReturnFilteredList, getMenuList_FilterByStatusBeen_ShouldReturnFilteredList (+31) |
| `backend/src/test/java/com/aicoupledish/FeedServiceTest.java` | sendFeed_NotBindCouple_ShouldThrowException, sendFeed_AlreadySentToday_ShouldThrowException, sendFeed_MealType_ShouldSuccess, sendFeed_DessertType_ShouldSuccess, sendFeed_SnackType_ShouldSuccess (+24) |
| `backend/src/test/java/com/aicoupledish/NoteServiceTest.java` | getNoteList_NotBindCouple_ShouldThrowException, getNoteList_WithNotes_ShouldReturnList, getNoteList_FilterByAnniversary_ShouldReturnFilteredList, getNoteList_EmptyList_ShouldReturnEmptyList, updateNote_Author_ShouldSuccess (+21) |
| `backend/src/test/java/com/aicoupledish/CoupleServiceTest.java` | bindCouple_Success, bindCouple_AlreadyBound_ThrowsException, bindCouple_InvalidCode_ThrowsException, bindCouple_SelfBind_ThrowsException, setUp (+15) |
| `backend/src/test/java/com/aicoupledish/WishServiceTest.java` | getWishList_Success, getWishList_UserNotBound_ReturnsEmptyList, getWishList_NoWishes_ReturnsEmptyList, getWishDetail_Success, getWishDetail_NotFound_ThrowsException (+14) |
| `backend/src/test/java/com/aicoupledish/CoupleServiceIntegrationTest.java` | bindCouple_ValidCode_ShouldSuccess, bindCouple_InvalidCode_ShouldThrowException, setUp, getCoupleInfo_BoundCouple_ShouldReturnInfo, getCoupleInfo_NotBound_ShouldReturnNull (+12) |
| `backend/src/test/java/com/aicoupledish/SecurityTest.java` | generateTestToken, getUserIdFromTestToken, isTestTokenExpired, refreshTestToken, getClaimsFromTestToken (+12) |
| `backend/src/test/java/com/aicoupledish/NotificationServiceTest.java` | sendCoupleNotification_Success, sendCoupleNotification_OnlyOneUser, setUp, markAllAsRead_Success, getNotificationList_Success (+10) |
| `backend/src/test/java/com/aicoupledish/AnniversaryServiceTest.java` | addAnniversary_LoveType_ShouldCheckDuplicate, addAnniversary_MeetType_ShouldSuccess, addAnniversary_NotBindCouple_ShouldThrowException, updateAnniversary_OtherType_ShouldSuccess, updateAnniversary_LoveTypeCannotChangeType_ShouldThrowException (+9) |
| `backend/src/main/java/com/aicoupledish/service/impl/MenuServiceImpl.java` | getMenuList, buildMenuDTOList, getMenuDetail, buildMenuDTO, getStatusName (+8) |

## Entry Points

Start here when exploring this area:

- **`CoupleMenu`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/CoupleMenu.java:13`
- **`LoginRespDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/LoginRespDTO.java:9`
- **`BindCoupleReq`** (Class) — `backend/src/main/java/com/aicoupledish/domain/req/BindCoupleReq.java:8`
- **`WechatLoginReq`** (Class) — `backend/src/main/java/com/aicoupledish/domain/req/WechatLoginReq.java:8`
- **`TimeCapsuleReq`** (Class) — `backend/src/main/java/com/aicoupledish/domain/req/TimeCapsuleReq.java:14`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `CoupleMenu` | Class | `backend/src/main/java/com/aicoupledish/dao/model/CoupleMenu.java` | 13 |
| `LoginRespDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/LoginRespDTO.java` | 9 |
| `BindCoupleReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/BindCoupleReq.java` | 8 |
| `WechatLoginReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/WechatLoginReq.java` | 8 |
| `TimeCapsuleReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/TimeCapsuleReq.java` | 14 |
| `HeartMomentReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/HeartMomentReq.java` | 11 |
| `Wish` | Class | `backend/src/main/java/com/aicoupledish/dao/model/Wish.java` | 12 |
| `User` | Class | `backend/src/main/java/com/aicoupledish/dao/model/User.java` | 11 |
| `TimeCapsule` | Class | `backend/src/main/java/com/aicoupledish/dao/model/TimeCapsule.java` | 12 |
| `Couple` | Class | `backend/src/main/java/com/aicoupledish/dao/model/Couple.java` | 12 |
| `AddAnniversaryReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/AddAnniversaryReq.java` | 9 |
| `SendFeedReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/SendFeedReq.java` | 9 |
| `FoodNoteDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/FoodNoteDTO.java` | 8 |
| `AddNoteReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/AddNoteReq.java` | 9 |
| `MenuDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/MenuDTO.java` | 9 |
| `UserInfoDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/UserInfoDTO.java` | 7 |
| `CoupleUnbindRecord` | Class | `backend/src/main/java/com/aicoupledish/dao/model/CoupleUnbindRecord.java` | 12 |
| `FoodNote` | Class | `backend/src/main/java/com/aicoupledish/dao/model/FoodNote.java` | 12 |
| `AddMenuReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/AddMenuReq.java` | 10 |
| `GenerateCodeReq` | Class | `backend/src/main/java/com/aicoupledish/domain/req/GenerateCodeReq.java` | 8 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `GetTodayEvents → GetLunarMonthDays` | cross_community | 7 |
| `WechatLogin → CoupleInfoDTO` | cross_community | 6 |
| `WechatLogin → GetUserById` | cross_community | 6 |
| `WechatLogin → PartnerInfoDTO` | cross_community | 6 |
| `PhoneLogin → CoupleInfoDTO` | cross_community | 6 |
| `PhoneLogin → GetUserById` | cross_community | 6 |
| `PhoneLogin → PartnerInfoDTO` | cross_community | 6 |
| `GetUserInfo → CoupleInfoDTO` | cross_community | 6 |
| `GetUserInfo → GetUserById` | cross_community | 6 |
| `GetUserInfo → PartnerInfoDTO` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Controller | 74 calls |
| Impl | 33 calls |
| Task | 24 calls |
| Dto | 2 calls |
| Interceptor | 1 calls |

## How to Explore

1. `gitnexus_context({name: "CoupleMenu"})` — see callers and callees
2. `gitnexus_query({query: "aicoupledish"})` — find related execution flows
3. Read key files listed above for implementation details
