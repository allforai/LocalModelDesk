#!/bin/bash
# Drop the mlx-lm server so H3 / Music can use unified memory.
set -euo pipefail
PIDS=$(lsof -tiTCP:8767 -sTCP:LISTEN 2>/dev/null || true)
if [[ -n "${PIDS}" ]]; then
  kill $PIDS 2>/dev/null || true
  sleep 0.4
  kill -9 $PIDS 2>/dev/null || true
fi
echo "MLX LLM unloaded"
