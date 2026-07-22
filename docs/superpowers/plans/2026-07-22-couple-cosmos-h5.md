# Couple Cosmos H5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Vue 3 H5 从旧的 Rose & Cream 皮肤完整迁移到可运行、可降级、可测试的 Couple Cosmos 移动端体验，并忠实覆盖已导出的 Stitch 页面、现有业务能力和商业化规格中的前端状态。

**Architecture:** 保留 Vue Router、Pinia、Vant、Axios 和现有业务 API 边界，先修复测试基线，再建立深色宇宙设计令牌、应用壳、共享状态组件和领域 Store。页面按认证/绑定、美食库、投喂/回忆、地图/AI、设置/隐私分批迁移；首页只在 `docs/design/stitch/couple-cosmos/README.md` 登记最终方案后实现。FastAPI 迁移属于后续独立工作包，本计划通过 API 模块保持后端可替换性。

**Tech Stack:** Vue 3.4、Vite 5、Vue Router 4、Pinia 2、Vant 4、Sass、Axios、Vitest、Vue Test Utils、Playwright Chromium。

## Global Constraints

- 唯一视觉基准是 `docs/design/stitch/couple-cosmos/`；不得继续使用 `frontend-h5/design/stitch/` 的 Rose & Cream 令牌。
- 背景使用深夜蓝黑与紫黑，主色 `#FF5D73`，辅色 `#54E8D3`，高光 `#FFC857`；主卡片圆角 `24px`，弹层圆角 `28px`。
- 固定五栏底部导航文案和顺序为“星球、菜单、投喂、回忆、我们”。
- 所有可见产品文案使用简体中文；触控目标至少 `44px`；中文文字 `letter-spacing: 0`。
- 业务页必须以完整正常业务态为主体；loading、empty、error、unauthorized、unbound 和 offline-draft 是互斥状态，不得作为开发者状态画廊嵌在正常页面。
- 微交互约 `180ms`，卡片过渡约 `320ms`，页面过渡约 `500ms`；优先使用 `transform` 和 `opacity`。
- 所有动效必须支持 `prefers-reduced-motion: reduce`，不得改变业务提交时序或成为唯一状态提示。
- 页面数据流固定为 View -> Feature Component/Composable -> Pinia Store -> API Module -> Axios；页面不得拼接 API URL 或自行读取 token。
- 用户、情侣、主题、通知使用全局 Store；菜单、菜谱、投喂、回忆使用领域 Store；首页卡片必须支持部分成功和独立重试。
- 关键操作日志为结构化对象，包含 `event`、`result`、`durationMs`、`module`、`operation` 和脱敏上下文；禁止密码、JWT、完整手机号、私密正文、图片内容、密钥和带敏感 query 的 URL。
- Stitch/AIDA 图片只作为构图参考，不得下载或热链到产品；运行时内置图片必须重新生成或取得可验证授权，并在 manifest 中记录来源、授权证据、SHA-256 和用途。不得依赖 Tailwind CDN、Google Fonts、Material Symbols 或 `lh3.googleusercontent.com`。
- 必须覆盖 `375px`、`390px`、`430px` 移动视口、减弱动效、慢速网络、接口失败和未绑定状态。
- 不在本计划中修改 Spring Boot 或实现 FastAPI；后端缺失合同使用明确的 unavailable 状态，不伪造业务成功。
- 修改任何现有函数、类或方法前执行 GitNexus upstream impact；每个提交前执行 GitNexus `detect_changes(scope: staged)`。

---

## Scope Boundary And Decisions

- `note-detail` 使用独立只读路由 `/memories/notes/:id`，结构取自 `memories` 时间线与 `note-editor`，不等待新增 Stitch 屏。
- 地图保留现有 QQMap 接入，但必须提供无需地图 SDK 的地点列表降级和定位权限拒绝态。
- 通知中心先使用现有 HTTP 列表、已读和批量已读 API；实时推送在 FastAPI 通知合同计划中处理。
- 菜单、菜谱和笔记草稿先保存在按用户 ID 隔离的 localStorage 命名空间；服务端草稿同步属于后端迁移计划。
- 解绑页面只展示现有申请/确认能力和“数据归属规则待服务端合同确认”的不可提交状态；不得自行承诺删除或保留政策。
- 首页实现任务开始前，`Selected home variant` 必须为 `home-emotion`、`home-food` 或 `home-memory`；值为 `none` 时该任务必须停止。
- Task 3 为尚未进入实现任务的目标路由统一使用一个 Couple Cosmos `UnavailableView`，只显示明确的“功能建设中”状态；Task 4-8 创建真实页面后必须逐一替换，不得将占位页保留到 Task 10。
- Task 3 的路由守卫只负责保留并编码 `redirect`；登录和绑定成功消费该参数属于 Task 4，避免在应用壳任务中修改认证页面。
- Task 3 的情侣门禁读取启动时已 hydration 的 Pinia/localStorage 快照；不得在每次导航中请求情侣接口。服务端刷新继续由应用启动流程负责，Task 4 再覆盖绑定后的同步与重定向竞态。

