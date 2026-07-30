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

