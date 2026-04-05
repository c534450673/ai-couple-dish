# SRS-004: 提取用户认证逻辑到 AOP 切面

## 1. 需求背景

当前每个 Controller 都直接通过 `HttpServletRequest` 获取 token 并解析用户 ID，代码重复且难以维护。如果认证逻辑需要变更（如添加权限校验），需要修改所有 Controller。

## 2. 当前问题

**位置**: 多个 Controller 中，例如 `MenuController.java` 第 123-129 行：

```java
@PostMapping("/add")
public Resp<Void> addMenu(HttpServletRequest request, @RequestBody MenuAddReq req) {
    String token = request.getHeader("Authorization");
    Long userId = jwtService.parseToken(token);
    // ... 业务逻辑
}
```

问题：
- 认证逻辑与业务逻辑混杂
- 代码重复，每个接口都要写相同的三行代码
- 无法统一进行认证校验（如白名单、限流）
- 测试困难

## 3. 解决方案

### 3.1 创建自定义注解

**新建**: `common/annotation/Authenticated.java`

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Authenticated {
    boolean required() default true;
}
```

### 3.2 创建 AOP 切面

**新建**: `common/aspect/AuthAspect.java`

```java
@Aspect
@Component
public class AuthAspect {

    @Autowired
    private HttpServletRequest request;

    @Autowired
    private JwtService jwtService;

    @Pointcut("@annotation(com.aicoupledish.common.annotation.Authenticated)")
    public void authPointcut() {}

    @Around("authPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        String token = request.getHeader("Authorization");

        if (token == null || token.isEmpty()) {
            throw new BizException(RespCode.UNAUTHORIZED, "请先登录");
        }

        Long userId = jwtService.parseToken(token);
        // 将用户ID存入 ThreadLocal 供后续使用
        UserContext.setUserId(userId);

        try {
            return joinPoint.proceed();
        } finally {
            UserContext.clear();
        }
    }
}
```

### 3.3 创建用户上下文工具类

**新建**: `common/utils/UserContext.java`

```java
public class UserContext {
    private static final ThreadLocal<Long> userIdHolder = new ThreadLocal<>();

    public static void setUserId(Long userId) {
        userIdHolder.set(userId);
    }

    public static Long getUserId() {
        return userIdHolder.get();
    }

    public static void clear() {
        userIdHolder.remove();
    }
}
```

### 3.4 重构 Controller

将所有需要认证的接口添加 `@Authenticated` 注解，移除手动的 token 解析代码：

```java
@PostMapping("/add")
@Authenticated
public Resp<Void> addMenu(@RequestBody MenuAddReq req) {
    Long userId = UserContext.getUserId();  // 从 ThreadLocal 获取
    // ... 业务逻辑
}
```

## 4. 验收标准

- [ ] 新建 `Authenticated` 注解
- [ ] 新建 `AuthAspect` 切面类
- [ ] 新建 `UserContext` 工具类
- [ ] 所有需要认证的 Controller 方法添加 `@Authenticated` 注解
- [ ] 移除 Controller 中手动的 token 解析代码
- [ ] 编写单元测试验证认证逻辑
- [ ] 无需认证的接口（如登录、注册）不受影响

## 5. 影响范围

- `backend/src/main/java/com/aicoupledish/common/annotation/Authenticated.java`（新建）
- `backend/src/main/java/com/aicoupledish/common/aspect/AuthAspect.java`（新建）
- `backend/src/main/java/com/aicoupledish/common/utils/UserContext.java`（新建）
- 所有需要认证的 Controller

## 6. 优先级

**P1** - 中优先级

## 7. 预计工时

4-6 小时