## Baseline Evidence

- `npm run build` 当前通过，仅有 Sass legacy API deprecation。
- `npm test -- --run` 当前为 181 个用例中 101 通过、33 失败，并有 3 个测试进程错误。
- 失败集中在错误的 Axios mock、响应包装断言、重复 user store 测试和日期时区断言；这不是可接受的长期基线。
- `npx eslint ...` 当前有 133 errors / 58 warnings；迁移任务必须使所有修改文件无 lint error，最终任务再清零全仓错误。

## File Structure

```text
frontend-h5/
├── scripts/
│   └── verify-cosmos-assets.mjs       # 运行时图片 manifest 与 SHA-256 校验
├── src/
│   ├── assets/
│   │   ├── cosmos/                    # 本地运行时图片
│   │   ├── cosmos-manifest.json       # 来源、授权、hash、用途
│   │   └── styles/
│   │       ├── tokens.scss            # Couple Cosmos SCSS token/mixin
│   │       ├── main.scss              # 全局 CSS 变量、reset、Vant override
│   │       └── motion.scss            # 动效和 reduced-motion 降级
│   ├── components/cosmos/
│   │   ├── AppShell.vue               # 顶栏、内容区、五栏导航壳
│   │   ├── AppHeader.vue              # 统一页头
│   │   ├── AsyncState.vue             # loading/empty/error/unauthorized/unbound
│   │   ├── CoupleGate.vue             # 未绑定能力门禁
│   │   ├── GlassCard.vue              # 玻璃卡片
│   │   ├── IconButton.vue             # 44px icon button 与 aria-label
│   │   ├── MediaCard.vue              # 固定比例媒体卡
│   │   └── StatusChip.vue             # 语义状态标签
│   ├── composables/
│   │   ├── useAsyncResource.js        # 标准请求状态与 retry
│   │   ├── useDraft.js                # 用户隔离本地草稿
│   │   ├── useReducedMotion.js        # 动效偏好
│   │   └── useStructuredLog.js        # 脱敏结构化前端日志
│   ├── layouts/MainLayout.vue         # RouterView 主布局
│   ├── stores/
│   │   ├── theme.js
│   │   ├── notification.js
│   │   ├── menu.js
│   │   ├── recipe.js
│   │   ├── feed.js
│   │   └── memories.js
│   ├── views/
│   │   ├── auth/
│   │   ├── recipe/
│   │   ├── memories/
│   │   ├── ai/
│   │   ├── notification/
│   │   ├── legal/
│   │   └── states/
│   └── tests/
│       ├── components/cosmos/
│       ├── composables/
│       ├── stores/
│       └── views/
└── tests/e2e/
    ├── fixtures/
    ├── cosmos-navigation.spec.js
    ├── cosmos-states.spec.js
    └── cosmos-visual.spec.js
```

### Task 1: 修复前端测试与请求合同基线

**Files:**
- Modify: `frontend-h5/vitest.config.js`
- Modify: `frontend-h5/src/tests/setup.js`
- Modify: `frontend-h5/src/tests/api/api.spec.js`
- Modify: `frontend-h5/src/tests/api/newApi.spec.js`
- Modify: `frontend-h5/src/tests/stores/user.test.js`
- Modify: `frontend-h5/src/tests/utils/date.spec.js`
- Modify: `frontend-h5/src/api/request.js`
- Test: `frontend-h5/src/tests/api/request.test.js`

**Interfaces:**
- Preserves: API success response shape `{ code, message, data }`.
- Produces: `resetRequestState() -> void` for deterministic tests and logout cleanup.
- Produces: a green Vitest baseline with no real network calls.

- [ ] **Step 1: 固化 API 模块 mock 合同**

在 API 测试中用 hoisted request mock 代替给错误 Axios 实例挂 `MockAdapter`：

```js
const requestMock = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()
}))

vi.mock('@/api/request', () => ({ default: requestMock }))
```

每个 API 用例断言调用参数和 `{ code: 200, data }` 返回值，不允许测试发出真实 XHR。

