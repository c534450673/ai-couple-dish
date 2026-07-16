### Task 3: 建立 Stitch 客户端健康检查与断点状态

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/client.mjs
- Create: tools/stitch/src/state-store.mjs
- Create: tools/stitch/bin/health.mjs
- Create: tools/stitch/test/client.test.mjs

**Interfaces:**
- Produces: createStitchSdk(config, dependencies) -> { sdk: Stitch, client: StitchToolClient }
- Produces: assertRequiredTools(client) -> Promise<string[]>
- Produces: readGenerationState(path) -> Promise<GenerationState>
- Produces: writeGenerationState(path, state) -> Promise<void>
- GenerationState: { projectId: string | null, projectTitle: string, screens: Record<string, { screenId: string, kind: string }> }

- [ ] **Step 1: 写客户端工具集失败测试**

Create tools/stitch/test/client.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { assertRequiredTools } from "../src/client.mjs";
import {
  emptyGenerationState,
  readGenerationState,
  writeGenerationState
} from "../src/state-store.mjs";

test("assertRequiredTools accepts the Stitch generation tool set", async () => {
  const client = {
    async listTools() {
      return {
        tools: [
          { name: "create_project" },
          { name: "generate_screen_from_text" },
          { name: "get_screen" }
        ]
      };
    }
  };

  assert.deepEqual(await assertRequiredTools(client), [
    "create_project",
    "generate_screen_from_text",
    "get_screen"
  ]);
});

test("assertRequiredTools rejects a missing generation tool", async () => {
  const client = {
    async listTools() {
      return { tools: [{ name: "create_project" }] };
    }
  };

  await assert.rejects(
    () => assertRequiredTools(client),
    /Missing required Stitch tools/
  );
});

test("generation state persists with an atomic round trip", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-state-"));
  const filePath = join(root, "generation-state.json");
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1",
    screens: {
      login: { screenId: "screen-1", kind: "base" }
    }
  };

  await writeGenerationState(filePath, state);
  assert.deepEqual(await readGenerationState(filePath), state);
});
~~~

- [ ] **Step 2: 运行测试并验证客户端模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/client.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现客户端、状态存储和健康检查**

Create tools/stitch/src/client.mjs:

~~~javascript
import { Stitch, StitchToolClient } from "@google/stitch-sdk";

const REQUIRED_TOOLS = [
  "create_project",
  "generate_screen_from_text",
  "get_screen"
];

export function createStitchSdk(
  config,
  dependencies = { Stitch, StitchToolClient }
) {
  const client = new dependencies.StitchToolClient({
    apiKey: config.apiKey,
    baseUrl: config.host,
    timeout: 300000
  });
  return {
    sdk: new dependencies.Stitch(client),
    client
  };
}

export async function assertRequiredTools(client) {
  const response = await client.listTools();
  const names = response.tools.map(tool => tool.name);
  const missing = REQUIRED_TOOLS.filter(name => !names.includes(name));
  if (missing.length > 0) {
    throw new Error("Missing required Stitch tools: " + missing.join(", "));
  }
  return REQUIRED_TOOLS;
}
~~~

Create tools/stitch/src/state-store.mjs:

~~~javascript
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export function emptyGenerationState() {
  return {
    projectId: null,
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {}
  };
}

export async function readGenerationState(filePath) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      return emptyGenerationState();
    }
    throw error;
  }
}

export async function writeGenerationState(filePath, state) {
  await mkdir(dirname(filePath), { recursive: true });
  const temporaryPath = filePath + ".tmp";
  await writeFile(temporaryPath, JSON.stringify(state, null, 2) + String.fromCharCode(10));
  await rename(temporaryPath, filePath);
}
~~~

Create tools/stitch/bin/health.mjs:

~~~javascript
import { performance } from "node:perf_hooks";
import { readStitchConfig, publicConfig } from "../src/config.mjs";
import { createStitchSdk, assertRequiredTools } from "../src/client.mjs";
import { logEvent } from "../src/logger.mjs";

const started = performance.now();
const config = readStitchConfig();
const { client } = createStitchSdk(config);

try {
  const tools = await assertRequiredTools(client);
  logEvent("stitch.health", {
    result: "ok",
    durationMs: Math.round(performance.now() - started),
    tools,
    config: publicConfig(config)
  });
} catch (error) {
  logEvent("stitch.health", {
    result: "error",
    durationMs: Math.round(performance.now() - started),
    errorName: error.name,
    errorMessage: error.message
  });
  process.exitCode = 1;
} finally {
  await client.close();
}
~~~

Add the health command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:health=node bin/health.mjs'
~~~

- [ ] **Step 4: 运行测试和真实健康检查**

Run:

~~~bash
cd tools/stitch
npm test
test -n "$STITCH_API_KEY"
npm run stitch:health
~~~

Expected: tests PASS；健康检查输出单行 JSON，result 为 ok，不包含 API key。

- [ ] **Step 5: 提交客户端边界**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/client.mjs tools/stitch/src/state-store.mjs tools/stitch/bin/health.mjs tools/stitch/test/client.test.mjs
git commit -m "design: 增加Stitch客户端健康检查"
~~~
