#!/bin/bash
# api:uninstallApp — remove the legacy LaunchAgent and this application's bundle.
# Deliberately avoids `set -e`: cleanup should report failures after trying each step.
set -uo pipefail

BUNDLE_ID="com.aa.localmodeldesk"
APP_PATH="/Applications/LocalModelDesk.app"
DATA_ROOT="$HOME/Library/Application Support/LocalModelDesk"
LA_DIR="$HOME/Library/LaunchAgents"
PURGE=0
DRY_RUN=0

usage() {
  echo 'Usage: uninstall-app.sh [--app-path P] [--data-root P] [--launch-agents-dir P] [--purge-data] [--dry-run]' >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-path) [[ $# -ge 2 ]] || usage; APP_PATH="$2"; shift 2 ;;
    --data-root) [[ $# -ge 2 ]] || usage; DATA_ROOT="$2"; shift 2 ;;
    --launch-agents-dir) [[ $# -ge 2 ]] || usage; LA_DIR="$2"; shift 2 ;;
    --purge-data) PURGE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) usage ;;
  esac
done

FAILED=0
fail() {
  echo "uninstall-app: $1" >&2
  FAILED=1
}

guarded_remove() {
  local path="$1"
  case "$path" in
    /*) ;;
    *) fail "refusing to remove relative path: $path"; return 1 ;;
  esac
  if [[ "$path" == "/" || "$path" == "$HOME" ]]; then
    fail "refusing to remove protected path: $path"
    return 1
  fi
  [[ -e "$path" || -L "$path" ]] || return 0
  if [[ "$DRY_RUN" == 1 ]]; then
    echo "[dry-run] rm -rf '$path'"
  elif [[ -L "$path" ]]; then
    rm -f -- "$path" || fail "failed to remove $path"
  else
    rm -rf -- "$path" || fail "failed to remove $path"
  fi
}

LA_PLIST="$LA_DIR/$BUNDLE_ID.plist"
if [[ "$DRY_RUN" == 1 ]]; then
  echo "[dry-run] launchctl bootout gui/$(id -u)/$BUNDLE_ID"
  [[ -e "$LA_PLIST" || -L "$LA_PLIST" ]] && echo "[dry-run] rm '$LA_PLIST'"
else
  launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
  [[ -e "$LA_PLIST" || -L "$LA_PLIST" ]] && rm -f -- "$LA_PLIST" || true
fi

if [[ -e "$APP_PATH" || -L "$APP_PATH" ]]; then
  ACTUAL_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Contents/Info.plist" 2>/dev/null || true)"
  if [[ "$ACTUAL_ID" == "$BUNDLE_ID" ]]; then
    guarded_remove "$APP_PATH"
  else
    fail "refusing to remove $APP_PATH: unexpected bundle id ${ACTUAL_ID:-<missing>}"
  fi
fi

# User data is deliberately retained unless the protected purge workflow is requested.
if [[ "$PURGE" == 1 && "$DRY_RUN" == 1 && -d "$DATA_ROOT" ]]; then
  echo "[dry-run] preserve data-root '$DATA_ROOT' pending purge safeguards"
fi

[[ "$FAILED" == 0 ]] || exit 1
echo "uninstall-app: complete"
