#!/bin/bash
# run_reviewer.sh <N> <BATCH> <log>: one independent visual reviewer on one batch.
# N=1 -> claude -p (fresh context); N=2 -> codex exec. Neither sees the other's output.
set -u
N=$1; BATCH=$2; LOG=$3
cd "$(dirname "$0")/../../.."
if [ "$N" = 1 ]; then BACKEND="claude -p fresh context"; else BACKEND="codex exec"; fi
PROMPT=$(sed -e "s/{N}/$N/g" -e "s/{BATCH}/$BATCH/g" -e "s/{BACKEND}/$BACKEND/g" .allforai/verify/visual-acceptance-batches/reviewer-prompt.txt)
if [ "$N" = 1 ]; then
  claude -p "$PROMPT" --model claude-opus-5-5 --allowedTools "Read" "Write" "Glob" "Grep" --permission-mode acceptEdits > "$LOG" 2>&1
else
  printf '%s' "$PROMPT" | codex exec --sandbox workspace-write -c model_reasoning_effort=medium - > "$LOG" 2>&1
fi
echo "exit=$?" >> "$LOG"
