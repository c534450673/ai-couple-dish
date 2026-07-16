import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { runStitchHealth } from "../bin/health.mjs";
import { assertRequiredTools } from "../src/client.mjs";
import {
  emptyGenerationState,
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";

const TOOL_NAMES = [
  "create_project",
  "generate_screen_from_text",
  "get_screen"
];
const TEST_CONFIG = {
  apiKey: "test-placeholder",
  host: "https://example.invalid"
};

function makeAbortError(message) {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
}

function makeFakeClient({ tools = TOOL_NAMES, list, close } = {}) {
  const state = { closeCount: 0 };
  return {
    state,
    client: {
      async listTools() {
        await list?.();
        return { tools: tools.map(name => ({ name })) };
      },
      async close() {
        state.closeCount += 1;
        await close?.();
      }
    }
  };
}

async function captureHealth(overrides = {}, onWrite) {
  const actualConsoleError = console.error;
  const rawConsoleCalls = [];
  const restoredConsoleError = (...args) => rawConsoleCalls.push(args);
  const writes = [];
  console.error = restoredConsoleError;
  try {
    const exitCode = await runStitchHealth({
      readConfig: () => TEST_CONFIG,
      ...overrides,
      write(line) {
        onWrite?.();
        writes.push(line);
      }
    });
    await new Promise(resolve => setImmediate(resolve));
    return {
      exitCode,
      writes,
      event: writes.length === 1 ? JSON.parse(writes[0]) : null,
      rawConsoleCalls,
      consoleRestored: console.error === restoredConsoleError
    };
  } finally {
    console.error = actualConsoleError;
  }
}

test("assertRequiredTools accepts the Stitch generation tool set", async () => {
  const client = {
    async listTools() {
      return { tools: TOOL_NAMES.map(name => ({ name })) };
    }
  };
  assert.deepEqual(await assertRequiredTools(client), TOOL_NAMES);
});

test("assertRequiredTools rejects a missing generation tool", async () => {
  await assert.rejects(
    () =>
      assertRequiredTools({
        async listTools() {
          return { tools: [{ name: "create_project" }] };
        }
      }),
    /Missing required Stitch tools/
  );
});

test("generation state persists with an atomic round trip", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-state-"));
  const filePath = join(root, "generation-state.json");
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1",
    screens: { login: { screenId: "screen-1", kind: "base" } }
  };
  await writeGenerationState(filePath, state);
  assert.deepEqual(await readGenerationState(filePath), state);
});

test("empty generation state starts with an empty project registry", () => {
  assert.deepEqual(emptyGenerationState().projects, []);
});

test("health closes once and suppresses only the expected close AbortError", async () => {
  const fake = makeFakeClient({
    close() {
      setImmediate(() =>
        console.error(
          "Stitch Transport Error:",
          makeAbortError("The operation was aborted")
        )
      );
    }
  });
  const result = await captureHealth(
    { createSdk: () => ({ client: fake.client }) },
    () => assert.equal(fake.state.closeCount, 1)
  );
  assert.equal(result.exitCode, 0);
  assert.equal(fake.state.closeCount, 1);
  assert.equal(result.writes.length, 1);
  assert.equal(result.rawConsoleCalls.length, 0);
  assert.equal(result.consoleRestored, true);
  assert.equal(result.event.result, "ok");
});

test("health serializes configuration and construction failures", async t => {
  const cases = [
    ["configuration", { readConfig: () => { throw new Error("config failed"); } }, /config failed/],
    ["construction", { createSdk: () => { throw new TypeError("construct failed"); } }, /construct failed/]
  ];
  for (const [name, overrides, message] of cases) {
    await t.test(name, async () => {
      const result = await captureHealth(overrides);
      assert.equal(result.exitCode, 1);
      assert.equal(result.writes.length, 1);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.match(result.event.errorMessage, message);
    });
  }
});

test("health closes and serializes tool or close failures", async t => {
  const cases = [
    [makeFakeClient({ tools: ["create_project"] }), /Missing required Stitch tools/],
    [makeFakeClient({ close: () => { throw new Error("close failed"); } }), /close failed/]
  ];
  for (const [fake, message] of cases) {
    await t.test(String(message), async () => {
      const result = await captureHealth({
        createSdk: () => ({ client: fake.client })
      });
      assert.equal(result.exitCode, 1);
      assert.equal(fake.state.closeCount, 1);
      assert.equal(result.writes.length, 1);
      assert.match(result.event.errorMessage, message);
    });
  }
});

test("health preserves unexpected SDK console errors in its JSON", async t => {
  const cases = [
    [makeFakeClient({ close: () => console.error("Stitch Transport Error:", new Error("close noise")) }), /close noise/],
    [makeFakeClient({ list: () => console.error("Stitch Transport Error:", makeAbortError("early abort")) }), /early abort/],
    [makeFakeClient({ close: () => console.error("Other Transport Error:", makeAbortError("wrong prefix")) }), /Other Transport Error/]
  ];
  for (const [fake, message] of cases) {
    await t.test(String(message), async () => {
      const result = await captureHealth({
        createSdk: () => ({ client: fake.client })
      });
      assert.equal(result.exitCode, 1);
      assert.equal(result.writes.length, 1);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.equal(result.consoleRestored, true);
      assert.match(result.event.errorMessage, message);
    });
  }
});
