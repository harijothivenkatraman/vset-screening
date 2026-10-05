#!/bin/bash
set -e

BACKUP_DIR="${1:-/home/ubuntu/backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/vset_backup_$TIMESTAMP.sql"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting database backup..."

# Run pg_dump via docker exec
if ! docker exec vset-db-1 pg_dump -U vset vset > "$BACKUP_FILE"; then
    echo "Backup failed!"
    exit 1
fi

FILE_SIZE=$(wc -c < "$BACKUP_FILE")
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup created: $BACKUP_FILE (Size: $FILE_SIZE bytes)"

# Delete backups older than 7 days
find "$BACKUP_DIR" -name "vset_backup_*.sql" -type f -mtime +7 -exec rm {} \;
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Cleaned up backups older than 7 days."

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup process completed successfully."
