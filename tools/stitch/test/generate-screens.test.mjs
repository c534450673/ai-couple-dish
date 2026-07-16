import assert from "node:assert/strict";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { runStitchGenerate } from "../bin/generate.mjs";
import { generateRemainingScreens } from "../src/generate-screens.mjs";
import { SCREEN_SPECS, getScreenPrompt } from "../src/prompts.mjs";

const REMAINING_SCREENS = SCREEN_SPECS.filter(screen => screen.id !== "home");
const TEST_CONFIG = { apiKey: "test-placeholder", host: "https://example.invalid" };

function makeState({
  projectId = "project-1",
  projectTitle = "AI Couple Dish - Couple Cosmos",
  completed = REMAINING_SCREENS.map(screen => screen.id),
  home = true
} = {}) {
  const screens = home
    ? { "home-base": { screenId: "home-id", kind: "base" } }
    : {};
  for (const id of completed) {
    screens[id] = { screenId: `${id}-id`, kind: "base" };
  }
  return { projectId, projectTitle, screens };
}

function makeSdk(generate) {
  return {
    project(projectId) {
      assert.equal(projectId, "project-1");
      return { generate };
    }
  };
}

async function captureEvents(operation) {
  const lines = [];
  const originalWrite = process.stderr.write;
  process.stderr.write = line => {
    lines.push(String(line).trim());
    return true;
  };
  try {
    return { value: await operation(), events: lines.map(line => JSON.parse(line)) };
  } catch (error) {
    return { error, events: lines.map(line => JSON.parse(line)) };
  } finally {
    process.stderr.write = originalWrite;
  }
}

async function captureGenerate({ runner = runStitchGenerate, state = makeState(),
  close, overrides = {}, onWrite } = {}) {
  const actualConsoleError = console.error;
  const rawConsoleCalls = [];
  const restoredConsoleError = (...args) => rawConsoleCalls.push(args);
  const lines = [];
  const lifecycle = { closeCount: 0 };
  const client = { async close() {
    lifecycle.closeCount += 1;
    await close?.();
  } };
  console.error = restoredConsoleError;
  try {
    const exitCode = await runner({
      readConfig: () => TEST_CONFIG,
      createSdk: () => ({ sdk: {}, client }),
      readState: async () => state,
      writeState: async () => {},
      generateHome: async (_sdk, current) => ({
        ...current,
        projectId: current.projectId || "project-1",
        screens: {
          ...current.screens,
          "home-base": current.screens["home-base"] || {
            screenId: "home-id",
            kind: "base"
          }
        }
      }),
      generateScreens: async (_sdk, current) => current,
      statePath: "/tmp/generation-state.json",
      ...overrides,
      write(line) {
        onWrite?.(JSON.parse(line), lifecycle);
        lines.push(line);
      }
    });
    await new Promise(resolve => setImmediate(resolve));
    return { exitCode, events: lines.map(line => JSON.parse(line)), lifecycle,
      rawConsoleCalls, consoleRestored: console.error === restoredConsoleError };
  } finally {
    console.error = actualConsoleError;
  }
}

function makeGenerateAbortError(message) {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
}

test("generateRemainingScreens skips completed screens and checkpoints each new screen", async () => {
  const generated = [];
  const checkpoints = [];
  const state = makeState({ completed: ["login"] });
  const result = await captureEvents(() =>
    generateRemainingScreens(
      makeSdk(async (prompt, deviceType) => {
        generated.push({ prompt, deviceType });
        return { screenId: `screen-${generated.length}` };
      }),
      state,
      { maxAttempts: 1, sleep: async () => {},
        checkpoint: async next => checkpoints.push(next) }
    )
  );

  assert.equal(result.value.screens.login.screenId, "login-id");
  assert.deepEqual(
    generated,
    REMAINING_SCREENS.filter(screen => screen.id !== "login").map(screen => ({
      prompt: getScreenPrompt(screen.id),
      deviceType: "MOBILE"
    }))
  );
  assert.deepEqual(
    checkpoints.map(checkpoint => Object.keys(checkpoint.screens).length),
    Array.from({ length: 15 }, (_, index) => index + 3)
  );
  assert.equal(result.events.filter(event => event.event === "stitch.screen.skip").length, 1);
  assert.equal(result.events.filter(event => event.result === "started").length, 15);
  const successes = result.events.filter(event => event.result === "ok" && event.remoteScreenId);
  assert.equal(successes.length, 15);
  assert.ok(successes.every(event => Number.isInteger(event.durationMs)));
});

