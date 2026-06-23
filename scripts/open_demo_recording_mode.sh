#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m scripts.build_static_demo

PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/demo/index.html?autoplay=1&seconds=${DEMO_SECONDS:-420}"

echo "Starting local demo server on port ${PORT}"
echo "Open recording URL: ${URL}"
echo "Press Ctrl-C here after the browser is open and recording is finished."

python3 -m http.server "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

sleep 1
open "$URL"
wait "$SERVER_PID"

