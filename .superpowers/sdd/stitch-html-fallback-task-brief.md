### Task S4: 为缺失 Stitch HTML 的屏幕提供可追溯截图预览降级

**Files:**
- Modify: `tools/stitch/src/exporter.mjs`
- Modify: `tools/stitch/src/verifier.mjs`
- Modify: `tools/stitch/test/exporter.test.mjs`
- Modify: `tools/stitch/test/verifier.test.mjs`

**Goal:** 当 `screen.getHtml()` 返回空字符串时，仍导出可打开的本地 HTML 视觉参考，但明确标记为 `screenshot-fallback`；正常屏幕保持 Stitch 原生 HTML。

**Required behavior:**
- 先导出真实 Stitch screenshot。
- HTML URL 为非空字符串时继续下载，`htmlSource: "stitch"`。
- HTML URL 为空时写入 UTF-8 fallback HTML，引用 `../screenshots/<localId>.png`，包含 `data-stitch-html-source="screenshot-fallback"` 和清晰的“仅视觉参考”说明。
- manifest 每屏新增 `htmlSource`，只允许 `stitch` 或 `screenshot-fallback`。
- `stitch.export.screen` 成功日志新增 `artifactSource`；失败日志与现有脱敏/事务语义不变。
- verifier 对存在的 `htmlSource` 严格校验枚举；缺字段的旧 manifest 继续按 `stitch` 兼容。
- fallback HTML 仍参与 SHA-256、secret scanning、路径与 realpath 校验。
- 保留 staging、promotion、manifest-last、错误 identity、URL/staging 脱敏。

**TDD:**
1. 新增 exporter 失败测试：一个 screen 的 `getHtml()` 返回空；旧实现必须失败。
2. 最小实现后断言 fallback 文件内容、相对截图路径、manifest `htmlSource`、日志 `artifactSource`、未向 fetch 传空 URL。
3. 新增 verifier 测试：接受 `screenshot-fallback`，拒绝未知来源，旧 fixture 无字段仍通过。
4. 运行定向测试、`npm test`、`node --check`、`git diff --check`。
5. GitNexus impact/detect 后只提交上述四文件，提交消息：`fix: 支持Stitch截图HTML降级导出`。

**Boundaries:**
- 不修改真实 `generation-state.json`、不访问网络/密钥。
- 不为有 HTML URL 的屏幕降级。
- 不把 fallback 标记为 Stitch 原生 HTML。
