# SRS-011: 简化配置文件结构

## 1. 需求背景

当前 `backend/src/main/resources/` 目录下存在多个 `application-*.yml` 配置文件，配置存在重复，部分配置冗余，增加了维护成本和出错概率。

## 2. 当前问题

### 2.1 配置文件列表

```
resources/
├── application.yml          # 主配置（包含默认配置）
├── application-dev.yml      # 开发环境
├── application-local.yml     # 本地环境
└── application-prod.yml     # 生产环境
```

### 2.2 问题分析

| 问题 | 说明 |
|------|------|
| 配置重复 | 多个文件有相同的配置项 |
| 优先级不清晰 | 难以确定最终生效的配置 |
| profile 切换复杂 | 需要手动指定或配置 Maven |
| 本地/开发配置混淆 | local 和 dev 边界不明确 |

### 2.3 当前 application.yml 示例

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/aicoupledish
    username: root
    password: ${DB_PASSWORD}
  redis:
    host: localhost
    password: ${REDIS_PASSWORD}

jwt:
  secret: ${JWT_SECRET}
  expiration: 86400000

mybatis-plus:
  configuration:
    log-impl: org.apache.ibatis.logging.stdout
```

## 3. 解决方案

### 3.1 简化后的结构

```
resources/
├── application.yml          # 公共默认配置
├── application-dev.yml      # 开发环境覆盖
├── application-local.yml    # 本地环境覆盖（IDE直接运行）
└── application-prod.yml    # 生产环境覆盖
```

### 3.2 原则

1. **公共配置放主文件**：所有环境共同的配置放在 `application.yml`
2. **差异化配置放 profile**：仅覆盖需要不同的配置
3. **敏感信息不写文件**：通过环境变量或 `-D` 参数传入
4. **使用 Maven Profile 切换**：在 `pom.xml` 中配置

### 3.3 配置示例

**application.yml（公共配置）**
```yaml
spring:
  application:
    name: ai-couple-dish
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:dev}

  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5

  redis:
    lettuce:
      pool:
        max-active: 8
        max-idle: 8

mybatis-plus:
  configuration:
    map-underscore-to-camel-case: true
  global-config:
    db-config:
      logic-delete-field: isDeleted
      logic-delete-value: 1
      logic-not-delete-value: 0
```

**application-dev.yml（开发环境）**
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/aicoupledish?useUnicode=true&characterEncoding=utf8
  redis:
    host: localhost
    port: 6379

server:
  port: 8080

jwt:
  secret: ${JWT_SECRET:dev_secret_change_me}
  expiration: 86400000

logging:
  level:
    com.aicoupledish: DEBUG
    com.aicoupledish.dao: DEBUG
```

**application-prod.yml（生产环境）**
```yaml
spring:
  datasource:
    url: jdbc:mysql://${DB_HOST}:${DB_PORT}/${DB_NAME}?useUnicode=true&characterEncoding=utf8&useSSL=true
  redis:
    host: ${REDIS_HOST}
    port: ${REDIS_PORT}
    password: ${REDIS_PASSWORD}
    ssl: true

server:
  port: ${SERVER_PORT:8080}

jwt:
  secret: ${JWT_SECRET}
  expiration: ${JWT_EXPIRATION:86400000}

logging:
  level:
    com.aicoupledish: INFO
  file:
    name: /var/log/aicoupledish/application.log
```

## 4. 验收标准

- [ ] 移除 `application.yml` 中的冗余配置
- [ ] 确保 dev/local/prod profile 覆盖正确的配置
- [ ] 敏感信息全部使用环境变量
- [ ] 配置 Maven Profile 支持 `mvn spring-boot:run -Pdev`
- [ ] 更新部署文档说明 profile 切换方式
- [ ] 测试各 profile 启动正常

## 5. 影响范围

- `backend/src/main/resources/application.yml`
- `backend/src/main/resources/application-dev.yml`
- `backend/src/main/resources/application-local.yml`
- `backend/src/main/resources/application-prod.yml`
- `backend/pom.xml`

## 6. 优先级

**P2** - 低优先级

## 7. 预计工时

3-4 小时
