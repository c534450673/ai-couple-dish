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
