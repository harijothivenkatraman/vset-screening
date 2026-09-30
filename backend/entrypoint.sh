#!/usr/bin/env bash
set -euo pipefail

echo "=== vSET Backend Starting ==="

echo "Waiting for database to accept connections..."
python -c '
import asyncio, sys
from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def wait_db():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    for attempt in range(1, 31):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("Database connection successfully established.")
            await engine.dispose()
            return
        except Exception as e:
            print(f"Waiting for database (attempt {attempt}/30): {e}")
            await asyncio.sleep(1)
    print("Database connection timed out after 30 attempts.")
    sys.exit(1)

asyncio.run(wait_db())
'

echo "Running database schema migrations / initialization..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head || true
fi

echo "Running seed script (idempotent)..."
python seed.py

echo "Starting Uvicorn..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --workers "${WEB_CONCURRENCY:-1}"
