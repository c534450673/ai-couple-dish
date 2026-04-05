# 情侣私密菜单 - 多平台版本说明

## 项目概述

本项目包含三个前端平台版本，共用同一个后端服务：

| 平台 | 目录 | 技术栈 | 适用场景 |
|------|------|--------|----------|
| 微信小程序 | `frontend/` | 原生小程序 | 微信生态 |
| H5浏览器 | `frontend-h5/` | Vue 3 + Vite + Vant | 浏览器、微信/QQ/头条等内置浏览器 |
| UniApp跨平台 | `frontend-uniapp/` | Vue 3 + UniApp | iOS/Android App Store、应用宝等 |

## 后端配置

所有前端版本共用后端API，后端地址配置如下：

### 开发环境
```bash
# H5
VITE_API_BASE_URL=http://localhost:8080/api

# UniApp
BASE_URL=http://localhost:8080/api
```

### 生产环境
```bash
# H5
VITE_API_BASE_URL=https://api.aicoupledish.com/api

# UniApp
BASE_URL=https://api.aicoupledish.com/api
```

## H5版本 (frontend-h5)

### 技术栈
- Vue 3 + Composition API
- Vite 5
- Vant 4 (移动端UI组件库)
- Pinia (状态管理)
- Axios (HTTP请求)
- SCSS (样式)

### 安装和运行
```bash
cd frontend-h5

# 安装依赖
npm install

# 开发环境
npm run dev

# 生产构建
npm run build
```

### 主要功能页面
- `/login` - 手机号登录
- `/bind` - 绑定TA（情侣码绑定）
- `/home` - 首页（恋爱计时、快捷功能、统计）
- `/menu` - 私密菜单列表
- `/menu/add` - 添加餐厅
- `/menu/:id` - 餐厅详情
- `/feed` - 投喂功能
- `/anniversary` - 纪念日管理
- `/note` - 美食笔记
- `/wish` - 心愿单
- `/settings` - 设置

### H5部署
```bash
# 构建生产版本
npm run build

# 上传 dist 目录到服务器
# 配置 Nginx 指向 dist 目录
# 反向代理 /api 请求到后端服务
```

## UniApp版本 (frontend-uniapp)

### 技术栈
- Vue 3 + Composition API
- UniApp 3.x (跨平台框架)
- Pinia (状态管理)
- SCSS (样式)

### 安装和运行
```bash
cd frontend-uniapp

# 安装依赖
npm install

# H5开发
npm run dev:h5

# 微信小程序开发
npm run dev:mp-weixin

# Android App开发
npm run build:app

# iOS App开发 (需要macOS和Xcode)
# 使用HBuilderX打开项目，选择发行-原生App-iOS
```

### 平台特性配置

#### 微信小程序 (mp-weixin)
在 `manifest.json` 中配置：
```json
{
  "mp-weixin": {
    "appid": "wx0000000000000000",
    "setting": {
      "urlCheck": false
    }
  }
}
```

#### Android App
配置签名和图标后，使用以下命令构建：
```bash
npm run build:app
# 输出目录: dist/build/app
```

#### iOS App
1. 使用 HBuilderX 打开项目
2. 选择 `发行` -> `原生App-iOS`
3. 配置证书和App ID
4. 提交到 App Store

### 主要功能页面
与H5版本一致，适配各平台原生组件。

## 登录方式对比

| 平台 | 支持的登录方式 |
|------|---------------|
| 微信小程序 | 微信授权登录 |
| H5 | 手机号+验证码、微信OAuth2.0、Apple登录 |
| UniApp | 手机号+验证码、微信OAuth2.0、Apple登录 |

## 多平台发布指南

### 1. 微信小程序发布
1. 使用微信开发者工具打开 `frontend/` 目录
2. 配置 AppID
3. 提交审核
4. 发布上线

### 2. H5发布
1. 构建: `cd frontend-h5 && npm run build`
2. 部署 dist 目录到 Web 服务器
3. 配置 Nginx 反向代理

### 3. Android应用商店发布
1. 构建: `cd frontend-uniapp && npm run build:app`
2. 使用 `android studio` 签名打包 APK
3. 提交到各应用商店（华为、小米、OPPO等）

### 4. iOS App Store发布
1. 使用 HBuilderX 或 Xcode 打包
2. 在 Xcode 中配置证书
3. 提交到 App Store Connect
4. 审核后上线

## 目录结构

```
ai-couple-dish/
├── backend/                    # Spring Boot 后端
│   ├── src/main/java/          # Java源代码
│   ├── src/main/resources/     # 配置文件
│   └── Dockerfile              # Docker构建文件
│
├── frontend/                   # 微信小程序版本
│   ├── pages/                  # 页面
│   ├── services/               # API服务
│   └── app.js                  # 应用入口
│
├── frontend-h5/                # H5浏览器版本
│   ├── src/
│   │   ├── api/               # API请求封装
│   │   ├── pages/              # 页面组件
│   │   ├── router/            # 路由配置
│   │   ├── stores/             # Pinia状态管理
│   │   └── views/              # 页面视图
│   ├── vite.config.js          # Vite配置
│   └── package.json
│
├── frontend-uniapp/            # UniApp跨平台版本
│   ├── src/
│   │   ├── api/                # API请求封装
│   │   ├── pages/              # 页面组件
│   │   ├── store/              # Pinia状态管理
│   │   └── styles/             # 全局样式
│   ├── pages.json              # UniApp页面配置
│   ├── manifest.json           # 应用配置
│   └── package.json
│
├── deploy/                      # 部署配置
│   ├── dev/                    # 开发环境
│   │   ├── docker/             # Docker Compose配置
│   │   └── k8s/                # Kubernetes配置
│   └── prod/                   # 生产环境
│       ├── docker/
│       └── k8s/
│
└── docs/                        # 文档
```

## 注意事项

1. **API域名配置**
   - 各平台需要配置正确的API域名
   - H5和UniApp需要在manifest.json中配置可信域名

2. **微信登录**
   - 微信登录仅在微信环境可用
   - H5需要自行实现微信OAuth2.0跳转

3. **App Store审核**
   - iOS App需要配置隐私政策URL
   - 确保所有功能符合App Store指南

4. **第三方登录**
   - Apple登录在非Apple平台不可用
   - 需要在对应开放平台申请应用ID