test("generateRemainingScreens retries only recoverable failures", async t => {
  const cases = [
    { name: "recoverable success", recoverable: true, succeeds: true,
      maxAttempts: 2, expectedAttempts: 2, expectedDelays: [1000] },
    { name: "unrecoverable", recoverable: false,
      maxAttempts: 3, expectedAttempts: 1, expectedDelays: [] },
    { name: "recoverable exhausted", recoverable: true,
      maxAttempts: 3, expectedAttempts: 3, expectedDelays: [1000, 2000] }
  ];
  for (const scenario of cases) {
    await t.test(scenario.name, async () => {
      let attempts = 0;
      const delays = [];
      const result = await captureEvents(() =>
        generateRemainingScreens(
          makeSdk(async () => {
            attempts += 1;
            if (scenario.succeeds && attempts === 2) return { screenId: "login-ok" };
            const error = new TypeError(scenario.name + " failure");
            error.recoverable = scenario.recoverable;
            throw error;
          }),
          makeState({ completed: REMAINING_SCREENS.map(screen => screen.id).filter(id => id !== "login") }),
          { maxAttempts: scenario.maxAttempts,
            sleep: async delay => delays.push(delay), checkpoint: async () => {} }
        )
      );

      assert.equal(attempts, scenario.expectedAttempts);
      assert.deepEqual(delays, scenario.expectedDelays);
      if (scenario.succeeds) {
        assert.equal(result.value.screens.login.screenId, "login-ok");
        const retry = result.events.find(event => event.event === "stitch.screen.retry");
        assert.deepEqual(
          [retry.result, retry.attempt, retry.delayMs, retry.errorName, retry.errorMessage],
          ["retry", 1, 1000, "TypeError", "recoverable success failure"]
        );
      } else {
        assert.match(result.error.message, new RegExp(scenario.name + " failure"));
        const failures = result.events.filter(event =>
          event.event === "stitch.screen.generate" && event.result === "error");
        assert.equal(failures.length, 1);
        assert.deepEqual(
          [failures[0].projectId, failures[0].screenId,
            failures[0].screenTitle, failures[0].deviceType,
            failures[0].attempt, failures[0].maxAttempts, failures[0].stage,
            failures[0].errorName, failures[0].errorMessage],
          ["project-1", "login", "登录与注册", "MOBILE",
            scenario.expectedAttempts, scenario.maxAttempts, "generate",
            "TypeError", scenario.name + " failure"]
        );
        assert.ok(Number.isInteger(failures[0].durationMs));
      }
    });
  }
});

test("generateRemainingScreens stops when a checkpoint fails", async () => {
  let generated = 0;
  const state = makeState({ completed: [] });
  const result = await captureEvents(() =>
    generateRemainingScreens(
      makeSdk(async () => ({ screenId: `screen-${++generated}` })),
      state,
      { maxAttempts: 1, sleep: async () => {},
        checkpoint: async () => { throw new Error("checkpoint failed"); } }
    )
  );
  assert.match(result.error.message, /checkpoint failed/);
  assert.equal(generated, 1);
  assert.deepEqual(state.screens, { "home-base": { screenId: "home-id", kind: "base" } });
  const failure = result.events.find(event => event.result === "error");
  assert.deepEqual(
    [failure.projectId, failure.screenId, failure.screenTitle,
      failure.deviceType, failure.attempt, failure.maxAttempts,
      failure.stage, failure.errorName, failure.errorMessage],
    ["project-1", "login", "登录与注册", "MOBILE", 1, 1,
      "checkpoint", "Error", "checkpoint failed"]
  );
  assert.ok(Number.isInteger(failure.durationMs));
});

test("generateRemainingScreens sends every screen event to the injected writer", async () => {
  const customLines = [];
  const leakedLines = [];
  const originalWrite = process.stderr.write;
  let calls = 0;
  process.stderr.write = line => { leakedLines.push(String(line)); return true; };
  try {
    await assert.rejects(
      generateRemainingScreens(
        makeSdk(async () => {
          calls += 1;
          if (calls === 1) {
            const error = new Error("retry once");
            error.recoverable = true;
            throw error;
          }
          if (calls === 2) return { screenId: "bind-ok" };
          throw new TypeError("menu failed");
        }),
        makeState({ completed: ["login"] }),
        { maxAttempts: 2, sleep: async () => {}, checkpoint: async () => {},
          write: line => customLines.push(line) }
      ),
      /menu failed/
    );
  } finally {
    process.stderr.write = originalWrite;
  }
  const events = customLines.map(line => JSON.parse(line));
  assert.deepEqual(leakedLines, []);
  assert.equal(events.filter(event => event.event === "stitch.screen.skip").length, 1);
  assert.equal(events.filter(event => event.result === "started").length, 3);
  assert.equal(events.filter(event => event.event === "stitch.screen.retry").length, 1);
  assert.equal(events.filter(event => event.result === "ok" && event.remoteScreenId).length, 1);
  assert.equal(events.filter(event => event.result === "error").length, 1);
});

test("generateRemainingScreens rejects a blank remote screen id before checkpoint", async () => {
  let checkpoints = 0;
  const completed = REMAINING_SCREENS.map(screen => screen.id).filter(id => id !== "login");
  const result = await captureEvents(() => generateRemainingScreens(
    makeSdk(async () => ({ screenId: "   " })), makeState({ completed }), {
      maxAttempts: 1,
      sleep: async () => {},
      checkpoint: async () => { checkpoints += 1; }
    }
  ));
  assert.match(result.error.message, /non-empty screenId/);
  assert.equal(checkpoints, 0);
});

