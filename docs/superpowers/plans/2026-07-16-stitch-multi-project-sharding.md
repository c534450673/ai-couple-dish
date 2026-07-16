# Stitch Multi-Project Sharding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Couple Cosmos 在 Stitch 单项目 12 屏限制下自动分卷生成、跨项目导出并精确校验 20 个屏幕。

**Architecture:** 保留顶层 `projectId` 作为主项目，新增有序 `projects` 注册表和屏幕级 `projectId`。生成器在当前分卷达到 12 屏时先创建并 checkpoint 新项目，再生成屏幕；exporter 按屏幕项目获取资产，verifier 交叉校验 state/manifest 的项目集与屏幕归属。

**Tech Stack:** Node.js 20+、`@google/stitch-sdk@0.3.5`、`node:test`、JSON state/manifest、SHA-256。

## Global Constraints

- `STITCH_API_KEY` 只能由当前进程环境提供，不写入 Git、日志、命令、截图或 manifest。
- 所有工具日志必须为结构化 JSON，包含 `event`、`result`、`durationMs` 和非敏感上下文。
- Stitch SDK 继续精确锁定 `0.3.5`。
- 单个 Stitch 分卷最多安排 `12` 个屏幕。
- 保留旧单项目 state/manifest 的向后兼容。
- 不修改 `frontend-h5` 或后端业务代码。
- 真实密钥、项目恢复和远程续跑由 controller 在审查通过后执行，实现子代理不访问网络或密钥。

---

## File Structure

```text
tools/stitch/src/project-shards.mjs       # 分卷常量、旧状态兼容与屏幕项目解析
tools/stitch/src/state-store.mjs          # 默认 projects 注册表
tools/stitch/src/generate-home.mjs        # 主项目注册与首页屏幕归属
tools/stitch/src/generate-screens.mjs     # 12 屏自动分卷、项目 checkpoint
tools/stitch/src/exporter.mjs             # 跨项目导出与 manifest.projectIds
tools/stitch/src/verifier.mjs             # 项目注册表与屏幕归属精确校验
tools/stitch/test/*.test.mjs              # 分卷、导出、校验回归
```

### Task 1: 扩展状态并自动创建 Stitch 分卷

**Files:**
- Create: `tools/stitch/src/project-shards.mjs`
- Modify: `tools/stitch/src/state-store.mjs`
- Modify: `tools/stitch/src/generate-home.mjs`
- Modify: `tools/stitch/src/generate-screens.mjs`
- Modify: `tools/stitch/test/client.test.mjs`
- Modify: `tools/stitch/test/generate-home.test.mjs`
- Modify: `tools/stitch/test/generate-screens.test.mjs`

**Interfaces:**
- Produces: `PROJECT_SCREEN_LIMIT = 12`
- Produces: `effectiveProjectId(state, reference) -> string | null`
- Produces: `projectRegistry(state) -> Array<{ projectId: string, title: string }>`
- Produces: `ensureProjectRegistry(state) -> GenerationState`
- Extends: `GenerationState.projects`
- Extends: `GenerationState.screens[*].projectId`

- [ ] **Step 1: Write failing state and home ownership tests**

```javascript
test("home generation registers its primary project and owns every home screen", async () => {
  const result = await generateHomeDesign(fakeHomeSdk("project-1"), emptyGenerationState());
  assert.deepEqual(result.projects, [
    { projectId: "project-1", title: "AI Couple Dish - Couple Cosmos" }
  ]);
  for (const id of ["home-base", "home-emotion", "home-food", "home-memory"]) {
    assert.equal(result.screens[id].projectId, "project-1");
  }
});

test("completed legacy home state gains a primary project registry", async () => {
  const legacy = {
    ...emptyGenerationState(),
    projectId: "project-1",
    projects: undefined,
    screens: { "home-base": { screenId: "home-1", kind: "base" } }
  };
  const result = await generateHomeDesign(noCallSdk(), legacy);
  assert.deepEqual(result.projects, [
    { projectId: "project-1", title: legacy.projectTitle }
  ]);
});
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd tools/stitch
node --test test/client.test.mjs test/generate-home.test.mjs
```

