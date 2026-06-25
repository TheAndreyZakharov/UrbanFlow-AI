#!/bin/bash

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_PORT=8000
WEB_PORT=5173
EXTRA_PORT=8080
SHUTTING_DOWN=0

kill_port() {
  local port="$1"
  local pids=""

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"

  if [ -n "$pids" ]; then
    echo "Freeing port $port..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 0.4
  fi
}

cleanup() {
  if [ "$SHUTTING_DOWN" = "1" ]; then
    exit 0
  fi

  SHUTTING_DOWN=1

  echo ""
  echo "Stopping UrbanFlow AI..."

  if [ -n "${SERVER_PID:-}" ]; then
    pkill -P "$SERVER_PID" 2>/dev/null || true
    kill "$SERVER_PID" 2>/dev/null || true
  fi

  if [ -n "${WEB_PID:-}" ]; then
    pkill -P "$WEB_PID" 2>/dev/null || true
    kill "$WEB_PID" 2>/dev/null || true
  fi

  sleep 0.5

  kill_port "$SERVER_PORT"
  kill_port "$WEB_PORT"
  kill_port "$EXTRA_PORT"

  exit 0
}

trap cleanup INT TERM EXIT

kill_port "$SERVER_PORT"
kill_port "$WEB_PORT"
kill_port "$EXTRA_PORT"

echo "Starting UrbanFlow AI server..."
cd "$ROOT_DIR/server" || exit 1
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port "$SERVER_PORT" &
SERVER_PID=$!

echo "Starting UrbanFlow AI web..."
cd "$ROOT_DIR/web" || exit 1
npm run dev &
WEB_PID=$!

echo ""
echo "UrbanFlow AI is running:"
echo "Server: http://127.0.0.1:$SERVER_PORT"
echo "Web:    http://127.0.0.1:$WEB_PORT"
echo ""
echo "Press Ctrl+C to stop everything."

wait