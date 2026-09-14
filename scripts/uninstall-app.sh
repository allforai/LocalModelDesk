#!/bin/bash
# api:uninstallApp — remove the legacy LaunchAgent and this application's bundle.
# Deliberately avoids `set -e`: cleanup should report failures after trying each step.
set -uo pipefail

BUNDLE_ID="com.aa.localmodeldesk"
APP_PATH="/Applications/LocalModelDesk.app"
DATA_ROOT="$HOME/Library/Application Support/LocalModelDesk"
DEFAULT_LA_DIR="$HOME/Library/LaunchAgents"
LA_DIR="$DEFAULT_LA_DIR"
PURGE=0
DRY_RUN=0

usage_text() {
  cat <<'EOF'
Usage: uninstall-app.sh [--app-path P] [--data-root P] [--launch-agents-dir P] [--purge-data] [--dry-run]

  --app-path P          应用包路径，默认 /Applications/LocalModelDesk.app
  --data-root P         数据目录，默认 ~/Library/Application Support/LocalModelDesk
  --launch-agents-dir P LaunchAgents 目录，默认 ~/Library/LaunchAgents
  --purge-data          同时清除数据目录（模型目录始终保留）
  --dry-run             只打印将要执行的操作，不真的删除
  --help, -h            打印本帮助并退出
EOF
}

usage() { usage_text >&2; exit 2; }
help() { usage_text; exit 0; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-path) [[ $# -ge 2 ]] || usage; APP_PATH="$2"; shift 2 ;;
    --data-root) [[ $# -ge 2 ]] || usage; DATA_ROOT="$2"; shift 2 ;;
    --launch-agents-dir) [[ $# -ge 2 ]] || usage; LA_DIR="$2"; shift 2 ;;
    --purge-data) PURGE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) help ;;
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

paths_overlap() {
  /usr/bin/python3 - "$1" "$2" <<'PY'
from pathlib import Path
import sys

first, second = (Path(value).expanduser().resolve() for value in sys.argv[1:])
try:
    first.relative_to(second)
except ValueError:
    try:
        second.relative_to(first)
    except ValueError:
        raise SystemExit(1)
raise SystemExit(0)
PY
}

purge_data() {
  local models_root child name
  if ! models_root="$(/usr/bin/python3 - "$DATA_ROOT" <<'PY'
import json
from pathlib import Path
import sys

data_root = Path(sys.argv[1]).expanduser().resolve()
config_path = data_root / "config.json"
if config_path.exists() or config_path.is_symlink():
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read config: {exc}")
    if not isinstance(raw, dict):
        raise SystemExit("config top level is not an object")
    configured = raw.get("models_root", data_root / "models")
    if not isinstance(configured, str) or not configured:
        raise SystemExit("config models_root is not a non-empty string")
    model_path = Path(configured).expanduser()
    if not model_path.is_absolute():
        model_path = data_root / model_path
else:
    model_path = data_root / "models"
print(model_path.resolve())
PY
)"; then
    fail "refusing to purge data: config.json is corrupt or unreadable"
    return 1
  fi

  for child in "$DATA_ROOT"/* "$DATA_ROOT"/.[!.]* "$DATA_ROOT"/..?*; do
    [[ -e "$child" || -L "$child" ]] || continue
    name="${child##*/}"
    if [[ "$name" == "models" ]]; then
      echo "uninstall-app: preserving models directory $child"
    elif paths_overlap "$child" "$models_root"; then
      echo "uninstall-app: preserving configured models path $child"
    else
      guarded_remove "$child"
    fi
  done
}

LA_PLIST="$LA_DIR/$BUNDLE_ID.plist"
LA_TARGET="gui/$(id -u)/$BUNDLE_ID"
if [[ "$LA_DIR" != "$DEFAULT_LA_DIR" ]]; then
  echo "uninstall-app: skip: 自定义 LaunchAgents 目录，不对当前用户域执行 launchctl bootout"
elif [[ "$DRY_RUN" == 1 ]]; then
  echo "[dry-run] launchctl bootout ${LA_TARGET}（若已加载）"
elif launchctl print "$LA_TARGET" >/dev/null 2>&1; then
  launchctl bootout "$LA_TARGET" 2>/dev/null || fail "无法停止旧 LaunchAgent ${LA_TARGET}；请手动运行 launchctl bootout ${LA_TARGET} 后重试"
fi
if [[ -e "$LA_PLIST" || -L "$LA_PLIST" ]]; then
  if [[ "$DRY_RUN" == 1 ]]; then
    echo "[dry-run] rm '$LA_PLIST'"
  else
    rm -f -- "$LA_PLIST" || fail "failed to remove $LA_PLIST"
  fi
fi

if [[ -e "$APP_PATH" || -L "$APP_PATH" ]]; then
  ACTUAL_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Contents/Info.plist" 2>/dev/null || true)"
  if [[ "$ACTUAL_ID" == "$BUNDLE_ID" ]]; then
    guarded_remove "$APP_PATH"
  else
    fail "refusing to remove $APP_PATH: unexpected bundle id ${ACTUAL_ID:-<missing>}"
  fi
else
  echo "uninstall-app: skip: 应用包不存在，无需删除：$APP_PATH"
fi

# User data is deliberately retained unless the protected purge workflow is requested.
if [[ "$PURGE" == 1 ]]; then
  if [[ -d "$DATA_ROOT" ]]; then
    purge_data
  else
    echo "uninstall-app: skip: 数据目录不存在，无需清除：$DATA_ROOT"
  fi
fi

[[ "$FAILED" == 0 ]] || exit 1
echo "uninstall-app: complete"
