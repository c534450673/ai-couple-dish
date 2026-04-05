# SRS-009: 添加项目 README 文档

## 1. 需求背景

项目根目录的 `/README.md` 是空文件，缺少项目概述、架构说明、快速开始指南等内容，影响新成员的上手效率和项目可维护性。

## 2. 当前问题

- `/README.md` 文件为空
- 新成员无法快速了解项目
- 缺少技术栈说明
- 缺少开发环境搭建指南
- 缺少架构设计文档链接

## 3. 解决方案

### 3.1 README.md 结构设计

```markdown
# AI Couple Dish - 情侣私密菜单

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 项目简介

情侣私密菜单是一款帮助情侣共享美食偏好、管理约会餐厅选择的微信小程序/应用。

## 功能特性

- [ ] 情侣绑定
- [ ] 私密菜单管理
- [ ] 美食笔记分享
- [ ] 纪念日提醒
- [ ] 投喂记录
- [ ] 心愿单

## 技术栈

### 后端
- Java 17
- Spring Boot 2.7.18
- MyBatis Plus 3.5.3
- MySQL 8.0
- Redis
- JWT

### 前端
- UniApp (Vue 3)
- Vite 5
- Pinia

## 快速开始

### 环境要求

- JDK 17+
- Node.js 18+
- MySQL 8.0+
- Redis 6.0+

### 后端启动

```bash
cd backend
cp .env.example .env  # 配置环境变量
mvn spring-boot:run
```

### 前端启动

```bash
cd frontend-uniapp
npm install
npm run dev:mp-weixin  # 微信小程序
npm run dev:h5         # H5
```

## 项目结构

```
ai-couple-dish/
├── backend/           # 后端服务
├── frontend/          # 微信小程序原生版
├── frontend-h5/       # H5 版本
├── frontend-uniapp/  # UniApp 跨平台版
├── deploy/            # 部署配置
└── docs/              # 项目文档
```

## API 文档

- 开发环境: http://localhost:8080/doc.html
- 生产环境: (待配置)

## 部署指南

详见 [DEPLOYMENT_GUIDE.md](deploy/DEPLOYMENT_GUIDE.md)

## 开发指南

- [多平台开发说明](docs/MULTI_PLATFORM_README.md)
- [环境变量配置](docs/ENVIRONMENT.md)

## License

MIT License
```

### 3.2 补充文档

| 文档 | 位置 | 说明 |
|------|------|------|
| ARCHITECTURE.md | docs/ | 系统架构设计 |
| API_GUIDE.md | docs/ | API 开发指南 |
| CONTRIBUTION.md | docs/ | 贡献指南 |

## 4. 验收标准

- [ ] `/README.md` 内容完整，包含项目简介、技术栈、快速开始、项目结构
- [ ] 包含 Badges（License、Build Status 等）
- [ ] 提供后端和前端的启动说明
- [ ] 链接到所有相关文档
- [ ] 添加项目结构树形图
- [ ] 包含 License 文件链接

## 5. 影响范围

- `/README.md`
- `/docs/ARCHITECTURE.md`（新建）
- `/docs/CONTRIBUTION.md`（新建）
- `/LICENSE`（新建）

## 6. 优先级

**P1** - 中优先级

## 7. 预计工时

2-3 小时