test("runStitchGenerate serializes every lifecycle failure into one final event", async t => {
  const cases = [
    ["configuration", { readConfig: () => { throw new Error("config failed"); } }, /config failed/, 0],
    ["construction", { createSdk: () => { throw new Error("construct failed"); } }, /construct failed/, 0],
    ["state read", { readState: async () => { throw new Error("read failed"); } }, /read failed/, 1],
    ["home", { generateHome: async () => { throw new Error("home failed"); } }, /home failed/, 1],
    ["state write", { writeState: async () => { throw new Error("write failed"); } }, /write failed/, 1],
    ["remaining", { generateScreens: async () => { throw new Error("screens failed"); } }, /screens failed/, 1]
  ];
  for (const [name, overrides, expected, closeCount] of cases) {
    await t.test(name, async () => {
      const result = await captureGenerate({ overrides });
      const finals = result.events.filter(event => event.event === "stitch.generate");
      assert.equal(result.exitCode, 1);
      assert.equal(result.lifecycle.closeCount, closeCount);
      assert.equal(finals.length, 1);
      assert.equal(finals[0].result, "error");
      assert.match(finals[0].errorMessage, expected);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.equal(result.consoleRestored, true);
    });
  }
});

test("runStitchGenerate logs create, resume and skip home phases", async t => {
  const cases = [
    ["create", makeState({ projectId: null, completed: [], home: false })],
    ["resume", makeState({ completed: [], home: false })],
    ["skip", makeState()]
  ];
  for (const [action, state] of cases) {
    await t.test(action, async () => {
      const result = await captureGenerate({ state });
      const home = result.events.filter(event => event.event === "stitch.home.generate");
      assert.equal(result.exitCode, 0);
      assert.deepEqual(home.map(event => event.result), ["started", "ok"]);
      assert.deepEqual(home.map(event => event.action), [action, action]);
      assert.equal(home[0].screenId, "home");
      assert.equal(home[0].projectTitle, state.projectTitle);
      assert.equal(home[1].projectId, "project-1");
      assert.equal(home[1].remoteScreenId, "home-id");
      assert.ok(home.every(event => Number.isInteger(event.durationMs)));
      assert.equal(result.events.filter(event => event.event === "stitch.generate").length, 1);
    });
  }
});

test("runStitchGenerate forwards its injected writer to screen generation", async () => {
  const result = await captureGenerate({
    overrides: {
      generateScreens: async (_sdk, state, options) => {
        options.write(JSON.stringify({ event: "stitch.screen.probe", result: "ok" }));
        return state;
      }
    }
  });
  assert.equal(result.exitCode, 0);
  assert.equal(result.events.filter(event => event.event === "stitch.screen.probe").length, 1);
});

test("runStitchGenerate anchors its default state path to the repository", async () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
  const originalCwd = process.cwd();
  let actualPath;
  process.chdir(root);
  try {
    const { runStitchGenerate: runner } = await import(`../bin/generate.mjs?cwd=${Date.now()}`);
    const result = await captureGenerate({
      runner,
      overrides: { statePath: undefined,
        readState: async path => { actualPath = path; return makeState(); } }
    });
    assert.equal(result.exitCode, 0);
  } finally {
    process.chdir(originalCwd);
  }
  assert.equal(actualPath, join(root, "docs/design/stitch/couple-cosmos/generation-state.json"));
});

test("runStitchGenerate suppresses only the active close AbortError", async t => {
  const cases = [
    { name: "expected close abort", expectedExit: 0,
      close: () => setImmediate(() => console.error(
        "Stitch Transport Error:", makeGenerateAbortError("closed"))) },
    {
      name: "same error before close",
      overrides: {
        generateScreens: async (_sdk, current) => {
          console.error("Stitch Transport Error:", makeGenerateAbortError("early"));
          return current;
        }
      },
      expectedExit: 1,
      expectedError: /early/
    },
    { name: "wrong prefix during close", expectedExit: 1,
      close: () => console.error("Other Transport Error:", makeGenerateAbortError("wrong prefix")),
      expectedError: /Other Transport Error/ },
    { name: "close throws", expectedExit: 1,
      close: () => { throw new Error("close failed"); }, expectedError: /close failed/ }
  ];
  for (const scenario of cases) {
    await t.test(scenario.name, async () => {
      const result = await captureGenerate({
        close: scenario.close,
        overrides: scenario.overrides,
        onWrite(event, lifecycle) {
          if (event.event === "stitch.generate") assert.equal(lifecycle.closeCount, 1);
        }
      });
      const finals = result.events.filter(event => event.event === "stitch.generate");
      assert.equal(result.exitCode, scenario.expectedExit);
      assert.equal(result.lifecycle.closeCount, 1);
      assert.equal(finals.length, 1);
      if (scenario.expectedError) assert.match(finals[0].errorMessage, scenario.expectedError);
      assert.equal(result.rawConsoleCalls.length, 0);
      assert.equal(result.consoleRestored, true);
    });
  }
});
