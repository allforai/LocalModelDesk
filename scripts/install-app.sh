#!/bin/bash
# api:installApp — verify a bundle before copying it into an Applications directory.
set -euo pipefail

usage() {
  echo 'Usage: install-app.sh [--app dist/LocalModelDesk.app] [--dest /Applications] [--source-root <checkout root>]' >&2
  exit 2
}

APP="dist/LocalModelDesk.app"
DEST="/Applications"
SOURCE_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)         [[ $# -ge 2 ]] || usage; APP="$2"; shift 2 ;;
    --dest)        [[ $# -ge 2 ]] || usage; DEST="$2"; shift 2 ;;
    --source-root) [[ $# -ge 2 ]] || usage; SOURCE_ROOT="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -d "$APP" && -d "$DEST" ]] || usage
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY=("$REPO/scripts/verify-app.sh" "$APP")
if [[ -n "$SOURCE_ROOT" ]]; then
  VERIFY+=(--source-root "$SOURCE_ROOT")
fi
"${VERIFY[@]}"

TARGET="$DEST/LocalModelDesk.app"
if [[ -e "$TARGET" ]]; then
  EXISTING_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$TARGET/Contents/Info.plist" 2>/dev/null || true)"
  if [[ "$EXISTING_ID" != "com.aa.localmodeldesk" ]]; then
    echo "refusing to replace $TARGET: unexpected bundle id ${EXISTING_ID:-<missing>}" >&2
    exit 1
  fi
  rm -rf -- "$TARGET"
fi

ditto "$APP" "$TARGET"
echo "installed: $TARGET"
