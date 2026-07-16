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
