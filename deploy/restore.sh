#!/usr/bin/env bash
set -euo pipefail

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_backup.sql.gz> [target_db] [--force]" >&2
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="vset"
FORCE=0

# Parse arguments
for arg in "$@"; do
    if [ "$arg" = "--force" ] || [ "$arg" = "-f" ]; then
        FORCE=1
    elif [ "$arg" != "$BACKUP_FILE" ]; then
        TARGET_DB="$arg"
    fi
done

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

cd "${ROOT_DIR}"

# Confirmation for live database
if [ "${TARGET_DB}" = "vset" ] && [ "${FORCE}" -ne 1 ]; then
    echo "==================================================================="
    echo "WARNING: You are about to overwrite the LIVE production database '${TARGET_DB}'!"
    echo "Backup file: ${BACKUP_FILE}"
    echo "==================================================================="
    read -r -p "Are you sure you want to continue? (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        echo "Restore operation cancelled."
        exit 0
    fi
fi

echo "Ensuring target database '${TARGET_DB}' exists..."
docker compose exec -T db psql -U vset -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";" 2>/dev/null || true

echo "Restoring database '${TARGET_DB}' from '${BACKUP_FILE}'..."
if gunzip -c "${BACKUP_FILE}" | docker compose exec -T db psql -U vset -d "${TARGET_DB}" -v ON_ERROR_STOP=1 -q; then
    echo "Restore completed successfully into '${TARGET_DB}'!"
else
    echo "[ERROR] Database restore failed!" >&2
    exit 1
fi