- [ ] **Step 2: 修正 legacy API 测试的 Axios 双层 data 断言**

`newApi.spec.js` 测试的是原始 Axios，因此断言统一为：

```js
const response = await timeCapsuleApi.getList()
expect(response.data.data).toHaveLength(2)
```

并显式导入 `afterEach`，确保 adapter 每例恢复。

- [ ] **Step 3: 暴露请求状态清理函数**

```js
export const resetRequestState = () => {
  pendingRequestMap.clear()
  memoryCache.clear()
}
```

在 `afterEach` 调用它，禁止缓存、重试计数和 interval 跨测试污染；`setInterval` 必须保存句柄并在测试环境不启动。

- [ ] **Step 4: 合并重复 user store 断言并固定日期时区**

保留覆盖更完整的 `user.spec.js`；`user.test.js` 只保留不同的 logout/API failure 用例。日期测试使用带时区的 ISO 值与 fake timer：

```js
vi.useFakeTimers()
vi.setSystemTime(new Date('2026-07-22T12:00:00+08:00'))
```

- [ ] **Step 5: 运行基线验证**

Run:

```bash
cd frontend-h5
npm test -- --run
npm run build
```

Expected: 0 failed tests、0 unhandled errors、build exit 0。

- [ ] **Step 6: 影响分析并提交**

```bash
git add frontend-h5/vitest.config.js frontend-h5/src/tests frontend-h5/src/api/request.js
git commit -m "test: 修复H5测试与请求合同基线"
```

### Task 2: 建立 Couple Cosmos 设计令牌、动效和资源门禁

**Files:**
- Modify: `frontend-h5/src/assets/styles/tokens.scss`
- Modify: `frontend-h5/src/assets/styles/main.scss`
- Create: `frontend-h5/src/assets/styles/motion.scss`
- Create: `frontend-h5/src/assets/cosmos-manifest.json`
- Create: `frontend-h5/scripts/verify-cosmos-assets.mjs`
- Create: `docs/legal/assets/cosmos-runtime-assets.md`
- Modify: `frontend-h5/src/main.js`
- Modify: `frontend-h5/package.json`
- Test: `frontend-h5/src/tests/design/cosmos-tokens.spec.js`
- Test: `frontend-h5/src/tests/design/cosmos-assets.spec.js`

**Interfaces:**
- Produces SCSS tokens: `$cosmos-bg`, `$cosmos-surface`, `$cosmos-primary`, `$cosmos-secondary`, `$cosmos-gold`, `$cosmos-card-radius`, `$cosmos-sheet-radius`.
- Produces CSS variables with matching `--cosmos-*` names.
- Produces command: `npm run assets:verify`.

- [ ] **Step 1: 写设计 token 失败测试**

```js
const css = await readFile(resolve('src/assets/styles/tokens.scss'), 'utf8')
expect(css).toContain('$cosmos-primary: #ff5d73')
expect(css).toContain('$cosmos-secondary: #54e8d3')
expect(css).toContain('$cosmos-gold: #ffc857')
expect(css).not.toContain('#fff8f5')
```

- [ ] **Step 2: 替换旧主题 token**

定义三层深色表面、可读文字、玻璃边框、44px 触控尺寸、24/28px 圆角和 180/320/500ms 动效时长。中文字体栈为：

```scss
$font-family-base: 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
```

禁止负字距和 viewport 字号缩放。

- [ ] **Step 3: 建立全局动效与降级**

`motion.scss` 只使用 transform/opacity 的 `cosmos-fade`、`cosmos-rise`、`cosmos-breathe`、`cosmos-orbit`；加入：