Expected: FAIL because `projects` and screen-level `projectId` do not exist.

- [ ] **Step 3: Implement compatibility helpers and home ownership**

Create `tools/stitch/src/project-shards.mjs`:

```javascript
export const PROJECT_SCREEN_LIMIT = 12;

export function effectiveProjectId(state, reference) {
  return reference?.projectId || state?.projectId || null;
}

export function projectRegistry(state) {
  if (Array.isArray(state?.projects) && state.projects.length > 0) {
    return state.projects;
  }
  if (!state?.projectId) return [];
  return [{ projectId: state.projectId, title: state.projectTitle }];
}

export function ensureProjectRegistry(state) {
  const projects = projectRegistry(state);
  if (state.projects === projects) return state;
  return { ...state, projects };
}
```

Update `emptyGenerationState()` to include `projects: []`. In `generateHomeDesign`, normalize completed legacy state before returning. After a new project is generated, write the primary registry and add `projectId: project.projectId` to all four home references.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all focused tests PASS.

- [ ] **Step 5: Write failing automatic shard tests**

```javascript
test("generation checkpoints a new shard before its first screen", async () => {
  const order = [];
  const state = stateWithProjectScreenCount(12);
  const sdk = {
    async createProject(title) {
      order.push(["create", title]);
      return { projectId: "project-2" };
    },
    project(projectId) {
      assert.equal(projectId, "project-2");
      return {
        async generate() {
          order.push(["generate", projectId]);
          return { screenId: "memories-2" };
        }
      };
    }
  };
  const result = await generateRemainingScreens(sdk, state, {
    maxAttempts: 1,
    sleep: async () => {},
    async checkpoint(next) {
      order.push(["checkpoint", structuredClone(next)]);
    }
  });
  assert.equal(order[0][0], "create");
  assert.equal(order[1][0], "checkpoint");
  assert.equal(order[2][0], "generate");
  assert.equal(result.screens.memories.projectId, "project-2");
});

test("generation resumes an existing non-full shard without creating another", async () => {
  const state = stateWithProjectsAndOneShardScreen();
  const sdk = shardResumeSdk({ forbidCreateProject: true });
  const result = await generateRemainingScreens(sdk, state, noDelayOptions());
  assert.equal(result.projects.length, 2);
  assert.equal(result.screens["note-editor"].projectId, "project-2");
});
```

- [ ] **Step 6: Run shard tests and verify RED**

Run `node --test test/generate-screens.test.mjs`.

Expected: FAIL because generation always uses `state.projectId` and never creates/checkpoints a shard.

- [ ] **Step 7: Implement minimal shard selection**

Add to `generate-screens.mjs`:

```javascript
import {
  PROJECT_SCREEN_LIMIT,
  effectiveProjectId,
  ensureProjectRegistry
} from "./project-shards.mjs";

function countScreens(state, projectId) {
  return Object.values(state.screens).filter(
    reference => effectiveProjectId(state, reference) === projectId
  ).length;
}

async function ensureWritableProject(sdk, state, checkpoint, write) {
  const active = state.projects.at(-1);
  if (active && countScreens(state, active.projectId) < PROJECT_SCREEN_LIMIT) {
    return { state, projectId: active.projectId };
  }
  const shardNumber = state.projects.length + 1;
  const title = `${state.projectTitle} - Part ${shardNumber}`;
  const started = performance.now();
  logEvent("stitch.project.shard", {
    result: "started",
    shardNumber,
    title,
    currentScreenCount: active ? countScreens(state, active.projectId) : 0
  }, write);
  const project = await sdk.createProject(title);
  if (typeof project?.projectId !== "string" || !project.projectId.trim()) {
    throw new Error("Expected a non-empty Stitch shard projectId");
  }
  const next = {
    ...state,
    projects: [...state.projects, { projectId: project.projectId, title }]
  };
  await checkpoint(next);
  logEvent("stitch.project.shard", {
    result: "ok",
    shardNumber,
    projectId: project.projectId,
    title,
    durationMs: Math.round(performance.now() - started)
  }, write);
  return { state: next, projectId: project.projectId };
}
```

