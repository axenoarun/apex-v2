#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------
# Wait for PostgreSQL to accept connections
# ---------------------------------------------------------------
echo "[entrypoint] Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY=0
until python -c "
import sys, asyncio, asyncpg
async def check():
    url = '${DATABASE_URL}'.replace('+asyncpg', '')
    conn = await asyncpg.connect(url.replace('postgresql+asyncpg', 'postgresql'))
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        echo "[entrypoint] ERROR: PostgreSQL not reachable after ${MAX_RETRIES} attempts. Exiting."
        exit 1
    fi
    echo "[entrypoint] PostgreSQL not ready (attempt ${RETRY}/${MAX_RETRIES}), retrying in 2s..."
    sleep 2
done
echo "[entrypoint] PostgreSQL is ready."

# ---------------------------------------------------------------
# Run database migrations
# ---------------------------------------------------------------
echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

# ---------------------------------------------------------------
# Seed data (idempotent)
# ---------------------------------------------------------------
echo "[entrypoint] Running seed data..."
python -m app.seed || echo "[entrypoint] WARNING: Seed script exited with non-zero status (may be expected if already seeded)."
echo "[entrypoint] Seed step done."

# ---------------------------------------------------------------
# Hand off to CMD (uvicorn or celery, depending on service)
# ---------------------------------------------------------------
echo "[entrypoint] Starting application: $*"
exec "$@"
