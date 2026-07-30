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

