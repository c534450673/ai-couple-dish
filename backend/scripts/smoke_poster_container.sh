#!/usr/bin/env bash
set -Eeuo pipefail

smoke_started=${SECONDS}
current_operation="preflight"
operation_started=${SECONDS}
image_name=""
volume_name=""
container_one=""
container_two=""
work_dir=""
first_download=""
second_download=""

log_event() {
  local event="$1"
  local operation="$2"
  local result="$3"
  local duration_ms="$4"
  local error_code="${5:-}"
  printf '{"event":"%s","module":"poster_container_smoke","operation":"%s",' \
    "$event" "$operation" >&2
  printf '"result":"%s","durationMs":%s' "$result" "$duration_ms" >&2
  if [[ -n "$error_code" ]]; then
    printf ',"errorCode":"%s"' "$error_code" >&2
  fi
  printf '}\n' >&2
}

log_evidence() {
  local image_sha="$1"
  local poster_url="$2"
  local download_sha="$3"
  printf '{"event":"poster_container_evidence","module":"poster_container_smoke",' >&2
  printf '"operation":"persistence","result":"passed","durationMs":0,' >&2
  printf '"imageSha":"%s","posterUrl":"%s","downloadSha":"%s"}\n' \
    "$image_sha" "$poster_url" "$download_sha" >&2
}

fail() {
  local error_code="$1"
  log_event "poster_container_smoke_failed" "$current_operation" "failed" \
    "$(( (SECONDS - operation_started) * 1000 ))" "$error_code"
  exit 1
}

on_error() {
  local exit_code="$?"
  trap - ERR
  log_event "poster_container_step_completed" "$current_operation" "failed" \
    "$(( (SECONDS - operation_started) * 1000 ))" "command_failed"
  exit "$exit_code"
}

cleanup() {
  local exit_code="$?"
  local cleanup_failed=0
  local cleanup_started=${SECONDS}
  set +e

  for container_name in "$container_one" "$container_two"; do
    if [[ -n "$container_name" ]] \
      && docker container inspect "$container_name" >/dev/null 2>&1 \
      && ! docker rm --force "$container_name" >/dev/null 2>&1; then
      cleanup_failed=1
    fi
  done
  if [[ -n "$volume_name" ]] \
    && docker volume inspect "$volume_name" >/dev/null 2>&1 \
    && ! docker volume rm "$volume_name" >/dev/null 2>&1; then
    cleanup_failed=1
  fi
  if [[ -n "$image_name" ]] \
    && docker image inspect "$image_name" >/dev/null 2>&1 \
    && ! docker image rm "$image_name" >/dev/null 2>&1; then
    cleanup_failed=1
  fi
  if [[ -n "$first_download" ]] && ! rm -f -- "$first_download"; then
    cleanup_failed=1
  fi
  if [[ -n "$second_download" ]] && ! rm -f -- "$second_download"; then
    cleanup_failed=1
  fi
  if [[ -n "$work_dir" && -d "$work_dir" ]] && ! rmdir -- "$work_dir"; then
    cleanup_failed=1
  fi

  if (( cleanup_failed != 0 )); then
    log_event "poster_container_cleanup_completed" "cleanup" "failed" \
      "$(( (SECONDS - cleanup_started) * 1000 ))" "cleanup_failed"
    if (( exit_code == 0 )); then
      exit_code=1
    fi
  else
    log_event "poster_container_cleanup_completed" "cleanup" "passed" \
      "$(( (SECONDS - cleanup_started) * 1000 ))"
  fi
  trap - EXIT
  exit "$exit_code"
}

run_step() {
  local operation="$1"
  shift
  current_operation="$operation"
  operation_started=${SECONDS}
  log_event "poster_container_step_started" "$operation" "started" 0
  "$@"
  log_event "poster_container_step_completed" "$operation" "passed" \
    "$(( (SECONDS - operation_started) * 1000 ))"
}

check_prerequisites() {
  if [[ "${RUN_POSTER_CONTAINER_SMOKE:-}" != "1" ]]; then
    fail "explicit_opt_in_required"
  fi
  local command_name
  for command_name in docker curl cmp mktemp; do
    command -v "$command_name" >/dev/null 2>&1 || fail "missing_prerequisite"
  done
  docker info >/dev/null 2>&1 || fail "docker_daemon_unavailable"
}

build_image() {
  docker build --file Dockerfile.fastapi --tag "$image_name" .
}

initialize_volume() {
  docker volume create "$volume_name" >/dev/null
  docker run --rm --user 0:0 --volume "$volume_name:/app/uploads" \
    "$image_name" sh -c 'chown 10001:10001 /app/uploads && chmod 0755 /app/uploads'
}

render_poster() {
  docker run --rm --interactive --volume "$volume_name:/app/uploads" \
    "$image_name" python - <<'PY'
import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageFont, features

from app.services.poster_renderer import PosterPalette, PosterRenderPayload, render_and_publish

if os.getuid() != 10001 or os.getgid() != 10001:
    raise RuntimeError("unexpected_runtime_identity")
if not features.check("freetype2"):
    raise RuntimeError("missing_freetype2")
if not features.check("webp"):
    raise RuntimeError("missing_webp")

font_dir = Path("/app/app/assets/fonts")
font_expectations = (
    ("NotoSansCJKsc-Regular.otf", ("Noto Sans CJK SC", "Regular")),
    ("NotoSansCJKsc-Bold.otf", ("Noto Sans CJK SC", "Bold")),
)
for font_name, expected_name in font_expectations:
    font = ImageFont.truetype(font_dir / font_name, 20)
    if font.getname() != expected_name:
        raise RuntimeError("unexpected_font_identity")

upload_root = Path("/app/uploads")
write_probe = upload_root / ".poster-smoke-write-probe"
write_probe.write_bytes(b"ok")
write_probe.unlink()

published = render_and_publish(
    upload_root=upload_root,
    file_base_url="/api/uploads",
    user_id=10001,
    payload=PosterRenderPayload(
        poster_type="couple",
        type_name="Couple",
        title="Container persistence smoke",
        subtitle="Runtime render and static download",
        couple_name="Smoke Test",
        invite_code="SMOKE001",
        generated_date=date(2026, 1, 2),
        metrics=(("Status", "Ready"),),
        palette=PosterPalette(),
    ),
)
with Image.open(published.path) as rendered:
    rendered.load()
    if rendered.format != "PNG" or rendered.size != (1080, 1440) or rendered.mode != "RGB":
        raise RuntimeError("unexpected_rendered_image")
print(published.key)
PY
}

