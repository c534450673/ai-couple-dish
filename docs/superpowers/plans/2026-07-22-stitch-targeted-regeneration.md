# Stitch Targeted Regeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 安全替换视觉审计不合格的 11 个 Stitch 页面，同时保持精确 20 个本地页面 ID、三项目追溯和失败可恢复性。

**Architecture:** 将正常业务态提示词与全局状态组件提示词分离；新增独立的定向重生成模块和 CLI，只在远端生成及原子 checkpoint 成功后替换单个本地引用。第三分卷承载 11 个新屏幕，exporter 和 verifier 继续负责事务式导出与最终资产门禁。

**Tech Stack:** Node.js 24、node:test、@google/stitch-sdk 0.3.5、Undici ProxyAgent、SHA-256、GitNexus。

## Global Constraints

- `STITCH_API_KEY` 只能通过当前进程环境提供，不写入文件、命令、日志、截图或 manifest。
- 所有新增运行时日志必须为结构化 JSON，并包含 `event`、`result`、`durationMs` 和非敏感上下文。
- 业务页面必须以单个完整正常态为主体，禁止状态指南、调试画廊和可见实现说明。
- 仅 `system-states` 允许生成完整状态组件表。
- 底部导航出现时固定为“星球、菜单、投喂、回忆、我们”。
- 第三分卷项目 ID 从 state 注册表读取，不硬编码到源码。
- 每次单屏 checkpoint 成功前不得改变已提交 state 引用。
- 不删除 Stitch 远端历史项目或屏幕，不替用户选择首页变体。
- 修改现有符号前执行 GitNexus upstream impact；提交前执行 GitNexus `detect_changes`。

---

## File Structure

```text
tools/stitch/src/prompts.mjs                    # 正常态提示词、目标 ID 与 home-base 映射
tools/stitch/test/prompts.test.mjs              # 提示词契约测试
tools/stitch/src/targeted-regeneration.mjs      # 目标校验、容量、重试、单屏事务
tools/stitch/test/targeted-regeneration.test.mjs# 模块 TDD
tools/stitch/bin/regenerate.mjs                 # CLI 生命周期、关闭与最终日志
tools/stitch/test/regenerate.test.mjs           # CLI 生命周期测试
tools/stitch/package.json                       # stitch:regenerate 命令
tools/stitch/src/verifier.mjs                   # login-only fallback 门禁
tools/stitch/test/verifier.test.mjs             # HTML 来源策略回归
docs/design/stitch/couple-cosmos/*              # 真实 state、manifest、HTML、截图
```

### Task 1: 固化正常业务态提示词

**Files:**
- Modify: `tools/stitch/src/prompts.mjs`
- Modify: `tools/stitch/test/prompts.test.mjs`

**Interfaces:**
- Produces: `TARGETED_REGENERATION_LOCAL_IDS: readonly string[]`
- Produces: `getRegenerationPrompt(localId: string) -> string`
- Preserves: `getScreenPrompt(screenId: string) -> string`

- [ ] **Step 1: 写失败测试**

在 `prompts.test.mjs` 导入新接口并增加：

```javascript
test("business prompts prioritize one normal page and fixed navigation", () => {
  for (const { id } of SCREEN_SPECS) {
    if (id === "login" || id === "system-states") continue;
    const prompt = getScreenPrompt(id);
    assert.match(prompt, /complete, actionable normal-state business screen/);
    assert.match(prompt, /Do not create a state guide/);
    assert.match(prompt, /星球、菜单、投喂、回忆、我们/);
  }
});

test("only system-states permits a full status component sheet", () => {
  assert.match(getScreenPrompt("system-states"), /only screen permitted/i);
  for (const { id } of SCREEN_SPECS) {
    if (id === "system-states") continue;
    assert.match(getScreenPrompt(id), /Do not create a state guide/);
    assert.doesNotMatch(getScreenPrompt(id), /only screen permitted/i);
  }
});

test("targeted regeneration has exactly the audited ids", () => {
  assert.deepEqual(TARGETED_REGENERATION_LOCAL_IDS, [
    "home-base", "bind", "menu-detail", "recipe-list", "recipe-editor",
    "feed", "note-editor", "map", "ai-chat", "notification-center",
    "system-states"
  ]);
  assert.equal(getRegenerationPrompt("home-base"), getScreenPrompt("home"));
  assert.throws(() => getRegenerationPrompt("home-emotion"), /Unknown targeted/);
  assert.throws(() => getRegenerationPrompt("login"), /Unknown targeted/);
});

test("binding and AI prompts require their primary workflows", () => {
  assert.match(getRegenerationPrompt("bind"), /邀请 TA/);
  assert.match(getRegenerationPrompt("bind"), /输入情侣码/);
  assert.match(getRegenerationPrompt("ai-chat"), /real Chinese conversation messages/);
  assert.match(getRegenerationPrompt("ai-chat"), /write-action confirmation preview/);
});
```

