import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, mkdtemp, readFile, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { isAbsolute, join } from "node:path";
import test from "node:test";
import { runStitchExport } from "../bin/export.mjs";
import { downloadArtifact, exportDesignProject } from "../src/exporter.mjs";

function digest(value) {
  return createHash("sha256").update(value).digest("hex");
}

function makeSdk(screenIds) {
  return {
    project(projectId) {
      assert.equal(projectId, "project-1");
      return {
        async getScreen(screenId) {
          assert.ok(screenIds.includes(screenId));
          return {
            async getImage() {
              return `https://assets.example/${screenId}/image?token=secret`;
            },
            async getHtml() {
              return `https://assets.example/${screenId}/html?token=secret`;
            }
          };
        }
      };
    }
  };
}

function makeFetch(failurePath) {
  return async (url, options) => {
    assert.deepEqual(options, { redirect: "follow" });
    const path = new URL(url).pathname;
    if (path === failurePath) return { ok: false, status: 503 };
    return {
      ok: true,
      status: 200,
      async arrayBuffer() {
        return Buffer.from(path.slice(1).replaceAll("/", "-"));
      }
    };
  };
}

function makeState() {
  return {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {
      login: { screenId: "screen-1", kind: "base" },
      menu: { screenId: "screen-2", kind: "variant" }
    }
  };
}

function twoProjectState() {
  const state = makeState();
  return {
    ...state,
    projects: [
      { projectId: "project-1", title: state.projectTitle },
      { projectId: "project-2", title: `${state.projectTitle} - Part 2` }
    ],
    screens: {
      memories: {
        screenId: "screen-3",
        kind: "base",
        projectId: "project-2"
      },
      ...state.screens
    }
  };
}

function fakeExportProject(projectId, screenReads) {
  return {
    async getScreen(screenId) {
      screenReads.push([projectId, screenId]);
      return {
        async getImage() {
          return `https://assets.example/${projectId}/${screenId}/image?token=secret`;
        },
        async getHtml() {
          return `https://assets.example/${projectId}/${screenId}/html?token=secret`;
        }
      };
    }
  };
}

test("downloadArtifact rejects non-2xx responses without writing the target", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-download-"));
  const output = join(root, "artifact.png");

  await assert.rejects(
    downloadArtifact("https://assets.example/image", output, makeFetch("/image")),
    /Artifact download failed with HTTP 503/
  );
  await assert.rejects(access(output), { code: "ENOENT" });
});

test("exportDesignProject writes multi-screen artifacts, manifest and detailed logs", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-"));
  const lines = [];

  const manifest = await exportDesignProject(
    makeSdk(["screen-1", "screen-2"]),
    makeState(),
    root,
    makeFetch(),
    line => lines.push(line)
  );

  assert.deepEqual(manifest, JSON.parse(await readFile(join(root, "manifest.json"), "utf8")));
  assert.equal(manifest.version, 1);
  assert.equal(manifest.projectId, "project-1");
  assert.deepEqual(manifest.screens.map(screen => screen.localId), ["login", "menu"]);
  for (const screen of manifest.screens) {
    const reference = makeState().screens[screen.localId];
    const screenshotBytes = `${reference.screenId}-image`;
    const htmlBytes = `${reference.screenId}-html`;
    assert.deepEqual(Object.keys(screen), [
      "localId", "projectId", "screenId", "kind", "screenshot",
      "screenshotSha256", "html", "htmlSha256", "exportedAt"
    ]);
    assert.equal(screen.projectId, "project-1");
    assert.equal(screen.screenId, reference.screenId);
    assert.equal(screen.kind, reference.kind);
    assert.equal(screen.screenshot, `screenshots/${screen.localId}.png`);
    assert.equal(screen.html, `html/${screen.localId}.html`);
    assert.equal(screen.screenshotSha256, digest(screenshotBytes));
    assert.equal(screen.htmlSha256, digest(htmlBytes));
    assert.match(screen.exportedAt, /^\d{4}-\d{2}-\d{2}T/);
    assert.equal(await readFile(join(root, screen.screenshot), "utf8"), screenshotBytes);
    assert.equal(await readFile(join(root, screen.html), "utf8"), htmlBytes);
  }

  const events = lines.map(line => JSON.parse(line));
  assert.deepEqual(events.map(event => [event.localId, event.artifact, event.result]), [
    ["login", "screenshots/login.png", "started"],
    ["login", "screenshots/login.png", "ok"],
    ["login", "html/login.html", "started"],
    ["login", "html/login.html", "ok"],
    ["menu", "screenshots/menu.png", "started"],
    ["menu", "screenshots/menu.png", "ok"],
    ["menu", "html/menu.html", "started"],
    ["menu", "html/menu.html", "ok"]
  ]);
  assert.ok(events.every(event => event.event === "stitch.export.screen"));
  assert.ok(events.every(event => event.projectId === "project-1"));
  assert.ok(events.every(event => Number.isInteger(event.durationMs)));
  assert.ok(events.filter(event => event.result === "ok")
    .every(event => event.bytes > 0 && event.hash.length === 64));
  assert.doesNotMatch(lines.join("\n"), /token=secret/);
});