server_environment=(
  --env "APP_ENV=test"
  --env "DB_PASSWORD=poster-smoke-unused"
  --env "JWT_SECRET=poster_container_smoke_only_not_a_secret_value_0123456789_abcdefghijklmnopqrstuvwxyz"
  --env "FILE_UPLOAD_PATH=/app/uploads"
  --env "FILE_BASE_URL=/api/uploads"
  --env "FILE_PUBLIC_PATH=/api/uploads"
)

start_server() {
  local container_name="$1"
  local port_binding="$2"
  docker run --detach --name "$container_name" \
    --publish "$port_binding" \
    --volume "$volume_name:/app/uploads" \
    "${server_environment[@]}" \
    "$image_name" uvicorn app.main:app --host 0.0.0.0 --port 8000 --lifespan off \
    >/dev/null
}

download_when_ready() {
  local poster_url="$1"
  local destination="$2"
  local attempt
  for attempt in $(seq 1 60); do
    if curl --fail --silent --output "$destination" "$poster_url"; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

verify_download() {
  local download_path="$1"
  docker run --rm --interactive "$image_name" python -c '
import io
import sys
from PIL import Image

with Image.open(io.BytesIO(sys.stdin.buffer.read())) as image:
    image.load()
    if image.format != "PNG" or image.size != (1080, 1440) or image.mode != "RGB":
        raise RuntimeError("unexpected_downloaded_image")
' < "$download_path"
}

sha256_file() {
  local download_path="$1"
  docker run --rm --interactive "$image_name" \
    python -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())' \
    < "$download_path"
}

trap cleanup EXIT
trap on_error ERR

run_step "preflight" check_prerequisites

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd -- "$script_dir/.." && pwd)"
cd "$backend_dir"

smoke_id="$(date +%s)-$$-${RANDOM}"
image_name="ai-couple-dish-poster-smoke:${smoke_id}"
volume_name="ai-couple-dish-poster-smoke-${smoke_id}"
container_one="ai-couple-dish-poster-smoke-one-${smoke_id}"
container_two="ai-couple-dish-poster-smoke-two-${smoke_id}"
temp_root="${TMPDIR:-/tmp}"
temp_root="${temp_root%/}"
work_dir="$(mktemp -d "$temp_root/poster-container-smoke.XXXXXX")"
first_download="$work_dir/first.png"
second_download="$work_dir/second.png"

run_step "image_build" build_image
image_sha="$(docker image inspect --format '{{.Id}}' "$image_name")"
run_step "volume_initialization" initialize_volume

current_operation="runtime_validation"
operation_started=${SECONDS}
log_event "poster_container_step_started" "$current_operation" "started" 0
poster_key="$(render_poster)"
if [[ ! "$poster_key" =~ ^poster/user/10001/2026/01/02/[0-9a-f]{32}\.png$ ]]; then
  fail "unexpected_poster_key"
fi
log_event "poster_container_step_completed" "$current_operation" "passed" \
  "$(( (SECONDS - operation_started) * 1000 ))"

run_step "first_container_start" start_server "$container_one" "127.0.0.1::8000"
host_binding="$(docker port "$container_one" 8000/tcp)"
host_port="${host_binding##*:}"
if [[ ! "$host_port" =~ ^[0-9]+$ ]]; then
  fail "unexpected_host_port"
fi
poster_url="http://127.0.0.1:${host_port}/api/uploads/${poster_key}"
run_step "first_container_download" download_when_ready "$poster_url" "$first_download"
run_step "first_download_decode" verify_download "$first_download"
run_step "first_container_remove" docker rm --force "$container_one"
container_one=""

run_step "second_container_start" start_server \
  "$container_two" "127.0.0.1:${host_port}:8000"
run_step "second_container_download" download_when_ready "$poster_url" "$second_download"
run_step "second_download_decode" verify_download "$second_download"

current_operation="byte_comparison"
operation_started=${SECONDS}
log_event "poster_container_step_started" "$current_operation" "started" 0
sameBytes=false
if cmp --silent "$first_download" "$second_download"; then
  sameBytes=true
fi
if [[ "$sameBytes" != "true" ]]; then
  fail "download_bytes_changed"
fi
first_sha="$(sha256_file "$first_download")"
second_sha="$(sha256_file "$second_download")"
if [[ "$first_sha" != "$second_sha" ]]; then
  fail "download_sha_changed"
fi
log_event "poster_container_step_completed" "$current_operation" "passed" \
  "$(( (SECONDS - operation_started) * 1000 ))"
log_evidence "$image_sha" "$poster_url" "$first_sha"
log_event "poster_container_smoke_completed" "acceptance" "passed" \
  "$(( (SECONDS - smoke_started) * 1000 ))"
