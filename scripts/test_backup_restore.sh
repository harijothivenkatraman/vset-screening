#!/bin/bash
set -e

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting backup and restore test..."

# 1. Create a test backup
TEST_BACKUP_DIR="/tmp/vset_test_backup"
mkdir -p "$TEST_BACKUP_DIR"
./scripts/backup_postgres.sh "$TEST_BACKUP_DIR"

BACKUP_FILE=$(ls -t $TEST_BACKUP_DIR/vset_backup_*.sql | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "Error: Failed to create test backup."
    exit 1
fi

echo "Created test backup: $BACKUP_FILE"

# 2. Get original table and row counts from the main database
ORIG_TABLE_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d '[:space:]')
ORIG_COMPANIES_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset -t -c "SELECT count(*) FROM companies;" | tr -d '[:space:]')
ORIG_REPORTS_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset -t -c "SELECT count(*) FROM reports;" | tr -d '[:space:]')

echo "Original database:"
echo "  Public tables: $ORIG_TABLE_COUNT"
echo "  Companies:     $ORIG_COMPANIES_COUNT"
echo "  Reports:       $ORIG_REPORTS_COUNT"

# 3. Create a temporary test database
echo "Creating scratch database vset_test..."
docker exec -i vset-db-1 psql -U vset -d postgres -c "DROP DATABASE IF EXISTS vset_test;"
docker exec -i vset-db-1 psql -U vset -d postgres -c "CREATE DATABASE vset_test;"

# 4. Restore the backup into the test database
echo "Restoring to scratch database..."
./scripts/restore_postgres.sh "$BACKUP_FILE" vset_test --force > /dev/null

# 5. Verify the restored database row counts
REST_TABLE_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset_test -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d '[:space:]')
REST_COMPANIES_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset_test -t -c "SELECT count(*) FROM companies;" | tr -d '[:space:]')
REST_REPORTS_COUNT=$(docker exec -i vset-db-1 psql -U vset -d vset_test -t -c "SELECT count(*) FROM reports;" | tr -d '[:space:]')

echo "Restored database:"
echo "  Public tables: $REST_TABLE_COUNT"
echo "  Companies:     $REST_COMPANIES_COUNT"
echo "  Reports:       $REST_REPORTS_COUNT"

if [ "$ORIG_TABLE_COUNT" != "$REST_TABLE_COUNT" ] || [ "$ORIG_COMPANIES_COUNT" != "$REST_COMPANIES_COUNT" ] || [ "$ORIG_REPORTS_COUNT" != "$REST_REPORTS_COUNT" ]; then
    echo "Error: Verification failed. Row counts do not match!"
    docker exec -i vset-db-1 psql -U vset -d postgres -c "DROP DATABASE IF EXISTS vset_test;"
    rm -rf "$TEST_BACKUP_DIR"
    exit 1
fi

echo "Verification successful! All table and row counts match exactly."

# 6. Cleanup
echo "Cleaning up scratch database and test backup..."
docker exec -i vset-db-1 psql -U vset -d postgres -c "DROP DATABASE IF EXISTS vset_test;"
rm -rf "$TEST_BACKUP_DIR"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Test completed successfully."
