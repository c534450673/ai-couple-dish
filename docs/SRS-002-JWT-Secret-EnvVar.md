# SRS-002: JWT Secret 生产环境强制使用环境变量

## 1. 需求背景

当前 `application.yml` 中 JWT Secret 配置了默认的静态值作为 fallback，生产环境使用默认 Secret 会导致严重的安全风险。攻击者可能利用这个已知 Secret 伪造 Token。

## 2. 当前问题

**位置**: `backend/src/main/resources/application.yml`

```yaml
jwt:
  secret: ${JWT_SECRET:aiCoupleDishSecretKey2024VeryLongAndSecureKeyThatIsAtLeast64CharactersLongForHS512Algorithm}
```

问题：
- 生产环境如果未设置 `JWT_SECRET` 环境变量，会使用默认的已知值
- 应用启动时不会对默认 Secret 进行警告
- 无法追踪哪些环境在使用默认 Secret

## 3. 解决方案

### 方案 A: 应用启动校验（推荐）

在应用启动时检测是否使用了默认 Secret：

```java
@Configuration
public class JwtSecretValidator implements ApplicationRunner {
    @Value("${jwt.secret}")
    private String jwtSecret;

    @Override
    public void run(ApplicationArguments args) {
        String defaultSecret = "aiCoupleDishSecretKey2024...";
        if (jwtSecret.equals(defaultSecret)) {
            throw new IllegalStateException(
                "FATAL: JWT Secret is using default value. " +
                "Please set JWT_SECRET environment variable."
            );
        }
    }
}
```

### 方案 B: 移除默认值

将配置改为必须指定：

```yaml
jwt:
  secret: ${JWT_SECRET}  # 无默认值，缺失则启动失败
```

## 4. 验收标准

- [ ] 生产环境配置文件（application-prod.yml）中 JWT Secret 无默认值
- [ ] 应用启动时校验 Secret 是否为默认值
- [ ] 使用默认值时应用启动失败并给出明确错误提示
- [ ] 部署文档说明必须设置 JWT_SECRET 环境变量

## 5. 影响范围

- `backend/src/main/resources/application.yml`
- `backend/src/main/resources/application-prod.yml`
- `backend/src/main/java/com/aicoupledish/common/config/JwtSecretValidator.java`（新建）

## 6. 优先级

**P0** - 紧急安全漏洞

## 7. 预计工时

2-3 小时
