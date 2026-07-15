# Couple Cosmos Stitch Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 使用安全、可重复的 Stitch 工作流生成 Couple Cosmos 全套移动端页面、首页变体、HTML、截图和可校验清单，为后续 H5 实现提供唯一视觉基准。

**Architecture:** 在 tools/stitch/ 建立与产品运行时隔离的 Node.js 设计工具，通过固定版本的 Google Labs Stitch SDK 调用 Stitch。提示词、生成状态、导出和验证各自独立；所有远端产物下载到 docs/design/stitch/couple-cosmos/，并用 SHA-256 manifest 保证可追溯。该工作包只生成和验证设计资产，不修改 frontend-h5 或后端业务代码。

**Tech Stack:** Node.js 20+、npm、@google/stitch-sdk 0.3.5、node:test、Node.js fetch、SHA-256。

## Global Constraints

- STITCH_API_KEY 只能由当前进程环境变量提供，不写入 Git、日志、命令、截图或 manifest。
- 所有工具日志必须为结构化 JSON，包含 event、result、durationMs 和非敏感上下文。
- Stitch SDK 必须固定为 0.3.5，不能使用浮动 latest。
- 设计目标设备为 MOBILE，关键宽度为 375px、390px、430px。
- 视觉方向固定为 Couple Cosmos：深夜蓝黑与紫黑背景、#FF5D73、#54E8D3、#FFC857、玻璃卡片和美食大图。
- 所有页面必须包含正常、加载、空数据、失败、无权限和未绑定状态的设计说明。
- 动效必须支持 prefers-reduced-motion，不能依赖动效表达唯一业务含义。
- 设计导出目录固定为 docs/design/stitch/couple-cosmos/。
- 不触碰当前工作区已有的 Java、前端 API 和其他未提交修改。

---

## File Structure

~~~text
tools/stitch/
├── package.json
├── package-lock.json
├── src/
│   ├── config.mjs
│   ├── logger.mjs
│   ├── prompts.mjs
│   ├── client.mjs
│   ├── state-store.mjs
│   ├── generate-home.mjs
│   ├── generate-screens.mjs
│   ├── exporter.mjs
│   └── verifier.mjs
├── bin/
│   ├── health.mjs
│   ├── generate.mjs
│   ├── export.mjs
│   └── verify.mjs
└── test/
    ├── config.test.mjs
    ├── prompts.test.mjs
    ├── client.test.mjs
    ├── generate-home.test.mjs
    ├── generate-screens.test.mjs
    ├── exporter.test.mjs
    └── verifier.test.mjs

docs/design/stitch/couple-cosmos/
├── README.md
├── generation-state.json
├── manifest.json
├── screenshots/
└── html/
~~~

## Scope Boundary

本计划是商业化规格的第一个独立工作包，覆盖规格第 3 至第 7 节和商用门槛第 1 项。FastAPI 迁移、H5 实现、功能扩展与商用验证必须分别使用后续实施计划，不能在本计划中顺手修改。

### Task 1: 建立隔离的 Stitch 工具与密钥安全边界

**Files:**
- Create: tools/stitch/package.json
- Create: tools/stitch/package-lock.json
- Create: tools/stitch/src/config.mjs
- Create: tools/stitch/src/logger.mjs
- Create: tools/stitch/test/config.test.mjs

**Interfaces:**
- Produces: readStitchConfig(env) -> { apiKey: string, host: string }
- Produces: publicConfig(config) -> { hasApiKey: boolean, host: string }
- Produces: logEvent(event, fields, write) -> void
- Consumes: process.env.STITCH_API_KEY and optional process.env.STITCH_HOST

- [ ] **Step 1: 写密钥与日志脱敏失败测试**

Create tools/stitch/test/config.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import test from "node:test";
import { readStitchConfig, publicConfig } from "../src/config.mjs";
import { logEvent } from "../src/logger.mjs";

test("readStitchConfig rejects a missing API key", () => {
  assert.throws(
    () => readStitchConfig({}),
    /STITCH_API_KEY must be provided through the process environment/
  );
});

test("publicConfig never returns the API key", () => {
  const config = readStitchConfig({
    STITCH_API_KEY: "secret-value",
    STITCH_HOST: "https://stitch.googleapis.com/mcp"
  });

  assert.deepEqual(publicConfig(config), {
    hasApiKey: true,
    host: "https://stitch.googleapis.com/mcp"
  });
});

