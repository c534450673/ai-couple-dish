import { createHash } from "node:crypto";
import { readFile, realpath } from "node:fs/promises";
import { isAbsolute, join, relative, resolve, sep } from "node:path";
import { performance } from "node:perf_hooks";
import { logEvent } from "./logger.mjs";

const VALID_KINDS = new Set(["base", "variant"]);

function hash(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function assertNoForbiddenValue(buffer, forbiddenValues, label) {
  for (const forbidden of forbiddenValues) {
    const value = Buffer.isBuffer(forbidden)
      ? forbidden
      : Buffer.from(String(forbidden));
    if (value.length > 0 && buffer.includes(value)) {
      throw new Error("Forbidden secret value found: " + label);
    }
  }
}

function assertNoForbiddenJsonValue(value, forbiddenValues, label) {
  if (typeof value === "string") {
    assertNoForbiddenValue(Buffer.from(value), forbiddenValues, label);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      assertNoForbiddenJsonValue(item, forbiddenValues, label);
    }
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value)) {
    assertNoForbiddenValue(Buffer.from(key), forbiddenValues, label);
    assertNoForbiddenJsonValue(item, forbiddenValues, label);
  }
}

function duplicateIds(ids) {
  const seen = new Set();
  const duplicates = new Set();
  for (const id of ids) {
    if (seen.has(id)) duplicates.add(id);
    seen.add(id);
  }
  return [...duplicates];
}

function assertExactIds(actualIds, expectedIds, label) {
  const duplicates = duplicateIds(actualIds);
  if (duplicates.length > 0) {
    throw new Error(`Duplicate ${label} screens: ${duplicates.join(", ")}`);
  }

  const actual = new Set(actualIds);
  const expected = new Set(expectedIds);
  const missing = expectedIds.filter(id => !actual.has(id));
  if (missing.length > 0) {
    throw new Error(`Missing ${label} screens: ${missing.join(", ")}`);
  }
  const unexpected = actualIds.filter(id => !expected.has(id));
  if (unexpected.length > 0) {
    throw new Error(`Unexpected ${label} screens: ${unexpected.join(", ")}`);
  }
}

function stateProjects(state) {
  if (state.projects === undefined) {
    return [{ projectId: state.projectId, title: state.projectTitle }];
  }
  if (
    !Array.isArray(state.projects) ||
    state.projects.some(project =>
      !project ||
      typeof project !== "object" ||
      Array.isArray(project) ||
      typeof project.projectId !== "string" ||
      !project.projectId.trim() ||
      typeof project.title !== "string" ||
      !project.title.trim()
    )
  ) {
    throw new Error("Invalid state projects");
  }
  return state.projects;
}

function manifestProjectIds(manifest) {
  if (manifest.projectIds === undefined) {
    return [manifest.projectId];
  }
  if (!Array.isArray(manifest.projectIds)) {
    throw new Error("Invalid manifest projects");
  }
  return manifest.projectIds;
}

function assertNonEmptyUniqueIds(ids, label) {
  if (
    ids.length === 0 ||
    ids.some(projectId => typeof projectId !== "string" || !projectId.trim())
  ) {
    throw new Error("Invalid " + label);
  }
  const duplicates = duplicateIds(ids);
  if (duplicates.length > 0) {
    throw new Error(`Duplicate ${label}: ${duplicates.join(", ")}`);
  }
}

function validateManifestAndState(manifest, state, expectedIds) {
  if (manifest?.version !== 1) {
    throw new Error("Invalid manifest version");
  }
  if (typeof manifest.projectId !== "string" || !manifest.projectId.trim()) {
    throw new Error("Invalid manifest project id");
  }
  if (!Array.isArray(manifest.screens)) {
    throw new Error("Invalid manifest screens");
  }
  if (
    !state ||
    typeof state !== "object" ||
    !state.screens ||
    typeof state.screens !== "object" ||
    Array.isArray(state.screens)
  ) {
    throw new Error("Invalid generation state screens");
  }
  if (!Array.isArray(expectedIds)) {
    throw new Error("Invalid expected screens");
  }

  const expectedDuplicates = duplicateIds(expectedIds);
  if (expectedDuplicates.length > 0) {
    throw new Error(
      "Duplicate expected screens: " + expectedDuplicates.join(", ")
    );
  }
  const exportedIds = manifest.screens.map(screen => screen?.localId);
  if (exportedIds.some(id => typeof id !== "string" || !id.trim())) {
    throw new Error("Invalid manifest local id");
  }
  assertExactIds(exportedIds, expectedIds, "exported");
  assertExactIds(Object.keys(state.screens), expectedIds, "state");

  if (state.projectId !== manifest.projectId) {
    throw new Error("Project id mismatch");
  }

  const projects = stateProjects(state);
  const stateProjectIds = projects.map(project => project?.projectId);
  const exportedProjectIds = manifestProjectIds(manifest);
  assertNonEmptyUniqueIds(stateProjectIds, "state projects");
  assertNonEmptyUniqueIds(exportedProjectIds, "manifest projects");
  if (
    stateProjectIds[0] !== state.projectId ||
    exportedProjectIds[0] !== manifest.projectId
  ) {
    throw new Error("Primary project id mismatch");
  }
  if (JSON.stringify(stateProjectIds) !== JSON.stringify(exportedProjectIds)) {
    throw new Error("Project registry mismatch");
  }
  for (const [localId, reference] of Object.entries(state.screens)) {
    const projectId = reference?.projectId || state.projectId;
    if (!stateProjectIds.includes(projectId)) {
      throw new Error("Unknown screen project id: " + localId);
    }
  }
}

