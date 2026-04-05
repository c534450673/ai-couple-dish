# SRS-005: 统一前端版本架构

## 1. 需求背景

项目同时维护三个前端版本：原生微信小程序（frontend）、H5 版本（frontend-h5）、UniApp 跨平台版本（frontend-uniapp）。功能重复导致：
- 代码重复，维护成本高
- bug 需要在三个地方修复
- 新功能需要在三个地方开发
- 构建和部署流程不统一

## 2. 当前问题

```
/frontend           # 微信小程序原生版
/frontend-h5        # Vue3 + Vite H5版
/frontend-uniapp    # UniApp 跨平台版
```

三个版本的功能几乎相同：
- 登录/注册
- 绑定情侣
- 私密菜单管理
- 美食笔记
- 纪念日
- 投喂功能
- 心愿单
- 通知

问题：
- `frontend-h5` 和 `frontend-uniapp` 的 API 请求封装重复
- `frontend-h5` 和 `frontend-uniapp` 的 store 逻辑重复
- 每次更新需要维护三套代码

## 3. 解决方案

### 方案 A: 统一使用 UniApp（推荐）

UniApp 支持一套代码编译到：
- 微信小程序
- H5
- iOS/Android 原生 App
- 各种小程序平台

**优势**：
- 一次开发，多端运行
- 社区活跃，生态成熟
- 支持 Vue 3
- 可通过条件编译处理平台差异

**实施步骤**：
1. 以 `frontend-uniapp` 为基础
2. 将 `frontend-h5` 中的特有功能迁移到 UniApp
3. 保留原生小程序中 UniApp 无法实现的功能（如果有）
4. 废弃 `frontend` 和 `frontend-h5` 目录
5. 更新构建和部署文档

### 方案 B: 统一使用 H5 版本

如果项目只需要 H5 和小程序，放弃 UniApp。

### 方案 C: 使用 Monorepo 结构

如果确实需要保留多个前端版本，使用 Monorepo 管理：
```
/frontend/packages
  /shared       # 共享代码
  /h5           # H5版本
  /weapp        # 微信小程序
  /uniapp       # UniApp
```

## 4. 验收标准

- [ ] 确定最终采用的方案（A/B/C）
- [ ] 制定详细的迁移计划
- [ ] 完成核心功能在同一版本的实现
- [ ] 废弃多余的代码目录
- [ ] 更新 README 和部署文档
- [ ] 团队成员确认并通过评审

## 5. 影响范围

- `frontend/` - 可能废弃
- `frontend-h5/` - 可能废弃
- `frontend-uniapp/` - 可能作为唯一前端版本
- 所有前端相关的 CI/CD 配置
- 部署文档

## 6. 优先级

**P1** - 中优先级（架构决策）

## 7. 预计工时

需要根据评估结果确定，可能需要 2-4 周

## 8. 前置条件

- [ ] 调研 UniApp 是否能覆盖所有业务场景
- [ ] 与团队讨论确认方案
- [ ] 评估迁移成本
