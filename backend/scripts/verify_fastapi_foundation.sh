#!/usr/bin/env bash
set -Eeuo pipefail

# This command is an acceptance gate, not a database provisioning command.
# It never stamps or migrates a schema; the caller must provide an isolated QA
# database URL explicitly so an accidental production connection is rejected.

foundation_started=${SECONDS}
current_operation="preflight"
current_started=${SECONDS}

log_event() {
  local event="$1"
  local operation="$2"
  local result="$3"
  local duration_ms="$4"
  printf '{"event":"%s","module":"fastapi_foundation","operation":"%s","result":"%s","durationMs":%s}\n' \
    "$event" "$operation" "$result" "$duration_ms" >&2
}

fail() {
  local code="$1"
  local message="$2"
  printf '{"event":"foundation_verification_failed","module":"fastapi_foundation",' >&2
  printf '"operation":"preflight","result":"failed","durationMs":0,' >&2
  printf '"errorCode":"%s","message":"%s"}\n' "$code" "$message" >&2
  exit 1
}

on_error() {
  local exit_code="$?"
  local duration_ms=$(( (SECONDS - current_started) * 1000 ))
  log_event "foundation_step_completed" "$current_operation" "failed" "$duration_ms"
  exit "$exit_code"
}

run_step() {
  local operation="$1"
  shift
  current_operation="$operation"
  current_started=${SECONDS}
  log_event "foundation_step_started" "$operation" "started" 0
  "$@"
  local duration_ms=$(( (SECONDS - current_started) * 1000 ))
  log_event "foundation_step_completed" "$operation" "passed" "$duration_ms"
}

trap on_error ERR

if [[ -z "${SCHEMA_DATABASE_URL:-}" ]]; then
  fail "missing_schema_database_url" \
    "SCHEMA_DATABASE_URL is required; provide an isolated QA MySQL URL (no production connection is attempted)."
fi

if [[ "${SCHEMA_DATABASE_ISOLATED:-}" != "true" ]]; then
  fail "isolated_database_confirmation_required" \
    "SCHEMA_DATABASE_ISOLATED=true is required; this gate never guesses whether a database is safe."
fi

log_event "foundation_verification_started" "acceptance" "started" 0

run_step "lock_check" uv lock --check
run_step "dependency_sync" uv sync --frozen
run_step "ruff_check" uv run ruff check app tests scripts
run_step "mypy_check" uv run mypy app
run_step "unit_api_contract_security_tests" \
  uv run pytest -m "not integration" --cov=app --cov-report=term-missing
run_step "integration_tests" uv run pytest -m integration -q

# Deliberately omit --stamp: verification must not mutate a database.
run_step "schema_verification" uv run python scripts/verify_mysql_schema.py
run_step "fastapi_image_build" docker build -f Dockerfile.fastapi .

log_event "foundation_verification_completed" "acceptance" "passed" \
  "$(( (SECONDS - foundation_started) * 1000 ))"