function assertArtifactPath(root, localId, actual, expected) {
  const rootPath = resolve(root);
  const targetPath = typeof actual === "string" ? resolve(root, actual) : "";
  const hasTraversal =
    typeof actual === "string" && actual.split(/[\\/]/).includes("..");
  const isInsideRoot = targetPath.startsWith(rootPath + sep);
  if (
    typeof actual !== "string" ||
    actual !== expected ||
    isAbsolute(actual) ||
    hasTraversal ||
    !isInsideRoot
  ) {
    throw new Error("Invalid artifact path: " + localId);
  }
}

function validateScreenEntry(root, state, screen) {
  const reference = state.screens[screen.localId];
  const projectId = reference?.projectId || state.projectId;
  if (screen.projectId !== projectId) {
    throw new Error("Manifest project id mismatch: " + screen.localId);
  }
  if (
    typeof screen.screenId !== "string" ||
    !screen.screenId.trim() ||
    typeof reference?.screenId !== "string" ||
    !reference.screenId.trim()
  ) {
    throw new Error("Invalid screen id: " + screen.localId);
  }
  if (!VALID_KINDS.has(screen.kind) || !VALID_KINDS.has(reference?.kind)) {
    throw new Error("Invalid screen kind: " + screen.localId);
  }
  if (screen.screenId !== reference.screenId) {
    throw new Error("Screen id mismatch: " + screen.localId);
  }
  if (screen.kind !== reference.kind) {
    throw new Error("Screen kind mismatch: " + screen.localId);
  }
  assertArtifactPath(
    root,
    screen.localId,
    screen.screenshot,
    `screenshots/${screen.localId}.png`
  );
  assertArtifactPath(
    root,
    screen.localId,
    screen.html,
    `html/${screen.localId}.html`
  );
}

async function readVerifiedArtifact(root, realRoot, localId, artifactPath) {
  const resolvedArtifactPath = await realpath(join(root, artifactPath));
  const relativeRealPath = relative(realRoot, resolvedArtifactPath);
  if (
    !relativeRealPath ||
    relativeRealPath === ".." ||
    relativeRealPath.startsWith(".." + sep) ||
    isAbsolute(relativeRealPath)
  ) {
    throw new Error("Invalid artifact path: " + localId);
  }
  return readFile(resolvedArtifactPath);
}

export async function verifyDesignExport(
  root,
  expectedIds,
  forbiddenValues = [],
  write = line => process.stderr.write(line + String.fromCharCode(10))
) {
  const manifestBuffer = await readFile(join(root, "manifest.json"));
  const stateBuffer = await readFile(join(root, "generation-state.json"));
  const activeForbiddenValues = forbiddenValues.filter(Boolean);
  assertNoForbiddenValue(manifestBuffer, activeForbiddenValues, "manifest.json");
  assertNoForbiddenValue(
    stateBuffer,
    activeForbiddenValues,
    "generation-state.json"
  );

  const manifest = JSON.parse(manifestBuffer.toString("utf8"));
  const state = JSON.parse(stateBuffer.toString("utf8"));
  assertNoForbiddenJsonValue(manifest, activeForbiddenValues, "manifest.json");
  assertNoForbiddenJsonValue(
    state,
    activeForbiddenValues,
    "generation-state.json"
  );
  validateManifestAndState(manifest, state, expectedIds);
  const realRoot = await realpath(root);

  for (const screen of manifest.screens) {
    const started = performance.now();
    const reference = state.screens[screen.localId];
    const context = {
      projectId: reference?.projectId || state.projectId,
      manifestProjectId: screen.projectId,
      localId: screen.localId,
      screenId: screen.screenId,
      kind: screen.kind,
      screenshotPath: `screenshots/${screen.localId}.png`,
      htmlPath: `html/${screen.localId}.html`
    };
    logEvent("stitch.verify.screen", { result: "started", ...context }, write);
    try {
      validateScreenEntry(root, state, screen);
      const screenshot = await readVerifiedArtifact(
        root,
        realRoot,
        screen.localId,
        screen.screenshot
      );
      assertNoForbiddenValue(
        screenshot,
        activeForbiddenValues,
        screen.localId
      );
      const html = await readVerifiedArtifact(
        root,
        realRoot,
        screen.localId,
        screen.html
      );
      assertNoForbiddenValue(html, activeForbiddenValues, screen.localId);
      if (hash(screenshot) !== screen.screenshotSha256) {
        throw new Error("Screenshot hash mismatch: " + screen.localId);
      }
      if (hash(html) !== screen.htmlSha256) {
        throw new Error("HTML hash mismatch: " + screen.localId);
      }
      logEvent(
        "stitch.verify.screen",
        {
          result: "ok",
          ...context,
          durationMs: Math.round(performance.now() - started)
        },
        write
      );
    } catch (error) {
      logEvent(
        "stitch.verify.screen",
        {
          result: "error",
          ...context,
          durationMs: Math.round(performance.now() - started),
          errorName: error?.name || "Error",
          errorMessage: error?.message || String(error)
        },
        write
      );
      throw error;
    }
  }

  return { screenCount: manifest.screens.length };
}
