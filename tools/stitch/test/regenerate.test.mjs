import assert from "node:assert/strict";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { runStitchRegenerate } from "../bin/regenerate.mjs";

const TEST_CONFIG = {
  apiKey: "test-placeholder",
  host: "https://example.invalid"
};

function makeState() {
  return {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    projects: [
      { projectId: "project-1" },
      { projectId: "project-2" },
      { projectId: "project-3" }
    ],
    screens: {}
  };
}

function makeAbortError(message) {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
}

async function captureRegenerate({
  runner = runStitchRegenerate,
  ids = ["bind"],
  state = makeState(),
  close,
  overrides = {},
  onWrite
} = {}) {
  const actualConsoleError = console.error;
  const rawConsoleCalls = [];
  const restoredConsoleError = (...args) => rawConsoleCalls.push(args);
  const events = [];
  const lifecycle = { closeCount: 0 };
  const client = {
    async close() {
      lifecycle.closeCount += 1;
      await close?.();
    }
  };
  console.error = restoredConsoleError;
  try {
    const exitCode = await runner(ids, {
      readConfig: () => TEST_CONFIG,
      createSdk: () => ({ sdk: {}, client }),
      readState: async () => state,
      writeState: async () => {},
      regenerate: async (_sdk, current) => current,
      statePath: "/tmp/generation-state.json",
      ...overrides,
      write(line) {
        const event = JSON.parse(line);
        onWrite?.(event, lifecycle);
        events.push(event);
      }
    });
    await new Promise(resolveImmediate => setImmediate(resolveImmediate));
    return {
      exitCode,
      events,
      lifecycle,
      rawConsoleCalls,
      consoleRestored: console.error === restoredConsoleError
    };
  } finally {
    console.error = actualConsoleError;
  }
}

test("runner forwards ids and checkpoints to the repository state path", async () => {
  const writes = [];
  const events = [];
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

  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
  assert.equal(result, 0);
  assert.deepEqual(writes, [[
    join(root, "docs/design/stitch/couple-cosmos/generation-state.json"),
    { ...makeState(), marker: true }
  ]]);
  assert.equal(events.length, 1);
  assert.equal(events.at(-1).event, "stitch.regenerate");
  assert.deepEqual(
    [events.at(-1).result, events.at(-1).targetCount, events.at(-1).projectId],
    ["ok", 1, "project-1"]
  );
  assert.equal(Number.isInteger(events.at(-1).durationMs), true);
});

test("runner serializes lifecycle failures into one final event", async t => {
  const cases = [
    ["configuration", { readConfig: () => { throw new Error("config failed"); } }, /config failed/, 0, undefined, null],
    ["construction", { createSdk: () => { throw new Error("construct failed"); } }, /construct failed/, 0, undefined, null],
    ["state read", { readState: async () => { throw new Error("state failed"); } }, /state failed/, 1, undefined, null],
    ["regeneration", { regenerate: async () => { throw new Error("regenerate failed"); } }, /regenerate failed/, 1, undefined, "project-1"],
    ["checkpoint", {
      regenerate: async (_sdk, state, _ids, options) => {
        await options.checkpoint(state);
        return state;
      },
      writeState: async () => { throw new Error("checkpoint failed"); }
    }, /checkpoint failed/, 1, undefined, "project-1"],
    ["close", {}, /close failed/, 1, () => { throw new Error("close failed"); }, "project-1"]
  ];

  for (const [name, overrides, expectedMessage, closeCount, close, projectId] of cases) {
    await t.test(name, async () => {
      const result = await captureRegenerate({ overrides, close });
      const finals = result.events.filter(event => event.event === "stitch.regenerate");
      assert.equal(result.exitCode, 1);
      assert.equal(result.lifecycle.closeCount, closeCount);
      assert.equal(finals.length, 1);
      assert.deepEqual(
        [finals[0].result, finals[0].targetCount, finals[0].projectId],
        ["error", 1, projectId]
      );
      assert.match(finals[0].errorMessage, expectedMessage);
      assert.equal(finals[0].errorName, "Error");
      assert.equal(Number.isInteger(finals[0].durationMs), true);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.equal(result.consoleRestored, true);
    });
  }
});

test("runner treats unexpected console errors as failures and redacts URL queries", async () => {
  const result = await captureRegenerate({
    overrides: {
      regenerate: async (_sdk, state) => {
        console.error(
          "unexpected",
          new Error("https://example.invalid/path?token=secret /generate?trace=private")
        );
        return state;
      }
    }
  });
  const [final] = result.events.filter(event => event.event === "stitch.regenerate");

  assert.equal(result.exitCode, 1);
  assert.equal(final.result, "error");
  assert.equal(final.errorName, "StitchConsoleError");
  assert.match(final.errorMessage, /https:\/\/example\.invalid\/path/);
  assert.match(final.errorMessage, /\/generate/);
  assert.doesNotMatch(final.errorMessage, /token=secret/);
  assert.doesNotMatch(final.errorMessage, /trace=private/);
  assert.equal(result.events.filter(event => event.event === "stitch.regenerate").length, 1);
});