test("exportDesignProject reads each screen from its owning project", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-shards-"));
  const calls = [];
  const screenReads = [];
  const lines = [];
  const state = twoProjectState();
  const sdk = {
    project(projectId) {
      calls.push(projectId);
      return fakeExportProject(projectId, screenReads);
    }
  };

  const manifest = await exportDesignProject(
    sdk,
    state,
    root,
    makeFetch(),
    line => lines.push(line)
  );

  assert.deepEqual(calls, ["project-2", "project-1"]);
  assert.deepEqual(screenReads, [
    ["project-2", "screen-3"],
    ["project-1", "screen-1"],
    ["project-1", "screen-2"]
  ]);
  assert.deepEqual(manifest.projectIds, ["project-1", "project-2"]);
  assert.equal(
    manifest.screens.find(screen => screen.localId === "memories").projectId,
    "project-2"
  );
  const memoryEvents = lines
    .map(line => JSON.parse(line))
    .filter(event => event.localId === "memories");
  assert.ok(memoryEvents.length > 0);
  assert.ok(memoryEvents.every(event => event.projectId === "project-2"));
});

test("exportDesignProject preserves the prior export on mid-download failure", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-failure-"));
  const manifestPath = join(root, "manifest.json");
  const lines = [];
  await exportDesignProject(
    makeSdk(["screen-1", "screen-2"]),
    makeState(),
    root,
    makeFetch(),
    () => {}
  );
  const priorManifestText = await readFile(manifestPath, "utf8");
  const priorManifest = JSON.parse(priorManifestText);
  const priorArtifacts = new Map();
  for (const screen of priorManifest.screens) {
    priorArtifacts.set(screen.screenshot, await readFile(join(root, screen.screenshot)));
    priorArtifacts.set(screen.html, await readFile(join(root, screen.html)));
  }
  const failingFetch = async (url, options) => {
    assert.deepEqual(options, { redirect: "follow" });
    const path = new URL(url).pathname;
    if (path === "/screen-2/html") return { ok: false, status: 503 };
    return {
      ok: true,
      status: 200,
      async arrayBuffer() {
        return Buffer.from("new-" + path.slice(1).replaceAll("/", "-"));
      }
    };
  };

  await assert.rejects(
    exportDesignProject(
      makeSdk(["screen-1", "screen-2"]),
      makeState(),
      root,
      failingFetch,
      line => lines.push(line)
    ),
    /Artifact download failed with HTTP 503/
  );

  assert.equal(await readFile(manifestPath, "utf8"), priorManifestText);
  for (const screen of priorManifest.screens) {
    for (const [artifact, hash] of [
      [screen.screenshot, screen.screenshotSha256],
      [screen.html, screen.htmlSha256]
    ]) {
      const content = await readFile(join(root, artifact));
      assert.deepEqual(content, priorArtifacts.get(artifact));
      assert.equal(digest(content), hash);
      assert.doesNotMatch(content.toString(), /^new-/);
    }
  }
  await assert.rejects(access(join(root, "manifest.json.tmp")), { code: "ENOENT" });
  assert.deepEqual((await readdir(root)).sort(), ["html", "manifest.json", "screenshots"]);
  const errors = lines.map(line => JSON.parse(line)).filter(event => event.result === "error");
  assert.equal(errors.length, 1);
  assert.deepEqual(
    [errors[0].localId, errors[0].screenId, errors[0].kind, errors[0].artifact,
      errors[0].errorName, errors[0].errorMessage],
    ["menu", "screen-2", "variant", "html/menu.html", "Error",
      "Artifact download failed with HTTP 503"]
  );
  assert.ok(Number.isInteger(errors[0].durationMs));
});

function makeAbortError(message) {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
}

async function captureExport({ close, overrides = {}, onExport } = {}) {
  const actualConsoleError = console.error;
  const rawConsoleCalls = [];
  const restoredConsoleError = (...args) => rawConsoleCalls.push(args);
  const lines = [];
  const lifecycle = { closeCount: 0 };
  const client = {
    async close() {
      lifecycle.closeCount += 1;
      await close?.();
    }
  };
  let paths;
  console.error = restoredConsoleError;
  try {
    const exitCode = await runStitchExport({
      readState: async statePath => {
        paths = { ...paths, statePath };
        return makeState();
      },
      readConfig: () => ({ apiKey: "test-placeholder", host: "https://example.invalid" }),
      createSdk: () => ({ sdk: {}, client }),
      exportProject: async (_sdk, state, outputRoot, _fetchImpl, write) => {
        paths = { ...paths, outputRoot };
        onExport?.({ state, write });
        return { version: 1, projectId: state.projectId, screens: [{}, {}] };
      },
      ...overrides,
      write: line => lines.push(line)
    });
    await new Promise(resolve => setImmediate(resolve));
    return {
      exitCode,
      events: lines.map(line => JSON.parse(line)),
      lifecycle,
      paths,
      rawConsoleCalls,
      consoleRestored: console.error === restoredConsoleError
    };
  } finally {
    console.error = actualConsoleError;
  }
}