```scss
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Step 4: 本地化运行时视觉资源**

从 Stitch HTML 中选择真正用于 Vue 页面的食物、头像和地点图，下载到 `src/assets/cosmos/`。`cosmos-manifest.json` 每项必须包含：

```json
{
  "path": "src/assets/cosmos/menu-hero.webp",
  "source": "project-generated",
  "designReference": "docs/design/stitch/couple-cosmos/html/menu-list.html:170",
  "licenseEvidence": "docs/legal/assets/cosmos-runtime-assets.md#food-hero",
  "sha256": "64-lowercase-hex",
  "usage": ["menu-list", "menu-detail"]
}
```

只生成/引入三个最小运行时位图：`food-hero.webp`、`partner-avatar.webp`、`place-restaurant.webp`；空态使用 CSS 与图标实现。若使用图像生成服务，记录模型、生成时间、prompt SHA-256 和账户输出权利依据；若使用图库，记录原始下载页、许可证版本、作者和下载日期。不具备可接受授权证据的图片不得进入运行时包。

- [ ] **Step 5: 实现资源校验并验证**

`verify-cosmos-assets.mjs` 使用 `JSON.parse`、`fs.readFile` 和 `crypto.createHash('sha256')` 校验路径在 `src/assets/cosmos/` 内、文件存在、hash 匹配、授权证据文件和锚点存在，并扫描源码禁止 `lh3.googleusercontent.com`、`cdn.tailwindcss.com`、`transparenttextures.com` 和 Google Fonts。

Run:

```bash
cd frontend-h5
npm run assets:verify
npm test -- --run src/tests/design
npm run build
```

- [ ] **Step 6: 提交设计基础**

```bash
git add frontend-h5/src/assets frontend-h5/scripts frontend-h5/src/main.js frontend-h5/package.json frontend-h5/package-lock.json frontend-h5/src/tests/design docs/legal/assets/cosmos-runtime-assets.md
git commit -m "design: 建立Couple Cosmos H5视觉基础"
```

### Task 3: 实现应用壳、五栏导航和统一状态模型

**Files:**
- Create: `frontend-h5/src/layouts/MainLayout.vue`
- Create: `frontend-h5/src/components/cosmos/AppShell.vue`
- Create: `frontend-h5/src/components/cosmos/AppHeader.vue`
- Create: `frontend-h5/src/components/cosmos/AsyncState.vue`
- Create: `frontend-h5/src/components/cosmos/CoupleGate.vue`
- Create: `frontend-h5/src/components/cosmos/GlassCard.vue`
- Create: `frontend-h5/src/components/cosmos/IconButton.vue`
- Create: `frontend-h5/src/components/cosmos/MediaCard.vue`
- Create: `frontend-h5/src/components/cosmos/StatusChip.vue`
- Create: `frontend-h5/src/composables/useAsyncResource.js`
- Create: `frontend-h5/src/composables/useReducedMotion.js`
- Create: `frontend-h5/src/composables/useStructuredLog.js`
- Create: `frontend-h5/src/views/states/UnavailableView.vue`
- Modify: `frontend-h5/src/components/AppTabbar.vue`
- Modify: `frontend-h5/src/App.vue`
- Modify: `frontend-h5/src/router/index.js`
- Test: `frontend-h5/src/tests/components/cosmos/AppShell.spec.js`
- Test: `frontend-h5/src/tests/components/cosmos/AsyncState.spec.js`
- Test: `frontend-h5/src/tests/router/cosmos-router.spec.js`

**Interfaces:**
- Produces: `useAsyncResource(loader, options) -> { status, data, error, execute, retry, reset }`.
- Produces: `logUiEvent(event, fields) -> void`, recursively redacting sensitive keys.
- Produces route meta: `{ requiresAuth, requiresCouple, shell, tab }`.

- [ ] **Step 1: 写导航和状态失败测试**

断言五栏文本与路由精确对应：

```js
expect(tabs).toEqual([
  ['星球', '/home'], ['菜单', '/menu'], ['投喂', '/feed'],
  ['回忆', '/memories'], ['我们', '/settings']
])
```

`AsyncState` 必须对 loading、empty、error、unauthorized、unbound 分别渲染一个 `role="status"` 或 `role="alert"`，error/unbound 提供明确事件。

- [ ] **Step 2: 实现异步资源状态机**

状态只允许 `idle | loading | success | empty | error | unauthorized | unbound`。并发执行使用递增 request id，旧请求完成不得覆盖新结果；日志只记录状态、耗时和脱敏错误码。

- [ ] **Step 3: 实现应用壳和无障碍组件**

`AppShell` 提供 `header/default/navigation` slots；`IconButton` 必须要求非空 `label` 并输出 `aria-label`；固定控件用稳定尺寸，底部安全区使用 `env(safe-area-inset-bottom)`。

- [ ] **Step 4: 扩展路由和情侣门禁**

新增：

```text
/recipes
/recipes/:id
/recipes/new
/recipes/:id/edit
/memories
/memories/notes/new
/memories/notes/:id
/ai
/notifications
/legal
/states
```

对应业务页面尚未由后续任务创建时，路由先指向 `UnavailableView`；每个后续页面任务必须在同一提交中替换对应路由。Task 3 不修改登录或绑定页面，只验证 `redirect` 查询参数被正确保留。

守卫先检查 token，再检查 `requiresCouple`；未绑定跳转 `/bind?redirect=<encoded fullPath>`。Task 4 的登录/绑定成功流程必须消费该参数并恢复原路由。

- [ ] **Step 5: 验证**

```bash
cd frontend-h5
npm test -- --run src/tests/components/cosmos src/tests/router
npm run build
```

- [ ] **Step 6: 提交应用壳**

```bash
git add frontend-h5/src/App.vue frontend-h5/src/router frontend-h5/src/layouts frontend-h5/src/components frontend-h5/src/composables frontend-h5/src/tests
git commit -m "feat: 建立Couple Cosmos应用壳与状态模型"
```

### Task 4: 重做登录、注册和情侣绑定主链路

**Files:**
- Modify: `frontend-h5/src/views/login/index.vue`
- Modify: `frontend-h5/src/views/bind/index.vue`
- Modify: `frontend-h5/src/stores/user.js`
- Modify: `frontend-h5/src/api/index.js`
- Modify: `frontend-h5/src/components/AgreementDialog.vue`
- Test: `frontend-h5/src/tests/views/login.spec.js`
- Create: `frontend-h5/src/tests/views/bind.spec.js`
- Create: `frontend-h5/src/tests/e2e/auth-bind.spec.js`

**Interfaces:**
- Produces: `userStore.login(credentials)` and `userStore.register(profile)` using password-based request DTOs.
- Preserves: redirect query restoration.
- Produces binding modes: `invite | enter-code`.

- [ ] **Step 1: 写密码登录和绑定失败测试**

登录测试必须证明：没有微信/Apple/验证码入口；字段旁显示错误；提交中按钮 disabled；成功后恢复 redirect。绑定测试必须证明：生成码、复制、重新生成、输入码、有效期进度和错误恢复可操作。

- [ ] **Step 2: 对齐认证 API 模块**

新增或复用实际后端合同：

```js
login: credentials => request.post('/user/phoneLogin', credentials),
register: profile => request.post('/user/register', profile)
```

当前 Java 若不支持密码注册，UI 显示明确 unavailable，不回退到伪短信或将密码当验证码。

- [ ] **Step 3: 按 Stitch 重做登录与绑定**

登录以 `login.png` 为视觉参考；绑定以 `bind.html` 为结构参考。绑定成功动画通过独立 CSS class 触发，减弱动效下直接显示完成态。

- [ ] **Step 4: 增加结构化日志**

只记录 `auth.login`、`auth.register`、`couple.code.generate`、`couple.bind` 的 result、durationMs、业务错误码和脱敏 user id，不记录手机号、密码或情侣码。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/views/login.spec.js src/tests/views/bind.spec.js
npm run build
git add src/views/login src/views/bind src/stores/user.js src/api/index.js src/components/AgreementDialog.vue src/tests
git commit -m "feat: 重做Couple Cosmos认证与绑定"
```

