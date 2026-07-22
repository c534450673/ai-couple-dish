# AI Couple Dish 跨机器续跑说明

## 1. 权威仓库与分支

- GitHub：`https://github.com/c534450673/ai-couple-dish.git`
- 工作分支：`codex/couple-cosmos-stitch`
- 当前阶段：Couple Cosmos 全页面 Stitch 设计生成、导出与视觉验收。

新机器执行：

```bash
git clone https://github.com/c534450673/ai-couple-dish.git
cd ai-couple-dish
git checkout codex/couple-cosmos-stitch
cd tools/stitch
npm ci
npm test
```

## 2. 不可改变的用户需求

- 始终使用中文沟通。
- 后端迁移采用 Python + FastAPI，不再采用 Java 作为目标后端。
- 前端需要完整实现最终设计稿，包含大量动态组件与酷炫但可用的动效。
- 保留并修复原有功能，完成代码优化、接口测试、集成测试和真实浏览器全页面测试。
- 完成当前功能后继续进行商用化功能扩展、设计、实现和验证闭环。
- 实现代码必须包含详细、结构化且不泄漏敏感信息的日志。
- 修改现有符号前必须执行 GitNexus impact；提交前必须执行 GitNexus detect_changes。

## 3. 敏感信息与代理

- 不要把 `STITCH_API_KEY` 写入 Git、`.env`、日志、命令历史、截图或报告。
- 在新机器上通过当前进程环境或安全的 PTY 静默输入提供 `STITCH_API_KEY`。
- 已验证的本地代理地址为 `http://127.0.0.1:7897`。
- Google Stitch MCP 地址为 `https://stitch.googleapis.com/mcp`。
- Node/Undici 需要使用 `ProxyAgent`；当前网络偶发 TLS CONNECT 超时，建议把 `requestTls.timeout` 调整为 `60000` 毫秒。
- Stitch 连接失败后请求可能仍在服务端完成，不能直接盲目重试；先检查项目更新时间与 `screenInstances`。

## 4. 当前设计状态

- `docs/design/stitch/couple-cosmos/generation-state.json` 是权威远程检查点。
- 设计 local ID 已达到精确 20 屏。
- 已实现 Stitch 多项目分卷；state 中包含 3 个项目注册项。
- 主项目与第二分卷已达到或接近远程实际容量上限；第三分卷用于后续修复/扩展。
- 20 张 Stitch 截图均可获得。
- 只有 `login` 没有 Stitch 原生 `htmlCode.downloadUrl`；其余 19 屏有原生 HTML。
- `home-base` 已切换到带截图和 HTML 的第二分卷完整屏幕。
- 真实导出尚未完成，当前 `manifest.json`、`screenshots/*`、`html/*` 不能视为最终资产。

## 5. 当前代码验证状态

- Stitch 工具全量测试最近一次为 `151/151` 通过。
- 多项目生成、跨项目导出、严格 verifier、secret scanning、SHA-256、路径穿越和 symlink containment 已实现。
- 提交 `13316a9` 增加了 `screenshot-fallback` HTML：当 Stitch HTML URL 为空时，用真实截图生成明确标注“仅视觉参考”的本地 HTML，并在 manifest/log 中记录来源。
- 提交 `8790e7a` 已修复 fallback HTML 截图 `src` 的 URL path-segment 编码，并通过独立复审；`#`、`?`、HTML/XSS 转义回归覆盖均保留。

## 6. 新机器的第一项任务

S4 URL 编码修复已经完成。下一项任务是按第 7 节执行真实 Stitch 导出、完整校验与视觉复核；开始前必须通过安全环境提供轮换后的 `STITCH_API_KEY`，不得复用或在聊天、命令、日志中暴露旧密钥。

## 7. 修复后的真实 Stitch 流程

1. 运行 `npm test`。
2. 通过安全环境提供 `STITCH_API_KEY`，经本地代理运行 `bin/health.mjs`。
3. 对 generation state 做精确 20 local ID、项目注册表、字段白名单和安全 slug 检查。
4. 运行 `bin/export.mjs`；`login` 应产生 `htmlSource: "screenshot-fallback"`，其余屏幕应为 `htmlSource: "stitch"`。
5. 运行 `bin/verify.mjs`，同时把真实 API key 作为 forbidden value 扫描，确认 manifest、state、HTML、截图无泄漏且哈希一致。
6. 使用本地图片查看器逐页复核至少：`login`、`bind`、三个首页变体、`menu-list`、`recipe-detail`、`feed`、`memories`、`map`、`ai-chat`、`settings`、`system-states`。
7. 向用户展示三个首页真实变体并给出推荐，必须由用户明确选择 `home-emotion`、`home-food` 或 `home-memory`；不得替用户默认选择。
8. 用户选择后更新设计 README、复验、提交最终 Stitch 资产。

## 8. 后续总路线

1. 根据最终 Stitch 设计全面实现 Vue 3/Vite H5 页面、动效、状态和可访问性。
2. 制定并执行 Java 后端到 FastAPI 的合同优先迁移计划。
3. 修复原有业务功能并兼容新前端合同。
4. 执行 Python 单元/集成/API 测试、前端测试和真实浏览器全路径测试。
5. 基于商用化目标继续扩展功能，并重复设计、实现、验证、浏览器验收闭环。

## 9. 必读文件

- `AGENTS.md`
- `docs/superpowers/specs/2026-07-15-couple-dish-commercialization-design.md`
- `docs/superpowers/plans/2026-07-15-couple-cosmos-stitch-design.md`
- `docs/superpowers/specs/2026-07-16-stitch-multi-project-sharding-design.md`
- `docs/superpowers/plans/2026-07-16-stitch-multi-project-sharding.md`
- `.superpowers/sdd/progress.md`
- `.superpowers/sdd/task-8-brief.md`
- `.superpowers/sdd/task-8-report.md`（交接包内提供）
- `.superpowers/sdd/stitch-html-fallback-task-brief.md`
- `docs/design/stitch/couple-cosmos/generation-state.json`

## 10. 完成定义

当前分支推送和交接不代表总目标完成。只有 UI 设计与选择、H5 全量实现、FastAPI 后端迁移、原功能修复、接口与真实浏览器全量测试、商用化扩展均有权威证据通过时，才能完成总目标。
