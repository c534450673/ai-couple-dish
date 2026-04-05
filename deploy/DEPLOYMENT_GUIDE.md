# 情侣私密菜单 - 部署指南

> 文档版本：V2.0
> 更新日期：2026-03-21
> 部署模式：Docker Compose / Kubernetes

---

## 目录

1. [部署架构](#1-部署架构)
2. [开发环境部署](#2-开发环境部署)
3. [生产环境部署](#3-生产环境部署)
4. [一键部署脚本](#4-一键部署脚本)
5. [运维指南](#5-运维指南)

---

## 1. 部署架构

### 1.1 架构说明

```
┌─────────────────────────────────────────────────────────────────┐
│                         开发环境 (dev)                            │
│                                                                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│   │   MySQL │    │  Redis  │    │ Backend │ (本地嵌入式)       │
│   │ (本地)  │    │ (本地)  │    │         │                  │
│   └─────────┘    └─────────┘    └─────────┘                  │
│         │              │              │                         │
│         └──────────────┼──────────────┘                         │
│                        │                                         │
│                   Docker Compose                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         生产环境 (prod)                          │
│                                                                 │
│   云服务 (RDS/Redis)  ───  Kubernetes  ───  SLB/Ingress        │
│        │                      │                   │               │
│        ▼                      ▼                   ▼               │
│   ┌─────────┐           ┌─────────┐       ┌─────────┐         │
│   │  MySQL │           │ Backend │       │  Nginx  │         │
│   │ (云服务)│           │  (多副本)│       │ (代理)   │         │
│   └─────────┘           └─────────┘       └─────────┘         │
│                                                                 │
│   公共组件独立部署，业务组件按需扩缩                              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 环境差异

| 组件 | 开发环境 | 生产环境 |
|------|---------|---------|
| MySQL | 本地Docker Compose | 云数据库(RDS/CDB) |
| Redis | 本地Docker Compose | 云缓存(ApsaraDB/Redis) |
| Backend | 单副本 | 多副本+HPA |
| Nginx | 可选 | 必须 |
| Ingress | - | 云负载均衡 |

### 1.3 部署目录结构

```
deploy/
├── common/                    # 公共配置（两环境共用）
│   ├── backend/              # 后端K8s配置模板
│   └── init.sql             # 数据库初始化脚本
├── dev/                     # 开发环境
│   ├── docker/              # Docker Compose开发环境
│   │   ├── docker-compose.yml
│   │   ├── .env.dev
│   │   └── init.sql
│   └── k8s/                 # K8s开发环境
│       ├── configmap.yaml
│       ├── backend.yaml
│       └── ingress.yaml
├── prod/                    # 生产环境
│   ├── docker/              # Docker Compose生产环境（使用外部服务）
│   │   ├── docker-compose.yml
│   │   └── .env.prod
│   └── k8s/                 # K8s生产环境
│       ├── configmap.yaml
│       ├── backend.yaml
│       ├── hpa.yaml
│       └── ingress.yaml
└── scripts/                # 部署脚本
    ├── deploy-dev.sh
    ├── deploy-prod.sh
    └── one-click.sh
```

---

## 2. 开发环境部署

### 2.1 Docker Compose开发环境

**适用场景**：本地开发、调试、演示

```bash
# 进入开发环境目录
cd deploy/dev/docker

# 复制环境配置
cp .env.dev .env

# 编辑.env配置（主要是微信小程序的appid和secret）
vim .env

# 启动所有服务（MySQL + Redis + Backend + Nginx）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

**开发环境服务**：
- MySQL 8.0 (端口3306)
- Redis 7 (端口6379)
- Backend (端口8080)
- Nginx (端口80/443)

### 2.2 Kubernetes开发环境

**适用场景**：K8s本地测试、开发

```bash
cd deploy/dev/k8s

# 部署到默认namespace
kubectl apply -f configmap.yaml
kubectl apply -f backend.yaml
kubectl apply -f ingress.yaml

# 或部署到独立namespace
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f backend.yaml
```

**注意**：开发K8s环境使用本地存储，生产环境应使用云存储。

---

## 3. 生产环境部署

### 3.1 前置要求

#### 3.1.1 云服务准备

| 服务 | 阿里云 | 腾讯云 | 自建 |
|------|--------|--------|------|
| 数据库 | RDS MySQL 8.0 | CDB MySQL | MySQL 8.0 |
| 缓存 | Redis 7.0 | Redis | Redis |
| K8s | ACK | TKE | 自建K8s |

#### 3.1.2 配置云数据库

```sql
-- 创建数据库和用户
CREATE DATABASE ai_couple_dish DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aicoupledish'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ai_couple_dish.* TO 'aicoupledish'@'%';
FLUSH PRIVILEGES;

-- 执行初始化脚本
source init.sql;
```

#### 3.1.3 配置云Redis

```bash
# 设置密码或开启免密（内网）
# 确保K8s集群与Redis在同一VPC
```

### 3.2 生产环境K8s部署

#### 3.2.1 配置Secrets

```bash
cd deploy/prod/k8s

# 编辑secret.yaml，配置所有密码和密钥
vim secret.yaml
```

**必须配置的Secrets**：
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-couple-dish-secrets
data:
  # Base64编码的值
  DB_PASSWORD: <base64编码的数据库密码>
  REDIS_PASSWORD: <base64编码的Redis密码>
  JWT_SECRET: <base64编码的JWT密钥(至少32字符)>
  WX_MINIAPP_APPID: <base64编码的微信AppID>
  WX_MINIAPP_SECRET: <base64编码的微信Secret>
```

#### 3.2.2 配置ConfigMap

```bash
# 编辑configmap.yaml
vim configmap.yaml
```

**关键配置**：
```yaml
data:
  # 数据库地址（云数据库地址）
  DB_HOST: "rm-xxxxx.mysql.rds.aliyuncs.com"
  DB_PORT: "3306"
  DB_NAME: "ai_couple_dish"

  # Redis地址（云Redis地址）
  REDIS_HOST: "r-xxxxx.redis.rds.aliyuncs.com"
  REDIS_PORT: "6379"
```

#### 3.2.3 部署

```bash
# 部署到生产namespace
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f backend.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml

# 检查部署状态
kubectl get pods -n ai-couple-dish-prod

# 查看日志
kubectl logs -f deployment/backend -n ai-couple-dish-prod
```

### 3.3 使用Helm部署（推荐）

```bash
# 使用生产环境values
helm upgrade --install ai-couple-dish \
  ../helm/ai-couple-dish \
  -f values-prod.yaml \
  -n ai-couple-dish-prod \
  --create-namespace
```

---

## 4. 一键部署脚本

### 4.1 开发环境部署

```bash
# 本地Docker Compose开发
./deploy/scripts/deploy-dev.sh docker

# K8s开发环境
./deploy/scripts/deploy-dev.sh k8s
```

### 4.2 生产环境部署

```bash
# 构建并推送到镜像仓库
./deploy/scripts/deploy-prod.sh build

# 部署到阿里云ACK
./deploy/scripts/deploy-prod.sh aliyun

# 部署到腾讯云TKE
./deploy/scripts/deploy-prod.sh tencent

# 部署到自建K8s
./deploy/scripts/deploy-prod.sh k8s
```

### 4.3 交互式部署

```bash
./deploy/scripts/one-click.sh
```

---

## 5. 运维指南

### 5.1 日志管理

```bash
# Docker Compose
docker-compose logs -f backend

# Kubernetes
kubectl logs -f deployment/backend -n ai-couple-dish
kubectl logs --tail=100 -l app=backend -n ai-couple-dish

# 查看历史日志（建议配置ELK/Loki）
```

### 5.2 扩缩容

```bash
# Kubernetes HPA（自动扩缩容，已配置）
kubectl get hpa -n ai-couple-dish-prod

# 手动扩缩容
kubectl scale deployment/backend -n ai-couple-dish-prod --replicas=5

# 滚动更新
kubectl set image deployment/backend backend=registry.cn-hangzhou.aliyuncs.com/ai-couple-dish/backend:v2.0.0 -n ai-couple-dish-prod
kubectl rollout status deployment/backend -n ai-couple-dish-prod
```

### 5.3 健康检查

```bash
# API健康检查
curl http://localhost:8080/api/actuator/health

# Kubernetes健康检查
kubectl exec -it <pod-name> -n ai-couple-dish-prod -- curl localhost:8080/api/actuator/health
```

### 5.4 数据库备份

```bash
# 云数据库备份（使用云控制台或CLI）
# 阿里云RDS
aliyun rds DescribeBackupPolicy --DBInstanceId rm-xxxxx
aliyun rds CreateBackup --DBInstanceId rm-xxxxx --BackupMethod Physical

# 手动备份
mysqldump -h rm-xxxxx.mysql.rds.aliyuncs.com -u aicoupledish -p ai_couple_dish > backup.sql
```

### 5.5 监控告警

**Actuator端点**：
- `/actuator/health` - 健康检查
- `/actuator/info` - 应用信息
- `/actuator/metrics` - 监控指标
- `/actuator/prometheus` - Prometheus格式指标

---

## 附录

### A. 环境变量参考

| 变量 | 开发环境 | 生产环境 | 说明 |
|------|---------|---------|------|
| DB_HOST | mysql | 云数据库地址 | 数据库主机 |
| DB_PORT | 3306 | 3306 | 数据库端口 |
| DB_NAME | ai_couple_dish | ai_couple_dish | 数据库名 |
| REDIS_HOST | redis | 云Redis地址 | Redis主机 |
| REDIS_PORT | 6379 | 6379 | Redis端口 |

### B. 资源配额建议

| 环境 | CPU请求 | CPU限制 | 内存请求 | 内存限制 |
|------|---------|---------|---------|---------|
| 开发 | 250m | 1000m | 512Mi | 2Gi |
| 生产 | 500m | 2000m | 1Gi | 4Gi |

### C. 快速命令参考

```bash
# 开发环境
cd deploy/dev/docker && docker-compose up -d

# 生产环境
cd deploy/prod/k8s && kubectl apply -f .

# Helm部署
helm upgrade --install ai-couple-dish -n ai-couple-dish-prod -f values-prod.yaml .
```
