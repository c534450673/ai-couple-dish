---
name: dto
description: "Skill for the Dto area of ai-couple-dish. 8 symbols across 7 files."
---

# Dto

8 symbols | 7 files | Cohesion: 75%

## When to Use

- Working with code in `backend/`
- Understanding how PartnerInfoDTO, CoupleInfoDTO, ReferralDTO work
- Modifying dto-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/service/impl/CoupleServiceImpl.java` | checkRecoverableData, buildCoupleInfoDTO |
| `backend/src/main/java/com/aicoupledish/service/CoupleService.java` | checkRecoverableData |
| `backend/src/main/java/com/aicoupledish/controller/CoupleController.java` | checkRecoverableData |
| `backend/src/main/java/com/aicoupledish/domain/dto/PartnerInfoDTO.java` | PartnerInfoDTO |
| `backend/src/main/java/com/aicoupledish/domain/dto/CoupleInfoDTO.java` | CoupleInfoDTO |
| `backend/src/main/java/com/aicoupledish/domain/dto/ReferralDTO.java` | ReferralDTO |
| `backend/src/main/java/com/aicoupledish/service/impl/InviteServiceImpl.java` | buildReferralDTO |

## Entry Points

Start here when exploring this area:

- **`PartnerInfoDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/PartnerInfoDTO.java:7`
- **`CoupleInfoDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/CoupleInfoDTO.java:7`
- **`ReferralDTO`** (Class) — `backend/src/main/java/com/aicoupledish/domain/dto/ReferralDTO.java:10`
- **`checkRecoverableData`** (Method) — `backend/src/main/java/com/aicoupledish/service/CoupleService.java:63`
- **`checkRecoverableData`** (Method) — `backend/src/main/java/com/aicoupledish/controller/CoupleController.java:112`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `PartnerInfoDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/PartnerInfoDTO.java` | 7 |
| `CoupleInfoDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/CoupleInfoDTO.java` | 7 |
| `ReferralDTO` | Class | `backend/src/main/java/com/aicoupledish/domain/dto/ReferralDTO.java` | 10 |
| `checkRecoverableData` | Method | `backend/src/main/java/com/aicoupledish/service/CoupleService.java` | 63 |
| `checkRecoverableData` | Method | `backend/src/main/java/com/aicoupledish/controller/CoupleController.java` | 112 |
| `checkRecoverableData` | Method | `backend/src/main/java/com/aicoupledish/service/impl/CoupleServiceImpl.java` | 470 |
| `buildCoupleInfoDTO` | Method | `backend/src/main/java/com/aicoupledish/service/impl/CoupleServiceImpl.java` | 609 |
| `buildReferralDTO` | Method | `backend/src/main/java/com/aicoupledish/service/impl/InviteServiceImpl.java` | 387 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `WechatLogin → CoupleInfoDTO` | cross_community | 6 |
| `WechatLogin → GetUserById` | cross_community | 6 |
| `WechatLogin → PartnerInfoDTO` | cross_community | 6 |
| `PhoneLogin → CoupleInfoDTO` | cross_community | 6 |
| `PhoneLogin → GetUserById` | cross_community | 6 |
| `PhoneLogin → PartnerInfoDTO` | cross_community | 6 |
| `GetUserInfo → CoupleInfoDTO` | cross_community | 6 |
| `GetUserInfo → GetUserById` | cross_community | 6 |
| `GetUserInfo → PartnerInfoDTO` | cross_community | 6 |
| `CheckRecoverableData → GetSigningKey` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Controller | 1 calls |
| Impl | 1 calls |

## How to Explore

1. `gitnexus_context({name: "PartnerInfoDTO"})` — see callers and callees
2. `gitnexus_query({query: "dto"})` — find related execution flows
3. Read key files listed above for implementation details
