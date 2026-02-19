#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# venv
source ~/venvs/ai-dnd-bot.venv/bin/activate

# env
set -a
source .env
set +a

# run
python -m uvicorn app.web.server:app --host 127.0.0.1 --port 8000
