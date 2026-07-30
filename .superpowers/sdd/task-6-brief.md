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