### Task 5: 重做美食库、菜谱和可恢复编辑器

**Files:**
- Modify: `frontend-h5/src/views/menu/index.vue`
- Modify: `frontend-h5/src/views/menu/detail.vue`
- Modify: `frontend-h5/src/views/menu/add.vue`
- Create: `frontend-h5/src/views/recipe/index.vue`
- Create: `frontend-h5/src/views/recipe/detail.vue`
- Modify: `frontend-h5/src/views/recipe/add.vue`
- Create: `frontend-h5/src/stores/menu.js`
- Create: `frontend-h5/src/stores/recipe.js`
- Create: `frontend-h5/src/composables/useDraft.js`
- Modify: `frontend-h5/src/api/index.js`
- Create: `frontend-h5/src/tests/stores/menu.spec.js`
- Create: `frontend-h5/src/tests/stores/recipe.spec.js`
- Create: `frontend-h5/src/tests/views/menu.spec.js`
- Create: `frontend-h5/src/tests/views/recipe.spec.js`

**Interfaces:**
- Produces: `useMenuStore()` and `useRecipeStore()` with list/detail/mutation states.
- Produces: `useDraft({ userId, resource, resourceId }) -> { draft, hasDraft, save, restore, clear }`.
- Produces: `recipeApi` in `src/api/index.js`; removes direct fetch from recipe view.

- [ ] **Step 1: 写列表、详情和草稿恢复失败测试**

覆盖搜索、筛选、分页、空态、单次重试、详情操作、图片上传失败、草稿恢复、离开提醒和成功后清草稿。草稿 key 精确为：

```js
`couple-cosmos:draft:${userId}:${resource}:${resourceId || 'new'}`
```

- [ ] **Step 2: 实现领域 Store 与 recipe API**

