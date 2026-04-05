# SRS-001: 修复开发环境 K8s Secret 明文密码问题

## 1. 需求背景

当前 `deploy/dev/k8s/secret.yaml` 文件中存储了数据库、Redis、JWT 等敏感信息以明文形式存在，这是严重的安全隐患。在 Git 版本控制中暴露明文密码，可能导致生产环境密钥泄露风险。

## 2. 当前问题

**位置**: `deploy/dev/k8s/secret.yaml`

```yaml
data:
  DB_PASSWORD: "dev_password_2024"
  REDIS_PASSWORD: "redis_dev_pass_2024"
  JWT_SECRET: "dev_jwt_secret_key_32_chars_minimum"
```

明文密码存在的问题：
- 密码在 Git 历史中永久留存
- 任何有代码仓库访问权限的人都能看到密码
- 无法实现密钥的定期轮换

## 3. 解决方案

### 方案 A: 使用 Kubernetes Secret（推荐）

1. 删除 `secret.yaml` 中的明文密码
2. 使用 `kubectl create secret` 命令创建 Secret
3. 在 `secret.yaml` 中仅保留注释说明如何创建 Secret

```bash
kubectl create secret generic ai-couple-dish-secrets \
  --from-literal=DB_PASSWORD='your_dev_password' \
  --from-literal=REDIS_PASSWORD='your_redis_password' \
  --from-literal=JWT_SECRET='your_jwt_secret'
```

### 方案 B: 使用 sealed-secrets

使用 Bitnami Sealed Secrets 将加密后的 Secret 提交到 Git。

## 4. 验收标准

- [ ] `deploy/dev/k8s/secret.yaml` 文件中不包含任何明文密码
- [ ] 添加 README 说明如何在本地创建 Secret
- [ ] 部署文档中包含 Secret 创建步骤
- [ ] CI/CD 流程验证 Secret 文件不包含敏感信息

## 5. 影响范围

- `deploy/dev/k8s/secret.yaml`
- `deploy/dev/k8s/README.md`（如需新建）

## 6. 优先级

**P0** - 紧急安全漏洞

## 7. 预计工时

1-2 小时
