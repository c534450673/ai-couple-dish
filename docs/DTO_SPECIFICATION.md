# DTO and Entity Specification

## Overview

This document defines the conventions for using DTOs (Data Transfer Objects), Entities, and Request objects in the backend project.

## Package Structure

```
com.aicoupledish.domain/
├── dto/           # Data Transfer Objects for responses
├── req/           # Request objects for API inputs
└── resp/          # Response wrappers (optional)

com.aicoupledish.dao.model/   # MyBatis Plus Entities
```

## Class Naming Conventions

| Type | Suffix | Example |
|------|--------|---------|
| Entity | (none) | `User`, `Menu` |
| DTO | `DTO` | `UserInfoDTO`, `MenuDTO` |
| Request | `Req` | `LoginReq`, `AddMenuReq` |
| Response | `Resp` | `LoginResp` |
| Query | `Query` | `MenuQuery`, `UserQuery` |
| VO | `VO` | `UserVO`, `MenuVO` |

## When to Use Each Type

### Entity (`dao.model`)

**Purpose**: Database table mapping

**Rules**:
- Use for MyBatis Plus operations only
- Do not expose directly in API responses
- Contains database column annotations (`@TableField`, etc.)
- Should implement `Serializable`

```java
@TableName("t_user")
public class User implements Serializable {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String nickName;
    // ... other fields
}
```

### DTO (`domain/dto`)

**Purpose**: Data returned to API clients

**Rules**:
- Use for API response data
- Can combine multiple entities
- Should not contain sensitive data (passwords, tokens)
- Use camelCase for field names (matches JSON convention)

```java
@Data
public class UserInfoDTO {
    private Long id;
    private String nickName;
    private String avatarUrl;
    private String phone;
    // ... only safe fields
}
```

### Req (`domain/req`)

**Purpose**: API request payload

**Rules**:
- Use for POST/PUT request bodies
- Add validation annotations (`@NotBlank`, `@NotNull`, etc.)
- Should be specific to each operation
- Do not reuse across unrelated endpoints

```java
@Data
public class AddMenuReq {
    @NotBlank(message = "Menu name cannot be empty")
    private String name;

    private String description;

    private String imageUrl;
}
```

### VO (`domain/vo` - View Object)

**Purpose**: Internal view representation

**Rules**:
- Use for complex view compositions
- Can include computed fields
- Used within service layer, not exposed directly

## Conversion Patterns

### Entity to DTO

Use MyBatis Plus `lambdaQuery` or manual mapping:

```java
// Manual mapping (recommended for simple cases)
public UserInfoDTO convertToDTO(User user) {
    UserInfoDTO dto = new UserInfoDTO();
    dto.setId(user.getId());
    dto.setNickName(user.getNickName());
    dto.setAvatarUrl(user.getAvatarUrl());
    return dto;
}

// Using BeanUtil (Hutool)
public UserInfoDTO convertToDTO(User user) {
    UserInfoDTO dto = new UserInfoDTO();
    BeanUtil.copyProperties(user, dto);
    return dto;
}
```

### DTO to Entity (for updates)

```java
public void updateEntityFromDTO(UserUpdateReq req, User user) {
    if (req.getNickName() != null) {
        user.setNickName(req.getNickName());
    }
    if (req.getAvatarUrl() != null) {
        user.setAvatarUrl(req.getAvatarUrl());
    }
}
```

## Field Naming

### Java to JSON

| Java Field | JSON Output |
|------------|-------------|
| `userId` | `userId` or `user_id` (configurable) |
| `nickName` | `nickName` |
| `createTime` | `createTime` |

### Guidelines

1. **Use camelCase** for Java field names
2. **Configure MyBatis Plus** to auto-convert underscore to camelCase:
   ```yaml
   mybatis-plus:
     configuration:
       map-underscore-to-camel-case: true
   ```
3. **Avoid abbreviations**: `userId` not `uid`
4. **Be consistent**: If one DTO uses `menuId`, all DTOs should use `menuId`

## Validation Rules

### Basic Validations

```java
@Data
public class AddMenuReq {
    @NotBlank(message = "Name cannot be empty")
    private String name;

    @NotNull(message = "Price cannot be null")
    @DecimalMin(value = "0.01", message = "Price must be greater than 0")
    private BigDecimal price;

    @Size(max = 500, message = "Description cannot exceed 500 characters")
    private String description;

    @Pattern(regexp = "^https?://.*", message = "Invalid image URL")
    private String imageUrl;
}
```

### Common Annotations

| Annotation | Use Case |
|------------|----------|
| `@NotNull` | Object cannot be null |
| `@NotBlank` | String cannot be empty or blank |
| `@NotEmpty` | Collection/Array cannot be empty |
| `@Min/@Max` | Number constraints |
| `@Size` | String/Collection length |
| `@Pattern` | Regex validation |
| `@Email` | Email format |
| `@Phone` | Phone number format |

## Security Considerations

### DO NOT include in DTOs:

- Passwords or hashed passwords
- Internal IDs that shouldn't be exposed
- Business logic internals
- Sensitive personal information beyond what's needed

### DO NOT include in Responses:

- Full entity objects
- Debug information
- Stack traces
- Internal error details

## Pagination

### Request Query Object

```java
@Data
public class MenuQuery {
    private Integer page = 1;
    private Integer pageSize = 20;
    private String keyword;
    private Long categoryId;
}
```

### Paginated Response

```java
@Data
public class PageDTO<T> {
    private List<T> list;
    private Long total;
    private Integer page;
    private Integer pageSize;
    private Integer totalPages;
}
```

## Best Practices

1. **One DTO per response type**: Don't reuse DTOs across unrelated endpoints
2. **Separate read and write models**: Don't expose entities directly
3. **Validate early**: Add validation in Req classes, not in service
4. **Use interfaces**: Consider using interfaces for DTOs if you need multiple implementations
5. **Document complex DTOs**: Add Javadoc for non-obvious fields
6. **Keep DTOs flat**: Avoid deeply nested DTOs when possible
7. **Use conversion methods**: Create explicit conversion methods rather than relying on reflection

## Anti-Patterns to Avoid

❌ **Don't expose Entity directly**:
```java
// BAD
@PostMapping("/user")
public User createUser(@RequestBody User user) {
    return userService.create(user);
}
```

✅ **Use DTO**:
```java
// GOOD
@PostMapping("/user")
public UserInfoDTO createUser(@RequestBody @Valid CreateUserReq req) {
    return userService.create(req);
}
```

❌ **Don't use Entity for both input and output**:
```java
// BAD - mixing concerns
public class User {
    private Long id;
    private String password;  // Should not be here for API
    private String confirmPassword;  // Only for input
}
```

✅ **Separate concerns**:
```java
// GOOD
public class User extends BaseEntity { ... }  // Entity
public class UserDTO { ... }  // Output
public class CreateUserReq { ... }  // Input
```