test("logEvent redacts key and token fields recursively", () => {
  const lines = [];
  logEvent(
    "stitch.health",
    {
      result: "ok",
      apiKey: "secret-value",
      nested: { accessToken: "token-value", screenId: "screen-1" }
    },
    line => lines.push(line)
  );

  assert.equal(lines.length, 1);
  assert.equal(lines[0].includes("secret-value"), false);
  assert.equal(lines[0].includes("token-value"), false);
  assert.equal(lines[0].includes("screen-1"), true);
});
~~~

- [ ] **Step 2: 运行测试并验证因模块不存在而失败**

Run:

~~~bash
cd tools/stitch
node --test test/config.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 创建固定依赖和安全配置实现**

Create tools/stitch/package.json:

~~~json
{
  "name": "@ai-couple-dish/stitch-design",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "node --test test/*.test.mjs"
  },
  "dependencies": {
    "@google/stitch-sdk": "0.3.5"
  }
}
~~~

Create tools/stitch/src/config.mjs:

~~~javascript
const DEFAULT_HOST = "https://stitch.googleapis.com/mcp";

export function readStitchConfig(env = process.env) {
  const apiKey = String(env.STITCH_API_KEY || "").trim();
  if (!apiKey) {
    throw new Error(
      "STITCH_API_KEY must be provided through the process environment"
    );
  }

  return Object.freeze({
    apiKey,
    host: String(env.STITCH_HOST || DEFAULT_HOST).trim()
  });
}

export function publicConfig(config) {
  return Object.freeze({
    hasApiKey: Boolean(config.apiKey),
    host: config.host
  });
}
~~~

Create tools/stitch/src/logger.mjs:

~~~javascript
const SENSITIVE_NAMES = new Set([
  "apikey",
  "api_key",
  "token",
  "accesstoken",
  "access_token",
  "authorization"
]);

function sanitize(value, key = "") {
  const normalizedKey = key.toLowerCase();
  if (SENSITIVE_NAMES.has(normalizedKey)) {
    return "[REDACTED]";
  }
  if (Array.isArray(value)) {
    return value.map(item => sanitize(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([name, item]) => [name, sanitize(item, name)])
    );
  }
  return value;
}

export function logEvent(
  event,
  fields = {},
  write = line => process.stderr.write(line + String.fromCharCode(10))
) {
  write(
    JSON.stringify({
      timestamp: new Date().toISOString(),
      event,
      ...sanitize(fields)
    })
  );
}
~~~

- [ ] **Step 4: 安装依赖并运行安全测试**

Run:

~~~bash
cd tools/stitch
npm install
npm test
~~~

Expected: package-lock.json 生成，3 tests PASS，安装版本为 @google/stitch-sdk@0.3.5。

- [ ] **Step 5: 提交隔离工具基础**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/package-lock.json tools/stitch/src/config.mjs tools/stitch/src/logger.mjs tools/stitch/test/config.test.mjs
git commit -m "build: 建立安全的Stitch设计工具"
~~~

### Task 2: 固化 Couple Cosmos 页面目录与实际提示词

**Files:**
- Create: tools/stitch/src/prompts.mjs
- Create: tools/stitch/test/prompts.test.mjs

**Interfaces:**
- Produces: SCREEN_SPECS: readonly ScreenSpec[]
- Produces: getScreenPrompt(screenId) -> string
- Produces: HOME_VARIANT_PROMPT: string
- ScreenSpec: { id: string, title: string, deviceType: "MOBILE", requirements: string[] }

- [ ] **Step 1: 写页面完整性失败测试**

Create tools/stitch/test/prompts.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import test from "node:test";
import {
  SCREEN_SPECS,
  getScreenPrompt,
  HOME_VARIANT_PROMPT
} from "../src/prompts.mjs";

const REQUIRED_IDS = [
  "login",
  "bind",
  "home",
  "menu-list",
  "menu-detail",
  "recipe-list",
  "recipe-detail",
  "recipe-editor",
  "feed",
  "memories",
  "note-editor",
  "map",
  "ai-chat",
  "settings",
  "notification-center",
  "legal-privacy",
  "system-states"
];

test("screen catalog contains every approved screen exactly once", () => {
  const ids = SCREEN_SPECS.map(item => item.id);
  assert.deepEqual(ids.toSorted(), REQUIRED_IDS.toSorted());
  assert.equal(new Set(ids).size, ids.length);
});

