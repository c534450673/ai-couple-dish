# Spring / H5 迁移合同基线

本目录冻结 FastAPI 兼容迁移所需的 Spring 路由、H5 消费者、错误码和 Redis key
命名。它描述当前可观察合同，不表示任何业务已经迁移。

## 来源与计数

- 生成时间：2026-07-25 23:36:53（Asia/Shanghai）。
- Spring commit：`efa0c99ffd06ad13c928b128327b37b5addf66aa`。
- Spring 运行时来源：`http://127.0.0.1:8080/api/v2/api-docs`，HTTP 200，Swagger
  2.0。`/api/v3/api-docs` 在当前鉴权配置下返回 HTTP 401，因此不是本次导出源。
- `spring-openapi.json`：192 个 path；仅保留 schema 文档，不执行业务请求，也不保存
  Spring 响应正文。
- Swagger 中 GET/POST/PUT/DELETE/PATCH 共 198 个 operation；`routes.json` 为 27 个业务
  Controller 的 193 个 operation，`method + path` 唯一。
- `h5-consumers.json`：当前源码中 74 个 Axios 调用和 4 个 AI fetch，共 78 个消费者。
- `error-codes.json`：60 个可观察错误码；`redis-keys.json`：8 个 pattern。

## OpenAPI 规范化与静态对账

导出器同时接受 Swagger 2 和 OpenAPI 3。规范化会递归稳定排序、统一末尾换行，删除
`host`、`basePath`、`schemes`、`servers` 及 operation 中仅代表部署环境的 forwarding
header 参数。每个目标文件先写入同目录临时文件、flush/fsync，再以 `os.replace` 原子替换。

198 到 193 的差异不是截断，而是按 tag `basic-error-controller` 显式排除 Spring 自动注册的
`/api/error` 框架入口：

| Method | Operation ID | 原因 |
|---|---|---|
| GET | `errorUsingGET` | Spring 框架错误分派，不属于业务 Controller |
| POST | `errorUsingPOST` | Spring 框架错误分派，不属于业务 Controller |
| PUT | `errorUsingPUT` | Spring 框架错误分派，不属于业务 Controller |
| DELETE | `errorUsingDELETE` | Spring 框架错误分派，不属于业务 Controller |
| PATCH | `errorUsingPATCH` | Spring 框架错误分派，不属于业务 Controller |

其余 193 条按 Controller 静态盘点逐模块计数完全一致，本次静态补齐数为 0。后续若运行时
文档漏掉业务 route，必须以具体 Java Controller 文件和 mapping 注解为来源增加显式补齐项，
在本节逐项记录 method、path、Controller、源文件和缺失原因；不得伪造计数或按数量截断。

## 路由字段判定

`controller` 按 `/api` 后的首段映射至 27 个 Java Controller。`migrationBatch` 固定为：

- 批次 1：user、couple。
- 批次 2：menu、recipe、note、feed、anniversary、wish、notification、upload。
- 批次 3：ai。
- 批次 4：dailyGreeting、dailyTask、mood、sweetBomb、deepQa、challenge、coupleTree、
  relationshipWeather、heartMoment、loveCalendar、coupleRank。
- 批次 5：cart、order、invite、poster、timeCapsule；定时任务沿用批次 5，但没有 HTTP route。

`sideEffect` 对非 GET 为 true。GET 不按方法名盲猜：静态追踪 service 后，以下接口会惰性创建
记录或更新状态，显式为 true：`coupleRank/info`、`coupleRank/rewards`、`coupleTree/info`、
`coupleTree/skins`、`dailyTask/today`、`deepQa/current`、`deepQa/progress`、`invite/code`、
`relationshipWeather/current`、`relationshipWeather/suggestions`、`relationshipWeather/forecast`。
其余 GET 当前只读；普通数据库/Redis 读取不单独视为副作用。

所有 route 初始 `owner="spring"`。只有对应 FastAPI 路由通过 method/path、请求位置、响应外壳、
错误码、副作用合同和真实集成门禁后，才能登记到 `migration-ownership.json`。导出器会从同目录
读取该清单并事务式合并 owner，未知路由或无效清单会中止导出，因此重新导出不会静默撤销已批准
切流。当前用户、情侣、通知和心愿共 32 条 route 为 FastAPI owner，其余 161 条仍为 Spring。
不要直接手改生成的 `routes.json`，也不要用 owner 变更宣称全部业务已经迁移。

## H5 规格纠偏

批准计划依据旧盘点，计数是 54 个 Axios + 4 个 AI + 1 个菜谱 direct fetch = 59。当前源码已
发生可验证重构：`recipeApi` 14 个导出、情侣码 2 个导出、菜单 unlike/unfavorite 2 个导出已进入
`frontend-h5/src/api/index.js`；旧的菜谱 direct fetch 已由 store/API 层替代。净结果是 72 个
Axios + 4 个 AI fetch = 76，本合同以当前源码为权威，不保留不存在的 direct consumer。

每项记录 `sourceFile`、`exportName`、`functionName`、`sourceLine`、transport、method、path 和
path/query/body/multipart 参数位置。模板路径以 H5 函数参数名表示，例如 `{id}`；它与 Spring
中的 `{recipeId}` 在线协议上是同一位置参数。

## 错误码、Redis 与敏感信息

一般业务错误维持 HTTP 200；400/401/429 与用户未登录 1003 保持当前 HTTP 状态。9001-9005
存在跨模块重复语义，已逐项保存在 `ambiguousUsages`，不得静默重编号。Redis 文件只保存
占位 pattern 和 TTL 语义，不保存任何运行时值。

合同、测试、日志和错误信息严禁写入 URL query、Spring 响应正文、JWT、验证码、完整手机号、
真实情侣码、Stitch key、AI key 或其他密钥。导出日志只记录去 query 的来源、HTTP 状态、字节数、
path/route 计数和目标文件名。

## 重新导出

```bash
cd backend
uv run python scripts/export_spring_contract.py \
  --url http://127.0.0.1:8080/api/v2/api-docs \
  --output contracts/spring-openapi.json \
  --routes contracts/routes.json
uv run pytest tests/contract/test_export_spring_contract.py -q
```
