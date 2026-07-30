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

