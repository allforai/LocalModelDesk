#!/bin/bash
# api:buildAppBundle — clean checkout to a self-contained, signed app bundle.
# A failed build removes its staging directory; an existing published bundle is untouched.
set -euo pipefail

usage() {
  echo 'Usage: build-app.sh [--output dist] [--identity "…"] [--adhoc] [--python-version cpython-X.Y.Z]' >&2
  exit 2
}

OUTPUT="dist"
IDENTITY=""
ADHOC=0
PYVER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)         [[ $# -ge 2 ]] || usage; OUTPUT="$2"; shift 2 ;;
    --identity)       [[ $# -ge 2 ]] || usage; IDENTITY="$2"; shift 2 ;;
    --adhoc)          ADHOC=1; shift ;;
    --python-version) [[ $# -ge 2 ]] || usage; PYVER="$2"; shift 2 ;;
    *) usage ;;
  esac
done

REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "$PYVER" ]]; then
  PYVER="$(tr -d '[:space:]' < "$REPO/packaging/python-version.txt")"
fi
VERSION="$(tr -d '[:space:]' < "$REPO/packaging/VERSION")"
MIN_OS="15.0"

mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
STAGING="$OUTPUT/.staging.$$"
trap 'rm -rf "$STAGING"' EXIT
APP="$STAGING/LocalModelDesk.app"
RES="$APP/Contents/Resources"
mkdir -p "$APP/Contents/MacOS" "$RES"

echo "==> [1/9] Swift compile"
xcrun swiftc -O "$REPO"/macos/*.swift \
  -o "$APP/Contents/MacOS/LocalModelDesk" -target "arm64-apple-macos$MIN_OS"

echo "==> [2/9] Copy desk package"
rsync -a --exclude '__pycache__' --exclude '.pytest_cache' "$REPO/desk/" "$RES/desk/"

echo "==> [3/9] Embed CPython $PYVER"
PY_DIR="$STAGING/uv-python"
UV_PYTHON_INSTALL_DIR="$PY_DIR" uv python install "$PYVER"
SRC_PY="$(find "$PY_DIR" -maxdepth 1 -type d -name 'cpython-*' | head -n1)"
if [[ -z "$SRC_PY" ]]; then
  echo "error: uv did not produce a CPython directory ($PYVER)" >&2
  exit 1
fi
rsync -a "$SRC_PY/" "$RES/python/"
if [[ ! -x "$RES/python/bin/python3.13" ]]; then
  echo "error: missing embedded interpreter $RES/python/bin/python3.13" >&2
  exit 1
fi

echo "==> [4/9] Install dependency libraries"
mkdir -p "$RES/requirements"
for name in desk music h3; do
  uv pip install --python "$RES/python/bin/python3.13" --target "$RES/pylibs/$name" \
    --no-compile-bytecode -r "$REPO/packaging/requirements-$name.txt"
  rm -rf "$RES/pylibs/$name/bin"
  find "$RES/pylibs/$name" -type d -name __pycache__ -prune -exec rm -rf {} +
  cp "$REPO/packaging/requirements-$name.txt" "$RES/requirements/"
done

echo "==> [5/9] Render Info.plist"
sed "s/@VERSION@/$VERSION/g" "$REPO/packaging/Info.plist.template" > "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist"

echo "==> [6/9] Build icon"
ICONSET="$STAGING/AppIcon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
  sips -z "$size" "$size" "$REPO/packaging/icon/icon-1024.png" \
    --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  sips -z "$((size * 2))" "$((size * 2))" "$REPO/packaging/icon/icon-1024.png" \
    --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/AppIcon.icns"

echo "==> [7/9] Write bundle marker"
printf '{"app": "LocalModelDesk", "bundle_version": "%s", "python": "python/bin/python3.13"}\n' \
  "$VERSION" > "$RES/bundle.json"

echo "==> [8/9] Sign"
SIGN=("$REPO/scripts/sign-app.sh" "$APP")
if [[ "$ADHOC" == 1 ]]; then SIGN+=(--adhoc); fi
if [[ -n "$IDENTITY" ]]; then SIGN+=(--identity "$IDENTITY"); fi
"${SIGN[@]}"

echo "==> [9/9] Verify"
"$REPO/scripts/verify-app.sh" "$APP" --source-root "$REPO"

# Publish only after all nine steps succeed.  The replacement is a short rename sequence.
rm -rf "$OUTPUT/LocalModelDesk.app.old"
if [[ -e "$OUTPUT/LocalModelDesk.app" ]]; then
  mv "$OUTPUT/LocalModelDesk.app" "$OUTPUT/LocalModelDesk.app.old"
fi
mv "$APP" "$OUTPUT/LocalModelDesk.app"
rm -rf "$OUTPUT/LocalModelDesk.app.old"
echo "built: $OUTPUT/LocalModelDesk.app"