test("every screen prompt contains visual tokens and system states", () => {
  for (const screen of SCREEN_SPECS) {
    const prompt = getScreenPrompt(screen.id);
    assert.match(prompt, /Couple Cosmos/);
    assert.match(prompt, /#FF5D73/);
    assert.match(prompt, /#54E8D3/);
    assert.match(prompt, /loading/);
    assert.match(prompt, /empty/);
    assert.match(prompt, /error/);
    assert.equal(screen.deviceType, "MOBILE");
  }
});

test("home variant prompt requests three materially different layouts", () => {
  assert.match(HOME_VARIANT_PROMPT, /three/);
  assert.match(HOME_VARIANT_PROMPT, /layout/);
  assert.match(HOME_VARIANT_PROMPT, /information hierarchy/);
});
~~~

- [ ] **Step 2: 运行测试并验证提示词模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/prompts.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 创建完整页面提示词目录**

Create tools/stitch/src/prompts.mjs:

~~~javascript
const BASE_PROMPT = [
  "Design a production-grade mobile H5 screen for AI Couple Dish.",
  "Brand direction: Couple Cosmos, a private food universe shared by two partners.",
  "Use deep midnight navy and purple-black gradients, coral #FF5D73, electric mint #54E8D3, star gold #FFC857, translucent glass cards and cinematic food photography.",
  "Use modern Chinese typography, 24px primary card radius and 28px sheet radius.",
  "Maintain WCAG-readable contrast and touch targets of at least 44px.",
  "Define normal, loading, empty, error, unauthorized and unbound-couple states.",
  "Motion notes must include reduced-motion behavior and must never hide business meaning.",
  "Target mobile widths 375px, 390px and 430px.",
  "All visible product copy must be Simplified Chinese."
];

const specs = [
  ["login", "登录与注册", [
    "Show two luminous planets gradually approaching above a secure phone and password form.",
    "Include login/register mode, password visibility, inline validation, loading button, privacy links and redirect recovery."
  ]],
  ["bind", "情侣绑定", [
    "Provide Invite TA and Enter Couple Code paths.",
    "Show code expiry progress, copy, share, regenerate and a celebratory avatar-orbit merge state."
  ]],
  ["home", "星球首页", [
    "Show partner avatar orbit, love-day counter, mood and online presence.",
    "Use a dynamic Bento Grid for anniversary, wish, feed, recipe, recent restaurant and Tonight We Eat."
  ]],
  ["menu-list", "我们的美食库", [
    "Combine restaurant, recipe and map tabs with search and filters.",
    "Use image-first cards for want-to-go, visited, recommended and favorites."
  ]],
  ["menu-detail", "餐厅详情", [
    "Use a shared hero food image, status, location, price, tags, partner activity and edit actions.",
    "Include like, favorite, map and create-memory actions."
  ]],
  ["recipe-list", "共同菜谱列表", [
    "Show want-to-cook, cooked, mine and partner filters.",
    "Include difficulty, cooking time, ingredients and inventory match."
  ]],
  ["recipe-detail", "菜谱详情", [
    "Show hero image, ingredients, numbered cooking steps, serving adjustment and shared completion state.",
    "Include add-to-shopping-list and AI adaptation actions."
  ]],
  ["recipe-editor", "菜谱与餐厅编辑器", [
    "Use a progressive form with image upload, draft status and leave confirmation.",
    "Show field errors beside fields and preserve entered content after upload or network errors."
  ]],
  ["feed", "情侣投喂", [
    "Use a central press-and-hold feed action with food, time, message and surprise mode.",
    "Show accept, reject, alternative proposal, countdown and completion celebration."
  ]],
  ["memories", "双人回忆时间轴", [
    "Combine anniversaries, wishes, notes and footprints in a filterable timeline.",
    "Use orbit countdowns, illuminated completed wishes and year grouping."
  ]],
  ["note-editor", "美食笔记编辑", [
    "Support photos, text, location, linked restaurant, linked recipe and local draft.",
    "Include upload progress, retry and privacy explanation."
  ]],
  ["map", "共同足迹地图", [
    "Show a dark cosmic map, clustered food locations and a draggable memory card.",
    "Include list/map switch, nearby filter, location permission and offline state."
  ]],
  ["ai-chat", "AI 美食星球", [
    "Show a luminous assistant planet, streaming answer trail and quick prompts.",
    "Any write tool must show an explicit preview, data source explanation, confirm and reject actions."
  ]],
  ["settings", "我们与设置", [
    "Show couple profile, relationship stage, shared metrics, privacy, theme, files, password, unbind and logout.",
    "Dangerous actions require clear consequence copy and dual confirmation."
  ]],
  ["notification-center", "情侣通知中心", [
    "Group feed, wish, anniversary, task and system notifications.",
    "Show unread state, bulk read, notification settings and failure recovery."
  ]],
  ["legal-privacy", "隐私与数据权利", [
    "Present privacy policy, terms, third-party services, data export, account deletion and couple-data ownership.",
    "Use readable long-form layout with a persistent section navigator."
  ]],
  ["system-states", "全局状态组件", [
    "Create a component sheet for skeleton, empty, network error, unauthorized, unbound couple, offline draft, toast, modal and reduced-motion variants.",
    "Include exact spacing, icon and button hierarchy."
  ]]
];

export const SCREEN_SPECS = Object.freeze(
  specs.map(([id, title, requirements]) =>
    Object.freeze({
      id,
      title,
      deviceType: "MOBILE",
      requirements: Object.freeze(requirements)
    })
  )
);

export const HOME_VARIANT_PROMPT = [
  "Generate three materially different Couple Cosmos home-screen variants.",
  "Vary layout and information hierarchy, not only color.",
  "Keep the partner orbit, Tonight We Eat action and five-tab navigation.",
  "Variant one prioritizes emotional status, variant two prioritizes food decisions, and variant three prioritizes shared memories.",
  "All variants must retain accessibility and reduced-motion notes."
].join(" ");

export function getScreenPrompt(screenId) {
  const screen = SCREEN_SPECS.find(item => item.id === screenId);
  if (!screen) {
    throw new Error("Unknown Stitch screen id: " + screenId);
  }
  return [...BASE_PROMPT, ...screen.requirements].join(" ");
}
~~~

- [ ] **Step 4: 运行提示词测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 6 tests PASS。

- [ ] **Step 5: 提交页面目录**

Run:

~~~bash
git add tools/stitch/src/prompts.mjs tools/stitch/test/prompts.test.mjs
git commit -m "design: 固化双人宇宙页面提示词"
~~~

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

### Task 4: 生成项目、首页与三个真实变体

**Files:**
- Create: tools/stitch/src/generate-home.mjs
- Create: tools/stitch/test/generate-home.test.mjs
- Create: docs/design/stitch/couple-cosmos/README.md

**Interfaces:**
- Consumes: Stitch SDK createProject(title), Project.generate(prompt, deviceType), Screen.variants(prompt, options, deviceType)
- Produces: generateHomeDesign(sdk, state) -> updated GenerationState
- State screen keys: home-base, home-emotion, home-food, home-memory

- [ ] **Step 1: 写首页生成失败测试**

Create tools/stitch/test/generate-home.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import test from "node:test";
import { generateHomeDesign } from "../src/generate-home.mjs";
import { emptyGenerationState } from "../src/state-store.mjs";

test("generateHomeDesign creates a project, base screen and three variants", async () => {
  const calls = [];
  const baseScreen = {
    screenId: "home-base-id",
    async variants(prompt, options, deviceType) {
      calls.push({ prompt, options, deviceType });
      return [
        { screenId: "home-emotion-id" },
        { screenId: "home-food-id" },
        { screenId: "home-memory-id" }
      ];
    }
  };
  const sdk = {
    async createProject(title) {
      assert.equal(title, "AI Couple Dish - Couple Cosmos");
      return {
        projectId: "project-1",
        async generate(prompt, deviceType) {
          assert.match(prompt, /Couple Cosmos/);
          assert.equal(deviceType, "MOBILE");
          return baseScreen;
        }
      };
    }
  };

  const result = await generateHomeDesign(sdk, emptyGenerationState());

  assert.equal(result.projectId, "project-1");
  assert.equal(result.screens["home-base"].screenId, "home-base-id");
  assert.equal(result.screens["home-emotion"].screenId, "home-emotion-id");
  assert.equal(calls[0].options.variantCount, 3);
});

test("generateHomeDesign resumes an existing project without creating another", async () => {
  let createCalls = 0;
  const baseScreen = {
    screenId: "home-base-id",
    async variants() {
      return [
        { screenId: "home-emotion-id" },
        { screenId: "home-food-id" },
        { screenId: "home-memory-id" }
      ];
    }
  };
  const project = {
    projectId: "project-1",
    async generate() {
      return baseScreen;
    }
  };
  const sdk = {
    async createProject() {
      createCalls += 1;
      return project;
    },
    project(projectId) {
      assert.equal(projectId, "project-1");
      return project;
    }
  };
  const state = {
    ...emptyGenerationState(),
    projectId: "project-1"
  };

  const result = await generateHomeDesign(sdk, state);
  assert.equal(createCalls, 0);
  assert.equal(result.projectId, "project-1");
});
~~~

- [ ] **Step 2: 运行测试并验证生成模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/generate-home.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现项目和首页变体生成**

Create tools/stitch/src/generate-home.mjs:

~~~javascript
import { getScreenPrompt, HOME_VARIANT_PROMPT } from "./prompts.mjs";

const VARIANT_KEYS = ["home-emotion", "home-food", "home-memory"];

export async function generateHomeDesign(sdk, state) {
  if (state.projectId && state.screens["home-base"]) {
    return state;
  }

  const project = state.projectId
    ? sdk.project(state.projectId)
    : await sdk.createProject(state.projectTitle);
  const base = await project.generate(getScreenPrompt("home"), "MOBILE");
  const variants = await base.variants(
    HOME_VARIANT_PROMPT,
    {
      variantCount: 3,
      creativeRange: "EXPLORE",
      aspects: ["LAYOUT", "COLOR_SCHEME", "IMAGES", "TEXT_CONTENT"]
    },
    "MOBILE"
  );

  const screens = {
    ...state.screens,
    "home-base": { screenId: base.screenId, kind: "base" }
  };
  for (const [index, screen] of variants.entries()) {
    screens[VARIANT_KEYS[index]] = {
      screenId: screen.screenId,
      kind: "variant"
    };
  }

  return {
    ...state,
    projectId: project.projectId,
    screens
  };
}
~~~

Create docs/design/stitch/couple-cosmos/README.md:

~~~markdown
# Couple Cosmos Stitch Design Assets

本目录保存 AI Couple Dish 的 Stitch 设计导出物。

- generation-state.json：Stitch 项目和屏幕 ID，不包含密钥。
- manifest.json：本地导出文件、来源屏幕和 SHA-256。
- screenshots/：页面截图。
- html/：Stitch HTML 导出。

## Selection

Selected home variant: none

任何文件更新后都必须运行 tools/stitch 的 stitch:verify。
~~~

- [ ] **Step 4: 运行首页单元测试**

Run:

~~~bash
cd tools/stitch
node --test test/generate-home.test.mjs
~~~

Expected: PASS。

- [ ] **Step 5: 提交首页生成器**

Run:

~~~bash
git add tools/stitch/src/generate-home.mjs tools/stitch/test/generate-home.test.mjs docs/design/stitch/couple-cosmos/README.md
git commit -m "design: 增加双人宇宙首页变体生成"
~~~

### Task 5: 断点生成其余页面并记录详细日志

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

### Task 6: 导出 HTML、截图和 SHA-256 manifest

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/exporter.mjs
- Create: tools/stitch/bin/export.mjs
- Create: tools/stitch/test/exporter.test.mjs
- Generate: docs/design/stitch/couple-cosmos/manifest.json
- Generate: docs/design/stitch/couple-cosmos/screenshots/*
- Generate: docs/design/stitch/couple-cosmos/html/*

**Interfaces:**
- Produces: downloadArtifact(url, outputPath, fetchImpl) -> Promise<{ sha256, bytes }>
- Produces: exportDesignProject(sdk, state, outputRoot, fetchImpl) -> Promise<Manifest>
- Manifest entry: { localId, projectId, screenId, kind, screenshot, screenshotSha256, html, htmlSha256, exportedAt }

- [ ] **Step 1: 写下载与 manifest 失败测试**

Create tools/stitch/test/exporter.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { exportDesignProject } from "../src/exporter.mjs";

test("exportDesignProject writes screenshot, html and hashes", async () => {
  const root = await mkdtemp(join(tmpdir(), "stitch-export-"));
  const sdk = {
    project(projectId) {
      assert.equal(projectId, "project-1");
      return {
        async getScreen(screenId) {
          assert.equal(screenId, "screen-1");
          return {
            async getImage() {
              return "https://assets.example/image";
            },
            async getHtml() {
              return "https://assets.example/html";
            }
          };
        }
      };
    }
  };
  const fetchImpl = async url => ({
    ok: true,
    status: 200,
    async arrayBuffer() {
      return Buffer.from(url.endsWith("image") ? "image-bytes" : "html-bytes");
    }
  });
  const state = {
    projectId: "project-1",
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {
      login: { screenId: "screen-1", kind: "base" }
    }
  };

  const manifest = await exportDesignProject(sdk, state, root, fetchImpl);
  assert.equal(manifest.version, 1);
  assert.equal(manifest.screens.length, 1);
  assert.equal(
    await readFile(join(root, "screenshots", "login.png"), "utf8"),
    "image-bytes"
  );
  assert.equal(
    await readFile(join(root, "html", "login.html"), "utf8"),
    "html-bytes"
  );
  assert.equal(manifest.screens[0].screenshotSha256.length, 64);
});
~~~

- [ ] **Step 2: 运行测试并验证导出模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/exporter.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现安全下载、哈希和原子 manifest**

Create tools/stitch/src/exporter.mjs:

~~~javascript
import { createHash } from "node:crypto";
import { mkdir, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

export async function downloadArtifact(url, outputPath, fetchImpl = fetch) {
  const response = await fetchImpl(url, { redirect: "follow" });
  if (!response.ok) {
    throw new Error("Artifact download failed with HTTP " + response.status);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await writeFile(outputPath, buffer);
  return { sha256: sha256(buffer), bytes: buffer.length };
}

export async function exportDesignProject(
  sdk,
  state,
  outputRoot,
  fetchImpl = fetch
) {
  const screenshotRoot = join(outputRoot, "screenshots");
  const htmlRoot = join(outputRoot, "html");
  await mkdir(screenshotRoot, { recursive: true });
  await mkdir(htmlRoot, { recursive: true });

  const project = sdk.project(state.projectId);
  const screens = [];
  for (const [localId, reference] of Object.entries(state.screens)) {
    const screen = await project.getScreen(reference.screenId);
    const screenshot = "screenshots/" + localId + ".png";
    const html = "html/" + localId + ".html";
    const imageResult = await downloadArtifact(
      await screen.getImage(),
      join(outputRoot, screenshot),
      fetchImpl
    );
    const htmlResult = await downloadArtifact(
      await screen.getHtml(),
      join(outputRoot, html),
      fetchImpl
    );
    screens.push({
      localId,
      projectId: state.projectId,
      screenId: reference.screenId,
      kind: reference.kind,
      screenshot,
      screenshotSha256: imageResult.sha256,
      html,
      htmlSha256: htmlResult.sha256,
      exportedAt: new Date().toISOString()
    });
  }

  const manifest = { version: 1, projectId: state.projectId, screens };
  const temporary = join(outputRoot, "manifest.json.tmp");
  const destination = join(outputRoot, "manifest.json");
  await writeFile(
    temporary,
    JSON.stringify(manifest, null, 2) + String.fromCharCode(10)
  );
  await rename(temporary, destination);
  return manifest;
}
~~~

Create tools/stitch/bin/export.mjs:

~~~javascript
import { resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { readStitchConfig } from "../src/config.mjs";
import { createStitchSdk } from "../src/client.mjs";
import { readGenerationState } from "../src/state-store.mjs";
import { exportDesignProject } from "../src/exporter.mjs";
import { logEvent } from "../src/logger.mjs";

const root = resolve("../../docs/design/stitch/couple-cosmos");
const state = await readGenerationState(resolve(root, "generation-state.json"));
if (!state.projectId) {
  throw new Error("Run npm run stitch:generate before export");
}
const started = performance.now();
const config = readStitchConfig();
const { sdk, client } = createStitchSdk(config);

try {
  const manifest = await exportDesignProject(sdk, state, root);
  logEvent("stitch.export", {
    result: "ok",
    projectId: manifest.projectId,
    screenCount: manifest.screens.length,
    durationMs: Math.round(performance.now() - started)
  });
} catch (error) {
  logEvent("stitch.export", {
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

Add the export command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:export=node bin/export.mjs'
~~~

- [ ] **Step 4: 运行导出测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 14 tests PASS。

- [ ] **Step 5: 提交导出器代码**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/exporter.mjs tools/stitch/bin/export.mjs tools/stitch/test/exporter.test.mjs
git commit -m "design: 增加Stitch设计资产导出"
~~~

### Task 7: 校验页面覆盖、文件哈希和密钥泄漏

**Files:**
- Modify: tools/stitch/package.json
- Create: tools/stitch/src/verifier.mjs
- Create: tools/stitch/bin/verify.mjs
- Create: tools/stitch/test/verifier.test.mjs

**Interfaces:**
- Produces: verifyDesignExport(root, expectedIds, forbiddenValues) -> Promise<{ screenCount: number }>
- Consumes: manifest.json, generation-state.json, screenshots/*, html/*

- [ ] **Step 1: 写缺页、哈希错误和密钥泄漏失败测试**

Create tools/stitch/test/verifier.test.mjs:

~~~javascript
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { verifyDesignExport } from "../src/verifier.mjs";

function hash(value) {
  return createHash("sha256").update(value).digest("hex");
}

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "stitch-verify-"));
  await mkdir(join(root, "screenshots"));
  await mkdir(join(root, "html"));
  await writeFile(join(root, "screenshots", "login.png"), "image");
  await writeFile(join(root, "html", "login.html"), "html");
  await writeFile(
    join(root, "manifest.json"),
    JSON.stringify({
      version: 1,
      projectId: "project-1",
      screens: [{
        localId: "login",
        projectId: "project-1",
        screenId: "screen-1",
        kind: "base",
        screenshot: "screenshots/login.png",
        screenshotSha256: hash("image"),
        html: "html/login.html",
        htmlSha256: hash("html"),
        exportedAt: "2026-07-15T00:00:00.000Z"
      }]
    })
  );
  return root;
}

test("verifyDesignExport accepts complete matching files", async () => {
  const root = await fixture();
  assert.deepEqual(
    await verifyDesignExport(root, ["login"], ["secret-value"]),
    { screenCount: 1 }
  );
});

test("verifyDesignExport rejects a missing required screen", async () => {
  const root = await fixture();
  await assert.rejects(
    () => verifyDesignExport(root, ["login", "bind"], []),
    /Missing exported screens: bind/
  );
});

test("verifyDesignExport rejects leaked secrets", async () => {
  const root = await fixture();
  await writeFile(join(root, "html", "login.html"), "secret-value");
  await assert.rejects(
    () => verifyDesignExport(root, ["login"], ["secret-value"]),
    /Forbidden secret value found/
  );
});
~~~

- [ ] **Step 2: 运行测试并验证校验模块不存在**

Run:

~~~bash
cd tools/stitch
node --test test/verifier.test.mjs
~~~

Expected: FAIL，错误包含 ERR_MODULE_NOT_FOUND。

- [ ] **Step 3: 实现覆盖率、哈希和泄漏校验**

Create tools/stitch/src/verifier.mjs:

~~~javascript
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

function hash(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

export async function verifyDesignExport(
  root,
  expectedIds,
  forbiddenValues = []
) {
  const manifestBuffer = await readFile(join(root, "manifest.json"));
  const manifest = JSON.parse(manifestBuffer.toString("utf8"));
  const exportedIds = manifest.screens.map(screen => screen.localId);
  const missing = expectedIds.filter(id => !exportedIds.includes(id));
  if (missing.length > 0) {
    throw new Error("Missing exported screens: " + missing.join(", "));
  }

  for (const screen of manifest.screens) {
    const screenshot = await readFile(join(root, screen.screenshot));
    const html = await readFile(join(root, screen.html));
    if (hash(screenshot) !== screen.screenshotSha256) {
      throw new Error("Screenshot hash mismatch: " + screen.localId);
    }
    if (hash(html) !== screen.htmlSha256) {
      throw new Error("HTML hash mismatch: " + screen.localId);
    }
    const searchable = Buffer.concat([screenshot, html, manifestBuffer]);
    for (const forbidden of forbiddenValues.filter(Boolean)) {
      if (searchable.includes(Buffer.from(forbidden))) {
        throw new Error("Forbidden secret value found: " + screen.localId);
      }
    }
  }

  return { screenCount: manifest.screens.length };
}
~~~

Create tools/stitch/bin/verify.mjs:

~~~javascript
import { resolve } from "node:path";
import { SCREEN_SPECS } from "../src/prompts.mjs";
import { verifyDesignExport } from "../src/verifier.mjs";
import { logEvent } from "../src/logger.mjs";

const expectedIds = [
  "home-base",
  "home-emotion",
  "home-food",
  "home-memory",
  ...SCREEN_SPECS.filter(screen => screen.id !== "home").map(screen => screen.id)
];
const root = resolve("../../docs/design/stitch/couple-cosmos");

try {
  const result = await verifyDesignExport(
    root,
    expectedIds,
    [process.env.STITCH_API_KEY, process.env.STITCH_ACCESS_TOKEN]
  );
  logEvent("stitch.verify", { result: "ok", ...result });
} catch (error) {
  logEvent("stitch.verify", {
    result: "error",
    errorName: error.name,
    errorMessage: error.message
  });
  process.exitCode = 1;
}
~~~

Add the verification command:

~~~bash
cd tools/stitch
npm pkg set 'scripts.stitch:verify=node bin/verify.mjs'
~~~

- [ ] **Step 4: 运行校验测试**

Run:

~~~bash
cd tools/stitch
npm test
~~~

Expected: 17 tests PASS。

- [ ] **Step 5: 提交校验器**

Run:

~~~bash
git add tools/stitch/package.json tools/stitch/src/verifier.mjs tools/stitch/bin/verify.mjs tools/stitch/test/verifier.test.mjs
git commit -m "test: 校验Stitch页面与导出哈希"
~~~

### Task 8: 执行真实 Stitch 生成、视觉复核与工作包验收

**Files:**
- Generate: docs/design/stitch/couple-cosmos/generation-state.json
- Generate: docs/design/stitch/couple-cosmos/manifest.json
- Generate: docs/design/stitch/couple-cosmos/screenshots/*
- Generate: docs/design/stitch/couple-cosmos/html/*
- Modify: docs/design/stitch/couple-cosmos/README.md

**Interfaces:**
- Consumes: 用户提供的 STITCH_API_KEY，仅存在于当前执行进程。
- Produces: 至少 20 个导出屏幕：首页基础稿、三个首页变体、其余 16 个页面/状态稿。
- Produces: 用户最终选择的首页变体 ID 和视觉复核记录。

- [ ] **Step 1: 在不打印密钥的情况下确认环境**

Run:

~~~bash
cd tools/stitch
node -e 'if (!process.env.STITCH_API_KEY) process.exit(1)'
~~~

Expected: exit 0，无标准输出。

- [ ] **Step 2: 运行完整单元测试和 SDK 健康检查**

Run:

~~~bash
cd tools/stitch
npm ci
npm test
npm run stitch:health
~~~

Expected: 17 tests PASS；健康检查 result 为 ok；日志中不含密钥。

- [ ] **Step 3: 生成项目、首页变体和全部页面**

Run:

~~~bash
cd tools/stitch
npm run stitch:generate
~~~

Expected: result 为 ok，screenCount 为 20；中断后再次运行会跳过 generation-state.json 中已完成屏幕。

- [ ] **Step 4: 导出并验证所有设计资产**

Run:

~~~bash
cd tools/stitch
npm run stitch:export
npm run stitch:verify
~~~

Expected: manifest.json 包含 20 项；每项 HTML 与截图文件存在且 SHA-256 匹配；无密钥泄漏。

- [ ] **Step 5: 逐页进行视觉复核**

Review checklist:

- 使用本地图片查看器检查 login、bind、home-emotion、home-food、home-memory、menu-list、recipe-detail、feed、memories、map、ai-chat、settings 和 system-states。
- 确认所有页面使用 Couple Cosmos 令牌而非玫瑰奶油令牌。
- 确认中文文本没有乱码或溢出。
- 确认 375px、390px、430px 布局说明完整。
- 确认六类系统状态和 reduced-motion 说明存在。
- 确认表单、危险操作和 AI 写操作具备明确确认与错误恢复。

After the user selects one variant, set SELECTED_HOME_VARIANT to exactly home-emotion, home-food or home-memory, then run:

~~~bash
cd tools/stitch
case "$SELECTED_HOME_VARIANT" in
  home-emotion|home-food|home-memory) ;;
  *) exit 1 ;;
esac
node - "$SELECTED_HOME_VARIANT" <<'NODE'
import { readFileSync, writeFileSync } from "node:fs";
const file = "../../docs/design/stitch/couple-cosmos/README.md";
const selected = process.argv[2];
const content = readFileSync(file, "utf8");
writeFileSync(
  file,
  content.replace(
    /Selected home variant: (none|home-emotion|home-food|home-memory)/,
    "Selected home variant: " + selected
  )
);
NODE
~~~

Expected: 视觉复核记录没有未解决的阻断项；README.md 记录一个且仅一个已批准首页变体。

- [ ] **Step 6: 运行提交前检查**

Run:

~~~bash
cd tools/stitch
npm test
npm run stitch:verify
cd ../..
git diff --check
~~~

Expected: tests PASS，验证 result 为 ok，git diff --check 无输出。

- [ ] **Step 7: 运行 GitNexus 变更检测并提交设计产物**

Run GitNexus:

~~~text
gitnexus_detect_changes({scope: "all"})
~~~

Expected: 只影响 tools/stitch、docs/design/stitch 和本计划预期文件，不影响业务执行流程。

Run:

~~~bash
git add tools/stitch docs/design/stitch/couple-cosmos
git commit -m "design: 生成双人宇宙全页面设计"
~~~

## Work Package Completion Gate

完成本计划必须同时满足：

- @google/stitch-sdk 锁定为 0.3.5。
- 单元测试全部通过。
- Stitch 健康检查成功且日志无密钥。
- 20 个页面/变体均有截图和 HTML。
- manifest 文件和 SHA-256 校验通过。
- 用户已复核首页三个真实变体并选定最终版本。
- Stitch 项目 ID、屏幕 ID 和导出文件可追溯。
- 未修改 frontend-h5 和后端业务代码。
- GitNexus 检测没有非预期执行流影响。

通过此门槛后，下一份独立计划为 FastAPI 后端合同与迁移计划。
