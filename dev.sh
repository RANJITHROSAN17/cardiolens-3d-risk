#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d node_modules ]; then
  echo "Installing web dependencies..."
  npm install
fi

if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  echo "Creating backend virtual environment..."
  python -m venv "$ROOT/backend/.venv"
fi
API_PY="$ROOT/backend/.venv/bin/python"
if ! "$API_PY" -c 'import fastapi, uvicorn, sklearn; assert sklearn.__version__ == "1.6.1"' >/dev/null 2>&1; then
  echo "Installing API dependencies..."
  "$API_PY" -m pip install -r backend/requirements.txt
fi

(cd "$ROOT/backend" && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
npm run dev -- --host 0.0.0.0
