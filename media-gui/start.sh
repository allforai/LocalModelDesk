#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
LOG="$ROOT/desk.log"
mkdir -p "$ROOT" "$REPO/outputs"
exec >>"$LOG" 2>&1

if ! curl -sf -o /dev/null --max-time 1 "http://127.0.0.1:8766/"; then
  echo "$(date '+%F %T') starting desk"
  nohup python3 -u "$ROOT/server.py" >>"$LOG" 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -sf -o /dev/null --max-time 1 "http://127.0.0.1:8766/" && break
    sleep 0.3
  done
fi

if [[ "${OPEN_UI:-0}" == "1" ]]; then
  open "http://127.0.0.1:8766/"
fi
