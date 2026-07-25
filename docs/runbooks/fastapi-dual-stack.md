# FastAPI 双栈基础设施运行手册

本文只描述迁移期基础设施。Java `backend/Dockerfile` 和 Spring Boot 仍是 193 条业务
route 的唯一业务写者；`backend/Dockerfile.fastapi` 只提供 FastAPI 基础 health route，
不表示后端迁移完成。H5 继续使用同源相对 `/api`，浏览器不直接访问 FastAPI 端口。

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
`GET /api/actuator/health` 是 FastAPI 基础 route；业务 `/api/**` 仍由 Spring 处理。

## 双栈 Compose

Task11 的项目名和端口示例必须保持唯一，避免干扰共享服务。可用一个临时项目名和未占用
的 Nginx 端口运行：

```bash
cd deploy/dev/docker
PROJECT_NAME='fastapi-foundation-qa' NGINX_PORT='<inject-at-runtime>' \
  JWT_SECRET='<inject-at-runtime>' \
  docker compose -f docker-compose.yml -f docker-compose.fastapi.yml config --quiet
PROJECT_NAME='fastapi-foundation-qa' NGINX_PORT='<inject-at-runtime>' \
  JWT_SECRET='<inject-at-runtime>' \
  docker compose -f docker-compose.yml -f docker-compose.fastapi.yml up -d --build
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
   执行 `bash backend/scripts/verify_fastapi_foundation.sh` 或仅运行 verifier 做只读校验。
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

切流只替换 Nginx conf 挂载文件，保留 Spring 容器和共享数据。回滚时恢复上一份已审计的
`api.conf`，先做语法检查，再 reload；不要编辑 compose 中的业务 writer：

```bash
docker compose -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -t
docker compose -f docker-compose.yml -f docker-compose.fastapi.yml exec nginx nginx -s reload
```

发生错误时把 `api-fastapi-foundation.conf` 替换为已签名的 Spring-only 单文件，执行同样的
`nginx -t` 和 reload。切流前后保留 request ID、状态和耗时等脱敏证据。

## 清理与上传风险

只停止本次项目的服务和临时容器，不删除共享 volume：

```bash
docker compose -p fastapi-foundation-qa -f docker-compose.yml \
  -f docker-compose.fastapi.yml down --remove-orphans
docker rm -f '<inject-at-runtime>'
```

第二条仅用于明确列出的临时容器 ID；不要使用宽泛 glob，不要执行 `down -v`，不要删除
`mysql_data`、`redis_data`、`uploads_data` 或其他共享 volume。生产上传不能使用本地
`emptyDir`：节点重建或漂移会丢失文件，必须使用持久化对象存储/受管卷并单独审计访问权限。

未来切流 `/api/ai/chat/stream` 时，Nginx location 必须设置 `proxy_buffering off`，并
验证断线、超时和回滚；本基础阶段不添加该业务代理例外。
