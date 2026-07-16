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
