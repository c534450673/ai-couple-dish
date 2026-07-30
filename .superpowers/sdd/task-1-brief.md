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

