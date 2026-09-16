#!/bin/bash
# Compile the headless harness (without AppKit) and print its binary path last.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${1:?usage: shell-lifecycle-test.sh <scratch-dir>}"
mkdir -p "$SCRATCH"
OUT="$SCRATCH/shellharness"
SOURCES=("$ROOT/macos/ShellStatus.swift" "$ROOT/macos/harness/ShellHarness.swift")
for extra in PortGuard.swift ServerController.swift VisualProbe.swift; do
  if [ -f "$ROOT/macos/$extra" ]; then SOURCES+=("$ROOT/macos/$extra"); fi
done
xcrun swiftc -O -o "$OUT" "${SOURCES[@]}" 1>&2
echo "$OUT"
