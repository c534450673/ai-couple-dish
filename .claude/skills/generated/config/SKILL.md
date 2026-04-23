---
name: config
description: "Skill for the Config area of ai-couple-dish. 5 symbols across 1 files."
---

# Config

5 symbols | 1 files | Cohesion: 89%

## When to Use

- Working with code in `backend/`
- Understanding how validateSecurityConfig, isProductionEnvironment, validateJwtSecret work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | validateSecurityConfig, isProductionEnvironment, validateJwtSecret, isWeakSecret, buildProductionSecurityError |

## Entry Points

Start here when exploring this area:

- **`validateSecurityConfig`** (Method) — `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java:50`
- **`isProductionEnvironment`** (Method) — `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java:63`
- **`validateJwtSecret`** (Method) — `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java:68`
- **`isWeakSecret`** (Method) — `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java:114`
- **`buildProductionSecurityError`** (Method) — `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java:118`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `validateSecurityConfig` | Method | `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | 50 |
| `isProductionEnvironment` | Method | `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | 63 |
| `validateJwtSecret` | Method | `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | 68 |
| `isWeakSecret` | Method | `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | 114 |
| `buildProductionSecurityError` | Method | `backend/src/main/java/com/aicoupledish/common/config/SecurityConfigValidator.java` | 118 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Exception | 1 calls |

## How to Explore

1. `gitnexus_context({name: "validateSecurityConfig"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
