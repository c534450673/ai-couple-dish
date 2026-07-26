# FastAPI 双栈基础设施运行手册

本文只描述迁移期基础设施。Java `backend/Dockerfile` 和 Spring Boot 仍是未切流业务
route 的唯一写者；当前用户、情侣、通知、心愿、心动瞬间、情侣挑战、心情和时光胶囊共 59 条 HTTP route 已由 FastAPI 接管，
其余业务 route 仍由 Spring 处理。`backend/Dockerfile.fastapi` 提供 FastAPI 业务与基础
health route。H5 继续使用同源相对 `/api`，浏览器不直接访问 FastAPI 端口。

## 前置条件

- Python 3.12、`uv` 0.11.21、Docker Compose v2、Java 17、Maven。
- MySQL 8 和 Redis 7；本地服务启动方式见 [ENVIRONMENT.md](../ENVIRONMENT.md)。
- 仅在隔离 QA 数据库执行 schema capture、verify 或 stamp。凭据、JWT 和令牌必须由
  密钥管理器或 CI secret 在运行时注入，文档只保留 `<inject-at-runtime>` 占位符。

示例环境变量（值必须在 shell 外部注入，不要写入仓库或日志）：

```bash
export DB_HOST='<inject-at-runtime>'
export DB_PORT='<inject-at-runtime>'
export DB_NAME='<inject-at-runtime>'
export DB_USERNAME='<inject-at-runtime>'
export DB_PASSWORD='<inject-at-runtime>'
export REDIS_HOST='<inject-at-runtime>'
export REDIS_PORT='<inject-at-runtime>'
export REDIS_PASSWORD='<inject-at-runtime>'
export JWT_SECRET='<inject-at-runtime>'
export SCHEMA_DATABASE_URL='<inject-at-runtime>'
export SCHEMA_DATABASE_ISOLATED=true
```

## 本地 FastAPI

在 `backend/` 执行以下命令。`DB_PASSWORD`、`JWT_SECRET` 和 `SCHEMA_DATABASE_URL` 不要回显：

