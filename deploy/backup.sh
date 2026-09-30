#!/usr/bin/env bash
set -euo pipefail

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/vset_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Starting database backup..."
cd "${ROOT_DIR}"

# Execute pg_dump inside db container and stream through gzip
if docker compose exec -T db pg_dump -U vset vset | gzip > "${BACKUP_FILE}"; then
    if [ ! -s "${BACKUP_FILE}" ]; then
        echo "[ERROR] Backup file is empty: ${BACKUP_FILE}" >&2
        rm -f "${BACKUP_FILE}"
        exit 1
    fi
    FILE_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
    echo "Backup completed successfully!"
    echo "Location: ${BACKUP_FILE}"
    echo "Size: ${FILE_SIZE}"
else
    echo "[ERROR] Database backup failed!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "Cleaning up backups older than 7 days..."
find "${BACKUP_DIR}" -type f -name "vset_*.sql.gz" -mtime +7 -exec rm -f {} + 2>/dev/null || true
echo "Retention cleanup complete."
