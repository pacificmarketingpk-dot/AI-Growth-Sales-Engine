#!/bin/sh
set -e
echo "Applying database migrations..."
alembic upgrade head
# One worker: OAuth state, the bulk-analysis queue and rate limits live in process memory.
# Scale by moving those to Redis first (see docs/ARCHITECTURE.md).
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips='*'