Normalize `initialState` with `ensureProjectRegistry`. Before each missing screen, call `ensureWritableProject`; use `sdk.project(projectId)`; store `{ screenId, kind: "base", projectId }`; preserve retry, validation, checkpoint and logging behavior.

- [ ] **Step 8: Run all tests and commit Task 1**

```bash
cd tools/stitch
npm test
node --check src/project-shards.mjs
node --check src/generate-home.mjs
node --check src/generate-screens.mjs
git diff --check
```

Expected: all tests PASS. Run GitNexus impact before editing existing symbols and `detect_changes(scope: "staged")` before commit.

```bash
git add tools/stitch/src/project-shards.mjs tools/stitch/src/state-store.mjs tools/stitch/src/generate-home.mjs tools/stitch/src/generate-screens.mjs tools/stitch/test/client.test.mjs tools/stitch/test/generate-home.test.mjs tools/stitch/test/generate-screens.test.mjs
git commit -m "design: 支持Stitch屏幕自动分卷"
```

### Task 2: 跨 Stitch 项目导出统一 manifest

**Files:**
- Modify: `tools/stitch/src/exporter.mjs`
- Modify: `tools/stitch/test/exporter.test.mjs`

**Interfaces:**
- Consumes: `effectiveProjectId(state, reference)`
- Consumes: `projectRegistry(state)`
- Produces: `manifest.projectIds: string[]`
- Produces: each manifest screen entry with its real `projectId`

- [ ] **Step 1: Write a failing multi-project export test**

```javascript
test("exportDesignProject reads each screen from its owning project", async () => {
  const calls = [];
  const state = twoProjectState();
  const sdk = {
    project(projectId) {
      calls.push(projectId);
      return fakeExportProject(projectId);
    }
  };
  const manifest = await exportDesignProject(
    sdk,
    state,
    root,
    fakeFetch,
    write
  );
  assert.deepEqual([...new Set(calls)], ["project-1", "project-2"]);
  assert.deepEqual(manifest.projectIds, ["project-1", "project-2"]);
  assert.equal(
    manifest.screens.find(screen => screen.localId === "memories").projectId,
    "project-2"
  );
});
```

- [ ] **Step 2: Run the exporter test and verify RED**

Run:

```bash
cd tools/stitch
node --test test/exporter.test.mjs
```

Expected: FAIL because exporter uses only `state.projectId` and manifest has no `projectIds`.

- [ ] **Step 3: Implement project caching and manifest project IDs**

Import `effectiveProjectId` and `projectRegistry`. Replace the single project handle with a cache:

```javascript
const projectHandles = new Map();
function projectFor(projectId) {
  if (!projectHandles.has(projectId)) {
    projectHandles.set(projectId, sdk.project(projectId));
  }
  return projectHandles.get(projectId);
}
```

For each reference:

```javascript
const projectId = effectiveProjectId(state, reference);
if (typeof projectId !== "string" || !projectId.trim()) {
  throw new Error("Expected every exported screen to have a projectId");
}
const screen = await projectFor(projectId).getScreen(reference.screenId);
```

Use the resolved project ID in the per-asset log context and manifest entry. Build the manifest as:

```javascript
const manifest = {
  version: 1,
  projectId: state.projectId,
  projectIds: projectRegistry(state).map(project => project.projectId),
  screens
};
```

Keep staging, promotion, URL/staging redaction and manifest-last behavior unchanged.

- [ ] **Step 4: Run tests and commit Task 2**

```bash
cd tools/stitch
node --test test/exporter.test.mjs
npm test
node --check src/exporter.mjs
git diff --check
```

Expected: all tests PASS. Run GitNexus impact/detect and commit:

