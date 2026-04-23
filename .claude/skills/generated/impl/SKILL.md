---
name: impl
description: "Skill for the Impl area of ai-couple-dish. 467 symbols across 111 files."
---

# Impl

467 symbols | 111 files | Cohesion: 79%

## When to Use

- Working with code in `backend/`
- Understanding how AnniversaryDTO, Anniversary, DeepQaAnswer work
- Modifying impl-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/service/impl/OrderServiceImpl.java` | cancelOrder, acceptOrder, startCooking, finishCooking, completeOrder (+15) |
| `backend/src/main/java/com/aicoupledish/service/impl/ChallengeServiceImpl.java` | getChallengeDetail, convertToChallengeDTO, convertToCheckinRecordDTO, convertToCheckinRecordDTOWithCache, getStatusDesc (+13) |
| `backend/src/main/java/com/aicoupledish/service/impl/RecipeServiceImpl.java` | updateRecipe, deleteRecipe, publishRecipe, getRecipeDetail, uncollectRecipe (+12) |
| `backend/src/main/java/com/aicoupledish/service/impl/DeepQaServiceImpl.java` | getCurrentQuestion, submitAnswer, getProgress, skipQuestion, getOrCreateProgress (+9) |
| `backend/src/main/java/com/aicoupledish/service/impl/SweetBombServiceImpl.java` | getUnreadBombs, markAsRead, answerBomb, getBombHistory, getUnreadCount (+9) |
| `backend/src/main/java/com/aicoupledish/service/impl/CoupleTreeServiceImpl.java` | waterTree, addNutrient, getNutrientLogs, calculateLevel, getUserById (+9) |
| `backend/src/main/java/com/aicoupledish/service/impl/LoveCalendarServiceImpl.java` | getCalendar, getUpcomingEvents, getYearOverview, isLoveAnniversary, getUserById (+8) |
| `backend/src/main/java/com/aicoupledish/service/impl/CoupleRankServiceImpl.java` | getRankInfo, getUserById, buildDTO, getTemperatureLevel, getRankRewards (+8) |
| `backend/src/main/java/com/aicoupledish/service/OrderService.java` | cancelOrder, acceptOrder, startCooking, finishCooking, completeOrder (+7) |
| `backend/src/main/java/com/aicoupledish/controller/OrderController.java` | cancelOrder, acceptOrder, startCooking, finishCooking, completeOrder (+7) |

## Entry Points

Start here when exploring this area:

- **`AnniversaryDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/AnniversaryDTO.java:7`
- **`Anniversary`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/Anniversary.java:12`
- **`DeepQaAnswer`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/DeepQaAnswer.java:11`
- **`CoupleQaProgress`** (Class) — `backend/src/main/java/com/aicoupledish/dao/model/CoupleQaProgress.java:11`
- **`RecipeDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/RecipeDTO.java:10`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `AnniversaryDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/AnniversaryDTO.java` | 7 |
| `Anniversary` | Class | `backend/src/main/java/com/aicoupledish/dao/model/Anniversary.java` | 12 |
| `DeepQaAnswer` | Class | `backend/src/main/java/com/aicoupledish/dao/model/DeepQaAnswer.java` | 11 |
| `CoupleQaProgress` | Class | `backend/src/main/java/com/aicoupledish/dao/model/CoupleQaProgress.java` | 11 |
| `RecipeDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/RecipeDTO.java` | 10 |
| `TimeCapsuleDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/TimeCapsuleDTO.java` | 11 |
| `RelationshipWeatherDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/RelationshipWeatherDTO.java` | 10 |
| `RelationshipWeather` | Class | `backend/src/main/java/com/aicoupledish/dao/model/RelationshipWeather.java` | 11 |
| `OrderDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/OrderDTO.java` | 10 |
| `LoveCalendarDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/LoveCalendarDTO.java` | 12 |
| `DeepQaDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/DeepQaDTO.java` | 10 |
| `PosterDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/PosterDTO.java` | 11 |
| `TreeNutrientLog` | Class | `backend/src/main/java/com/aicoupledish/dao/model/TreeNutrientLog.java` | 11 |
| `CheckinRecordDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/CheckinRecordDTO.java` | 10 |
| `ChallengeDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/ChallengeDTO.java` | 11 |
| `CoupleCodeDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/CoupleCodeDTO.java` | 7 |
| `StatsDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/StatsDTO.java` | 7 |
| `CoupleHomeDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/CoupleHomeDTO.java` | 7 |
| `WishDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/WishDTO.java` | 9 |
| `HeartMoment` | Class | `backend/src/main/java/com/aicoupledish/dao/model/HeartMoment.java` | 11 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `GetTodayEvents → GetLeapMonth` | cross_community | 9 |
| `GetCalendar → GetLeapMonth` | cross_community | 8 |
| `GetEventsByDate → GetLeapMonth` | cross_community | 8 |
| `GetUpcomingEvents → GetLeapMonth` | cross_community | 8 |
| `GetYearOverview → GetLeapMonth` | cross_community | 8 |
| `GetEventsByDateRange → GetLeapMonth` | cross_community | 7 |
| `GetTodayEvents → GetLunarMonthDays` | cross_community | 7 |
| `WechatLogin → GetUserById` | cross_community | 6 |
| `PhoneLogin → GetUserById` | cross_community | 6 |
| `GetUserInfo → GetUserById` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Controller | 91 calls |
| Aicoupledish | 8 calls |
| Task | 5 calls |
| Service | 4 calls |
| Exception | 1 calls |
| Dto | 1 calls |

## How to Explore

1. `gitnexus_context({name: "AnniversaryDTO"})` — see callers and callees
2. `gitnexus_query({query: "impl"})` — find related execution flows
3. Read key files listed above for implementation details