```bash
uv sync --frozen
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

只读检查：`GET /api/health/live`、`GET /api/health/ready` 和
`GET /api/actuator/health` 是 FastAPI 基础 route。已切流的 `/api/user/**`、
`/api/couple/**`、`/api/notification/**`、`/api/wish/**`、`/api/heartMoment/**`、`/api/challenge/**`、`/api/mood/**` 和 `/api/timeCapsule/**` 合同 route 由 FastAPI 提供，其余 `/api/**`
仍由 Spring 处理；权威清单见 `backend/contracts/migration-ownership.json`。

## HTTP 切流与回滚

当前启用 `user-couple-notification-v1`、`wish-v1`、`heart-moment-v1`、`challenge-v1`、`mood-v1` 和 `time-capsule-v1` 六个 HTTP 切流批次，覆盖用户 7 条、
情侣 13 条、通知 5 条、心愿 7 条、心动瞬间 4 条、情侣挑战 9 条、心情 8 条和时光胶囊 6 条，共 59 条合同 route。Nginx 使用十二个精确正则 location 将已登记路径转发到
`fastapi_backend`，未知路径仍落到 Spring 的通用 `/api/` location。配置校验必须确认：

- `routes.json` 中这 59 条的 owner 为 `fastapi`，其余 134 条仍为 `spring`；
- FastAPI/真实 MySQL/Redis 集成门禁、合同 owner 检查和 Nginx 配置检查全部通过；
- 六个启用批次的 `rollbackOwner` 均保持为 `spring`。

回滚时按批次回退同一个 Nginx 配置提交，先执行 `nginx -t` 再 reload；不要同时修改数据库、
Redis 或 Java 业务代码。回滚后重新运行 owner 检查，确认目标批次路径回到 Spring，再停止
对应 FastAPI 批次。任何校验失败都保留当前配置和备份，不 reload 未通过语法检查的文件。

## 双栈 Compose

Task11 的项目名和端口示例必须保持唯一，避免干扰共享服务。可用一个临时项目名和未占用
的 Nginx 端口运行：

```bash
cd deploy/dev/docker
PROJECT_NAME='fastapi-foundation-qa' NGINX_PORT='<inject-at-runtime>' \
  JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml config --quiet
PROJECT_NAME='fastapi-foundation-qa' NGINX_PORT='<inject-at-runtime>' \
  JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml up -d --build
```

合并配置中 FastAPI 只 `expose` 8000，不发布浏览器端口。Nginx 的三个 exact location
转发到 FastAPI；通用 `location /api/` 固定转发到 `spring_backend`。Task11 的真实
双栈启动曾因 Maven/Eclipse Temurin 镜像网络超时而无法完成；重试前配置组织代理或
预热镜像，不能把 Compose config 通过写成运行时通过。

## Spring 合同导出

在 Spring 实例可访问且已完成认证配置的隔离环境运行；导出日志只保留状态、计数和目标文件名：

```bash
cd backend
uv run python scripts/export_spring_contract.py \
  --url '<inject-at-runtime>' \
  --output contracts/spring-openapi.json \
  --routes contracts/routes.json
uv run pytest tests/contract/test_export_spring_contract.py -q
```

当前来源是 Spring Swagger v2 `/api/v2/api-docs`；`/api/v3/api-docs` 在现有鉴权配置下
可能返回未授权。路由清单必须仍为 193 条，业务 owner 默认是 Spring。

## Schema 审计、验证与 stamp

1. 在隔离 MySQL 8 capture 快照，审阅 JSON 与 SHA-256，再通过代码审查批准 canonical
   文件。capture 不执行迁移，也不连接生产：

   ```bash
   cd backend
   SCHEMA_DATABASE_URL='<inject-at-runtime>' SCHEMA_DATABASE_ISOLATED=true \
     uv run python scripts/capture_mysql_schema.py \
       --output contracts/mysql-schema.json --sha256 contracts/mysql-schema.sha256
   ```

2. 设置 `SCHEMA_DATABASE_URL=<inject-at-runtime>` 和 `SCHEMA_DATABASE_ISOLATED=true`，
   在当前 `backend/` 工作目录执行 `bash scripts/verify_fastapi_foundation.sh`，或仅运行
   verifier 做只读校验。
3. `--stamp` 只允许 canonical snapshot、匹配的 canonical hash，以及已登记的隔离数据库。
   stamp 前必须有 owner 审批、备份记录和回滚计划；生产库、未知 DSN、临时副本均拒绝。
   人工 stamp 前先确认隔离门禁，再运行：

   ```bash
   test "${SCHEMA_DATABASE_ISOLATED:-}" = true
   SCHEMA_DATABASE_URL='<inject-at-runtime>' \
     uv run python scripts/verify_mysql_schema.py --stamp
   ```
4. drift 时保留审计输出，停止发布；从备份恢复并重新 capture/verify，不能用脚本自动加载
   `schema.sql` 或隐式迁移。

```bash
cd backend
SCHEMA_DATABASE_URL='<inject-at-runtime>' SCHEMA_DATABASE_ISOLATED=true \
  uv run python scripts/verify_mysql_schema.py
```

## 合同比较

`compare_backends` 的 foundation fixture 固定 7 个 case：4 个 FastAPI 基础/unknown
检查、3 个 testApp case（跳过外部服务）。当前 193 条 Spring 业务 route 全部 skipped；
业务写入 case 在基础阶段必须被拒绝，不得为了比较而写库。只有明确 owner、隔离数据库和
变更审批后，未来迁移 route 才能启用双端比较。

```bash
cd backend
SPRING_BASE_URL='<inject-at-runtime>' FASTAPI_BASE_URL='<inject-at-runtime>' \
  uv run python scripts/compare_backends.py
```

输出仅包含 case 计数、HTTP 状态、业务 code 和差异路径；不要把 Authorization、请求 body、
响应正文、手机号、原始 IP 或完整 URL 写入终端或日志。

## Owner 变更流程

新增 FastAPI owner 前，先更新 Java Controller/Swagger 导出、`routes.json` 和 owner 审计记录，
补齐请求/响应/错误码/副作用合同与隔离测试。由模块 owner、平台 owner 和安全 reviewer 审批，
再更新 Nginx 精确 location 和回滚文件。未完成这些证据时，保持 `owner=spring`，不以代码数量
或 health route 宣称业务已迁移。

## Nginx 单文件回滚

切流只替换 Nginx 实际 bind mount 源文件
`nginx/conf.d/api-fastapi-foundation.conf`，保留 Spring 容器和共享数据。先备份当前文件，
用 `sed` 仅替换三个 FastAPI `proxy_pass`，写入同目录临时文件并原子替换：

```bash
cd deploy/dev/docker
source_file='nginx/conf.d/api-fastapi-foundation.conf'
backup_file='nginx/conf.d/api-fastapi-foundation.conf.fastapi.bak'
temporary_file='nginx/conf.d/.api-fastapi-foundation.conf.spring.tmp'
cp -- "$source_file" "$backup_file"
sed 's#proxy_pass http://fastapi_backend;#proxy_pass http://spring_backend;#g' \
  "$source_file" > "$temporary_file"
test "$(grep -c 'proxy_pass http://fastapi_backend;' "$temporary_file")" -eq 0
test "$(grep -c 'proxy_pass http://spring_backend;' "$temporary_file")" -eq 4
mv -- "$temporary_file" "$source_file"
PROJECT_NAME='fastapi-foundation-qa' JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -t
PROJECT_NAME='fastapi-foundation-qa' JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -s reload
```

需要恢复 FastAPI health 切流时，把备份经同目录临时文件原子恢复，再执行语法检查和 reload：

```bash
cp -- "$backup_file" "$temporary_file"
mv -- "$temporary_file" "$source_file"
PROJECT_NAME='fastapi-foundation-qa' JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -t
PROJECT_NAME='fastapi-foundation-qa' JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa \
    -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -s reload
```

任一步失败都保留备份，不 reload 未通过 `nginx -t` 的配置。切流前后只保留 request ID、
状态和耗时等脱敏证据。

## Poster orphan 清理

清理命令只维护 FastAPI 海报持久卷中的原子发布临时文件和孤立 PNG，不改变 route owner，
也不表示生产 Spring 海报写入已经切换到 FastAPI。唯一受支持的入口是在 `backend/` 工作目录
通过 Python module 运行；不要直接执行 `scripts/cleanup_poster_orphans.py`：

```bash
cd backend
uv run python -m scripts.cleanup_poster_orphans --help
```

命令默认只执行 dry-run，年龄阈值默认 24 小时，不删除文件。先用运行时注入的数据库、上传目录
和公开路径配置观察候选计数：

```bash
cd backend
uv run python -m scripts.cleanup_poster_orphans
```

确认备份可恢复、容量和 inode 正常、数据库 active URL 查询可用，并审阅 dry-run 的
`scanned`、`temp`、`final`、`refused`、`errors` 计数。候选数或失败数异常增长时停止，不执行
删除；先排查渲染失败、数据库提交失败、卷挂载、权限、磁盘容量和 scheduler 重复运行。

只有在 dry-run 计数已观察、备份和恢复步骤已验证且操作获批后，才显式传入 `--apply`：

```bash
cd backend
uv run python -m scripts.cleanup_poster_orphans --apply
```

执行后再次运行 dry-run，确认候选数回落且 `errors=0`。不要把 dry-run 省略 `--apply` 的输出
当成已经删除，也不要自动重试持续失败的 apply；失败时保留卷快照和审计记录，先恢复容量、权限
或数据库可用性。

建议由 daily scheduler（如受管 CronJob）每天运行一次 dry-run；apply 是否自动化须单独审批，
并保留互斥、超时和失败告警。至少监控 scheduler 成功率与耗时、卷容量/inode、`temp`/`final`
orphan 趋势、`refused`/`errors` 计数，以及 `CLEANUP_FAILED`、`FILESYSTEM_ERRORS`。备份保留期
必须覆盖默认 24 小时清理窗口，并定期验证恢复，脚本自身不提供恢复能力。

删除只移除当前持久卷中的文件，不能撤回浏览器、CDN、代理或客户端已缓存的副本。Poster 静态
响应当前使用短期 public cache，owner delete 和 cleanup 都不能承诺公开 URL 立即全网失效；涉及
敏感内容时应先执行缓存处置和事件响应流程，再评估文件删除。

## 清理与上传风险

只停止本次项目的服务和临时容器，不删除共享 volume：

```bash
PROJECT_NAME='fastapi-foundation-qa' JWT_SECRET='<inject-at-runtime>' \
  docker compose -p fastapi-foundation-qa -f docker-compose.yml \
    -f docker-compose.fastapi.yml down --remove-orphans
docker rm -f '<inject-at-runtime>'
```

第二条仅用于明确列出的临时容器 ID；不要使用宽泛 glob，不要执行 `down -v`，不要删除
`mysql_data`、`redis_data`、`uploads_data` 或其他共享 volume。生产上传不能使用本地
`emptyDir`：节点重建或漂移会丢失文件，必须使用持久化对象存储/受管卷并单独审计访问权限。

未来切流 `/api/ai/chat/stream` 时，Nginx location 必须设置 `proxy_buffering off`，并
验证断线、超时和回滚；本基础阶段不添加该业务代理例外。

## CoupleCodeTask shadow worker

Spring `CoupleCodeTask.checkExpiration` 仍是默认唯一 writer。FastAPI 的情侣码过期提醒是
默认关闭的 shadow worker，不属于 HTTP 路由，也绝不能挂入 Uvicorn/Gunicorn lifespan。它只有
一个受支持入口，受管 CronJob 每小时一次、使用 `Asia/Shanghai` 作为业务时区：

```bash
cd backend
FASTAPI_SCHEDULER_ENABLED=true uv run python -m scripts.run_couple_code_reminder
```

未显式设置 `FASTAPI_SCHEDULER_ENABLED=true` 时命令会以非零状态退出且不会连接数据库或 Redis。
生产切换前必须获得 owner 审批，先禁用 Spring 对应任务、确认只有一个受管 worker、检查 Redis
run lock 与 HMAC marker、备份并验证回滚。回滚时先停止 FastAPI CronJob，再恢复 Spring 任务；
禁止两个 writer 同时运行。worker 日志只保留 requestId、模块、操作、结果、耗时和错误码，不能
记录情侣码、Redis key、用户 ID、通知文案或原始异常。

Anniversary、DailyGreeting、DailyTask 和 Feed expiry 仍有其各自的多 writer 风险；本 worker
不迁移或接管这些任务。

## Feed expiry shadow worker

Spring `FeedExpireTask` 仍是默认唯一 writer。FastAPI worker 默认关闭，绝不能在 Web lifespan 启动；仅由单个受管 CronJob 每十分钟一次调用：

```bash
cd backend
FASTAPI_FEED_EXPIRY_ENABLED=true uv run python -m scripts.run_feed_expiry
```

切换前先禁用 Spring task，并获得单 CronJob、监控和回滚批准。还必须先将 Feed mutation HTTP owner 切到 FastAPI，或批准 Spring mutation 改为行锁/`status=0` 条件更新；否则跨栈 accept/reject 与 worker 不线性化。回滚时先停止 FastAPI CronJob，再恢复 Spring task。禁止双写。
