# SRS-010: 升级技术栈版本

## 1. 需求背景

当前项目使用的部分技术栈版本较旧，可能存在：
- 已知的安全漏洞
- 缺少新特性支持
- 社区支持逐渐减少
- 与新版依赖的兼容性问题

## 2. 当前问题

### 2.1 版本现状

| 组件 | 当前版本 | 最新 LTS | 差距 |
|------|----------|----------|------|
| Spring Boot | 2.7.18 | 3.2.x | 大版本升级 |
| MyBatis Plus | 3.5.3.1 | 3.5.5+ | 小版本 |
| Vue | 3.4.21 | 3.4.x | 较新 |
| Vite | 5.2.6 | 5.x | 较新 |
| Java | 17 | 21 | 可升级 |

### 2.2 升级风险评估

**Spring Boot 2.x -> 3.x 风险较高**
- 需要 Java 17+（当前 17 可满足）
- 需要修改 javax.* -> jakarta.* 命名空间
- 部分第三方库可能不兼容
- 需要全面回归测试

**MyBatis Plus 3.5.x -> 3.5.5+ 风险较低**
- 主要是 bug 修复
- 向后兼容

## 3. 解决方案

### 3.1 短期：安全补丁和小版本升级

立即执行：

```xml
<!-- pom.xml -->
<properties>
    <spring-boot.version>2.7.18</spring-boot.version>  <!-- 检查是否有 2.7.19 -->
    <mybatis-plus.version>3.5.5</mybatis-plus.version>
</properties>
```

### 3.2 中期：全面升级（计划中）

制定升级路线图：

```
Phase 1: 依赖版本审计
  - 执行 mvn dependency:update
  - 检查每个依赖的兼容版本

Phase 2: 测试覆盖增强
  - 添加集成测试
  - 添加 API 自动化测试
  - 确保测试覆盖率 > 70%

Phase 3: 小版本升级
  - Spring Boot 2.7.18 -> 2.7.19（如有）
  - MyBatis Plus 升级到最新

Phase 4: 大版本升级（可选）
  - Spring Boot 3.x 升级
  - 需要 Java 17 -> 21
  - 需要 6-12 个月准备
```

### 3.3 依赖版本检查脚本

```bash
#!/bin/bash
# scripts/check-dependencies.sh

echo "=== Spring Boot Version ==="
grep -A1 "spring-boot-dependencies" pom.xml | head -2

echo "=== Checking for updates ==="
mvn versions:display-dependency-updates
```

## 4. 验收标准

- [ ] 执行 `mvn dependency:analyze` 检查依赖版本
- [ ] 升级 MyBatis Plus 到最新补丁版本
- [ ] 升级其他小版本依赖
- [ ] 单元测试全部通过
- [ ] 集成测试全部通过
- [ ] 记录所有版本变更到 CHANGELOG.md

## 5. 影响范围

- `backend/pom.xml`
- 可能影响所有依赖这些库的功能

## 6. 优先级

**P2** - 低优先级（但建议尽快处理）

## 7. 预计工时

2-4 小时（小版本升级）
8-16 小时（完整大版本升级，需要单独立项）

## 8. 注意事项

- 大版本升级需要预留充足时间
- 建议在低峰期进行升级
- 准备好回滚方案