- [ ] **Step 2: 验证 RED**

Run:

```bash
cd tools/stitch
node --test test/prompts.test.mjs
```

Expected: FAIL，错误为新导出不存在或正常态断言不匹配。

- [ ] **Step 3: 实现分支化提示词**

在 `prompts.mjs` 增加：

```javascript
const NORMAL_SCREEN_GUARDRAILS = [
  "Create exactly one complete, actionable normal-state business screen; make that normal state visually dominant.",
  "Do not create a state guide, component sheet, debug gallery, developer-facing design notes, or vertically stacked page variants.",
  "Loading, empty data, failure, unauthorized, and unbound-couple cases may only be brief design notes and must never replace the normal-state page body.",
  "Do not visibly render DEBUG, UI STATES, implementation notes, or design instructions."
];

const PRODUCT_NAVIGATION_GUARDRAIL =
  "When bottom navigation is present, use exactly these Simplified Chinese labels: 星球、菜单、投喂、回忆、我们.";

const SYSTEM_STATES_GUARDRAILS = [
  "This is the only screen permitted to be a full global status-component sheet.",
  "Cover skeleton, empty data, network failure, unauthorized, unbound couple, offline draft, Toast, Modal, and reduced-motion variants across the whole product.",
  "Do not turn it into an AI-chef-only state page."
];

export const TARGETED_REGENERATION_LOCAL_IDS = Object.freeze([
  "home-base", "bind", "menu-detail", "recipe-list", "recipe-editor",
  "feed", "note-editor", "map", "ai-chat", "notification-center",
  "system-states"
]);

export function getRegenerationPrompt(localId) {
  if (!TARGETED_REGENERATION_LOCAL_IDS.includes(localId)) {
    throw new Error("Unknown targeted regeneration local id: " + localId);
  }
  return getScreenPrompt(localId === "home-base" ? "home" : localId);
}
```

`getScreenPrompt` 对 `system-states` 使用 `SYSTEM_STATES_GUARDRAILS`；其他页面使用 `NORMAL_SCREEN_GUARDRAILS`，除 `login` 外追加导航约束。强化 11 个目标的 requirements，明确正常主流程和禁止替代内容。

- [ ] **Step 4: 验证 GREEN**

Run: `node --test test/prompts.test.mjs`

