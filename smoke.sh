#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8000/}"

echo "[smoke] GET $URL"
code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || true)

if [ "$code" = "200" ]; then
  echo "[smoke] OK (200)"
  exit 0
fi

echo "[smoke] FAIL (http $code)"
exit 1
