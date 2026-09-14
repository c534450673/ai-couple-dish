#!/usr/bin/env bash
set -Eeuo pipefail

# 最小联调门禁：校验合并配置、启动完整 Python 服务组、检查八个容器健康
# 状态和 Nginx 同源 gateway 路由。日志只输出服务名、状态和耗时，不打印令牌。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.python.yml"
PROJECT_NAME="${PROJECT_NAME:-ai-couple-dish-python-smoke}"
COMPOSE=(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE")
STARTED=0

log() {
  printf 'event=python_compose_smoke_%s project=%s\n' "$1" "$PROJECT_NAME"
}

cleanup() {
  if [[ "$STARTED" == 1 && "${KEEP_SMOKE_STACK:-0}" != 1 ]]; then
    log cleanup_started
    "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
    log cleanup_completed
  fi
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "docker 命令不可用" >&2
  exit 127
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 不可用" >&2
  exit 127
fi

if [[ -z "${JWT_SECRET:-}" || ${#JWT_SECRET} -lt 64 ]]; then
  echo "JWT_SECRET 必须由运行环境注入且至少64字符" >&2
  exit 2
fi
if [[ -z "${ADMIN_JWT_SECRET:-}" || ${#ADMIN_JWT_SECRET} -lt 64 ]]; then
  echo "ADMIN_JWT_SECRET 必须由运行环境注入且至少64字符" >&2
  exit 2
fi
if [[ -z "${ADMIN_PASSWORD_HASH:-}" ]]; then
  echo "ADMIN_PASSWORD_HASH 必须由运行环境注入" >&2
  exit 2
fi

if [[ -n "${HTTP_PROXY:-}" || -n "${HTTPS_PROXY:-}" || -n "${ALL_PROXY:-}" ]]; then
  log proxy_detected
elif [[ "$(curl -sS --max-time 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:7892 2>/dev/null || true)" != 000 ]]; then
  export HTTP_PROXY="http://127.0.0.1:7892" HTTPS_PROXY="http://127.0.0.1:7892"
  log local_proxy_enabled
else
  log direct_network
fi

log config_started
"${COMPOSE[@]}" config --quiet
log config_completed

log startup_started
STARTED=1
"${COMPOSE[@]}" up -d --build
log startup_completed

for service in gateway identity catalog dining media admin analytics worker; do
  log "health_check_started service=${service}"
  container_id="$("${COMPOSE[@]}" ps -q "$service")"
  if [[ -z "$container_id" ]]; then
    echo "服务 ${service} 未创建容器" >&2
    exit 1
  fi
  health_status="starting"
  for _attempt in {1..60}; do
    health_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_id")"
    [[ "$health_status" == healthy ]] && break
    if [[ "$health_status" == unhealthy || "$health_status" == no-healthcheck ]]; then
      echo "服务 ${service} 健康检查失败: ${health_status}" >&2
      exit 1
    fi
    sleep 1
  done
  if [[ "$health_status" != healthy ]]; then
    echo "服务 ${service} 健康检查超时: ${health_status}" >&2
    exit 1
  fi
  log "health_check_completed service=${service} result=${health_status}"
done

port="${NGINX_PORT:-80}"
log http_smoke_started
response="$(curl -fsS --max-time 10 "http://127.0.0.1:${port}/api/health/live")"
case "$response" in
  *'"code":200'*|*'"status":"UP"'*|*'"status":"ok"'*) ;;
  *)
    echo "gateway health 响应不符合预期" >&2
    exit 1
    ;;
esac
log http_smoke_completed result=success