Expected: 全部提示词测试 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/stitch/src/prompts.mjs tools/stitch/test/prompts.test.mjs
git commit -m "design: 强化Stitch业务页面提示词"
```

### Task 2: 实现事务式定向重生成模块

**Files:**
- Create: `tools/stitch/src/targeted-regeneration.mjs`
- Create: `tools/stitch/test/targeted-regeneration.test.mjs`

**Interfaces:**
- Consumes: `TARGETED_REGENERATION_LOCAL_IDS`, `getRegenerationPrompt`, `PROJECT_SCREEN_LIMIT`, `effectiveProjectId`, `ensureProjectRegistry`, `logEvent`
- Produces: `validateRegenerationTargets(localIds, state) -> { localIds, projectId }`
- Produces: `regenerateScreens(sdk, state, localIds, options) -> Promise<GenerationState>`

- [ ] **Step 1: 写目标与容量失败测试**

使用含三个项目和 20 个页面引用的 fixture，增加表驱动测试：

```javascript
for (const [name, targets, mutate, expected] of [
  ["empty", [], state => state, /at least one/],
  ["duplicate", ["bind", "bind"], state => state, /Duplicate/],
  ["unknown", ["unknown"], state => state, /Unknown targeted/],
  ["variant", ["home-food"], state => state, /Unknown targeted/],
  ["missing shard", ["bind"], state => ({ ...state, projects: state.projects.slice(0, 2) }), /third Stitch project/]
]) {
  test(`validation rejects ${name}`, () => {
    assert.throws(
      () => validateRegenerationTargets(targets, mutate(makeState())),
      expected
    );
  });
}
```

另加容量测试：第三分卷已有 2 个引用时，11 个新目标必须在任何 SDK 调用前拒绝。

- [ ] **Step 2: 写事务、恢复和日志失败测试**

至少覆盖：

```javascript
test("regeneration replaces only requested ids after checkpoint", async () => {
  const before = makeState();
  const checkpoints = [];
  const result = await regenerateScreens(
    makeSdk(async (_prompt, deviceType) => {
      assert.equal(deviceType, "MOBILE");
      return { screenId: "new-bind" };
    }),
    before,
    ["bind"],
    noDelay({ checkpoint: async state => checkpoints.push(structuredClone(state)) })
  );
  assert.deepEqual(result.screens.bind, {
    screenId: "new-bind", kind: "base", projectId: "project-3"
  });
  assert.deepEqual(before.screens.bind, originalBindReference());
  assert.deepEqual(
    Object.fromEntries(Object.entries(result.screens).filter(([id]) => id !== "bind")),
    Object.fromEntries(Object.entries(before.screens).filter(([id]) => id !== "bind"))
  );
  assert.equal(checkpoints.length, 1);
});

test("checkpoint failure preserves the old reference", async () => {
  const state = makeState();
  await assert.rejects(
    regenerateScreens(makeSdk(async () => ({ screenId: "orphan" })), state,
      ["bind"], noDelay({ checkpoint: async () => { throw new Error("checkpoint failed"); } })),
    /checkpoint failed/
  );
  assert.deepEqual(state.screens.bind, originalBindReference());
});

