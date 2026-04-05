# Code Style Guide

## Overview

This guide defines naming conventions and coding standards for the AI Couple Dish project.

## Java Naming Conventions

### Classes and Interfaces

| Type | Convention | Example |
|------|------------|---------|
| Class | UpperCamelCase | `UserController`, `MenuService` |
| Interface | UpperCamelCase | `UserService`, `MenuRepository` |
| Enum | UpperCamelCase | `GenderEnum`, `OrderStatus` |
| Annotation | UpperCamelCase | `@RestController`, `@Component` |

### Methods

| Type | Convention | Example |
|------|------------|---------|
| Method | lowerCamelCase | `getUserById()`, `saveMenu()` |
| Private method | lowerCamelCase | `validateInput()`, `buildResponse()` |

### Variables

| Type | Convention | Example |
|------|------------|---------|
| Local variable | lowerCamelCase | `userId`, `menuList` |
| Parameter | lowerCamelCase | `userId`, `menuId` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE` |
| Boolean variable | lowerCamelCase with prefixes | `isLoggedIn`, `hasPermission` |

### Package Names

- Always lowercase: `com.aicoupledish.common.utils`
- Single word preferred for organization: `utils`, `controller`, `service`

### Database Naming (MyBatis Plus)

| Type | Convention | Example |
|------|------------|---------|
| Table | snake_case with prefix | `t_user`, `t_menu` |
| Column | snake_case | `user_id`, `create_time` |
| Index | idx_table_column | `idx_user_id` |

## JavaScript/TypeScript Naming Conventions

### Variables and Functions

| Type | Convention | Example |
|------|------------|---------|
| Variable | lowerCamelCase | `userId`, `menuList` |
| Function | lowerCamelCase | `getUserInfo()`, `saveMenu()` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Class | UpperCamelCase | `UserStore`, `MenuComponent` |

### Vue Components

| Type | Convention | Example |
|------|------------|---------|
| Single file component | PascalCase | `UserProfile.vue`, `MenuCard.vue` |
| Component variable | PascalCase | `const UserProfile = ref()` |

### API Modules

```javascript
// Good
export const userApi = {
  getUserInfo() { },
  updateUser() { }
}

// Avoid
export const UserAPI = { }  // Don't mix naming styles
```

## API Response Naming

### JSON Fields

Always use **camelCase** for JSON field names:

```json
{
  "userId": 123,
  "userName": "John",
  "coupleInfo": { },
  "createTime": "2024-01-01T00:00:00Z"
}
```

### Request Parameters

| Parameter | Type | Description |
|----------|------|-------------|
| page | Integer | Page number (1-indexed) |
| pageSize | Integer | Items per page |
| keyword | String | Search keyword |

## Comments

### JavaDoc for Public APIs

```java
/**
 * Get user information by user ID.
 *
 * @param userId the user ID
 * @return user information DTO
 * @throws UserNotFoundException if user does not exist
 */
public UserInfoDTO getUserById(Long userId) { }
```

### Inline Comments

```java
// Good: Explain WHY, not WHAT
// Use exponential backoff for retry
Thread.sleep(delay * retryCount);

// Avoid: Obvious comments
// Increment retry count
retryCount++;
```

## File Organization

### Java Files

```
com.aicoupledish/
├── controller/      # REST controllers
├── service/         # Service interfaces
│   └── impl/        # Service implementations
├── dao/
│   ├── mapper/      # MyBatis mappers
│   └── model/       # Entity classes
├── domain/
│   ├── dto/         # Data transfer objects
│   ├── req/         # Request objects
│   └── resp/        # Response objects
├── common/
│   ├── config/     # Configuration classes
│   ├── annotation/  # Custom annotations
│   ├── aspect/      # AOP aspects
│   ├── exception/   # Custom exceptions
│   ├── interceptor/ # Interceptors
│   └── utils/       # Utility classes
└── AiCoupleDishApplication.java
```

### Frontend Files

```
src/
├── api/           # API modules
├── assets/        # Static assets
├── components/    # Vue components
├── router/        # Vue Router config
├── stores/        # Pinia stores
├── utils/         # Utility functions
├── views/         # Page components
└── App.vue        # Root component
```

## Code Quality Rules

### DO

✅ Use meaningful variable names
✅ Keep methods small and focused
✅ Use early returns for guard clauses
✅ Use dependency injection
✅ Write unit tests for business logic

### DON'T

❌ Use magic numbers - use constants
❌ Leave commented-out code
❌ Use `var` in TypeScript
❌ Hardcode strings - use constants
❌ Create very long methods (>100 lines)

## ESLint/Prettier Configuration

See `.eslintrc.cjs` and `.prettierrc` in each frontend project for configuration.

## Git Commit Messages

Follow conventional commits:

```
feat: add user profile page
fix: resolve menu list pagination issue
docs: update API documentation
style: format code with prettier
refactor: extract authentication to AOP
test: add user service unit tests
chore: update dependencies
```
