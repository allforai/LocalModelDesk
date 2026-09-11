#!/bin/bash
# api:verifyAppBundle — read-only V1–V8 bundle verification.
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
PLIST="$APP/Contents/Info.plist"
FAILLOG="$(mktemp)"
trap 'rm -f "$FAILLOG"' EXIT
fail() { printf '  - %s\n' "$1" >> "$FAILLOG"; }

# V1: the complete application bundle must verify its signature.
if ! OUT="$(codesign --verify --deep --strict --verbose=2 "$APP" 2>&1)"; then
  fail "V1 签名验证失败: $OUT"
fi

# V1b: the bundle must carry a Developer ID Application signature (R-packaging-04), unless the
# build was explicitly allowed to be adhoc.  Notarization is a separate, later step, so an
# "Unnotarized Developer ID" verdict from Gatekeeper is acceptable here; "no usable signature" is not.
SPCTL_OUT="$(spctl --assess --type execute -vv "$APP" 2>&1 || true)"
CODESIGN_INFO="$(codesign -dvv "$APP" 2>&1 || true)"
if ! printf '%s' "$CODESIGN_INFO" | grep -q "Authority=Developer ID Application"; then
  if [[ "${LMD_ALLOW_ADHOC:-0}" != "1" ]]; then
    fail "V1b 未用 Developer ID Application 签名（spctl: $(printf '%s' "$SPCTL_OUT" | tr '\n' ' ')）；设置 LMD_ALLOW_ADHOC=1 以允许本机调试用 adhoc 签名"
  fi
elif printf '%s' "$SPCTL_OUT" | grep -q "Unnotarized Developer ID"; then
  echo "提示：已用 Developer ID 签名但未公证（spctl: Unnotarized Developer ID）；分发到其他机器前需 notarytool 公证" >&2
fi

# V2: every key required by the packaging plist template must be non-empty.
for key in CFBundleIdentifier CFBundleName CFBundleExecutable CFBundleShortVersionString \
           CFBundleVersion CFBundleIconFile LSMinimumSystemVersion CFBundlePackageType \
           NSHighResolutionCapable NSHumanReadableCopyright; do
  value="$(/usr/libexec/PlistBuddy -c "Print :$key" "$PLIST" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    fail "V2 Info.plist 缺键或为空: $key"
  fi
done

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

# V5: the runtime layout must contain the embedded interpreter and all resources.
PYBIN="$RES/python/bin/python3.13"
if [[ ! -x "$PYBIN" ]]; then
  fail "V5 缺内嵌解释器或不可执行: $PYBIN"
fi
for path in "$RES/desk" "$RES/pylibs/desk" "$RES/pylibs/music" "$RES/pylibs/h3" \
            "$RES/bundle.json" "$RES/AppIcon.icns"; do
  if [[ ! -e "$path" ]]; then
    fail "V5 缺结构项: $path"
  fi
done

# V6: imports use the embedded interpreter with user site-packages disabled.
if [[ -x "$PYBIN" ]]; then
  v6() {
    if ! OUT="$(cd "$RES" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$1" \
      "python/bin/python3.13" -s -c "$2" 2>&1)"; then
      fail "V6 导入失败 [PYTHONPATH=$1] [$2]: $OUT"
    fi
  }
  v6 ".:pylibs/desk" "import desk"
  v6 "pylibs/desk" "import mlx_lm"
  v6 "pylibs/music" "import mlx_minimax_music3"
  v6 "pylibs/h3" "import mlx_h3.cli"
  v6 "pylibs/desk" "from huggingface_hub.cli.hf import main"
fi

# V7: application functionality supersedes these legacy checkout scripts.
for script in initModels.sh run-h3.sh run-music3.py unload-llm.sh media-gui; do
  if [[ -e "$SOURCE_ROOT/$script" ]]; then
    fail "V7 遗留原型仍存在: $SOURCE_ROOT/$script"
  fi
done

# V8: any Python process started straight out of the signed bundle (without
# PYTHONDONTWRITEBYTECODE=1) writes __pycache__ back into it, which breaks the
# code-signing seal — codesign --verify then fails at the worst possible time
# (in front of the user). build-app.sh precompiles desk/ before signing, so any
# __pycache__ dated *after* the seal was applied (Contents/_CodeSignature) is a
# stray, runtime write rather than the build's own precompilation.
SEAL_MARKER="$APP/Contents/_CodeSignature/CodeResources"
if [[ -e "$SEAL_MARKER" && -d "$RES/desk" ]]; then
  STRAY_PYC="$(find "$RES/desk" -name '__pycache__' -newer "$SEAL_MARKER" 2>/dev/null | head -5 || true)"
  if [[ -n "$STRAY_PYC" ]]; then
    fail "V8 封条已破：包内出现签名后写入的字节码 $(printf '%s' "$STRAY_PYC" | tr '\n' ' ')"
  fi
fi

if [[ -s "$FAILLOG" ]]; then
  echo "verify-app: 发现以下失败（${APP}）:" >&2
  cat "$FAILLOG" >&2
  exit 1
fi

echo "verify-app: OK ($APP)"