test("resume skips targets already owned by the third shard", async () => {
  const state = makeState();
  state.screens.bind = { screenId: "done", kind: "base", projectId: "project-3" };
  let calls = 0;
  await regenerateScreens(makeSdk(async () => { calls += 1; }), state,
    ["bind"], noDelay());
  assert.equal(calls, 0);
});
```

增加不可恢复失败、可恢复重试后成功、重试耗尽、空 `screenId` 和前一屏成功后一屏失败用例。解析日志并断言 `started/retry/ok/error`、`projectId/localId/screenTitle/attempt/stage/durationMs`，同时断言日志不含 `token=`、API key 和完整 prompt。

- [ ] **Step 3: 验证 RED**

Run: `node --test test/targeted-regeneration.test.mjs`

Expected: FAIL，模块不存在。

- [ ] **Step 4: 实现最小模块**

核心事务必须保持以下顺序：

```javascript
const nextState = {
  ...state,
  screens: {
    ...state.screens,
    [localId]: {
      screenId: generated.screenId,
      kind: "base",
      projectId
    }
  }
};
await checkpoint(nextState);
state = nextState;
```

目标项目固定取 `ensureProjectRegistry(state).projects[2]`；不得创建新项目。容量为第三分卷当前有效引用数加本次尚未完成目标数，且不得超过 `PROJECT_SCREEN_LIMIT`。每个目标只对 `error.recoverable === true` 重试，延迟为 `1000 * attempt`。错误消息移除 URL query 后再写日志。

- [ ] **Step 5: 验证 GREEN 与全量回归**

```bash
node --test test/targeted-regeneration.test.mjs
npm test
```

Expected: 新测试及全部既有测试 PASS。

- [ ] **Step 6: 提交**

```bash
git add tools/stitch/src/targeted-regeneration.mjs tools/stitch/test/targeted-regeneration.test.mjs
git commit -m "design: 支持Stitch定向事务式重生成"
```

### Task 3: 增加重生成 CLI 生命周期

**Files:**
- Create: `tools/stitch/bin/regenerate.mjs`
- Create: `tools/stitch/test/regenerate.test.mjs`
- Modify: `tools/stitch/package.json`

**Interfaces:**
- Produces: `runStitchRegenerate(localIds = process.argv.slice(2), dependencies = {}) -> Promise<0|1>`
- Produces command: `npm run stitch:regenerate -- <local-id>...`

- [ ] **Step 1: 写 CLI 失败测试**

构建与现有 generate runner 一致的依赖注入 fixture，覆盖：

```javascript
test("runner forwards ids and checkpoints to the repository state path", async () => {
  const writes = [];
  const result = await runStitchRegenerate(["bind"], {
    readConfig: () => TEST_CONFIG,
    createSdk: () => ({ sdk: {}, client: { async close() {} } }),
    readState: async () => makeState(),
    writeState: async (path, state) => writes.push([path, state]),
    regenerate: async (_sdk, state, ids, options) => {
      assert.deepEqual(ids, ["bind"]);
      await options.checkpoint({ ...state, marker: true });
      return { ...state, marker: true };
    },
    write: line => events.push(JSON.parse(line))
  });
  assert.equal(result, 0);
  assert.equal(writes.length, 1);
  assert.equal(events.at(-1).event, "stitch.regenerate");
});
```

表驱动覆盖配置、构造、state 读取、重生成、checkpoint、close 和意外 console 错误；失败只能产生一条最终 `stitch.regenerate/error`。验证默认 state path 与 cwd 无关，仅关闭期标准 `AbortError` 被忽略。

- [ ] **Step 2: 验证 RED**

Run: `node --test test/regenerate.test.mjs`

Expected: FAIL，CLI 模块不存在。

- [ ] **Step 3: 实现 CLI**

生命周期顺序：读取配置、创建 SDK、读取 state、调用 `regenerateScreens`、逐屏使用 `writeGenerationState` checkpoint、关闭 client、最后输出单条汇总事件。错误事件包含 `targetCount`、`projectId`、`errorName`、脱敏 `errorMessage` 和 `durationMs`。

在 `package.json` 增加：

```json
"stitch:regenerate": "node bin/regenerate.mjs"
```

- [ ] **Step 4: 验证 GREEN 与全量回归**

```bash
node --test test/regenerate.test.mjs
npm test
```

Expected: 全部测试 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/stitch/bin/regenerate.mjs tools/stitch/test/regenerate.test.mjs tools/stitch/package.json
git commit -m "design: 增加Stitch定向重生成命令"
```

### Task 4: 强制 login-only HTML 降级策略

**Files:**
- Modify: `tools/stitch/src/verifier.mjs`
- Modify: `tools/stitch/test/verifier.test.mjs`

**Interfaces:**
- Preserves: `verifyDesignExport(root, expectedIds, forbiddenValues, write)`
- Adds invariant: `login -> screenshot-fallback`; every other local ID -> `stitch`

- [ ] **Step 1: 写失败测试**

```javascript
test("verifyDesignExport rejects fallback HTML outside login", async () => {
  const data = await multiProjectFixture();
  data.manifest.screens.find(screen => screen.localId === "bind").htmlSource =
    "screenshot-fallback";
  await persistMultiProjectFixture(data);
  await assert.rejects(
    () => verifyDesignExport(data.root, MULTI_PROJECT_IDS, [], () => {}),
    /Only login may use screenshot-fallback/
  );
});

test("verifyDesignExport requires login fallback HTML", async () => {
  const data = await fixture();
  data.manifest.screens.find(screen => screen.localId === "login").htmlSource = "stitch";
  await writeJson(join(data.root, "manifest.json"), data.manifest);
  await assert.rejects(
    () => verifyDesignExport(data.root, ["login"], [], () => {}),
    /Login must use screenshot-fallback/
  );
});
```

同时将 `screenEntry("login")` 和 `fixture()` 的登录页默认来源改为
`screenshot-fallback`；更新旧的单项目 fixture 测试，不再允许登录页缺失
`htmlSource`。补充断言：非登录页使用 fallback 被拒；登录页使用 `stitch`
或缺失 `htmlSource` 均被拒。

- [ ] **Step 2: 验证 RED**

Run: `node --test --test-name-pattern='fallback HTML|login fallback' test/verifier.test.mjs`