Store 将 API `{ code, data }` 归一为视图状态；mutation 成功只刷新相关实体。`recipe/add.vue` 不得保留 `fetch('/api/...')`。

- [ ] **Step 3: 按 Stitch 重做菜单页**

`menu-list.html` 对应 `/menu`，`menu-detail.html` 对应 `/menu/:id`；新增/编辑页复用设计系统表单而非复制详情卡。图片容器使用固定 aspect-ratio，失败有本地占位。

- [ ] **Step 4: 按 Stitch 实现菜谱页**

`recipe-list.html`、`recipe-detail.html`、`recipe-editor.html` 分别对应 `/recipes`、`/recipes/:id`、new/edit。食材与步骤编辑使用可排序列表和显式删除按钮，不用文本拼接存储结构化字段。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/stores/menu.spec.js src/tests/stores/recipe.spec.js src/tests/views/menu.spec.js src/tests/views/recipe.spec.js
npm run build
git add src/views/menu src/views/recipe src/stores src/composables/useDraft.js src/api/index.js src/tests
git commit -m "feat: 重做Couple Cosmos美食库与菜谱"
```

### Task 6: 整合投喂、回忆时间线和笔记

**Files:**
- Modify: `frontend-h5/src/views/feed/index.vue`
- Create: `frontend-h5/src/views/memories/index.vue`
- Create: `frontend-h5/src/views/memories/note-editor.vue`
- Create: `frontend-h5/src/views/memories/note-detail.vue`
- Modify: `frontend-h5/src/views/anniversary/index.vue`
- Modify: `frontend-h5/src/views/wish/index.vue`
- Modify: `frontend-h5/src/views/note/index.vue`
- Create: `frontend-h5/src/stores/feed.js`
- Create: `frontend-h5/src/stores/memories.js`
- Modify: `frontend-h5/src/api/index.js`
- Create: `frontend-h5/src/tests/stores/feed.spec.js`
- Create: `frontend-h5/src/tests/stores/memories.spec.js`
- Create: `frontend-h5/src/tests/views/memories.spec.js`

**Interfaces:**
- Produces feed state machine: `draft | sent | received | accepted | rejected | countered | completed`.
- Produces normalized timeline item: `{ id, type, occurredAt, creatorId, title, summary, media }`.

- [ ] **Step 1: 写 feed 状态机和时间线失败测试**

测试发起、接受、拒绝、替代、倒计时和完成。当前后端不支持的动作必须进入 `unavailable` 并保留用户输入，不得显示伪成功。

- [ ] **Step 2: 实现投喂 Store 和页面**

以 `feed.html` 正常业务态为主体；写操作有 pending/disabled，完成动画在 reduced motion 下改为静态成功反馈。

- [ ] **Step 3: 实现回忆聚合 Store**

并行请求 anniversary、wish、note 和 map footprint，使用 `Promise.allSettled`；任一来源失败只影响对应 filter/chip，时间线保留可用数据并显示局部重试。

- [ ] **Step 4: 实现回忆、笔记详情和编辑**

`memories.html` 对应聚合页，`note-editor.html` 对应新增/编辑；只读详情显示图片、正文、位置、关联菜谱和创建人。旧 `/anniversary`、`/wish`、`/note` 路由保留并重定向到 `/memories?type=...`。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/stores/feed.spec.js src/tests/stores/memories.spec.js src/tests/views/memories.spec.js
npm run build
git add src/views/feed src/views/memories src/views/anniversary src/views/wish src/views/note src/stores src/api/index.js src/tests
git commit -m "feat: 重做Couple Cosmos投喂与回忆"
```

### Task 7: 重做地图降级和完整 AI 对话

**Files:**
- Modify: `frontend-h5/src/views/map/index.vue`
- Modify: `frontend-h5/src/stores/map.js`
- Create: `frontend-h5/src/views/ai/index.vue`
- Modify: `frontend-h5/src/components/AiAssistantFab.vue`
- Modify: `frontend-h5/src/components/AiChatDrawer.vue`
- Modify: `frontend-h5/src/api/ai.js`
- Create: `frontend-h5/src/tests/views/map.spec.js`
- Create: `frontend-h5/src/tests/views/ai.spec.js`
- Create: `frontend-h5/src/tests/api/ai.spec.js`

**Interfaces:**
- Map view modes: `map | list`, with list always available.
- AI session states: `idle | streaming | interrupted | pending-confirmation | confirming | complete | error`.

- [ ] **Step 1: 写地图权限与 AI 中断失败测试**

