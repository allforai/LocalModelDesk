#!/bin/bash
# api:signAppBundle — sign nested Mach-O files before the application bundle.
set -euo pipefail

usage() { echo '用法: sign-app.sh <app路径> [--identity "…"] [--adhoc]' >&2; exit 2; }

APP="${1:-}"
if [[ -z "$APP" || ! -d "$APP" ]]; then usage; fi
shift

IDENTITY="${CODESIGN_IDENTITY:-}"
ADHOC=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --identity) [[ $# -ge 2 ]] || usage; IDENTITY="$2"; shift 2 ;;
    --adhoc) ADHOC=1; shift ;;
    *) usage ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENTITLEMENTS="$REPO_ROOT/packaging/entitlements.plist"

if [[ "$ADHOC" == 1 ]]; then
  SIGN_ARGS=(--force --options runtime --entitlements "$ENTITLEMENTS" -s -)
else
  if [[ -z "$IDENTITY" ]]; then
    CANDIDATES="$(security find-identity -v -p codesigning 2>&1 || true)"
    IDENTITY="$(printf '%s\n' "$CANDIDATES" | sed -n 's/.*"\(Developer ID Application: [^"]*\)".*/\1/p' | head -n1)"
    if [[ -z "$IDENTITY" ]]; then
      echo "错误：找不到 Developer ID Application 签名身份。security 候选如下：" >&2
      printf '%s\n' "$CANDIDATES" >&2
      exit 1
    fi
  fi
  SIGN_ARGS=(--force --options runtime --timestamp --entitlements "$ENTITLEMENTS" -s "$IDENTITY")
fi

is_macho() {
  local magic
  magic="$(xxd -p -l 4 "$1" 2>/dev/null || true)"
  case "$magic" in
    feedface|feedfacf|cefaedfe|cffaedfe|cafebabe|bebafeca) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r -d '' file; do
  if is_macho "$file"; then
    codesign "${SIGN_ARGS[@]}" "$file"
  fi
done < <(find "$APP/Contents/Resources" -type f -print0 2>/dev/null)

codesign "${SIGN_ARGS[@]}" "$APP/Contents/MacOS/LocalModelDesk"
codesign "${SIGN_ARGS[@]}" "$APP"
echo "signed: $APP"
