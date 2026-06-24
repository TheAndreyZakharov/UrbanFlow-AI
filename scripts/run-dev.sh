#!/bin/bash

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  echo ""
  echo "Stopping UrbanFlow AI..."
  kill "$SERVER_PID" "$WEB_PID" 2>/dev/null
  exit 0
}

trap cleanup INT TERM

echo "Starting UrbanFlow AI server..."
cd "$ROOT_DIR/server" || exit 1
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

echo "Starting UrbanFlow AI web..."
cd "$ROOT_DIR/web" || exit 1
npm run dev &
WEB_PID=$!

echo ""
echo "UrbanFlow AI is running:"
echo "Server: http://127.0.0.1:8000"
echo "Web:    http://127.0.0.1:5173"
echo ""
echo "Press Ctrl+C to stop everything."

wait