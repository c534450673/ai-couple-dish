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
