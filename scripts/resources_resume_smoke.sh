#!/bin/bash
# RG-2 helper: real resume smoke test (manual only; real network and hf CLI).
# Use a <1G HF repository and a temporary directory to confirm that after an
# interruption complete files are skipped and .incomplete files resume.
set -euo pipefail

REPO="${1:-hf-internal-testing/tiny-random-gpt2}"
DEST="${DEST_OVERRIDE:-$(mktemp -d /tmp/lmd-rg2.XXXXXX)}"

echo "== RG-2 resume smoke =="
echo "repo: $REPO"
echo "dest: $DEST"
echo "Interrupt the first download with Ctrl-C, then rerun with this same directory:"
echo "  DEST_OVERRIDE=$DEST bash scripts/resources_resume_smoke.sh $REPO"
echo

hf download "$REPO" --local-dir "$DEST"

echo
echo "Done. Inspect hf output: complete files should be skipped and .incomplete files resumed."
echo "Cleanup: rm -rf $DEST"
