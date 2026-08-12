#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Backend tests ==="
cd "$ROOT/backend"
python -m pytest tests/ -v

if [ -d "$ROOT/frontend" ]; then
  echo ""
  echo "=== Frontend tests ==="
  cd "$ROOT/frontend"
  npm test
fi
