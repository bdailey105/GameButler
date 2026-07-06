#!/bin/sh
set -eu

DB_FILE="${DB_FILE:-data/gamebutler.db}"
BACKUP="${1:-${BACKUP:-}}"
SAFETY_DIR="${SAFETY_DIR:-backups}"

[ -n "$BACKUP" ] || {
  echo "FAIL: pass a backup path, e.g. scripts/restore-db.sh backups/gamebutler-YYYYMMDD-HHMMSS.db" >&2
  exit 1
}

[ -f "$BACKUP" ] || {
  echo "FAIL: backup file does not exist: $BACKUP" >&2
  exit 1
}

mkdir -p "$(dirname "$DB_FILE")"

if [ -f "$DB_FILE" ]; then
  mkdir -p "$SAFETY_DIR"
  timestamp="$(date +%Y%m%d-%H%M%S)"
  safety_file="$SAFETY_DIR/pre-restore-$timestamp.db"
  cp "$DB_FILE" "$safety_file"
  echo "OK: saved current DB to $safety_file"
fi

cp "$BACKUP" "$DB_FILE"
echo "OK: restored $DB_FILE from $BACKUP"
