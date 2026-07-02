#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL..."
python /app/docker/wait_for_db.py

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
