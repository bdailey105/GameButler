#!/bin/sh
set -eu

DB_FILE="${DB_FILE:-data/gamebutler.db}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/gamebutler-$timestamp.db"

[ -f "$DB_FILE" ] || {
  echo "FAIL: $DB_FILE does not exist" >&2
  exit 1
}

mkdir -p "$BACKUP_DIR"
cp "$DB_FILE" "$backup_file"

echo "OK: backed up $DB_FILE to $backup_file"