地图覆盖 SDK 不可用、定位拒绝、无点位和详情 sheet。AI 覆盖 token 流、断线继续/重试、写操作预览、确认、拒绝和重复确认保护。

- [ ] **Step 2: 实现地图列表降级**

地图 SDK 不存在或权限拒绝时自动显示地点列表，不把空白画布当成功。BottomSheet 使用 button handle、焦点管理和 `Escape` 关闭。

- [ ] **Step 3: 实现 AI 完整页与抽屉共享会话**

抽屉上滑或显式按钮进入 `/ai`；消息与 pending action 抽到可复用 composable/store。业务写入前显示操作类型、字段 diff、影响对象和来源，只有用户确认后调用 confirm API。

- [ ] **Step 4: 结构化日志和敏感内容保护**

AI 日志只记录 session hash、stage、首 token 耗时、总耗时、取消原因和工具类型；不记录 prompt、回复正文或 pending payload。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/views/map.spec.js src/tests/views/ai.spec.js src/tests/api/ai.spec.js
npm run build
git add src/views/map src/views/ai src/stores/map.js src/components/AiAssistantFab.vue src/components/AiChatDrawer.vue src/api/ai.js src/tests
git commit -m "feat: 重做Couple Cosmos地图与AI对话"
```

### Task 8: 重做我们、通知和隐私数据权利

**Files:**
- Modify: `frontend-h5/src/views/settings/index.vue`
- Create: `frontend-h5/src/views/notification/index.vue`
- Create: `frontend-h5/src/views/legal/index.vue`
- Create: `frontend-h5/src/views/states/index.vue`
- Create: `frontend-h5/src/stores/theme.js`
- Create: `frontend-h5/src/stores/notification.js`
- Modify: `frontend-h5/src/api/index.js`
- Create: `frontend-h5/src/tests/views/settings.spec.js`
- Create: `frontend-h5/src/tests/views/notification.spec.js`
- Create: `frontend-h5/src/tests/views/legal.spec.js`

**Interfaces:**
- Produces notification filters: `all | interaction | system | ai`.
- Produces legal anchors: `privacy | terms | third-party | export | deletion | couple-data`.
- Produces theme preference: `cosmos | system-contrast`, never returning the old cream theme.

- [ ] **Step 1: 写设置、通知和法律状态失败测试**

覆盖资料更新、通知偏好、主题、退出、解绑不可提交政策、列表/已读/批量已读、隐私锚点、导出/注销入口和 unauthorized/unbound。

- [ ] **Step 2: 实现通知 Store 与 HTTP 行为**

通知列表支持分页和 filter；单条已读做乐观更新但失败回滚；批量已读只更新服务端确认的记录。无实时合同，不创建轮询定时器。

- [ ] **Step 3: 按 Stitch 重做设置、通知与隐私**

分别参考 `settings.html`、`notification-center.html`、`legal-privacy.html`。法律页不得保留 Stitch 原型中的 Normal/Loading/Error 开发切换按钮；状态由真实请求驱动。

- [ ] **Step 4: 实现全局状态展示路由**

`/states` 只在非生产环境注册，用于组件视觉回归；生产构建不得在导航或设置中暴露入口。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/views/settings.spec.js src/tests/views/notification.spec.js src/tests/views/legal.spec.js
npm run build
git add src/views/settings src/views/notification src/views/legal src/views/states src/stores src/api/index.js src/tests
git commit -m "feat: 重做Couple Cosmos我们与隐私中心"
```

### Task 9: 实现用户选定的星球首页

**Files:**
- Modify: `docs/design/stitch/couple-cosmos/README.md`
- Modify: `frontend-h5/src/views/home/index.vue`
- Create: `frontend-h5/src/stores/home.js`
- Create: `frontend-h5/src/components/home/CoupleOrbit.vue`
- Create: `frontend-h5/src/components/home/HomeBento.vue`
- Create: `frontend-h5/src/components/home/RollingCounter.vue`
- Create: `frontend-h5/src/tests/views/home.spec.js`
- Create: `frontend-h5/src/tests/components/home/CoupleOrbit.spec.js`

**Interfaces:**
- Consumes: exact `Selected home variant` from Stitch README.
- Produces independently retryable home resources: `couple`, `timer`, `anniversary`, `wish`, `feed`, `recipe`, `footprint`.

- [ ] **Step 1: 读取并验证首页选择**

Run:

```bash
rg '^Selected home variant: (home-emotion|home-food|home-memory)$' docs/design/stitch/couple-cosmos/README.md
```

Expected: exactly one match。若仍为 `none`，停止本 Task，不创建默认选择、不增加运行时 variant 开关。