```bash
git add tools/stitch/src/exporter.mjs tools/stitch/test/exporter.test.mjs
git commit -m "design: 跨Stitch分卷导出设计资产"
```

### Task 3: 校验多项目注册表与屏幕归属

**Files:**
- Modify: `tools/stitch/src/verifier.mjs`
- Modify: `tools/stitch/test/verifier.test.mjs`

**Interfaces:**
- Consumes: optional legacy `state.projects` / `manifest.projectIds`
- Verifies: exact ordered project registry and per-screen project ownership

- [ ] **Step 1: Write failing multi-project verifier tests**

```javascript
test("verifyDesignExport accepts exact multi-project ownership", async () => {
  const root = await multiProjectFixture();
  assert.deepEqual(await verifyDesignExport(root, EXPECTED_IDS, []), {
    screenCount: EXPECTED_IDS.length
  });
});

for (const mutation of [
  duplicateStateProject,
  unknownScreenProject,
  manifestProjectOrderMismatch,
  manifestEntryProjectMismatch
]) {
  test(`verifyDesignExport rejects ${mutation.name}`, async () => {
    const root = await multiProjectFixture();
    await mutation(root);
    await assert.rejects(() => verifyDesignExport(root, EXPECTED_IDS, []));
  });
}

test("legacy one-project fixture remains valid", async () => {
  const root = await legacyFixtureWithoutProjectArrays();
  assert.deepEqual(await verifyDesignExport(root, ["login"], []), {
    screenCount: 1
  });
});
```

- [ ] **Step 2: Run verifier tests and verify RED**

Run:

```bash
cd tools/stitch
node --test test/verifier.test.mjs
```

Expected: the valid multi-project fixture fails because project arrays and screen ownership are not cross-checked.

- [ ] **Step 3: Implement strict project registry validation**

Add helpers that treat missing arrays as a one-project legacy registry, but strictly validate arrays when present:

```javascript
function stateProjects(state) {
  return Array.isArray(state.projects) && state.projects.length > 0
    ? state.projects
    : [{ projectId: state.projectId, title: state.projectTitle }];
}

function manifestProjectIds(manifest) {
  return Array.isArray(manifest.projectIds) && manifest.projectIds.length > 0
    ? manifest.projectIds
    : [manifest.projectId];
}
```

Before per-screen logs:

```javascript
const projects = stateProjects(state);
const stateProjectIds = projects.map(project => project.projectId);
const exportedProjectIds = manifestProjectIds(manifest);
assertNonEmptyUniqueIds(stateProjectIds, "state projects");
assertNonEmptyUniqueIds(exportedProjectIds, "manifest projects");
if (stateProjectIds[0] !== state.projectId || exportedProjectIds[0] !== manifest.projectId) {
  throw new Error("Primary project id mismatch");
}
if (JSON.stringify(stateProjectIds) !== JSON.stringify(exportedProjectIds)) {
  throw new Error("Project registry mismatch");
}
```

For every state screen, resolve `reference.projectId || state.projectId` and require it to be registered. In `validateScreenEntry`, require `screen.projectId` to equal that effective state project ID. Do not change raw/decoded secret scanning, lexical/realpath containment, hash ordering or CLI behavior.

- [ ] **Step 4: Run tests and commit Task 3**

```bash
cd tools/stitch
node --test test/verifier.test.mjs
npm test
node --check src/verifier.mjs
git diff --check
```

Expected: all tests PASS. Run GitNexus impact/detect and commit:

```bash
git add tools/stitch/src/verifier.mjs tools/stitch/test/verifier.test.mjs
git commit -m "test: 校验Stitch分卷归属"
```

## Completion Gate

- Existing single-project fixtures still pass.
- A full primary project creates/checkpoints a new shard before generation.
- Screen references and manifest entries preserve real project ownership.
- Exporter fetches each screen through the correct project handle.
- Verifier rejects unknown, duplicate, reordered or mismatched project ownership.
- All tool tests pass and GitNexus reports no unexpected affected execution flow.
- No real Stitch call or secret is used during these three implementation tasks.
