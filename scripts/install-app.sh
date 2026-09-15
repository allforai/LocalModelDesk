#!/bin/bash
# api:installApp — verify a bundle before copying it into an Applications directory.
set -euo pipefail

usage_text() {
  cat <<'EOF'
Usage: install-app.sh [--app dist/LocalModelDesk.app] [--dest /Applications] [--source-root <checkout root>]

  --app DIR          要安装的应用包，默认 dist/LocalModelDesk.app
  --dest DIR         安装目标目录（必须已存在），默认 /Applications
  --source-root DIR  传给 verify-app.sh 的检出根目录（可选）
  --help, -h         打印本帮助并退出
EOF
}

usage() { usage_text >&2; exit 2; }
help() { usage_text; exit 0; }
die() { echo "install-app: $*" >&2; exit 2; }

APP="dist/LocalModelDesk.app"
DEST="/Applications"
SOURCE_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)         [[ $# -ge 2 ]] || usage; APP="$2"; shift 2 ;;
    --dest)        [[ $# -ge 2 ]] || usage; DEST="$2"; shift 2 ;;
    --source-root) [[ $# -ge 2 ]] || usage; SOURCE_ROOT="$2"; shift 2 ;;
    --help|-h)     help ;;
    *) usage ;;
  esac
done

[[ -d "$DEST" ]] || die "目标目录不存在：${DEST}（请先创建，或用 --dest 指定已存在的目录）"
[[ -d "$APP" ]] || die "应用包不存在：$APP"
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
