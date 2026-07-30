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
- Produces: `userStore.login(credentials)` and `userStore.register(profile)` returning `{ status: 'unavailable', reason: 'PASSWORD_AUTH_NOT_SUPPORTED' }` without issuing a request until the backend exposes a password contract.
- Preserves: redirect query restoration.
- Produces binding modes: `invite | enter-code`.
- Produces: `coupleApi.getCodeInfo()` and `coupleApi.refreshCode()` using the existing Java contracts; invite codes are exactly 8 characters and expire after 7 days.

- [ ] **Step 1: 写密码登录和绑定失败测试**

登录测试必须证明：没有微信/Apple/验证码入口；字段旁显示错误；提交中按钮 disabled；密码能力 unavailable 时不发网络请求、不写 token/localStorage、不跳转。绑定测试必须证明：生成码、复制、重新生成、输入 8 位码、7 天有效期进度和错误恢复可操作。

- [ ] **Step 2: 对齐认证 API 模块**

当前 Java 的 `/user/register` 与 `/user/phoneLogin` 都只接受 `{ phone, verifyCode }`，不存在密码字段、哈希或认证逻辑。Task 4 不新增伪密码 API 映射；`userStore.login/register` 必须返回固定 unavailable 结果，UI 显示“密码登录/注册暂不可用，当前服务端未提供该认证能力”，不得回退到短信、微信或将密码当验证码。现有 legacy API 方法可为未迁移调用方保留，但新 UI 不调用。

绑定使用实际合同：`POST /couple/generateCode`、`GET /couple/codeInfo`、`POST /couple/refreshCode`、`POST /couple/bind`。`generateCode` 对有效旧码幂等；“重新生成”必须调用 `refreshCode`，并在确认文案中说明服务端会将恋爱开始日重置为当天，不得伪装为无副作用刷新。

- [ ] **Step 3: 按 Stitch 重做登录与绑定**

登录以 `login.png` 为视觉参考；绑定以 `bind.html` 为结构参考。绑定成功动画通过独立 CSS class 触发，减弱动效下直接显示完成态。

登录或绑定恢复 `redirect` 时只接受单个 `/` 开头且不以 `//` 开头、并能被当前 Router 解析的站内路径；外部 URL、协议相对 URL、未知路由和空值回退 `/home`。绑定成功必须先持久化 `coupleInfo`，再执行重定向。

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

