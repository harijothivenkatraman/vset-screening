#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "=== Updating vSET Production Deployment ==="

echo "Pulling latest changes from git repository..."
git pull --ff-only

echo "Rebuilding containers..."
docker compose build

echo "Applying updates (recreating modified containers with brief restart)..."
docker compose up -d

echo "Waiting for services to become healthy..."
MAX_WAIT=60
ELAPSED=0
until [ "$(docker compose ps --format '{{.Health}}' backend 2>/dev/null)" = "healthy" ]; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "[WARNING] Backend did not report healthy within ${MAX_WAIT} seconds."
        docker compose logs --tail=50 backend
        break
    fi
    echo "Waiting for backend health check ($ELAPSED/$MAX_WAIT seconds)..."
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

echo "Current container status:"
docker compose ps

echo "Pruning dangling Docker images to conserve disk space..."
docker image prune -f

echo "=== Update deployment completed successfully! ==="
