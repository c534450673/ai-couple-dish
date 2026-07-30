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

