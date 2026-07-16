### Task 5: 断点生成其余页面并记录详细日志

> Controller resolution: 本任务中 `bin/generate.mjs` 的配置读取、SDK 构造和 `client.close()` 必须沿用 Task 3 已验证的单行结构化错误边界；不得照抄下方示例中 try 外初始化或让 SDK close AbortError 输出非 JSON 堆栈。这是 Global Constraints 对示例代码的约束，不改变业务接口。当前基线已有 26+项测试，Step 4 的“13 tests PASS”是过时计数；验收以全量新鲜测试全绿为准。

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/generate-screens.mjs
- Create: tools/stitch/bin/generate.mjs
- Create: tools/stitch/test/generate-screens.test.mjs

**Interfaces:**
- Consumes: sdk.project(projectId).generate(prompt, deviceType)
- Produces: generateRemainingScreens(sdk, state, options) -> updated GenerationState
- options: { checkpoint(state), sleep(ms), maxAttempts }

- [ ] **Step 1: 写断点、重试和检查点失败测试**

Create tools/stitch/test/generate-screens.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import test from "node:test";
import { generateRemainingScreens } from "../src/generate-screens.mjs";

test("generateRemainingScreens skips completed screens and checkpoints each new screen", async () => {
  const generated = [];
  const checkpoints = [];
  const sdk = {
    project(projectId) {
      assert.equal(projectId, "project-1");
      return {
        async generate(prompt, deviceType) {
          generated.push({ prompt, deviceType });
          return { screenId: "screen-" + generated.length };
        }
      };
    }
  };
  const state = {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {
      "home-base": { screenId: "home-id", kind: "base" },
      login: { screenId: "existing-login", kind: "base" }
    }
  };

  const result = await generateRemainingScreens(sdk, state, {
    maxAttempts: 1,
    sleep: async () => {},
    checkpoint: async next => checkpoints.push(next)
  });

  assert.equal(result.screens.login.screenId, "existing-login");
  assert.equal(generated.length, 15);
  assert.equal(checkpoints.length, 15);
});

test("generateRemainingScreens retries a recoverable failure", async () => {
  let attempts = 0;
  const sdk = {
    project() {
      return {
        async generate() {
          attempts += 1;
          if (attempts === 1) {
            const error = new Error("rate limited");
            error.recoverable = true;
            throw error;
          }
          return { screenId: "screen-ok" };
        }
      };
    }
  };
  const state = {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {
      "home-base": { screenId: "home-id", kind: "base" },
      bind: { screenId: "bind-id", kind: "base" },
      "menu-list": { screenId: "menu-list-id", kind: "base" },
      "menu-detail": { screenId: "menu-detail-id", kind: "base" },
      "recipe-list": { screenId: "recipe-list-id", kind: "base" },
      "recipe-detail": { screenId: "recipe-detail-id", kind: "base" },
      "recipe-editor": { screenId: "recipe-editor-id", kind: "base" },
      feed: { screenId: "feed-id", kind: "base" },
      memories: { screenId: "memories-id", kind: "base" },
      "note-editor": { screenId: "note-editor-id", kind: "base" },
      map: { screenId: "map-id", kind: "base" },
      "ai-chat": { screenId: "ai-chat-id", kind: "base" },
      settings: { screenId: "settings-id", kind: "base" },
      "notification-center": { screenId: "notification-id", kind: "base" },
      "legal-privacy": { screenId: "legal-id", kind: "base" },
      "system-states": { screenId: "states-id", kind: "base" }
    }
  };

  const result = await generateRemainingScreens(sdk, state, {
    maxAttempts: 2,
    sleep: async () => {},
    checkpoint: async () => {}
  });

  assert.equal(attempts, 2);
  assert.equal(result.screens.login.screenId, "screen-ok");
});
~~~

- [ ] **Step 2: 运行测试并验证模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/generate-screens.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现顺序生成、有限重试和逐屏检查点**

Create tools/stitch/src/generate-screens.mjs:

~~~javascript
import { SCREEN_SPECS, getScreenPrompt } from "./prompts.mjs";
import { logEvent } from "./logger.mjs";

async function withRetry(operation, options) {
  let lastError;
  for (let attempt = 1; attempt <= options.maxAttempts; attempt += 1) {
    try {
      return await operation(attempt);
    } catch (error) {
      lastError = error;
      const canRetry = error.recoverable === true && attempt < options.maxAttempts;
      if (!canRetry) {
        throw error;
      }
      await options.sleep(1000 * attempt);
    }
  }
  throw lastError;
}

export async function generateRemainingScreens(
  sdk,
  initialState,
  {
    checkpoint,
    sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds)),
    maxAttempts = 3
  }
) {
  let state = initialState;
  const project = sdk.project(state.projectId);
  const remaining = SCREEN_SPECS.filter(screen => screen.id !== "home");

  for (const screen of remaining) {
    if (state.screens[screen.id]) {
      logEvent("stitch.screen.skip", {
        result: "ok",
        screenId: screen.id,
        reason: "already-generated"
      });
      continue;
    }

    const started = performance.now();
    const generated = await withRetry(
      async attempt => {
        logEvent("stitch.screen.generate", {
          result: "started",
          screenId: screen.id,
          attempt
        });
        return project.generate(getScreenPrompt(screen.id), screen.deviceType);
      },
      { maxAttempts, sleep }
    );

    state = {
      ...state,
      screens: {
        ...state.screens,
        [screen.id]: {
          screenId: generated.screenId,
          kind: "base"
        }
      }
    };
    await checkpoint(state);
    logEvent("stitch.screen.generate", {
      result: "ok",
      screenId: screen.id,
      remoteScreenId: generated.screenId,
      durationMs: Math.round(performance.now() - started)
    });
  }

  return state;
}
~~~

Create tools/stitch/bin/generate.mjs:

~~~javascript
import { resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { readStitchConfig } from "../src/config.mjs";
import { createStitchSdk } from "../src/client.mjs";
import {
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";
import { generateHomeDesign } from "../src/generate-home.mjs";
import { generateRemainingScreens } from "../src/generate-screens.mjs";
import { logEvent } from "../src/logger.mjs";

const statePath = resolve(
  "../../docs/design/stitch/couple-cosmos/generation-state.json"
);
const started = performance.now();
const config = readStitchConfig();
const { sdk, client } = createStitchSdk(config);

try {
  let state = await readGenerationState(statePath);
  state = await generateHomeDesign(sdk, state);
  await writeGenerationState(statePath, state);
  state = await generateRemainingScreens(sdk, state, {
    async checkpoint(nextState) {
      await writeGenerationState(statePath, nextState);
    }
  });
  logEvent("stitch.generate", {
    result: "ok",
    projectId: state.projectId,
    screenCount: Object.keys(state.screens).length,
    durationMs: Math.round(performance.now() - started)
  });
} catch (error) {
  logEvent("stitch.generate", {
    result: "error",
    errorName: error.name,
    errorMessage: error.message,
    durationMs: Math.round(performance.now() - started)
  });
  process.exitCode = 1;
} finally {
  await client.close();
}
~~~

Add the generation command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:generate=node bin/generate.mjs'
~~~

- [ ] **Step 4: 运行全部工具单元测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 13 tests PASS。

- [ ] **Step 5: 提交断点生成器**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/generate-screens.mjs tools/stitch/bin/generate.mjs tools/stitch/test/generate-screens.test.mjs
git commit -m "design: 支持Stitch页面断点生成"
~~~
