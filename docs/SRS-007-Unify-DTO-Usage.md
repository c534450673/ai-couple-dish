# SRS-007: 统一 DTO 和 Entity 使用规范

## 1. 需求背景

当前部分 Controller 直接使用 Entity 进行数据传输，导致：
- 数据库结构与 API 契约耦合
- API 变更可能影响数据库设计
- 无法进行 API 层面的数据转换和验证
- 潜在的序列化问题（Entity 可能包含不该暴露的字段）

## 2. 当前问题

### 2.1 Entity 直接暴露

部分 Controller 直接返回 Entity：

```java
@GetMapping("/{id}")
public Resp<FoodNote> getNote(@PathVariable Long id) {
    FoodNote note = foodNoteService.getById(id);
    return Resp.success(note);  // 直接返回 Entity
}
```

### 2.2 问题风险

| 风险 | 说明 |
|------|------|
| 字段暴露 | Entity 中的 `password`、`isDeleted` 等敏感字段可能被序列化 |
| 循环引用 | Entity 间的关联关系可能导致 JSON 序列化死循环 |
| API 稳定性 | 数据库字段变更直接导致 API 变更 |
| 验证缺失 | 无法在 API 层进行独立的参数校验 |

### 2.3 现有分层

```
Controller -> Service -> DAO
                |
              Entity (DB)
```

## 3. 解决方案

### 3.1 完善分层架构

```
Controller -> Req/Resp DTO -> Service -> Domain DTO -> DAO
                                      |
                                    Entity (DB)
```

### 3.2 创建统一 DTO 包

```
/common/req/      # 请求 DTO
  MenuAddReq.java
  MenuQueryReq.java

/common/resp/     # 响应 DTO
  MenuResp.java
  FoodNoteResp.java

/domain/          # 领域 DTO（可选，用于服务间通信）
```

### 3.3 使用 MapStruct 简化转换

添加 MapStruct 依赖，自动处理 Entity <-> DTO 转换：

```xml
<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>1.5.5.Final</version>
</dependency>
```

转换接口：

```java
@Mapper(componentModel = "spring")
public interface MenuConverter {
    MenuResp toResp(Menu entity);
    Menu toEntity(MenuAddReq req);
}
```

### 3.4 配置 Jackson 忽略敏感字段

在 Entity 上使用 `@JsonIgnore` 或 `@JsonIgnoreProperties`：

```java
public class User {
    @JsonIgnore
    private String password;

    @JsonIgnore
    private String isDeleted;
}
```

## 4. 验收标准

- [ ] 所有 Controller 方法使用 Req DTO 接收参数
- [ ] 所有 Controller 方法使用 Resp DTO 返回数据
- [ ] Entity 中的敏感字段添加 `@JsonIgnore`
- [ ] 创建 MapStruct 转换器（如采用）
- [ ] API 文档更新，反映新的响应结构
- [ ] 确保没有循环引用导致的序列化问题

## 5. 影响范围

- `common/req/` - 新增 Request DTO
- `common/resp/` - 新增 Response DTO
- `common/converter/` - 新增转换器
- `dao/model/` - Entity 字段调整
- 所有 Controller

## 6. 优先级

**P1** - 中优先级

## 7. 预计工时

6-10 小时（取决于 Entity 和 Controller 的数量）
