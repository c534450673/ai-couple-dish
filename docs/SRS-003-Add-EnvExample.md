# SRS-003: 添加环境变量模板文件 .env.example

## 1. 需求背景

项目缺少环境变量配置模板，导致新开发者不清楚需要配置哪些环境变量，以及如何配置。这会影响开发效率，并可能导致配置错误。

## 2. 当前问题

- 项目根目录缺少 `.env.example` 文件
- 后端和前端各自有环境变量需求，但无统一说明
- 部署文档和代码中的环境变量名称可能不一致

## 3. 解决方案

### 3.1 创建根目录 .env.example

**位置**: `/Users/zhangsubo/ai-couple-dish/.env.example`

```bash
# ===================
# 后端服务配置
# ===================

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=aicoupledish
DB_USERNAME=root
DB_PASSWORD=your_password_here

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# JWT 配置（生产环境必须修改）
JWT_SECRET=your_jwt_secret_at_least_64_characters_long
JWT_EXPIRATION=86400000

# 服务器配置
SERVER_PORT=8080

# ===================
# 前端 H5 配置
# ===================
VITE_API_BASE_URL=http://localhost:8080/api
VITE_WS_URL=ws://localhost:8080/ws

# ===================
# 前端 UniApp 配置
# ===================
UNIAPP_API_BASE_URL=http://localhost:8080/api
```

### 3.2 创建各子项目的 .env.example

- `backend/.env.example`
- `frontend-h5/.env.example`
- `frontend-uniapp/.env.example`

### 3.3 更新文档

在 `docs/` 目录下添加 `ENVIRONMENT.md` 说明各环境变量的用途。

## 4. 验收标准

- [ ] 根目录存在 `.env.example` 文件
- [ ] 后端子目录存在 `.env.example` 文件
- [ ] 前端各版本目录存在 `.env.example` 文件
- [ ] `.gitignore` 中包含 `.env` 但排除 `.env.example`
- [ ] README 中链接到环境变量配置说明

## 5. 影响范围

- 新建 `.env.example` 文件（5个）
- 新建 `docs/ENVIRONMENT.md`
- 更新 `.gitignore`

## 6. 优先级

**P0** - 高优先级

## 7. 预计工时

1-2 小时