test("runner redacts environment credentials and credential-shaped fields", async () => {
  const originalApiKey = process.env.STITCH_API_KEY;
  const originalAccessToken = process.env.STITCH_ACCESS_TOKEN;
  process.env.STITCH_API_KEY = "environment-api-key-private";
  process.env.STITCH_ACCESS_TOKEN = "environment-access-token-private";
  try {
    const result = await captureRegenerate({
      overrides: {
        readConfig: () => {
          throw new Error(
            "configuration failed: environment-api-key-private " +
            "environment-access-token-private STITCH_API_KEY=named-key-private " +
            "STITCH_ACCESS_TOKEN: named-token-private Authorization: Bearer bearer-private " +
            "apiKey: camel-key-private token=token-private secret: secret-private " +
            "Authorization: Basic dXNlcjpwYXNz; context remains; " +
            "Authorization=opaque-authorization-private"
          );
        }
      }
    });
    const [final] = result.events.filter(event => event.event === "stitch.regenerate");

    assert.equal(result.exitCode, 1);
    assert.match(final.errorMessage, /configuration failed/);
    assert.match(final.errorMessage, /context remains/);
    for (const sensitiveValue of [
      "environment-api-key-private",
      "environment-access-token-private",
      "named-key-private",
      "named-token-private",
      "bearer-private",
      "camel-key-private",
      "token-private",
      "secret-private",
      "dXNlcjpwYXNz",
      "opaque-authorization-private"
    ]) {
      assert.doesNotMatch(final.errorMessage, new RegExp(sensitiveValue));
    }
  } finally {
    if (originalApiKey === undefined) delete process.env.STITCH_API_KEY;
    else process.env.STITCH_API_KEY = originalApiKey;
    if (originalAccessToken === undefined) delete process.env.STITCH_ACCESS_TOKEN;
    else process.env.STITCH_ACCESS_TOKEN = originalAccessToken;
  }
});

test("runner redacts complete quoted prompt values while preserving error context", async () => {
  const result = await captureRegenerate({
    overrides: {
      regenerate: async () => {
        throw new Error(
          "regeneration failed before; prompt=\"Do not log this private design\"; " +
          "payload={\"prompt\":\"JSON private design words\"}; " +
          "metadata={'prompt':'single quoted private design'}; after failure context"
        );
      }
    }
  });
  const [final] = result.events.filter(event => event.event === "stitch.regenerate");

  assert.equal(result.exitCode, 1);
  assert.match(final.errorMessage, /regeneration failed before/);
  assert.match(final.errorMessage, /after failure context/);
  assert.doesNotMatch(final.errorMessage, /Do not log this private design/);
  assert.doesNotMatch(final.errorMessage, /JSON private design words/);
  assert.doesNotMatch(final.errorMessage, /single quoted private design/);
});

test("runner anchors its default state path to the repository", async () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
  const originalCwd = process.cwd();
  let actualPath;
  process.chdir(root);
  try {
    const { runStitchRegenerate: runner } = await import(
      `../bin/regenerate.mjs?cwd=${Date.now()}`
    );
    const result = await captureRegenerate({
      runner,
      overrides: { statePath: undefined,
        readState: async path => { actualPath = path; return makeState(); } }
    });
    assert.equal(result.exitCode, 0);
  } finally {
    process.chdir(originalCwd);
  }
  assert.equal(
    actualPath,
    join(root, "docs/design/stitch/couple-cosmos/generation-state.json")
  );
});

test("runner suppresses only the active close AbortError", async t => {
  const cases = [
    {
      name: "expected close abort",
      expectedExit: 0,
      close: () => setImmediate(() => console.error(
        "Stitch Transport Error:", makeAbortError("closed")
      ))
    },
    {
      name: "same error before close",
      expectedExit: 1,
      overrides: {
        regenerate: async (_sdk, state) => {
          console.error("Stitch Transport Error:", makeAbortError("early"));
          return state;
        }
      },
      expectedError: /early/
    },
    {
      name: "wrong prefix during close",
      expectedExit: 1,
      close: () => console.error("Other Transport Error:", makeAbortError("wrong prefix")),
      expectedError: /Other Transport Error/
    },
    {
      name: "wrong argument count during close",
      expectedExit: 1,
      close: () => console.error("Stitch Transport Error:", makeAbortError("wrong count"), "extra"),
      expectedError: /wrong count/
    },
    {
      name: "delayed timer error after close resolves",
      expectedExit: 1,
      close: () => setImmediate(() => setTimeout(
        () => console.error("Delayed Transport Error:", new Error("delayed close error")),
        0
      )),
      expectedError: /delayed close error/
    }
  ];

  for (const scenario of cases) {
    await t.test(scenario.name, async () => {
      const result = await captureRegenerate({
        close: scenario.close,
        overrides: scenario.overrides,
        onWrite(event, lifecycle) {
          if (event.event === "stitch.regenerate") assert.equal(lifecycle.closeCount, 1);
        }
      });
      const finals = result.events.filter(event => event.event === "stitch.regenerate");
      assert.equal(result.exitCode, scenario.expectedExit);
      assert.equal(result.lifecycle.closeCount, 1);
      assert.equal(finals.length, 1);
      if (scenario.expectedError) assert.match(finals[0].errorMessage, scenario.expectedError);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.equal(result.consoleRestored, true);
    });
  }
});
