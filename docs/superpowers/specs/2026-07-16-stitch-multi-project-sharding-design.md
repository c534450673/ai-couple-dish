# Stitch 多项目分卷设计

## 背景与根因

Couple Cosmos 需要导出 20 个屏幕。真实执行中，主 Stitch 项目在已有 12 个屏幕后，继续生成 `memories` 稳定返回 `Request contains an invalid argument`。完全相同的提示词在新项目中成功，证明问题是单项目容量/状态限制，而非提示词。

## 选择的方案

采用自动多项目分卷，每个 Stitch 项目最多安排 12 个屏幕。不减少页面，不使用不可重复的人工 manifest 合并。

## 状态模型

`GenerationState` 扩展为：

```json
{
  "projectId": "primary-project-id",
  "projectTitle": "AI Couple Dish - Couple Cosmos",
  "projects": [
    { "projectId": "primary-project-id", "title": "AI Couple Dish - Couple Cosmos" },
    { "projectId": "shard-2-id", "title": "AI Couple Dish - Couple Cosmos - Part 2" }
  ],
  "screens": {
    "login": {
      "screenId": "screen-id",
      "kind": "base",
      "projectId": "primary-project-id"
    }
  }
}
```

- 保留顶层 `projectId` 作为主项目 ID，兼容已有状态和日志。
- `projects` 记录所有分卷，顺序即分卷顺序。
- 新屏幕必须写入所属 `projectId`。
- 旧状态中没有屏幕级 `projectId` 时，解析为顶层主 `projectId`，不要求一次性重写旧文件。

## 生成流程

1. 首页基础稿和三个变体始终位于主项目。
2. 生成其余页面前，按屏幕有效 `projectId` 统计每个分卷的数量。
3. 最后一个分卷达到 12 屏时，创建 `${projectTitle} - Part N`。
4. 新项目创建成功后先写 checkpoint，再生成屏幕，防止连接错误导致重复创建孤儿项目。
5. 每个屏幕成功后写入屏幕级 `projectId` 并立即 checkpoint。
6. 跳过已完成屏幕时，不调用远程 SDK。

## 导出与 manifest

- exporter 根据每个屏幕的有效 `projectId` 获取对应 `sdk.project()`，并缓存项目 handle。
- manifest 保持 `version: 1` 和顶层主 `projectId`，增加有序去重的 `projectIds`。
- 每个 manifest entry 的 `projectId` 必须是该屏幕真实所属项目，不再统一使用顶层主项目。
- HTML、截图、哈希和 staging 事务语义保持不变。

## 校验

verifier 新增以下精确检查：

- `state.projects` 与 manifest `projectIds` 是同一有序项目集，且包含顶层主 `projectId`。
- 每个 screen entry 的有效 `projectId`、`screenId`、`kind` 在 state 和 manifest 中一致。
- 拒绝未登记的项目、重复项目 ID、空项目 ID 和屏幕引用未知分卷。
- 原有路径、symlink、secret 和哈希校验保持不变。

## 现有真实资产恢复

- 主项目中的 12 个已完成屏幕保留。
- 已创建第二分卷，且 `memories` 已成功生成。
- 在恢复续跑前，将第二分卷和 `memories` 屏幕安全写入 generation-state；不重新生成前 13 个屏幕。

## 日志与安全

- 新增 `stitch.project.shard` 的 started/ok/error 结构化事件，包含分卷序号、项目 ID、屏幕数和耗时。
- 日志不记录 API key、access token、请求 header 或下载 URL。
- 分卷项目 ID 和屏幕 ID 为可追溯的非敏感设计元数据。

## 测试与验收

- TDD 覆盖达到 12 屏时自动建立分卷、项目 checkpoint 先于屏幕生成、断点恢复不重建分卷、跨项目导出和精确校验。
- 旧单项目 state/manifest fixture 仍必须通过，确保向后兼容。
- 真实续跑完成后，state 和 manifest 必须有 20 个屏幕、两个项目 ID，所有 HTML/截图哈希校验通过。

## 非目标

- 不改动 H5 或后端业务代码。
- 不尝试突破 Stitch 服务端容量限制。
- 不实现任意远程项目同步器，仅管理本工作包创建的分卷。
