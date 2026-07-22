import assert from "node:assert/strict";
import test from "node:test";
import {
  regenerateScreens,
  validateRegenerationTargets
} from "../src/targeted-regeneration.mjs";
import {
  TARGETED_REGENERATION_LOCAL_IDS,
  getRegenerationPrompt
} from "../src/prompts.mjs";

const PROJECTS = [
  { projectId: "project-1", title: "Couple Cosmos" },
  { projectId: "project-2", title: "Couple Cosmos - Part 2" },
  { projectId: "project-3", title: "Couple Cosmos - Part 3" }
];

function makeState() {
  const screens = {};
  const ids = [
    ...TARGETED_REGENERATION_LOCAL_IDS,
    "login", "menu-list", "recipe-detail", "memories", "settings",
    "legal-privacy", "home-emotion", "home-food", "home-memory"
  ];
  for (const [index, id] of ids.entries()) {
    screens[id] = {
      screenId: `${id}-original`,
      kind: id.startsWith("home-") && id !== "home-base" ? "variant" : "base",
      projectId: index < 10 ? "project-1" : index < 20 ? "project-2" : "project-3"
    };
  }
  return {
    projectId: "project-1",
    projectTitle: "Couple Cosmos",
    projects: structuredClone(PROJECTS),
    screens
  };
}

function originalBindReference() {
  return { screenId: "bind-original", kind: "base", projectId: "project-1" };
}

function makeSdk(generate) {
  const calls = [];
  return {
    calls,
    project(projectId) {
      calls.push({ projectId, type: "project" });
      return {
        async generate(prompt, deviceType) {
          calls.push({ projectId, prompt, deviceType, type: "generate" });
          return generate(prompt, deviceType);
        }
      };
    }
  };
}

function noDelay(overrides = {}) {
  return {
    checkpoint: async () => {},
    sleep: async () => {},
    maxAttempts: 3,
    write: () => {},
    ...overrides
  };
}

function captureEvents(operation) {
  const lines = [];
  return operation(noDelay({ write: line => lines.push(JSON.parse(line)) }))
    .then(value => ({ value, events: lines }), error => ({ error, events: lines }));
}

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

test("validation rejects capacity before any SDK call", async () => {
  const state = makeState();
  state.screens["home-memory"] = {
    screenId: "third-one", kind: "variant", projectId: "project-3"
  };
  state.screens["home-emotion"] = {
    screenId: "third-two", kind: "variant", projectId: "project-3"
  };
  const sdk = makeSdk(async () => assert.fail("SDK must not be called"));

  await assert.rejects(
    regenerateScreens(sdk, state, TARGETED_REGENERATION_LOCAL_IDS, noDelay()),
    /capacity/
  );
  assert.equal(sdk.calls.length, 0);
});

for (const invalidMaxAttempts of [0, -1, Number.NaN, 1.5]) {
  test(`validation rejects invalid maxAttempts ${String(invalidMaxAttempts)} before SDK calls`, async () => {
    const sdk = makeSdk(async () => assert.fail("SDK must not be called"));
    await assert.rejects(
      regenerateScreens(sdk, makeState(), ["bind"], noDelay({
        maxAttempts: invalidMaxAttempts
      })),
      /maxAttempts must be a positive integer/
    );
    assert.equal(sdk.calls.length, 0);
  });
}

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
    regenerateScreens(
      makeSdk(async () => ({ screenId: "orphan" })),
      state,
      ["bind"],
      noDelay({ checkpoint: async () => { throw new Error("checkpoint failed"); } })
    ),
    /checkpoint failed/
  );
  assert.deepEqual(state.screens.bind, originalBindReference());
});

test("resume skips targets already owned by the third shard", async () => {
  const state = makeState();
  state.screens.bind = { screenId: "done", kind: "base", projectId: "project-3" };
  const sdk = makeSdk(async () => assert.fail("completed target must be skipped"));
  const result = await regenerateScreens(sdk, state, ["bind"], noDelay());

  assert.equal(sdk.calls.length, 0);
  assert.equal(result, state);
});

test("non-recoverable generate failure does not retry", async () => {
  let attempts = 0;
  const error = new Error("permanent failure");
  const state = makeState();
  await assert.rejects(
    regenerateScreens(makeSdk(async () => {
      attempts += 1;
      throw error;
    }), state, ["bind"], noDelay()),
    /permanent failure/
  );
  assert.equal(attempts, 1);
  assert.deepEqual(state.screens.bind, originalBindReference());
});

