# S4 URL Encoding Fix Report

## 范围与影响

- 基线：`19b38125d5f7bd8459f6a3aa6e7432ef65d41c98`。
- 已核对 brief 中的 GitNexus 上游影响证据：`screenshotFallbackHtml`、`exportArtifact` 与 `exportDesignProject` 均为 LOW；直接调用方分别为 1、1、测试覆盖，且没有执行流。未扩大该范围。
- 原实现波次记录的 `gitnexus status` 显示索引提交与当时的当前提交均为 `19b3812`，状态为 up-to-date。
- 原实现波次仅核对了 GitNexus 顶层 CLI，未使用 `eval-server` 的变更检测能力，因而以 `git diff --check`、`git diff --name-only`、允许路径的精确状态检查与提交前 staged diff 作为补充检查。本审查修复波次已按下文记录补做 `detect_changes`。普通 diff 仅识别 exporter/test；brief/report 位于忽略目录，使用精确路径强制暂存后再由 staged diff 核对。

## TDD 证据

### RED

生产代码保持不变时，先将现有 fallback 测试的 `localId` 改为 `login#detail?mode=dark`，期望：

```text
src="../screenshots/login%23detail%3Fmode%3Ddark.png"
```

执行命令：

```sh
cd tools/stitch && node --test test/exporter.test.mjs
```

关键输出：18 个测试中 17 通过、1 失败；失败测试为 `exportDesignProject writes a traceable screenshot fallback when HTML is unavailable`。实际输出为 `src="../screenshots/login#detail?mode=dark.png"`，与包含 `%23detail%3Fmode%3Ddark` 的期望正则不匹配。

### GREEN

最小修复仅在 `screenshotFallbackHtml` 中新增：

```js
const safeScreenshotPathSegment = escapeHtml(encodeURIComponent(localId));
```

fallback `<img src>` 使用该值；标题与 `alt` 继续使用原有的 `safeLocalId`，保留原始文本与 HTML 属性转义。未修改现有结构化日志，因此继续由 `exportArtifact` 记录现有的事件、来源、哈希和耗时字段，且不引入敏感信息。

## 验证

原实现波次执行了以下命令；前四项成功，最后一项 `git diff --check` 并非成功，而是检出 brief 第 39 行的 EOF 空行：

```sh
cd tools/stitch && node --test test/exporter.test.mjs
cd tools/stitch && npm test
cd tools/stitch && node --check src/exporter.mjs
cd tools/stitch && node --check test/exporter.test.mjs
cd tools/stitch && git diff --check
```

关键输出：定向 exporter 测试 `18/18` 通过；完整 Stitch 测试 `150/150` 通过；两项语法检查无输出且退出码为 0；`git diff --check` 输出 `.superpowers/sdd/stitch-html-fallback-url-encoding-fix-brief.md:39: new blank line at EOF.`，退出码为 2。该空行在审查修复波次移除。

变更范围检测：`git diff --name-only` 仅输出 `tools/stitch/src/exporter.mjs` 与 `tools/stitch/test/exporter.test.mjs`；允许路径状态检查同时确认 brief/report 是忽略目录中的任务证据文件。精确暂存后的 `git diff --cached --name-only` 仅列出 brief 要求的四个文件。原波次的 `git diff --cached --check` 同样检出 brief 第 39 行 EOF 空行，并非无警告成功；该问题由下述审查修复波次处理。

## 文件与自审

- `tools/stitch/src/exporter.mjs`：降级截图 URL 的单个路径段先经 `encodeURIComponent`，再做 HTML 转义。
- `tools/stitch/test/exporter.test.mjs`：覆盖 `#` 与 `?` 被编码为 `%23`、`%3F`，以及 `=` 编码为 `%3D` 的回归场景。
- 本报告：记录影响、RED/GREEN、验证和变更检测证据。

自审：未访问网络、API key、真实 generation state 或设计资产；未改动 verifier、staging/promotion、manifest 哈希、`screenshot-fallback` 标记或正常 Stitch HTML 路径。改动局限于 brief 允许的四份文件。

## 审查修复波次

### Findings 修复与测试审查

- 保留精确 `localId = "login#detail?mode=dark"` 用例，继续断言 `src="../screenshots/login%23detail%3Fmode%3Ddark.png"`。
- 新增独立恶意输入 `localId = "profile'<script>"` 用例：`title` 与 `alt` 分别断言 `&#39;`、`&lt;script&gt;`；`src` 断言 `encodeURIComponent` 产生的 `%3Cscript%3E`，以及编码后仍存在的单引号再经 HTML 转义为 `&#39;`；同时断言输出不存在原始 `<script>`。
- 审查确认新用例没有替换 `#/?` 回归场景，且精确覆盖“URL 路径段编码后再做 HTML 转义”的顺序；测试未揭示新的生产缺陷，因此本波次未修改生产代码。
- 移除 brief 的 EOF 空行，并纠正本报告原先将 diff check 描述为成功的不一致表述。

### 验证结果

执行命令：

```sh
cd tools/stitch && node --test test/exporter.test.mjs
cd tools/stitch && npm test
cd tools/stitch && node --check src/exporter.mjs
cd tools/stitch && node --check test/exporter.test.mjs
git diff --check 19b3812..HEAD
git diff --check
```

结果：定向 exporter 测试 `19/19` 通过，完整 Stitch 测试 `151/151` 通过，两项 `node --check` 均退出 0。amend 前，`git diff --check 19b3812..HEAD` 如实复现 brief 第 39 行 EOF 空行并退出 2；包含未提交修复的 `git diff --check` 无输出且退出 0。精确暂存后另以 `git diff --cached --check 19b3812` 核对 amend 将形成的完整差异。

GitNexus eval-server 使用仓库 `couple-cosmos-stitch` 执行 `detect_changes`，参数为 `scope=compare`、`base_ref=19b3812`：检测到 4 个允许文件、30 个文件级映射符号、0 条受影响执行流，风险为 LOW。临时服务仅监听 `127.0.0.1`，调用结束后已关闭。

### 本波次自审

本波次仅接受并核对恶意 `localId` 回归测试、移除 brief EOF 空行、更新本报告；没有修改生产代码。未访问外网、API key、真实 generation state 或设计资产，未扩大到 verifier、staging/promotion、manifest 哈希、`screenshot-fallback` 标记或正常 Stitch HTML 路径。
