# Web版轻量级部署方案 (2核4G服务器)

针对资源受限的小型服务器优化的 Web 版本部署方案，适合个人开发者或小规模用户使用。

## 系统要求

| 项目 | 最低要求 |
|------|---------|
| CPU | 2核 |
| 内存 | 4GB |
| 存储 | 20GB SSD |
| 系统 | Linux (Ubuntu/CentOS/Debian) |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                      用户浏览器                          │
└─────────────────────┬───────────────────────────────────┘
                      │ :80/:443
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Nginx (Alpine)                         │
│  ├─ 静态文件: /usr/share/nginx/html (H5前端)            │
│  └─ API代理: /api/* → backend:8080                      │
└─────────────────────┬───────────────────────────────────┘
                      │ 内部网络
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│  Backend  │  │   MySQL   │  │   Redis   │
│ (Spring)  │  │    8.0    │  │    7      │
│  768MB    │  │   512MB   │  │   160MB   │
└───────────┘  └───────────┘  └───────────┘
```

## 资源分配

| 服务 | 内存限制 | CPU | 端口 |
|------|---------|-----|------|
| MySQL | 512MB | 0.5 | 3306 (内部) |
| Redis | 160MB | 0.25 | 6379 (内部) |
| Backend | 768MB | 1.0 | 8080 (内部) |
| Nginx | 64MB | 0.1 | 80, 443 |
| **系统预留** | ~600MB | - | - |

## 快速部署

### 1. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 安装 Docker Compose
apt install docker-compose-plugin
```

### 2. 上传部署文件

将 `deploy/lightweight` 目录上传到服务器:

```bash
scp -r deploy/lightweight user@your-server:/opt/ai-couple-dish
```

### 3. 构建前端（本地执行）

在本地开发机器上构建 H5 前端:

```bash
cd frontend-h5
npm install
npm run build

# 复制构建产物到部署目录
mkdir -p ../deploy/lightweight/frontend-h5/dist
cp -r dist/* ../deploy/lightweight/frontend-h5/dist/
```

### 4. 配置环境变量

```bash
cd /opt/ai-couple-dish
cp .env.example .env
vim .env
```

**必须修改的配置:**

```bash
# MySQL 密码
MYSQL_ROOT_PASSWORD=你的root密码
MYSQL_PASSWORD=你的用户密码

# Redis 密码
REDIS_PASSWORD=你的redis密码

# JWT密钥 (至少32字符)
# 生成命令: openssl rand -base64 64 | tr -d '\n'
JWT_SECRET=使用上面的命令生成一个随机字符串
```

### 5. 启动服务

```bash
chmod +x deploy.sh
./deploy.sh
```

或手动执行:

```bash
docker compose up -d --build
```

## 目录结构

```
lightweight/
├── docker-compose.yml    # 主编排文件
├── .env.example          # 环境变量模板
├── deploy.sh             # 一键部署脚本
├── backend/
│   └── Dockerfile        # 后端镜像构建
├── nginx/
│   ├── nginx.conf        # Nginx主配置
│   ├── conf.d/
│   │   └── default.conf  # 站点配置
│   └── ssl/              # SSL证书目录
└── frontend-h5/
    └── dist/             # H5构建产物
```

## 访问地址

部署完成后:

| 服务 | 地址 |
|------|------|
| Web 首页 | http://your-server |
| API 文档 | http://your-server/doc.html |
| 健康检查 | http://your-server/api/actuator/health |

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f backend

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 完全清理(包括数据卷)
docker compose down -v
```

## 性能优化说明

### MySQL 优化
- `innodb_buffer_pool_size=256M` - 减少内存占用
- `max_connections=100` - 限制连接数
- `performance_schema=OFF` - 关闭性能监控

### JVM 优化
- `-Xms384m -Xmx512m` - 限制堆内存
- `-XX:+UseG1GC` - 使用 G1 垃圾回收器
- `-XX:MaxMetaspaceSize=128m` - 限制元空间

### Redis 优化
- `maxmemory 128mb` - 限制内存使用
- `maxmemory-policy allkeys-lru` - LRU 淘汰策略

## 监控与维护

### 查看资源使用
```bash
docker stats
```

### 备份数据库
```bash
docker exec ai-couple-dish-mysql mysqldump -u root -p ai_couple_dish > backup_$(date +%Y%m%d).sql
```

### 恢复数据库
```bash
docker exec -i ai-couple-dish-mysql mysql -u root -p ai_couple_dish < backup.sql
```

## SSL/HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 certbot
apt install certbot

# 申请证书
certbot certonly --standalone -d your-domain.com

# 复制证书
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
```

### 修改 Nginx 配置

编辑 `nginx/conf.d/default.conf`，取消 HTTPS 部分的注释并修改域名。

## 常见问题

### Q: 服务启动失败
检查日志: `docker compose logs backend`

### Q: 内存不足
```bash
# 查看内存使用
free -m
# 查看各容器资源使用
docker stats
```

### Q: 前端页面空白
检查前端是否正确构建，确保 `frontend-h5/dist` 目录存在且包含文件。

### Q: API 请求 502
后端服务可能还在启动中，等待 1-2 分钟后重试。

## 扩容建议

当用户量增长时:

| 用户规模 | 建议 |
|---------|------|
| < 100 | 当前配置足够 |
| 100-500 | 升级到 4核8G |
| 500+ | 使用云数据库(RDS) + 云Redis |
