#!/usr/bin/env bash
set -Eeuo pipefail

# This command is an acceptance gate, not a database provisioning command.
# It never stamps or migrates a schema; the caller must provide an isolated QA
# database URL explicitly so an accidental production connection is rejected.

log_event() {
  local event="$1"
  local status="$2"
  printf '{"event":"%s","module":"fastapi_foundation","status":"%s"}\n' "$event" "$status" >&2
}

fail() {
  local code="$1"
  local message="$2"
  log_event "foundation_verification_failed" "${code}"
  printf 'FastAPI foundation verification stopped: %s\n' "$message" >&2
  exit 1
}

if [[ -z "${SCHEMA_DATABASE_URL:-}" ]]; then
  fail "missing_schema_database_url" \
    "SCHEMA_DATABASE_URL is required; provide an isolated QA MySQL URL (no production connection is attempted)."
fi

if [[ "${SCHEMA_DATABASE_ISOLATED:-}" != "true" ]]; then
  fail "isolated_database_confirmation_required" \
    "SCHEMA_DATABASE_ISOLATED=true is required; this gate never guesses whether a database is safe."
fi

log_event "foundation_verification_started" "running"

log_event "lock_check" "running"
uv lock --check
log_event "lock_check" "passed"

log_event "dependency_sync" "running"
uv sync --frozen
log_event "dependency_sync" "passed"

log_event "ruff_check" "running"
uv run ruff check app tests scripts
log_event "ruff_check" "passed"

log_event "mypy_check" "running"
uv run mypy app
log_event "mypy_check" "passed"

log_event "unit_api_contract_security_tests" "running"
uv run pytest -m "not integration" --cov=app --cov-report=term-missing
log_event "unit_api_contract_security_tests" "passed"

log_event "schema_verification" "running"
# Deliberately omit --stamp: verification must not mutate a database.
uv run python scripts/verify_mysql_schema.py
log_event "schema_verification" "passed"

log_event "fastapi_image_build" "running"
docker build -f Dockerfile.fastapi .
log_event "fastapi_image_build" "passed"
log_event "foundation_verification" "passed"
