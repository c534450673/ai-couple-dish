# 一次性修复清单（执行版）

> 目标：一次性收敛核心稳定性问题，减少后续返工。
> 范围：后端 `backend` + UniApp 前端 `frontend-uniapp`。

---

## 0. 修复目标（冻结标准）

- 认证链路统一（用户ID获取方式、未登录处理一致）
- 纪念日计算语义正确（当天、历史年份）
- 核心接口入参风格统一（减少 query 参数拼接）
- 上传与点赞等高风险点提升可靠性
- 具备最小可回归测试集合

---

## 1. P0（必须优先完成）

### P0-1 前端登录失效码兼容（401 / 9001）

**现象**
- 前端只识别 `code === 401`，后端常返回 `9001`（未登录）。

**根因**
- 前后端未统一“未登录/登录失效”业务码语义。

**修改文件**
- `frontend-uniapp/src/api/request.js`

**修改动作**
- 未登录分支改为：`code === 401 || code === 9001`。
- 统一执行：清 token / userInfo、跳登录页。

**验收标准**
- token 过期或无 token 时，任意受保护接口都能自动回登录页。

---

### P0-2 纪念日 nextDate 边界（当天被算到明年）

**现象**
- 当天纪念日被错误算作下一年，`daysUntil` 异常。

**根因**
- `calculateNextAnniversaryDate` 把 `isEqual(today)` 也当作过去。

**修改文件**
- `backend/src/main/java/com/aicoupledish/service/impl/AnniversaryServiceImpl.java`

**修改函数**
- `calculateNextAnniversaryDate(LocalDate anniversaryDate)`

**修改动作**
- 条件由 `isBefore(today) || isEqual(today)` 改为仅 `isBefore(today)`。

**验收标准**
- 当天纪念日 `daysUntil = 0`。

---

### P0-3 upcoming 语义按“下一次发生日”计算

**现象**
- 历史年份纪念日（如 2020-05-01）在今年未到时被遗漏。

**根因**
- 使用原始日期与 today 比较，而不是 nextDate。

**修改文件**
- `backend/src/main/java/com/aicoupledish/service/impl/AnniversaryServiceImpl.java`

**修改函数**
- `getUpcomingAnniversaries(Long userId)`

**修改动作**
- 去除 `anniversary_date >= today` 的原始日期过滤。
- 查询情侣全量纪念日后，按 `nextDate` 排序并返回。

**验收标准**
- 历史年份但“今年未到”的纪念日仍能出现在 upcoming。

---

### P0-4 Controller 认证获取方式全量收口

**现象**
- 部分控制器仍有手写 token 解析 / 重复 `getCurrentUserId`。

**根因**
- 历史代码风格不统一。

**修改文件（目录级）**
- `backend/src/main/java/com/aicoupledish/controller/*.java`

**修改动作**
- 删除控制器内重复 `getCurrentUserId`。
- 统一走 `BaseAuthController#getCurrentUserId(request, jwtUtils)`（或统一 `@RequestAttribute("userId")`，二选一）。
- 清理无用 import（如 `BusinessException`）。

**验收标准**
- 控制器层不再出现重复认证方法实现。
- 未登录行为与错误码一致。

---

## 2. P1（高优先级）

### P1-1 Wish 接口参数风格统一为 JSON Body

**现象**
- `wish/add`、`wish/update` 依赖 query 参数，前端需拼 `URLSearchParams`。

**修改文件**
- 后端：`backend/src/main/java/com/aicoupledish/controller/WishController.java`
- 后端新增 DTO：`backend/src/main/java/com/aicoupledish/domain/req/*`（如 `AddWishReq` / `UpdateWishReq`）
- 前端：`frontend-uniapp/src/api/index.js`

**修改动作**
- 接口改为 `@RequestBody`。
- 前端改为 body 传参。
- 可保留兼容期（旧 query 仍可用一版）。

**验收标准**
- Wish 模块不再依赖 query 拼参。

---

### P1-2 全局异常的 HTTP 语义增强（渐进）

**现象**
- 大量业务异常 HTTP 200，仅 body code 区分。

**修改文件**
- `backend/src/main/java/com/aicoupledish/common/exception/GlobalExceptionHandler.java`

**修改动作**
- 至少把“未登录/未授权”语义统一为 HTTP 401（body code 可保留兼容）。
- 参数错误保持 HTTP 400。

**验收标准**
- 未登录接口返回 401，前端/监控可感知。

---

### P1-3 上传安全增强（扩展名之外）

**现象**
- 上传仅校验扩展名，存在伪装文件风险。

**修改文件**
- `backend/src/main/java/com/aicoupledish/controller/UploadController.java`

**修改动作**
- 增加 MIME 白名单校验。
- 增加文件头（magic number）校验。
- 目录创建失败显式报错。

**验收标准**
- 非图片伪装文件被拒绝。

---

### P1-4 点赞幂等化（防重复点赞）

**现象**
- 同用户可重复点赞导致计数膨胀。

**修改文件（建议）**
- Service：`backend/src/main/java/com/aicoupledish/service/impl/NoteServiceImpl.java`
- DAO/Model/Migration：新增 `note_like`（或等价）关系表与唯一索引 `(user_id, note_id)`

**修改动作**
- `like`：先插关系，成功再 +1。
- `unlike`：删关系成功再 -1。

**验收标准**
- 同用户重复点赞不增加计数。

---

## 3. P2（可维护性优化）

### P2-1 可选依赖治理

**问题**
- `@Autowired(required = false)` 分散，行为不透明。

**动作**
- 必需依赖改构造注入；可选能力改配置开关。

---

### P2-2 DTO 映射抽离

**问题**
- Service 中映射逻辑膨胀、重复。

**动作**
- 抽 mapper 组件（手写或 MapStruct）。

---

### P2-3 前端错误分级

**问题**
- 网络/鉴权/业务错误提示同质化。

**动作**
- request 层区分 `auth / network / validation / business`。

---

## 4. 建议执行顺序（一次性实施）

1. `frontend-uniapp/src/api/request.js`（401/9001）
2. `AnniversaryServiceImpl`（nextDate + upcoming）
3. Controller 认证全量收口
4. Wish 入参统一 body（后端 DTO + 前端 API）
5. 异常语义增强（至少 auth=401）
6. 上传安全增强
7. 点赞幂等（涉及 DB 变更）

---

## 5. 最小回归测试清单

- 未登录访问：`/menu/list`、`/anniversary/list`、`/wish/list`
- token 失效自动跳登录（前端）
- 纪念日：当天 `daysUntil=0`；历史年份未来日期能进 upcoming
- Wish 新增/更新（body 传参）
- 上传合法图片成功、伪装文件失败
- 点赞重复请求幂等（若做）

---

## 6. 备注

- 本文是执行清单，不涉及详细代码 diff。
- 建议每完成一个 P0 项目就做一次小回归，避免尾部集中爆雷。
