# SRS-006: 统一前端 API 请求封装

## 1. 需求背景

`frontend-h5` 和 `frontend-uniapp` 两个前端版本各自实现了独立的 API 请求封装，功能类似但代码重复。需要统一封装逻辑，减少维护成本。

## 2. 当前问题

### 2.1 frontend-h5 API 封装

**位置**: `frontend-h5/src/api/request.js`

基于 axios 封装：
```javascript
// 包含拦截器、错误处理、Loading 等
```

### 2.2 frontend-uniapp API 封装

**位置**: `frontend-uniapp/src/api/request.js`

基于 uni.request 封装：
```javascript
// 功能类似但实现不同
```

### 2.3 问题总结

| 功能 | frontend-h5 | frontend-uniapp |
|------|-------------|-----------------|
| 请求拦截 | ✅ | ✅ |
| 响应拦截 | ✅ | ✅ |
| Token 自动注入 | ✅ | ✅ |
| 错误处理 | ✅ | ✅ |
| Loading 状态 | ✅ | ✅ |
| 请求重试 | ❌ | ❌ |
| 缓存机制 | ❌ | ❌ |

代码重复，维护成本高。

## 3. 解决方案

### 方案 A: 提取共享模块（推荐）

在项目根目录创建 `frontend-shared/` 包：

```
/frontend-shared
  /api
    request.ts      # 统一的请求封装
    client.ts       # API 客户端
    types.ts        # 类型定义
  /stores
    user.ts         # 用户状态管理
  /utils
    storage.ts      # 存储工具
    logger.ts       # 日志工具
```

各前端版本依赖这个共享包。

### 方案 B: 迁移到同一实现

选择其中一方的实现作为标准，迁移到另一方。

### 方案 C: 使用 GraphQL

如果 API 复杂度较高，可考虑使用 GraphQL 统一数据获取。

## 4. 详细设计（方案 A）

### 4.1 统一请求封装

```typescript
// frontend-shared/api/request.ts

interface RequestConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

interface RequestOptions {
  showLoading?: boolean;
  loadingText?: string;
  ignoreAuth?: boolean;
  retryCount?: number;
}

export function createRequest(config: RequestConfig) {
  const request = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeout || 10000,
  });

  // 请求拦截器
  request.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // 响应拦截器
  request.interceptors.response.use(
    (response) => response.data,
    (error) => handleError(error)
  );

  return { request };
}
```

### 4.2 依赖管理

```json
// frontend-shared/package.json
{
  "name": "@aicoupledish/shared",
  "version": "1.0.0",
  "main": "./dist/index.js",
  "dependencies": {
    "axios": "^1.6.0",
    "dayjs": "^1.11.0"
  }
}
```

## 5. 验收标准

- [ ] 创建 `frontend-shared/` 共享模块
- [ ] 统一的请求封装支持 Token 自动注入
- [ ] 统一的错误处理机制
- [ ] `frontend-h5` 依赖共享模块
- [ ] `frontend-uniapp` 依赖共享模块
- [ ] 移除各自重复的请求封装代码
- [ ] 编写单元测试

## 6. 影响范围

- `frontend-h5/src/api/request.js` - 简化或移除
- `frontend-uniapp/src/api/request.js` - 简化或移除
- 新建 `frontend-shared/` 目录

## 7. 优先级

**P1** - 中优先级

## 8. 预计工时

8-12 小时

## 9. 前置条件

依赖 SRS-005（统一前端版本架构）的决策结果
