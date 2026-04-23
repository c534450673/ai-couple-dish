---
name: exception
description: "Skill for the Exception area of ai-couple-dish. 16 symbols across 9 files."
---

# Exception

16 symbols | 9 files | Cohesion: 79%

## When to Use

- Working with code in `backend/`
- Understanding how cleanExpiredTasks, checkExpiration, cleanExpiredTasks work
- Modifying exception-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | handleUnauthorizedException, handleBusinessException, isAuthErrorCode, handleRuntimeException, handleException (+2) |
| `backend/src/main/java/com/aicoupledish/common/utils/Result.java` | error, badRequest |
| `backend/src/main/java/com/aicoupledish/task/DailyTaskGenerateTask.java` | cleanExpiredTasks |
| `backend/src/main/java/com/aicoupledish/task/CoupleCodeTask.java` | checkExpiration |
| `backend/src/main/java/com/aicoupledish/service/DailyTaskService.java` | cleanExpiredTasks |
| `backend/src/main/java/com/aicoupledish/service/CoupleService.java` | sendExpirationReminder |
| `backend/src/main/java/com/aicoupledish/service/impl/DailyTaskServiceImpl.java` | cleanExpiredTasks |
| `backend/src/main/java/com/aicoupledish/service/impl/CoupleServiceImpl.java` | sendExpirationReminder |
| `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | init |

## Entry Points

Start here when exploring this area:

- **`cleanExpiredTasks`** (Method) — `backend/src/main/java/com/aicoupledish/task/DailyTaskGenerateTask.java:51`
- **`checkExpiration`** (Method) — `backend/src/main/java/com/aicoupledish/task/CoupleCodeTask.java:21`
- **`cleanExpiredTasks`** (Method) — `backend/src/main/java/com/aicoupledish/service/DailyTaskService.java:44`
- **`sendExpirationReminder`** (Method) — `backend/src/main/java/com/aicoupledish/service/CoupleService.java:83`
- **`cleanExpiredTasks`** (Method) — `backend/src/main/java/com/aicoupledish/service/impl/DailyTaskServiceImpl.java:283`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `cleanExpiredTasks` | Method | `backend/src/main/java/com/aicoupledish/task/DailyTaskGenerateTask.java` | 51 |
| `checkExpiration` | Method | `backend/src/main/java/com/aicoupledish/task/CoupleCodeTask.java` | 21 |
| `cleanExpiredTasks` | Method | `backend/src/main/java/com/aicoupledish/service/DailyTaskService.java` | 44 |
| `sendExpirationReminder` | Method | `backend/src/main/java/com/aicoupledish/service/CoupleService.java` | 83 |
| `cleanExpiredTasks` | Method | `backend/src/main/java/com/aicoupledish/service/impl/DailyTaskServiceImpl.java` | 283 |
| `sendExpirationReminder` | Method | `backend/src/main/java/com/aicoupledish/service/impl/CoupleServiceImpl.java` | 771 |
| `error` | Method | `backend/src/main/java/com/aicoupledish/common/utils/Result.java` | 38 |
| `init` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 28 |
| `handleUnauthorizedException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 29 |
| `handleBusinessException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 38 |
| `isAuthErrorCode` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 59 |
| `handleRuntimeException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 90 |
| `handleException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 100 |
| `badRequest` | Method | `backend/src/main/java/com/aicoupledish/common/utils/Result.java` | 50 |
| `handleValidException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 66 |
| `handleBindException` | Method | `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java` | 78 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Task | 2 calls |

## How to Explore

1. `gitnexus_context({name: "cleanExpiredTasks"})` — see callers and callees
2. `gitnexus_query({query: "exception"})` — find related execution flows
3. Read key files listed above for implementation details
