#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT="${1:-demo_recording.mov}"
DURATION="${DEMO_RECORD_SECONDS:-600}"
PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}/demo/index.html?autoplay=1&seconds=${DEMO_SECONDS:-420}"

if ! command -v screencapture >/dev/null 2>&1; then
  echo "screencapture is not available on this machine."
  exit 1
fi

python3 -m scripts.build_static_demo

python3 -m http.server "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

sleep 1
open "$URL"

cat <<MSG
Recording target opened:
  ${URL}

macOS may ask for Screen Recording and microphone permissions.
The command below records the screen for ${DURATION} seconds:
  screencapture -v -V ${DURATION} -g -k "${OUT}"

Starting in 5 seconds. Press Ctrl-C to cancel.
MSG

sleep 5
screencapture -v -V "$DURATION" -g -k "$OUT"

echo "Wrote ${OUT}"

