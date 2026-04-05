# Technical Stack Upgrade Guide

## Upgrade Plan

This document outlines the planned upgrades for the project dependencies.

### Backend Dependencies

| Dependency | Current | Target | Notes |
|------------|---------|--------|-------|
| Spring Boot | 2.7.18 | 3.2.x | Requires Java 17+ |
| Java | 17 | 21 | LTS version |
| MyBatis Plus | 3.5.3.1 | 3.5.7 | Compatible |
| JWT (jjwt) | 0.11.5 | 0.12.x | API changes |
| Knife4j | 4.3.0 | 4.5.0 | For Spring Boot 3 |
| Hutool | 5.8.22 | 5.8.30 | Latest stable |
| MySQL Driver | 8.0.33 | 8.4 LTS | Latest stable |
| Redis | 6.x | 7.x | Latest stable |

### Frontend Dependencies

| Package | Current | Target |
|---------|---------|--------|
| Vue | 3.4.21 | 3.5.x |
| Vite | 5.2.6 | 5.4.x |
| Vant | 4.9.0 | 4.12.x |
| Pinia | 2.1.7 | 2.2.x |
| Axios | 1.6.8 | 1.7.x |

## Critical Changes for Spring Boot 3.x

### 1. Java Package Migration

```java
// Spring Boot 2.x
import javax.servlet.http.HttpServletRequest;

// Spring Boot 3.x
import jakarta.servlet.http.HttpServletRequest;
```

All `javax.*` imports must be changed to `jakarta.*` for:
- Servlet APIs
- Validation APIs
- Persistence APIs (JPA)

### 2. Configuration Changes

```yaml
# Spring Boot 2.x
spring:
  servlet:
    multipart:
      max-file-size: 10MB

# Spring Boot 3.x (unchanged)
spring:
  servlet:
    multipart:
      max-file-size: 10MB
```

### 3. Redis Configuration

```java
// Spring Boot 2.x - Lettuce is default
spring.data.redis.host=localhost

// Spring Boot 3.x - Configuration similar
spring.data.redis.host=localhost
spring.data.redis.timeout=10s
```

### 4. JWT API Changes

```java
// Spring Boot 2.x (jjwt 0.11.x)
Jwts.builder()
    .setClaims(claims)
    .signWith(SignatureAlgorithm.HS512, key)
    .compact();

// Spring Boot 3.x (jjwt 0.12.x)
Jwts.builder()
    .claims(claims)
    .signWith(key, Jwts.SIG.HS512)
    .compact();
```

### 5. MyBatis Plus Changes

Mostly compatible, but verify:
- Update `lambdaQuery` usage
- Check annotation changes

## Upgrade Steps

### Phase 1: Preparation

1. [ ] Run all existing tests
2. [ ] Create backup branch
3. [ ] Document current API usage

### Phase 2: Backend Upgrade

1. [ ] Update pom.xml versions
2. [ ] Fix javax → jakarta imports
3. [ ] Update JWT API calls
4. [ ] Update Redis configuration if needed
5. [ ] Run tests and fix failures
6. [ ] Update Dockerfile for Java 21

### Phase 3: Frontend Upgrade

1. [ ] Update package.json versions
2. [ ] Run `npm update`
3. [ ] Test all features
4. [ ] Fix any breaking changes

### Phase 4: Verification

1. [ ] Full test suite passes
2. [ ] Manual testing of critical flows
3. [ ] Performance testing
4. [ ] Security review

## Rollback Plan

If upgrade fails:
1. Revert pom.xml changes
2. Revert package.json changes
3. Restore from backup branch

## Estimated Timeline

- Backend upgrade: 4-6 hours
- Frontend upgrade: 2-3 hours
- Testing: 2-3 hours
- Total: 1-2 days
