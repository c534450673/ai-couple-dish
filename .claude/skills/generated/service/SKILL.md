---
name: service
description: "Skill for the Service area of ai-couple-dish. 125 symbols across 69 files."
---

# Service

125 symbols | 69 files | Cohesion: 90%

## When to Use

- Working with code in `backend/`
- Understanding how DailyTask, DailyGreetingDTO, RecipeLike work
- Modifying service-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/service/impl/DailyTaskServiceImpl.java` | claimReward, getTodayStats, getUserById, getTodayTasks, generateDailyTasks (+1) |
| `backend/src/main/java/com/aicoupledish/service/DailyTaskService.java` | claimReward, getTodayStats, getTodayTasks, generateDailyTasks, DailyTaskService |
| `backend/src/main/java/com/aicoupledish/service/RecipeService.java` | likeRecipe, collectRecipe, createRecipe, unlikeRecipe, RecipeService |
| `backend/src/main/java/com/aicoupledish/service/impl/RecipeServiceImpl.java` | likeRecipe, collectRecipe, createRecipe, unlikeRecipe, RecipeServiceImpl |
| `backend/src/main/java/com/aicoupledish/controller/RecipeController.java` | likeRecipe, collectRecipe, createRecipe, unlikeRecipe |
| `backend/src/main/java/com/aicoupledish/service/InviteService.java` | getInviteStats, getInviteRankList, validateInviteCode, InviteService |
| `backend/src/main/java/com/aicoupledish/service/impl/InviteServiceImpl.java` | getInviteStats, getInviteRankList, validateInviteCode, InviteServiceImpl |
| `backend/src/main/java/com/aicoupledish/controller/DailyTaskController.java` | claimReward, getTodayStats, getTodayTasks |
| `backend/src/main/java/com/aicoupledish/service/DailyGreetingService.java` | getTodayStatus, getBothCheckStatus, DailyGreetingService |
| `backend/src/main/java/com/aicoupledish/service/impl/DailyGreetingServiceImpl.java` | getTodayStatus, getBothCheckStatus, DailyGreetingServiceImpl |

## Entry Points

Start here when exploring this area:

- **`DailyTask`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/DailyTask.java:12`
- **`DailyGreetingDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/DailyGreetingDTO.java:10`
- **`RecipeLike`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/RecipeLike.java:11`
- **`RecipeCollect`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/RecipeCollect.java:11`
- **`Recipe`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/Recipe.java:11`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `DailyTask` | Class | `backend/src/main/java/com/aicoupledish/dao/model/DailyTask.java` | 12 |
| `DailyGreetingDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/DailyGreetingDTO.java` | 10 |
| `RecipeLike` | Class | `backend/src/main/java/com/aicoupledish/dao/model/RecipeLike.java` | 11 |
| `RecipeCollect` | Class | `backend/src/main/java/com/aicoupledish/dao/model/RecipeCollect.java` | 11 |
| `Recipe` | Class | `backend/src/main/java/com/aicoupledish/dao/model/Recipe.java` | 11 |
| `InviteStatsDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/InviteStatsDTO.java` | 10 |
| `Order` | Class | `backend/src/main/java/com/aicoupledish/dao/model/Order.java` | 12 |
| `WishServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/WishServiceImpl.java` | 24 |
| `UserServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/UserServiceImpl.java` | 29 |
| `TimeCapsuleServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/TimeCapsuleServiceImpl.java` | 31 |
| `SweetBombServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/SweetBombServiceImpl.java` | 23 |
| `RelationshipWeatherServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/RelationshipWeatherServiceImpl.java` | 23 |
| `RecipeServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/RecipeServiceImpl.java` | 31 |
| `PosterServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/PosterServiceImpl.java` | 24 |
| `OrderServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/OrderServiceImpl.java` | 30 |
| `NotificationServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/NotificationServiceImpl.java` | 21 |
| `NoteServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/NoteServiceImpl.java` | 32 |
| `MoodRecordServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/MoodRecordServiceImpl.java` | 30 |
| `MenuServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/MenuServiceImpl.java` | 35 |
| `LoveCalendarServiceImpl` | Class | `backend/src/main/java/com/aicoupledish/service/impl/LoveCalendarServiceImpl.java` | 23 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `GetTodayEvents → GetLeapMonth` | cross_community | 9 |
| `GetEventsByDate → GetLeapMonth` | cross_community | 8 |
| `GetTodayEvents → GetLunarMonthDays` | cross_community | 7 |
| `GetEventsByDate → GetLunarMonthDays` | cross_community | 6 |
| `ClaimReward → GetSigningKey` | cross_community | 5 |
| `ClaimReward → CoupleTree` | cross_community | 5 |
| `GetEventsByDate → GetSigningKey` | cross_community | 5 |
| `GetTodayEvents → GetSigningKey` | cross_community | 5 |
| `GetTodayEvents → GetUserById` | cross_community | 5 |
| `GetTodayEvents → BuildAnniversaryEvent` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Controller | 12 calls |
| Impl | 11 calls |

## How to Explore

1. `gitnexus_context({name: "DailyTask"})` — see callers and callees
2. `gitnexus_query({query: "service"})` — find related execution flows
3. Read key files listed above for implementation details
