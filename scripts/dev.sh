#!/usr/bin/env bash
# Start Workbase's API and web app together in one Codespaces terminal.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Python and Node.js/npm must be installed." >&2
  exit 1
fi

# Avoid running two competing servers, or silently switching Vite to port 5174.
python - <<'PY'
import socket
import sys
for port in (8000, 5173):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            print(f"Port {port} is already in use. Stop the old backend/frontend terminal (Ctrl+C) and run this command again.")
            sys.exit(1)
PY

if ! python -c 'import fastapi, sqlmodel, jwt, pwdlib, uvicorn' >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  python -m pip install -r backend/requirements.txt
fi

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

cd "$ROOT/backend"
echo "Starting FastAPI on port 8000..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

cleanup() {
  echo ""
  echo "Stopping the Workbase backend..."
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

READY=0
for _ in {1..60}; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FastAPI stopped during startup. See the error messages above." >&2
    exit 1
  fi
  if python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)' >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.5
done

if [ "$READY" -ne 1 ]; then
  echo "FastAPI did not become healthy on port 8000. See the Python output above." >&2
  exit 1
fi

echo ""
echo "FastAPI health check passed."
echo "Starting React on port 5173..."
echo "Open the forwarded port 5173. Keep this terminal open. Press Ctrl+C to stop both servers."
echo ""
cd "$ROOT/frontend"
npm run dev -- --strictPort