Expected: 两项新测试 FAIL。

- [ ] **Step 3: 实现来源策略**

在 manifest entry 结构验证后加入：

```javascript
if (screen.localId === "login" && screen.htmlSource !== "screenshot-fallback") {
  throw new Error("Login must use screenshot-fallback HTML");
}
if (screen.localId !== "login" && screen.htmlSource !== "stitch") {
  throw new Error("Only login may use screenshot-fallback HTML: " + screen.localId);
}
```

- [ ] **Step 4: 验证 GREEN 与全量回归**

```bash
node --test test/verifier.test.mjs
npm test
```

Expected: 全部测试 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/stitch/src/verifier.mjs tools/stitch/test/verifier.test.mjs
git commit -m "test: 限制Stitch截图HTML降级范围"
```

### Task 5: 真实重生成、导出与视觉验收

**Files:**
- Modify: `docs/design/stitch/couple-cosmos/generation-state.json`
- Regenerate: `docs/design/stitch/couple-cosmos/manifest.json`
- Regenerate: `docs/design/stitch/couple-cosmos/html/*`
- Regenerate: `docs/design/stitch/couple-cosmos/screenshots/*`
- Modify after user choice: `docs/design/stitch/couple-cosmos/README.md`

- [ ] **Step 1: 运行完整测试和安全健康检查**

通过 PTY `read -s` 注入密钥。使用 Undici `ProxyAgent` 指向 `http://127.0.0.1:7897`，`requestTls.timeout=60000`。不得在命令或输出中显示密钥。

Run: `npm test`，随后调用 `runStitchHealth()`。

Expected: 全部测试 PASS，health `result=ok`。

- [ ] **Step 2: 真实生成 11 屏**

目标顺序固定为：

```text
home-base bind menu-detail recipe-list recipe-editor feed note-editor map ai-chat notification-center system-states
```

使用 ProxyAgent 预加载后调用 `runStitchRegenerate(targets)`。

Expected: 11 个 `stitch.screen.regenerate/ok`，每次成功后 state 原子 checkpoint。

- [ ] **Step 3: 校验 state 精确范围**

```bash
jq --arg project '3134958192996908783' '
  [.screens | to_entries[] |
    select(.key == "home-base" or .key == "bind" or .key == "menu-detail" or
      .key == "recipe-list" or .key == "recipe-editor" or .key == "feed" or
      .key == "note-editor" or .key == "map" or .key == "ai-chat" or
      .key == "notification-center" or .key == "system-states") |
    select(.value.projectId == $project)] | length
' ../../docs/design/stitch/couple-cosmos/generation-state.json
```

Expected: `11`。state 总页面 ID 仍为 `20`，三个首页变体引用不变。

- [ ] **Step 4: 重新导出并严格验证**

使用 ProxyAgent 调用 `runStitchExport()`，随后运行 `npm run stitch:verify`。

Expected: `screenCount=20`；20 张截图、20 个 HTML；仅 login 为 `screenshot-fallback`；其余 19 屏为 `stitch`。

- [ ] **Step 5: 视觉复核**

逐页查看 11 个替换截图和三个首页变体。业务页必须显示正常主流程且不含 `DEBUG`、`UI STATES` 或设计说明；`system-states` 必须是唯一状态表。检查简体中文、页面职责元素和五项导航。

- [ ] **Step 6: 用户选择首页并更新 README**

展示 `home-emotion`、`home-food`、`home-memory`，给出推荐，等待用户返回精确 ID。只在收到选择后更新 README。

- [ ] **Step 7: 提交前门禁**

```bash
cd tools/stitch
npm test
npm run stitch:verify
cd ../..
git diff --check
```

运行 GitNexus `detect_changes({scope:"all", repo:"couple-cosmos-stitch"})`，确认仅影响预期工具、测试和设计资产。

- [ ] **Step 8: 提交并推送**

```bash
git add tools/stitch docs/design/stitch/couple-cosmos \
  docs/superpowers/plans/2026-07-22-stitch-targeted-regeneration.md
git commit -m "design: 完成双人宇宙页面定向重生成"
git push origin codex/couple-cosmos-stitch
```
