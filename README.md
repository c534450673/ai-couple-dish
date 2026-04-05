# AI Couple Dish - 情侣私密菜单

一款面向情侣的私密菜单管理应用，支持记录约会餐厅、管理心愿清单、纪念日提醒等功能。

## 项目结构

```
ai-couple-dish/
├── backend/              # Spring Boot 后端服务
├── frontend/              # 微信小程序版本
├── frontend-h5/           # H5 浏览器版本
├── frontend-uniapp/       # UniApp 跨平台版本
├── frontend/packages/     # 前端共享包
├── deploy/                # 部署配置文件
└── docs/                  # 项目文档
```

## 技术栈

### 后端

- **Java 17** + Spring Boot 2.7
- **MySQL** + MyBatis Plus
- **Redis** - 缓存和会话
- **JWT** - 用户认证
- **Knife4j** - API 文档

### 前端

| 版本 | 技术栈 | 说明 |
|------|--------|------|
| H5 | Vue 3 + Vite + Vant | 浏览器版本 |
| UniApp | Vue 3 + UniApp | 跨平台（iOS/Android/小程序） |

## 快速开始

### 环境要求

- JDK 17+
- Node.js 18+
- MySQL 8.0+
- Redis 6.0+

### 后端启动

```bash
cd backend

# 复制环境配置
cp .env.example .env
# 编辑 .env 填写数据库配置

# 启动服务
./mvnw spring-boot:run
```

后端启动后访问: http://localhost:8080/api/doc.html

### 前端 H5 启动

```bash
cd frontend-h5

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 前端 UniApp 启动

```bash
cd frontend-uniapp

# 安装依赖
npm install

# H5 开发
npm run dev:h5

# 微信小程序开发
npm run dev:mp-weixin
```

## 环境变量

详细配置请参考 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)

### 后端关键配置

| 变量 | 说明 | 必须 |
|------|------|------|
| `DB_HOST` | 数据库地址 | Yes |
| `DB_PASSWORD` | 数据库密码 | Yes |
| `JWT_SECRET` | JWT 密钥（生产环境必须修改） | Yes |
| `REDIS_PASSWORD` | Redis 密码 | No |

## 功能模块

- **用户模块** - 登录、注册、用户信息管理
- **情侣模块** - 绑定TA、情侣码、恋爱计时
- **菜单模块** - 私密餐厅收藏夹
- **投喂模块** - 每日投喂、接受/拒绝
- **纪念日模块** - 重要日期管理
- **心愿单模块** - TA的心愿、完成后标记
- **笔记模块** - 美食笔记记录

## API 文档

运行后端服务后访问: http://localhost:8080/api/doc.html

详细 API 规范见 [docs/API_DESIGN.md](docs/API_DESIGN.md)

## 部署

### Docker Compose (开发环境)

```bash
cd deploy/dev/docker
docker-compose up -d
```

### Kubernetes (生产环境)

```bash
# 开发环境
kubectl apply -f deploy/dev/k8s/

# 生产环境
kubectl apply -f deploy/prod/k8s/
```

详细部署文档见 `deploy/` 目录下的 README

## 开发指南

### 代码规范

- Java: 遵循阿里规约
- 前端: ESLint + Prettier
- 提交: 语义化提交信息

详见 [docs/CODE_STYLE.md](docs/CODE_STYLE.md)

### DTO 规范

详见 [docs/DTO_SPECIFICATION.md](docs/DTO_SPECIFICATION.md)

### 前端架构

详见 [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md)

## 文档目录

| 文档 | 说明 |
|------|------|
| `docs/MULTI_PLATFORM_README.md` | 多平台版本说明 |
| `docs/ENVIRONMENT.md` | 环境变量配置指南 |
| `docs/API_DESIGN.md` | API 设计规范 |
| `docs/DTO_SPECIFICATION.md` | DTO/Entity 规范 |
| `docs/FRONTEND_ARCHITECTURE.md` | 前端架构指南 |
| `docs/CODE_STYLE.md` | 代码风格指南 |

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
