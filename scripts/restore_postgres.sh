#!/bin/bash
set -e

BACKUP_FILE=$1
DB_NAME=${2:-vset}
FORCE=${3:-}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <path_to_backup_file> [database_name] [--force]"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file $BACKUP_FILE does not exist."
    exit 1
fi

if [ "$FORCE" != "--force" ]; then
    echo "Warning: You are about to restore the backup into the database '$DB_NAME'."
    echo "This will overwrite existing data."
    read -p "Are you sure you want to proceed? (y/N): " confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting restore into $DB_NAME..."
cat "$BACKUP_FILE" | docker exec -i vset-db-1 psql -U vset -d "$DB_NAME"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Restore completed."
