---
name: interceptor
description: "Skill for the Interceptor area of ai-couple-dish. 13 symbols across 4 files."
---

# Interceptor

13 symbols | 4 files | Cohesion: 81%

## When to Use

- Working with code in `backend/`
- Understanding how createToken, getUserIdFromToken, getClaimsFromToken work
- Modifying interceptor-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | createToken, getUserIdFromToken, getClaimsFromToken, validateToken, isTokenExpired (+2) |
| `backend/src/main/java/com/aicoupledish/common/interceptor/RateLimitInterceptor.java` | preHandle, buildKey, getClientIp |
| `backend/src/test/java/com/aicoupledish/RateLimitInterceptorTest.java` | rateLimit_NotHandlerMethod_ShouldPass, rateLimit_UnderLimit_ShouldPass |
| `backend/src/main/java/com/aicoupledish/common/interceptor/AuthInterceptor.java` | preHandle |

## Entry Points

Start here when exploring this area:

- **`createToken`** (Method) — `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java:62`
- **`getUserIdFromToken`** (Method) — `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java:78`
- **`getClaimsFromToken`** (Method) — `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java:97`
- **`validateToken`** (Method) — `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java:113`
- **`isTokenExpired`** (Method) — `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java:129`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `createToken` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 62 |
| `getUserIdFromToken` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 78 |
| `getClaimsFromToken` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 97 |
| `validateToken` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 113 |
| `isTokenExpired` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 129 |
| `refreshToken` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 141 |
| `getSigningKey` | Method | `backend/src/main/java/com/aicoupledish/common/utils/JwtUtils.java` | 150 |
| `preHandle` | Method | `backend/src/main/java/com/aicoupledish/common/interceptor/AuthInterceptor.java` | 35 |
| `preHandle` | Method | `backend/src/main/java/com/aicoupledish/common/interceptor/RateLimitInterceptor.java` | 52 |
| `buildKey` | Method | `backend/src/main/java/com/aicoupledish/common/interceptor/RateLimitInterceptor.java` | 90 |
| `getClientIp` | Method | `backend/src/main/java/com/aicoupledish/common/interceptor/RateLimitInterceptor.java` | 115 |
| `rateLimit_NotHandlerMethod_ShouldPass` | Method | `backend/src/test/java/com/aicoupledish/RateLimitInterceptorTest.java` | 49 |
| `rateLimit_UnderLimit_ShouldPass` | Method | `backend/src/test/java/com/aicoupledish/RateLimitInterceptorTest.java` | 59 |

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
| Aicoupledish | 1 calls |
| Exception | 1 calls |

## How to Explore

1. `gitnexus_context({name: "createToken"})` — see callers and callees
2. `gitnexus_query({query: "interceptor"})` — find related execution flows
3. Read key files listed above for implementation details