test("runStitchExport redacts real staging paths from exporter failures", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-redaction-"));
  const result = await captureExport({
    overrides: {
      readState: async () => ({
        ...makeState(),
        screens: {
          "nested/path": { screenId: "screen-1", kind: "base" }
        }
      }),
      createSdk: () => ({
        sdk: makeSdk(["screen-1"]),
        client: { async close() {} }
      }),
      exportProject: exportDesignProject,
      outputRoot: root,
      fetchImpl: makeFetch()
    }
  });

  const serialized = result.events.map(event => JSON.stringify(event)).join("\n");
  const final = result.events.find(event => event.event === "stitch.export");
  assert.equal(result.exitCode, 1);
  assert.match(serialized, /\[STAGING\]/);
  assert.equal(serialized.includes(root), false);
  assert.doesNotMatch(serialized, /\.stitch-export-/);
  assert.equal(final.result, "error");
  assert.equal("stack" in final, false);
});

test("runStitchExport serializes setup failures into one final JSON event", async t => {
  const cases = [
    ["missing state", { readState: async () => { throw new Error("state missing"); } }, /state missing/],
    ["missing project", { readState: async () => ({ ...makeState(), projectId: null }) }, /stitch:generate/],
    ["configuration", { readConfig: () => { throw new Error("config failed"); } }, /config failed/],
    ["construction", { createSdk: () => { throw new Error("construct failed"); } }, /construct failed/]
  ];
  for (const [name, overrides, expected] of cases) {
    await t.test(name, async () => {
      const result = await captureExport({ overrides });
      const finals = result.events.filter(event => event.event === "stitch.export");
      assert.equal(result.exitCode, 1);
      assert.equal(result.lifecycle.closeCount, 0);
      assert.equal(finals.length, 1);
      assert.match(finals[0].errorMessage, expected);
      assert.equal("stack" in finals[0], false);
      assert.deepEqual(result.rawConsoleCalls, []);
      assert.equal(result.consoleRestored, true);
    });
  }
});

test("runStitchExport uses repository paths, one writer and reports success after close", async () => {
  let forwardedWriter;
  const result = await captureExport({
    close: () => setImmediate(() => console.error(
      "Stitch Transport Error:", makeAbortError("closed")
    )),
    onExport({ write }) {
      forwardedWriter = write;
      write(JSON.stringify({ event: "stitch.export.screen", result: "ok", durationMs: 0 }));
    }
  });
  const final = result.events.find(event => event.event === "stitch.export");
  assert.equal(result.exitCode, 0);
  assert.equal(result.lifecycle.closeCount, 1);
  assert.equal(result.events.filter(event => event.event === "stitch.export.screen").length, 1);
  assert.equal(typeof forwardedWriter, "function");
  assert.ok(isAbsolute(result.paths.statePath));
  assert.equal(result.paths.statePath, join(result.paths.outputRoot, "generation-state.json"));
  assert.deepEqual([final.result, final.projectId, final.screenCount], ["ok", "project-1", 2]);
  assert.ok(Number.isInteger(final.durationMs));
  assert.deepEqual(result.rawConsoleCalls, []);
  assert.equal(result.consoleRestored, true);
});

test("runStitchExport preserves every unexpected console or close failure", async t => {
  const cases = [
    ["early abort", { onExport: () => console.error(
      "Stitch Transport Error:", makeAbortError("early")) }, /early/],
    ["wrong close prefix", { close: () => console.error(
      "Other Transport Error:", makeAbortError("wrong prefix")) }, /Other Transport Error/],
    ["extra close argument", { close: () => console.error(
      "Stitch Transport Error:", makeAbortError("extra"), "noise") }, /extra/],
    ["URL query", { onExport: () => console.error(
      "failed https://assets.example/image?token=secret") }, /\[REDACTED\]/],
    ["close throws", { close: () => { throw new Error("close failed"); } }, /close failed/]
  ];
  for (const [name, options, expected] of cases) {
    await t.test(name, async () => {
      const result = await captureExport(options);
      const finals = result.events.filter(event => event.event === "stitch.export");
      assert.equal(result.exitCode, 1);
      assert.equal(result.lifecycle.closeCount, 1);
      assert.equal(finals.length, 1);
      assert.match(finals[0].errorMessage, expected);
      assert.doesNotMatch(JSON.stringify(finals[0]), /token=secret/);
      assert.equal("stack" in finals[0], false);
      assert.deepEqual(result.rawConsoleCalls, []);
      assert.equal(result.consoleRestored, true);
    });
  }
});
