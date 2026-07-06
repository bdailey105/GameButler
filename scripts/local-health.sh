#!/bin/sh
set -eu

FRONTEND_URL="${FRONTEND_URL:-http://localhost:8095}"
API_HEALTH_URL="${API_HEALTH_URL:-$FRONTEND_URL/api/health}"
DB_FILE="${DB_FILE:-data/gamebutler.db}"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is not installed or not on PATH"
}

http_ok() {
  url="$1"
  status="$(curl -fsS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  [ "$status" = "200" ] || fail "$url returned HTTP ${status:-unreachable}"
}

require_command docker
require_command curl

docker compose ps --status running >/dev/null 2>&1 || fail "docker compose is not available for this project"

running_services="$(docker compose ps --services --status running)"
echo "$running_services" | grep -qx "backend" || fail "backend service is not running"
echo "$running_services" | grep -qx "frontend" || fail "frontend service is not running"

http_ok "$FRONTEND_URL"
http_ok "$API_HEALTH_URL"

[ -f "$DB_FILE" ] || fail "$DB_FILE does not exist"

echo "OK: frontend $FRONTEND_URL"
echo "OK: API health $API_HEALTH_URL"
echo "OK: database $DB_FILE"
