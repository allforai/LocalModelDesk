#!/bin/bash
# api:verifyAppBundle — collect verification failures before returning non-zero.
set -euo pipefail

usage() {
  echo '用法: verify-app.sh <app路径> [--source-root <checkout根>]' >&2
  exit 2
}

APP="${1:-}"
[[ -n "$APP" && -d "$APP" ]] || usage
shift

SOURCE_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-root)
      [[ $# -ge 2 ]] || usage
      SOURCE_ROOT="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 2
      ;;
  esac
done
if [[ -z "$SOURCE_ROOT" ]]; then
  SOURCE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

RES="$APP/Contents/Resources"
FAILLOG="$(mktemp)"
trap 'rm -f "$FAILLOG"' EXIT
fail() { printf '  - %s\n' "$1" >> "$FAILLOG"; }

# V3: installed applications must not contain checkout or build-machine paths.
for forbidden in /opt/homebrew "$SOURCE_ROOT" "$HOME/.local/share/uv" "$HOME/.local/bin"; do
  hits="$(grep -r -a -l -- "$forbidden" "$APP" 2>/dev/null || true)"
  if [[ -n "$hits" ]]; then
    while IFS= read -r hit; do
      fail "V3 自包含违例: 禁串 '$forbidden' 出现在 $hit"
    done <<< "$hits"
  fi
done

# V4: copying a venv into the bundle preserves machine-specific metadata.
while IFS= read -r file; do
  fail "V4 venv 残留 pyvenv.cfg: $file"
done < <(find "$APP" -name pyvenv.cfg -type f 2>/dev/null)

for directory in "$RES"/pylibs/*/bin; do
  if [[ -e "$directory" ]]; then
    fail "V4 pylibs bin 残留（shebang 带构建机路径）: $directory"
  fi
done

while IFS= read -r directory; do
  fail "V4 pylibs 内 __pycache__ 残留: $directory"
done < <(find "$RES/pylibs" -name __pycache__ -type d 2>/dev/null)

if [[ -s "$FAILLOG" ]]; then
  echo "verify-app: 发现以下失败（${APP}）:" >&2
  cat "$FAILLOG" >&2
  exit 1
fi

echo "verify-app: OK ($APP)"
