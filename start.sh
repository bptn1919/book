#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a; source "$ROOT/.env"; set +a
fi

echo "Starting backend..."
cd "$ROOT/backend"
uvicorn app.main:app --reload --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" &
BACKEND_PID=$!

FRONTEND_PID=""
if [ -d "$ROOT/frontend" ]; then
  echo "Starting frontend..."
  cd "$ROOT/frontend"
  npm run dev &
  FRONTEND_PID=$!
else
  echo "Frontend not set up yet — skipping"
fi

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Backend:  http://localhost:${APP_PORT:-8000}"
[ -n "$FRONTEND_PID" ] && echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."
wait "$BACKEND_PID"