- [ ] **Step 2: 写首页局部成功和动效失败测试**

每张卡独立显示 loading/success/error/retry；一个接口失败不得隐藏其余成功卡。轨道和数字滚动在 reduced motion 下输出静态最终值。

- [ ] **Step 3: 实现选定信息层级**

只实现 README 指定的一个方案；从对应 Stitch HTML 提取布局，不保留另外两个方案的死代码。双头像、恋爱天数、心情/在线、纪念日、心愿、投喂、菜谱、足迹和“今晚吃什么”均有真实路由或明确 unavailable。

- [ ] **Step 4: 验证 LCP 资源策略**

首页首图使用本地压缩资源、明确 width/height 和 `fetchpriority="high"`；其余图片 lazy。不得在首屏加载地图 SDK、完整 AI 模块或未选首页资源。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/views/home.spec.js src/tests/components/home
npm run build
git add ../docs/design/stitch/couple-cosmos/README.md src/views/home src/stores/home.js src/components/home src/tests
git commit -m "feat: 实现选定的Couple Cosmos首页"
```

### Task 10: 全量自动化、真实浏览器和视觉验收

**Files:**
- Create: `frontend-h5/playwright.config.js`
- Create: `frontend-h5/tests/e2e/fixtures/auth.js`
- Create: `frontend-h5/tests/e2e/cosmos-navigation.spec.js`
- Create: `frontend-h5/tests/e2e/cosmos-states.spec.js`
- Create: `frontend-h5/tests/e2e/cosmos-visual.spec.js`
- Create: `frontend-h5/tests/e2e/cosmos-ai.spec.js`
- Modify: `frontend-h5/package.json`
- Modify: `frontend-h5/vite.config.js`

**Interfaces:**
- Produces commands: `npm run test:e2e`, `npm run test:visual`.
- Produces screenshots for 375x812、390x844、430x932 and reduced-motion variants.

- [ ] **Step 1: 建立 Playwright 配置和 mock 合同 fixture**

Chromium 使用项目 Vite server；fixture 通过 `page.route('**/api/**')` 返回真实 `{ code, message, data }` 包装，并为每个测试断言无未处理请求。

- [ ] **Step 2: 覆盖五栏导航和核心状态**

测试每个 tab、详情返回、404、登录 redirect、未绑定 redirect、loading/empty/error/retry、离线草稿恢复和 reduced motion。

- [ ] **Step 3: 覆盖 AI 写入确认和关键表单**

测试 menu/recipe/note 表单草稿、AI pending preview 的确认/拒绝、重复提交保护、通知已读回滚和定位拒绝列表降级。

- [ ] **Step 4: 视觉对照**

对首页、绑定、菜单列表/详情、菜谱列表/详情/编辑、投喂、回忆、地图、AI、设置、通知、隐私分别保存三视口截图，并人工对照 `docs/design/stitch/couple-cosmos/screenshots/`。差异阈值只用于发现变化，不能替代人工检查正常业务态、溢出、重叠、图片和文案。

- [ ] **Step 5: 清零质量门槛**

Run:

```bash
cd frontend-h5
npm test -- --run
npm run build
npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs --ignore-path .gitignore
npm run assets:verify
npm run test:e2e
npm run test:visual
```

Expected: all commands exit 0；浏览器 console error 0；未处理失败网络请求 0。

- [ ] **Step 6: GitNexus 全范围检查并提交**

执行 `gitnexus_detect_changes({ scope: "all" })`，确认所有 d=1 依赖均已更新且没有未解释的执行流影响。

```bash
git add frontend-h5
git commit -m "test: 完成Couple Cosmos H5浏览器验收"
```

## Completion Evidence

本工作包只有在以下证据同时存在时完成：

1. Stitch README 已登记最终首页，H5 不包含未选首页死代码。
2. 20 个设计屏均有明确 Vue 路由、页面或非生产状态组件对应关系。
3. 五栏导航、所有正常态和六类异常/权限状态可在真实 Chromium 中操作。
4. Vitest、build、ESLint、资源 manifest、Playwright E2E 和视觉测试全部 exit 0。
5. 375px、390px、430px 及 reduced-motion 截图通过人工检查，无文字/控件重叠、空白主画布或外部图片失败。
6. 页面不直接拼 API URL，不直接处理 token，不包含 Stitch CDN、Google Fonts 或远程运行时图片。
7. 所有关键写操作有防重复、失败恢复和脱敏结构化日志。
8. FastAPI 相关未完成能力被明确标记为后端合同依赖，没有前端伪成功。