test("recoverable generate failure retries with linear delay then succeeds", async () => {
  let attempts = 0;
  const delays = [];
  const state = makeState();
  const result = await regenerateScreens(
    makeSdk(async () => {
      attempts += 1;
      if (attempts < 3) {
        const error = new Error("temporary failure");
        error.recoverable = true;
        throw error;
      }
      return { screenId: "after-retry" };
    }),
    state,
    ["bind"],
    noDelay({ sleep: async milliseconds => delays.push(milliseconds) })
  );

  assert.equal(attempts, 3);
  assert.deepEqual(delays, [1000, 2000]);
  assert.equal(result.screens.bind.screenId, "after-retry");
});

test("recoverable failure stops at max attempts", async () => {
  let attempts = 0;
  await assert.rejects(
    regenerateScreens(makeSdk(async () => {
      attempts += 1;
      const error = new Error("still temporary");
      error.recoverable = true;
      throw error;
    }), makeState(), ["bind"], noDelay({ maxAttempts: 2 })),
    /still temporary/
  );
  assert.equal(attempts, 2);
});

test("empty generated screen id is rejected without replacing the reference", async () => {
  const state = makeState();
  await assert.rejects(
    regenerateScreens(makeSdk(async () => ({ screenId: " " })), state, ["bind"], noDelay()),
    /non-empty screenId/
  );
  assert.deepEqual(state.screens.bind, originalBindReference());
});

test("a later screen failure keeps prior checkpoint and preserves input references", async () => {
  const state = makeState();
  const checkpoints = [];
  let calls = 0;
  await assert.rejects(
    regenerateScreens(makeSdk(async () => {
      calls += 1;
      if (calls === 1) return { screenId: "new-bind" };
      throw new Error("second screen failed");
    }), state, ["bind", "feed"], noDelay({
      checkpoint: async next => checkpoints.push(structuredClone(next))
    })),
    /second screen failed/
  );
  assert.equal(checkpoints.length, 1);
  assert.equal(checkpoints[0].screens.bind.screenId, "new-bind");
  assert.deepEqual(state.screens.bind, originalBindReference());
  assert.equal(state.screens.feed.screenId, "feed-original");
});

test("generation logs structured lifecycle events without sensitive values", async () => {
  const state = makeState();
  let attempts = 0;
  const captured = await captureEvents(options => regenerateScreens(
    makeSdk(async prompt => {
      attempts += 1;
      if (attempts === 1) {
        const error = new Error(`request ${prompt} https://stitch.example/generate?token=secret&apiKey=another`);
        error.recoverable = true;
        throw error;
      }
      return { screenId: "logged-bind" };
    }),
    state,
    ["bind"],
    options
  ));

  assert.equal(captured.error, undefined);
  const results = captured.events.map(event => event.result);
  assert.ok(results.includes("started"));
  assert.ok(results.includes("retry"));
  assert.ok(results.includes("ok"));
  for (const event of captured.events) {
    assert.equal(event.event, "stitch.screen.regenerate");
    assert.equal(event.projectId, "project-3");
    assert.equal(event.localId, "bind");
    assert.equal(event.screenTitle, "情侣绑定");
    assert.equal(typeof event.attempt, "number");
    assert.equal(typeof event.stage, "string");
    assert.equal(typeof event.durationMs, "number");
  }
  const serialized = JSON.stringify(captured.events);
  assert.doesNotMatch(serialized, /token=|apiKey=/);
  assert.doesNotMatch(serialized, /secret|another/);
  assert.equal(serialized.includes(getRegenerationPrompt("bind")), false);
});

test("generation logs an error lifecycle event", async () => {
  const captured = await captureEvents(options => regenerateScreens(
    makeSdk(async () => { throw new Error("broken"); }),
    makeState(),
    ["bind"],
    options
  ));
  assert.match(captured.error.message, /broken/);
  assert.ok(captured.events.some(event => event.result === "error" && event.stage === "generate"));
});

test("generation redacts colon-form secrets and relative URL queries from errors", async () => {
  const captured = await captureEvents(options => regenerateScreens(
    makeSdk(async prompt => {
      throw new Error(
        `connection refused for ${prompt}; Authorization: Bearer sk-live-123 token: raw-token apiKey: raw-key secret: raw-secret /generate?trace=private`
      );
    }),
    makeState(),
    ["bind"],
    options
  ));

  assert.match(captured.error.message, /connection refused/);
  const serialized = JSON.stringify(captured.events);
  for (const sensitiveValue of [
    "sk-live-123", "raw-token", "raw-key", "raw-secret", "trace=private",
    getRegenerationPrompt("bind")
  ]) {
    assert.equal(serialized.includes(sensitiveValue), false);
  }
  assert.match(serialized, /connection refused/);
});
