#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# venv (нужно для alembic)
source ~/venvs/ai-dnd-bot.venv/bin/activate

# env (нужно для DATABASE_URL_ASYNC)
set -a
source .env
set +a

echo "[db] starting docker db..."
docker compose up -d db

echo "[db] waiting for postgres..."
for i in {1..30}; do
  if docker exec ai_dnd_db pg_isready -U game -d game >/dev/null 2>&1; then
    echo "[db] postgres is ready"
    break
  fi
  sleep 1
  if [ "$i" = "30" ]; then
    echo "[db] postgres not ready after 30s"
    exit 1
  fi
done

echo "[db] alembic upgrade head..."
alembic upgrade head

echo "[db] done"
