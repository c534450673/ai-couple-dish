# SRS-015: 统一代码命名规范

## 1. 需求背景

当前代码中存在命名不一致的问题，影响代码可读性和维护效率：
- Controller 使用中文注释
- 部分变量命名混合中英文
- 包名和类名风格不统一

## 2. 当前问题

### 2.1 混合命名示例

| 问题 | 当前 | 建议 |
|------|------|------|
| Controller 注释 | `// 根据ID删除菜单` | `// Delete menu by ID` |
| 方法名 | `getMenuById` | 保持现有（已正确） |
| 变量名 | `menuIdArray` | `menuIds` |
| 包名 | `com.aicoupledish` | 保持现有 |

### 2.2 统一性问题

- Java 代码使用驼峰命名
- 数据库字段使用下划线
- API 响应字段应统一（建议驼峰）
- 常量命名应统一大写加下划线

## 3. 解决方案

### 3.1 制定命名规范

**Java 代码规范**

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | UpperCamelCase | `UserController` |
| 方法名 | lowerCamelCase | `getUserById` |
| 变量名 | lowerCamelCase | `userId`, `menuList` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 包名 | lowercase | `com.aicoupledish.common` |

**数据库规范**

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | t_小写蛇形 | `t_user`, `t_couple_menu` |
| 字段名 | 小写蛇形 | `user_id`, `create_time` |
| 索引名 | idx_表名_字段 | `idx_user_id` |

**API 响应规范**

- 使用驼峰命名（JSON 标准）
- 配置 Jackson 处理下划线到驼峰的转换

### 3.2 代码审查清单

创建 `docs/CODE_STYLE.md`：

```markdown
# 代码风格指南

## 命名规范

### Java

- 类名：UpperCamelCase
- 方法、变量：lowerCamelCase
- 常量：UPPER_SNAKE_CASE
- 包名：全小写

### 数据库

- 表名：t_小写蛇形
- 字段：小写蛇形

### API

- JSON 字段：camelCase
- 配置 MyBatis Plus map-underscore-to-camel-case: true

## 注释规范

- 使用英文注释
- 类和方法添加 Javadoc
- 复杂逻辑添加行内注释
```

### 3.3 批量修复

使用 IDE 的代码检查功能批量修复：
1. 搜索中文注释
2. 转换为英文
3. 注意保留业务含义

## 4. 验收标准

- [ ] 创建 `docs/CODE_STYLE.md` 命名规范文档
- [ ] 所有新的代码提交遵循命名规范
- [ ] CI 中添加命名规范检查（如启用）
- [ ] 关键类和方法有英文注释
- [ ] API 响应统一使用驼峰命名

## 5. 影响范围

- 所有 Java 源代码
- `docs/CODE_STYLE.md`（新建）

## 6. 优先级

**P3** - 低优先级（渐进式改进）

## 7. 预计工时

持续改进，无需集中工时投入
