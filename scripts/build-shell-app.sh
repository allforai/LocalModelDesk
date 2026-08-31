#!/bin/bash
# Compile the full shell executable for window-level acceptance (not an app bundle).
# Usage: build-shell-app.sh <out-dir>; the final stdout line is the binary path.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:?usage: build-shell-app.sh <out-dir>}"
mkdir -p "$OUT_DIR"
xcrun swiftc -O -o "$OUT_DIR/LocalModelDeskShell" "$ROOT"/macos/*.swift 1>&2
echo "$OUT_DIR/LocalModelDeskShell"
