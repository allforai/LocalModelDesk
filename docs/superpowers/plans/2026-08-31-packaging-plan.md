# 实施计划：packaging

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-packaging-spec.md`
**design** `docs/superpowers/specs/2026-08-31-packaging-design.md`
**覆盖需求** R-packaging-01 … R-packaging-09
**方法** 严格 TDD：每个任务 = 写失败测试 → 跑红 → 实现 → 跑绿 → commit。

## 约束回放（红线）

- T-packaging-12/13 的精确 acceptance 由 runner 在 trusted host 的候选接纳阶段执行，以访问锁定 cache 与 Developer ID keychain；失败候选不发布。
- T-packaging-12 的 pytest 必须通过 `"$MEGASTORM_TEST_PYTHON"` 选择锁定 CPython 3.13，不能依赖宿主 `/bin/sh` 的 `python3` 解析。
- 复制锁定 CPython 后必须删除其 `__pycache__`/`.pyc`，将 `libpython3.13.dylib` install-id 改为 bundle 相对值，并净化 `_sysconfigdata` 与依赖源码注释中的构建机绝对串；之后再签名。源前缀必须由 `SRC_PY` 推导，不能依赖 runner scratch `HOME`；文本枚举必须兼容 macOS 工具，不能把不支持的 `grep -Z` 错误吞掉。这些位置均由 V3 精确证据定位。
- 绝不触碰真实权重（`/Users/aa/LocalModelDesk/llms`、`minimax-h3`、`minimax-music3`）与真实 `outputs/`；
  一切破坏性验收只对 `tmp_path` 假目录执行。
- 任何 acceptance_cmd 不写 `/Applications`、`~/Applications`、`~/Library/LaunchAgents`。
- 真机安装 / 首运 / 菜单栏观察 = reality gate（T-packaging-13），附人工 runbook，不伪造证据。
- 错误保持错误：构建失败即非零退出、无半成品；不做静默降级。

## 任务总览与依赖 DAG

| id | 标题 | 依赖 | implements |
|---|---|---|---|
| T-packaging-01 | packaging/ 静态资产 + Info.plist 模板渲染测试 | — | |
| T-packaging-02 | 三份 `==` 钉死的依赖锁 | — | |
| T-packaging-03 | 假 bundle fixture + `sign-app.sh` | 01 | api:signAppBundle |
| T-packaging-04 | `verify-app.sh` 负路径：V3 禁串 / V4 venv 残留 / 全量汇总 | 03 | |
| T-packaging-05 | `verify-app.sh` 正路径：V1/V2/V5/V6/V7 干净通过 | 04 | api:verifyAppBundle |
| T-packaging-06 | `build-app.sh` + 失败无半成品测试 | 02, 05 | |
| T-packaging-07 | `install-app.sh`（tmp dest；异 id 拒绝） | 05 | api:installApp |
| T-packaging-08 | `uninstall-app.sh` 基础：LaunchAgent + App + 默认保数据 + dry-run | 03 | |
| T-packaging-09 | `uninstall-app.sh` purge 模型多重保护 | 08 | api:uninstallApp |
| T-packaging-10 | README 改写为安装后真实行为 | — | |
| T-packaging-11 | 删除五个旧脚本（R-packaging-08 执行半） | — | |
| T-packaging-12 | 离线复用锁定 CPython + Developer ID 无在线 timestamp 全量构建 + V1–V7 全绿（design §5.2） | 06, 11, shell-09 | api:buildAppBundle |
| T-packaging-13 | reality gate：真机安装/首运/菜单栏/卸载 runbook | 07, 09, 12 | |

跨模块 requires（不猜任务 id，只写注册表接口）：

- T-packaging-11 requires `api:listCatalog`、`api:verifyModel`、`api:startDownload`、`api:startVideoJob`、
  `api:startMusicJob`、`api:reapLlmPort`、`api:unloadLlm`、`api:spawnEmbeddedServer`
  （旧脚本行为在 App 内可达后才许删，design §2.7 顺序约束）。
- T-packaging-12 / 13 requires `api:spawnEmbeddedServer`、`ui:mainWindow`、`ui:deskShell`、`api:resolvePaths`
  （真实构建要编 `macos/*.swift`、拷 `desk/` 与 `desk/static/`）。

## 通用工程约定

- 全部脚本 `chmod +x`，shebang `#!/bin/bash`（macOS 自带 bash 3.2：**不用空数组 + `set -u` 的组合**，
  失败收集一律走临时文件）。
- `sign-app.sh`、`verify-app.sh`、`install-app.sh`、`build-app.sh` 用 `set -euo pipefail`；
  `uninstall-app.sh` 按 design §2.6「每步失败不阻塞后续、末尾汇总」用 `set -uo pipefail`（有意偏差，注释注明）。
- pytest 验收统一 `python3 -m pytest <节点id>`（pytest 零收集退出码 5 / 未知节点退出码 4，不可空转绿）。
- 常量单点：bundle id `com.aa.localmodeldesk`（A1）、`LSMinimumSystemVersion=15.0`（A2）、
  版本单点 `packaging/VERSION`（A8）、解释器 `packaging/python-version.txt` = `cpython-3.13.15`（A3）。

---

## 最终代码（各任务按下述文件落盘；每个任务只落它声明的部分）

### `packaging/Info.plist.template`（T-01）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleIdentifier</key>
	<string>com.aa.localmodeldesk</string>
	<key>CFBundleName</key>
	<string>LocalModelDesk</string>
	<key>CFBundleExecutable</key>
	<string>LocalModelDesk</string>
	<key>CFBundleShortVersionString</key>
	<string>@VERSION@</string>
	<key>CFBundleVersion</key>
	<string>@VERSION@</string>
	<key>CFBundleIconFile</key>
	<string>AppIcon</string>
	<key>LSMinimumSystemVersion</key>
	<string>15.0</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
```

### `packaging/VERSION`（T-01）

```
1.0.0
```

### `packaging/python-version.txt`（T-01）

```
cpython-3.13.15
```

### `packaging/entitlements.plist`（T-01，空 dict，A5）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict/>
</plist>
```

### `packaging/icon/icon-1024.png`（T-01，检入的占位图标；用下面一次性命令生成，A9）

```bash
mkdir -p packaging/icon && python3 - <<'EOF'
import struct, zlib
w = h = 1024
row = b"\x00" + bytes((30, 32, 40, 255)) * w        # 每行：filter0 + RGBA*1024
raw = row * h
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 9))
       + chunk(b"IEND", b""))
open("packaging/icon/icon-1024.png", "wb").write(png)
EOF
```

### `packaging/requirements-*.in` 与锁文件（T-02）

三个 `.in` 各一行（design §2.1）：

```
# packaging/requirements-desk.in
mlx-lm==0.31.3
# packaging/requirements-music.in
mlx-minimax-music3==0.0.1a0
# packaging/requirements-h3.in
mlx-h3==0.0.1a3
```

锁文件由构建机 uv 生成（不含头注释与绝对路径，测试强制）：

```bash
for n in desk music h3; do
  uv pip compile --python-version 3.13 --no-header --no-annotate \
    packaging/requirements-$n.in -o packaging/requirements-$n.txt
done
```

### `tests/packaging_fixture.py`（T-01 建立渲染函数；T-03 补齐假 bundle）

```python
"""微型假 .app fixture：几 KB 的伪造树，供 packaging 脚本测试使用。

只在 tmp_path 下造假目录；绝不触碰真实 /Applications、真实模型目录或真实权重。
"""
from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUNDLE_ID = "com.aa.localmodeldesk"

# 桩 python：shell 包装（非 Mach-O，顺带验证 sign-app.sh 的 magic 过滤不误签脚本）
PY_WRAPPER = '#!/bin/sh\nexec /usr/bin/python3 "$@"\n'


def render_info_plist(dest: Path, version: str = "0.0.1") -> None:
    tpl = (REPO / "packaging" / "Info.plist.template").read_text()
    dest.write_text(tpl.replace("@VERSION@", version))


def make_fake_bundle(root: Path, *, sign: bool = True) -> Path:
    """在 root 下伪造一个结构完整、可 ad-hoc 签名、能过 V1–V6 的 LocalModelDesk.app。"""
    app = root / "LocalModelDesk.app"
    res = app / "Contents" / "Resources"
    (app / "Contents" / "MacOS").mkdir(parents=True)
    res.mkdir(parents=True)
    render_info_plist(app / "Contents" / "Info.plist")

    # 真 Mach-O 主执行文件（codesign 需要）
    src = root / "stub.c"
    src.write_text("int main(void){return 0;}\n")
    subprocess.run(
        ["cc", "-x", "c", str(src), "-o", str(app / "Contents" / "MacOS" / "LocalModelDesk")],
        check=True,
    )
    src.unlink()

    (res / "bundle.json").write_text(
        '{"app": "LocalModelDesk", "bundle_version": "0.0.1", "python": "python/bin/python3.13"}\n'
    )
    (res / "AppIcon.icns").write_bytes(b"icns-stub")

    pybin = res / "python" / "bin"
    pybin.mkdir(parents=True)
    py = pybin / "python3.13"
    py.write_text(PY_WRAPPER)
    py.chmod(0o755)

    (res / "desk").mkdir()
    (res / "desk" / "__init__.py").write_text("")
    for libdir, pkgs in {
        "desk": ["mlx_lm", "huggingface_hub"],
        "music": ["mlx_minimax_music3"],
        "h3": ["mlx_h3"],
    }.items():
        for pkg in pkgs:
            d = res / "pylibs" / libdir / pkg
            d.mkdir(parents=True)
            (d / "__init__.py").write_text("")
    (res / "pylibs" / "h3" / "mlx_h3" / "cli.py").write_text("def main():\n    pass\n")
    hf_cli = res / "pylibs" / "desk" / "huggingface_hub" / "cli"
    hf_cli.mkdir()
    (hf_cli / "__init__.py").write_text("")
    (hf_cli / "hf.py").write_text("def main():\n    pass\n")

    if sign:
        subprocess.run([str(REPO / "scripts" / "sign-app.sh"), str(app), "--adhoc"], check=True)
    return app


def make_fake_app_dir(root: Path, bundle_id: str = BUNDLE_ID) -> Path:
    """仅含 Info.plist 的最小假 app（install/uninstall 的 bundle id 校验用）。"""
    app = root / "LocalModelDesk.app"
    (app / "Contents").mkdir(parents=True)
    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump({"CFBundleIdentifier": bundle_id}, f)
    return app
```

### `scripts/sign-app.sh` — `api:signAppBundle`（T-03，R-packaging-04）

```bash
#!/bin/bash
# api:signAppBundle — 由内向外签名（R-packaging-04）。
# 用法: sign-app.sh <app路径> [--identity "…"] [--adhoc]
set -euo pipefail

usage() { echo '用法: sign-app.sh <app路径> [--identity "…"] [--adhoc]' >&2; exit 2; }

APP="${1:-}"
if [[ -z "$APP" || ! -d "$APP" ]]; then usage; fi
shift

IDENTITY="${CODESIGN_IDENTITY:-}"
ADHOC=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --identity) IDENTITY="$2"; shift 2 ;;
    --adhoc)    ADHOC=1; shift ;;
    *) usage ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENTITLEMENTS="$REPO_ROOT/packaging/entitlements.plist"

if [[ "$ADHOC" == 1 ]]; then
  # 开发/测试构建：ad-hoc，跳过 timestamp；不作为正式构建的静默降级（A10）
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

# 1) Resources 里全部 Mach-O（.so/.dylib/内嵌 python 等），由内向外
while IFS= read -r -d '' f; do
  if is_macho "$f"; then
    codesign "${SIGN_ARGS[@]}" "$f"
  fi
done < <(find "$APP/Contents/Resources" -type f -print0 2>/dev/null)

# 2) 主执行文件
codesign "${SIGN_ARGS[@]}" "$APP/Contents/MacOS/LocalModelDesk"

# 3) 整体签一次，封 resource seal
codesign "${SIGN_ARGS[@]}" "$APP"
echo "signed: $APP"
```

### `scripts/verify-app.sh` — `api:verifyAppBundle`（T-04 落 V3/V4+汇总骨架；T-05 补 V1/V2/V5/V6/V7）

```bash
#!/bin/bash
# api:verifyAppBundle — 只读验证 V1–V7（R-packaging-05）。
# 收集全部失败后统一报告再 exit 1（一次跑出完整问题清单，不首错即停）。
# 用法: verify-app.sh <app路径> [--source-root <checkout根>]
set -euo pipefail

APP="${1:-}"
if [[ -z "$APP" || ! -d "$APP" ]]; then
  echo '用法: verify-app.sh <app路径> [--source-root <checkout根>]' >&2; exit 2
fi
shift
SOURCE_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-root) SOURCE_ROOT="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$SOURCE_ROOT" ]]; then
  SOURCE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

RES="$APP/Contents/Resources"
PLIST="$APP/Contents/Info.plist"

# bash 3.2 下空数组 + set -u 会炸，失败收集走临时文件
FAILLOG="$(mktemp)"
trap 'rm -f "$FAILLOG"' EXIT
fail() { printf '  - %s\n' "$1" >> "$FAILLOG"; }

# ---- V1 签名 ----
if ! OUT="$(codesign --verify --deep --strict --verbose=2 "$APP" 2>&1)"; then
  fail "V1 签名验证失败: $OUT"
fi

# ---- V2 plist 键（design §2.1 全键在且非空）----
for k in CFBundleIdentifier CFBundleName CFBundleExecutable CFBundleShortVersionString \
         CFBundleVersion CFBundleIconFile LSMinimumSystemVersion CFBundlePackageType \
         NSHighResolutionCapable; do
  V="$(/usr/libexec/PlistBuddy -c "Print :$k" "$PLIST" 2>/dev/null || true)"
  if [[ -z "$V" ]]; then fail "V2 Info.plist 缺键或为空: $k"; fi
done

# ---- V3 自包含扫描（收集全部命中）----
for s in "/opt/homebrew" "$SOURCE_ROOT" "$HOME/.local/share/uv" "$HOME/.local/bin"; do
  HITS="$(grep -ral -- "$s" "$APP" 2>/dev/null || true)"
  if [[ -n "$HITS" ]]; then
    while IFS= read -r h; do
      fail "V3 自包含违例: 禁串 '$s' 出现在 $h"
    done <<< "$HITS"
  fi
done

# ---- V4 无 venv 残留 ----
while IFS= read -r f; do
  fail "V4 venv 残留 pyvenv.cfg: $f"
done < <(find "$APP" -name pyvenv.cfg -type f 2>/dev/null)
for d in "$RES"/pylibs/*/bin; do
  if [[ -e "$d" ]]; then fail "V4 pylibs bin 残留（shebang 带构建机路径）: $d"; fi
done
while IFS= read -r d; do
  fail "V4 pylibs 内 __pycache__ 残留: $d"
done < <(find "$RES/pylibs" -name __pycache__ -type d 2>/dev/null)

# ---- V5 结构 ----
PYBIN="$RES/python/bin/python3.13"
if [[ ! -x "$PYBIN" ]]; then fail "V5 缺内嵌解释器或不可执行: $PYBIN"; fi
for p in "$RES/desk" "$RES/pylibs/desk" "$RES/pylibs/music" "$RES/pylibs/h3" \
         "$RES/bundle.json" "$RES/AppIcon.icns"; do
  if [[ ! -e "$p" ]]; then fail "V5 缺结构项: $p"; fi
done

# ---- V6 导入冒烟（内嵌解释器 + -s，与运行期契约 design §1.3 一致）----
if [[ -x "$PYBIN" ]]; then
  v6() {
    if ! OUT="$(cd "$RES" && PYTHONPATH="$1" "python/bin/python3.13" -s -c "$2" 2>&1)"; then
      fail "V6 导入失败 [PYTHONPATH=$1] [$2]: $OUT"
    fi
  }
  v6 ".:pylibs/desk" "import desk"
  v6 "pylibs/desk"   "import mlx_lm"
  v6 "pylibs/music"  "import mlx_minimax_music3"
  v6 "pylibs/h3"     "import mlx_h3.cli"
  v6 "pylibs/desk"   "from huggingface_hub.cli.hf import main"
fi

# ---- V7 旧脚本已亡（R-packaging-08 机检半）----
for s in initModels.sh run-h3.sh run-music3.py unload-llm.sh media-gui/start.sh; do
  if [[ -e "$SOURCE_ROOT/$s" ]]; then fail "V7 旧脚本仍存在: $SOURCE_ROOT/$s"; fi
done

if [[ -s "$FAILLOG" ]]; then
  echo "verify-app: 发现以下失败（$APP）：" >&2
  cat "$FAILLOG" >&2
  exit 1
fi
echo "verify-app: OK ($APP)"
```

（T-04 提交的版本 = 上述文件去掉 V1/V2/V5/V6/V7 五段；T-05 补齐为全文。）

### `scripts/build-app.sh` — 构建（T-06 落脚本，T-12 真跑；R-packaging-01/02/03）

```bash
#!/bin/bash
# api:buildAppBundle — 干净 checkout → 自包含、已签名、已验证的 dist/LocalModelDesk.app。
# 任一步失败即非零退出并清 staging；dist/LocalModelDesk.app 名下永不存在半成品（R-packaging-01）。
# 用法: build-app.sh [--output dist] [--identity "…"] [--adhoc] [--python-version cpython-X.Y.Z]
set -euo pipefail

OUTPUT="dist"; IDENTITY=""; ADHOC=0; PYVER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)         OUTPUT="$2"; shift 2 ;;
    --identity)       IDENTITY="$2"; shift 2 ;;
    --adhoc)          ADHOC=1; shift ;;
    --python-version) PYVER="$2"; shift 2 ;;
    *) echo '用法: build-app.sh [--output dist] [--identity "…"] [--adhoc] [--python-version X]' >&2; exit 2 ;;
  esac
done

REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "$PYVER" ]]; then PYVER="$(tr -d '[:space:]' < "$REPO/packaging/python-version.txt")"; fi
VERSION="$(tr -d '[:space:]' < "$REPO/packaging/VERSION")"
MIN_OS="15.0"

mkdir -p "$OUTPUT"
OUTPUT="$(cd "$OUTPUT" && pwd)"
STAGING="$OUTPUT/.staging.$$"
trap 'rm -rf "$STAGING"' EXIT
APP="$STAGING/LocalModelDesk.app"
RES="$APP/Contents/Resources"
mkdir -p "$APP/Contents/MacOS" "$RES"

echo "==> [1/9] Swift 编译"
xcrun swiftc -O "$REPO"/macos/*.swift \
  -o "$APP/Contents/MacOS/LocalModelDesk" -target "arm64-apple-macos$MIN_OS"

echo "==> [2/9] 拷贝 desk 包（含 desk/static/）"
rsync -a --exclude '__pycache__' --exclude '.pytest_cache' "$REPO/desk/" "$RES/desk/"

echo "==> [3/9] 内嵌 CPython $PYVER（python-build-standalone，经 uv）"
PY_DIR="$STAGING/uv-python"
UV_PYTHON_INSTALL_DIR="$PY_DIR" uv python install "$PYVER"
SRC_PY="$(find "$PY_DIR" -maxdepth 1 -type d -name 'cpython-*' | head -n1)"
if [[ -z "$SRC_PY" ]]; then echo "错误：uv 未产出 CPython 目录（$PYVER）" >&2; exit 1; fi
rsync -a "$SRC_PY/" "$RES/python/"
if [[ ! -x "$RES/python/bin/python3.13" ]]; then
  echo "错误：内嵌解释器缺失 $RES/python/bin/python3.13" >&2; exit 1
fi

echo "==> [4/9] 三套 pylibs（uv --target 平铺，禁字节码；R-packaging-02）"
mkdir -p "$RES/requirements"
for name in desk music h3; do
  uv pip install --python "$RES/python/bin/python3.13" --target "$RES/pylibs/$name" \
    --no-compile-bytecode -r "$REPO/packaging/requirements-$name.txt"
  rm -rf "$RES/pylibs/$name/bin"
  find "$RES/pylibs/$name" -type d -name __pycache__ -prune -exec rm -rf {} +
  cp "$REPO/packaging/requirements-$name.txt" "$RES/requirements/"
done

echo "==> [5/9] Info.plist（R-packaging-03）"
sed "s/@VERSION@/$VERSION/g" "$REPO/packaging/Info.plist.template" > "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist"

echo "==> [6/9] 图标"
ICONSET="$STAGING/AppIcon.iconset"
mkdir -p "$ICONSET"
for sz in 16 32 64 128 256 512; do
  sips -z "$sz" "$sz" "$REPO/packaging/icon/icon-1024.png" \
    --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
  sips -z "$((sz * 2))" "$((sz * 2))" "$REPO/packaging/icon/icon-1024.png" \
    --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/AppIcon.icns"

echo "==> [7/9] bundle 标记（packaging design §1.4，foundation 据此判 bundle 态）"
printf '{"app": "LocalModelDesk", "bundle_version": "%s", "python": "python/bin/python3.13"}\n' \
  "$VERSION" > "$RES/bundle.json"

echo "==> [8/9] 签名（R-packaging-04）"
SIGN=("$REPO/scripts/sign-app.sh" "$APP")
if [[ "$ADHOC" == 1 ]]; then SIGN+=(--adhoc); fi
if [[ -n "$IDENTITY" ]]; then SIGN+=(--identity "$IDENTITY"); fi
"${SIGN[@]}"

echo "==> [9/9] 验证（R-packaging-05）"
"$REPO/scripts/verify-app.sh" "$APP" --source-root "$REPO"

# 原子发布：dist/LocalModelDesk.app 名下永不存在半成品
rm -rf "$OUTPUT/LocalModelDesk.app.old"
if [[ -e "$OUTPUT/LocalModelDesk.app" ]]; then
  mv "$OUTPUT/LocalModelDesk.app" "$OUTPUT/LocalModelDesk.app.old"
fi
mv "$APP" "$OUTPUT/LocalModelDesk.app"
rm -rf "$OUTPUT/LocalModelDesk.app.old"
echo "built: $OUTPUT/LocalModelDesk.app"
```

### `scripts/install-app.sh` — `api:installApp`（T-07，R-packaging-06）

```bash
#!/bin/bash
# api:installApp — 先 verify 后安装（R-packaging-06）。
# 验收永远走 --dest <tmp>；对真实 /Applications 的安装只出现在人工 runbook。
set -euo pipefail

APP="dist/LocalModelDesk.app"; DEST="/Applications"; SOURCE_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)         APP="$2"; shift 2 ;;
    --dest)        DEST="$2"; shift 2 ;;
    --source-root) SOURCE_ROOT="$2"; shift 2 ;;
    *) echo '用法: install-app.sh [--app <app>] [--dest <dir>] [--source-root <dir>]' >&2; exit 2 ;;
  esac
done

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
VERIFY=("$SCRIPTS_DIR/verify-app.sh" "$APP")
if [[ -n "$SOURCE_ROOT" ]]; then VERIFY+=(--source-root "$SOURCE_ROOT"); fi
"${VERIFY[@]}"

EXPECTED_ID="com.aa.localmodeldesk"
TARGET="$DEST/LocalModelDesk.app"
if [[ -e "$TARGET" ]]; then
  EXISTING_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \
    "$TARGET/Contents/Info.plist" 2>/dev/null || true)"
  if [[ "$EXISTING_ID" != "$EXPECTED_ID" ]]; then
    echo "错误：$TARGET 已存在且 CFBundleIdentifier='$EXISTING_ID' != '$EXPECTED_ID'，拒绝删除或覆盖。" >&2
    exit 1
  fi
  rm -rf "$TARGET"
fi
mkdir -p "$DEST"
ditto "$APP" "$TARGET"   # ditto 保 xattr 与签名
echo "installed: $TARGET"
```

### `scripts/uninstall-app.sh` — `api:uninstallApp`（T-08 基础 + T-09 purge 保护，R-packaging-07）

```bash
#!/bin/bash
# api:uninstallApp — 卸 LaunchAgent、删 App、可选 purge 用户数据（R-packaging-07）。
# 不变量：模型权重在任何路径组合下都不会被本脚本删除。
# 有意偏差：design §2.6 要求每步失败不阻塞后续、末尾汇总，故不用 set -e。
set -uo pipefail

APP_PATH="/Applications/LocalModelDesk.app"
DATA_ROOT="$HOME/Library/Application Support/LocalModelDesk"
LA_DIR="$HOME/Library/LaunchAgents"
PURGE=0; DRY=0
BUNDLE_ID="com.aa.localmodeldesk"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-path)          APP_PATH="$2"; shift 2 ;;
    --data-root)         DATA_ROOT="$2"; shift 2 ;;
    --launch-agents-dir) LA_DIR="$2"; shift 2 ;;
    --purge-data)        PURGE=1; shift ;;
    --dry-run)           DRY=1; shift ;;
    *) echo '用法: uninstall-app.sh [--app-path P] [--data-root P] [--launch-agents-dir P] [--purge-data] [--dry-run]' >&2; exit 2 ;;
  esac
done

ERRLOG="$(mktemp)"
trap 'rm -f "$ERRLOG"' EXIT
err() { printf '  - %s\n' "$1" >> "$ERRLOG"; }

guarded_rm() {
  # 通用护栏：绝对路径、非 /、非 $HOME、存在才删；符号链接只删链接本身，不跟随
  local p="$1"
  case "$p" in
    /*) ;;
    *) err "护栏：拒绝删除相对路径 '$p'"; return 1 ;;
  esac
  if [[ "$p" == "/" || "$p" == "$HOME" ]]; then
    err "护栏：拒绝删除 '$p'"; return 1
  fi
  if [[ ! -e "$p" && ! -L "$p" ]]; then return 0; fi
  if [[ "$DRY" == 1 ]]; then echo "[dry-run] rm -rf '$p'"; return 0; fi
  if [[ -L "$p" ]]; then rm -f "$p"; else rm -rf "$p"; fi
}

# ---- 1) LaunchAgent（census A11）----
LA_PLIST="$LA_DIR/$BUNDLE_ID.plist"
if [[ "$DRY" == 1 ]]; then
  echo "[dry-run] launchctl bootout gui/$(id -u)/$BUNDLE_ID"
  if [[ -e "$LA_PLIST" ]]; then echo "[dry-run] rm '$LA_PLIST'"; fi
else
  launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true   # 不存在不算错（幂等）
  if [[ -e "$LA_PLIST" ]]; then
    rm -f "$LA_PLIST" || err "删除 LaunchAgent plist 失败: $LA_PLIST"
  fi
fi

# ---- 2) App（bundle id 匹配才删）----
if [[ -e "$APP_PATH" ]]; then
  ACTUAL_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \
    "$APP_PATH/Contents/Info.plist" 2>/dev/null || true)"
  if [[ "$ACTUAL_ID" == "$BUNDLE_ID" ]]; then
    guarded_rm "$APP_PATH" || err "删除 App 失败: $APP_PATH"
  else
    err "App bundle id 不符（'$ACTUAL_ID' != '$BUNDLE_ID'），拒绝删除 $APP_PATH"
  fi
fi

# ---- 3) 数据：默认一概不动；仅 --purge-data 时删，且模型多重保护 ----
if [[ "$PURGE" == 1 && -d "$DATA_ROOT" ]]; then
  CONFIG="$DATA_ROOT/config.json"
  MODELS_ROOT="$DATA_ROOT/models"    # config 不存在 ⇒ 默认布局（自定义根只能经首运写入 config）
  if [[ -e "$CONFIG" ]]; then
    PARSED="$(/usr/bin/python3 -c '
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(3)
root = cfg.get("models_root")
if not isinstance(root, str) or not root.strip():
    sys.exit(3)
print(root)
' "$CONFIG" 2>/dev/null)"
    RC=$?
    if [[ $RC -ne 0 || -z "$PARSED" ]]; then
      echo "错误：$CONFIG 存在但解析失败或缺 models_root——模型根未知，拒绝执行整个 purge，不删任何数据。" >&2
      exit 1
    fi
    MODELS_ROOT="$PARSED"
  fi

  skip_for_models_root() {
    # child == models_root，或互为前缀（任一方在另一方子树内），都跳过
    local child="$1"
    if [[ "$child" == "$MODELS_ROOT" ]]; then return 0; fi
    case "$child/" in "$MODELS_ROOT"/*) return 0 ;; esac
    case "$MODELS_ROOT/" in "$child"/*) return 0 ;; esac
    return 1
  }

  for child in "$DATA_ROOT"/* "$DATA_ROOT"/.[!.]*; do
    if [[ ! -e "$child" && ! -L "$child" ]]; then continue; fi   # 未匹配的字面 glob
    base="$(basename "$child")"
    case "$base" in
      models|llms|minimax-h3|minimax-music3)   # 名字兜底：收编目录被指为 data 邻位
        echo "跳过（模型保护）: $child"; continue ;;
    esac
    if skip_for_models_root "$child"; then
      echo "跳过（models_root 保护）: $child"; continue
    fi
    guarded_rm "$child" || err "purge 删除失败: $child"
  done
fi

if [[ -s "$ERRLOG" ]]; then
  echo "uninstall-app: 以下步骤失败：" >&2
  cat "$ERRLOG" >&2
  exit 1
fi
echo "uninstall-app: 完成"
```

### `tests/test_packaging.py`（累积落盘；每个任务只加它那组测试）

```python
"""packaging 模块验收测试（design §5.1）。

全部对 tmp_path 假目录执行；测试代码不出现真实 /Applications、真实模型路径（授权红线）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from packaging_fixture import (
    BUNDLE_ID,
    REPO,
    make_fake_app_dir,
    make_fake_bundle,
    render_info_plist,
)

SIGN = REPO / "scripts" / "sign-app.sh"
VERIFY = REPO / "scripts" / "verify-app.sh"
INSTALL = REPO / "scripts" / "install-app.sh"
UNINSTALL = REPO / "scripts" / "uninstall-app.sh"
BUILD = REPO / "scripts" / "build-app.sh"

PLIST_KEYS = [
    "CFBundleIdentifier", "CFBundleName", "CFBundleExecutable",
    "CFBundleShortVersionString", "CFBundleVersion", "CFBundleIconFile",
    "LSMinimumSystemVersion", "CFBundlePackageType", "NSHighResolutionCapable",
]


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def verify(app, source_root):
    return run([VERIFY, app, "--source-root", source_root])


def clean_source_root(tmp_path):
    d = tmp_path / "srcroot"
    d.mkdir()
    return d


# ---------------------------------------------------------------- T-packaging-01

def test_plist_template_renders_all_keys(tmp_path):
    import plistlib
    plist_path = tmp_path / "Info.plist"
    render_info_plist(plist_path, version="9.9.9")
    r = run(["plutil", "-lint", plist_path])
    assert r.returncode == 0, r.stdout + r.stderr
    data = plistlib.loads(plist_path.read_bytes())
    for key in PLIST_KEYS:
        assert key in data and data[key] not in ("", None), f"缺键或为空: {key}"
    assert data["CFBundleShortVersionString"] == "9.9.9"
    assert data["CFBundleVersion"] == "9.9.9"
    assert data["CFBundleIdentifier"] == BUNDLE_ID
    assert data["LSMinimumSystemVersion"] == "15.0"
    assert "@VERSION@" not in plist_path.read_text()


def test_entitlements_is_empty_dict():
    import plistlib
    data = plistlib.loads((REPO / "packaging" / "entitlements.plist").read_bytes())
    assert data == {}


def test_icon_source_is_1024_png():
    r = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight",
             REPO / "packaging" / "icon" / "icon-1024.png"])
    assert r.returncode == 0, r.stderr
    assert "pixelWidth: 1024" in r.stdout and "pixelHeight: 1024" in r.stdout


# ---------------------------------------------------------------- T-packaging-02

def test_requirements_locks_are_pinned():
    tops = {
        "desk": "mlx-lm==0.31.3",
        "music": "mlx-minimax-music3==0.0.1a0",
        "h3": "mlx-h3==0.0.1a3",
    }
    for name, top in tops.items():
        lock = REPO / "packaging" / f"requirements-{name}.txt"
        text = lock.read_text()
        lines = [l.strip() for l in text.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        assert lines, f"{lock} 为空"
        for line in lines:
            assert re.fullmatch(r"[A-Za-z0-9._\[\],-]+==[A-Za-z0-9.!+-]+", line), \
                f"{lock}: 未钉死的行 '{line}'"
        assert top in text, f"{lock} 缺顶层钉死项 {top}"
        for banned in ["file://", "/Users/", "/opt/"]:
            assert banned not in text, f"{lock} 含 '{banned}'"


# ---------------------------------------------------------------- T-packaging-03

def test_sign_adhoc_fixture_verifies(tmp_path):
    app = make_fake_bundle(tmp_path)          # 内部已调 sign-app.sh --adhoc
    r = run(["codesign", "--verify", "--deep", "--strict", app])
    assert r.returncode == 0, r.stderr


def test_sign_no_identity_found_errors(tmp_path):
    app = make_fake_bundle(tmp_path, sign=False)
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    sec = stub_bin / "security"
    sec.write_text('#!/bin/sh\necho "     0 valid identities found"\n')
    sec.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    env.pop("CODESIGN_IDENTITY", None)
    r = subprocess.run([str(SIGN), str(app)], capture_output=True, text=True, env=env)
    assert r.returncode != 0
    assert "找不到 Developer ID Application" in r.stderr
    assert "0 valid identities found" in r.stderr   # 候选列表已打印


# ---------------------------------------------------------------- T-packaging-04

def test_verify_flags_homebrew_reference(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)
    (app / "Contents/Resources/pylibs/desk/leak.txt").write_text(
        "interp = /opt/homebrew/bin/python3\n")
    r = verify(app, src)
    assert r.returncode != 0
    assert "/opt/homebrew" in r.stderr and "leak.txt" in r.stderr


def test_verify_flags_checkout_reference(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)
    (app / "Contents/Resources/desk/leak2.txt").write_text(f"path = {src}/desk\n")
    r = verify(app, src)
    assert r.returncode != 0 and "leak2.txt" in r.stderr


def test_verify_flags_pyvenv_and_bin(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)
    (app / "Contents/Resources/pylibs/desk/pyvenv.cfg").write_text("home = /nowhere\n")
    bindir = app / "Contents/Resources/pylibs/desk/bin"
    bindir.mkdir()
    (bindir / "hf").write_text("#!/nowhere/python\n")
    r = verify(app, src)
    assert r.returncode != 0
    assert "pyvenv.cfg" in r.stderr and "pylibs" in r.stderr and "/bin" in r.stderr


def test_verify_reports_all_failures_at_once(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)
    (app / "Contents/Resources/desk/leak.txt").write_text("/opt/homebrew\n")
    (app / "Contents/Resources/pylibs/music/pyvenv.cfg").write_text("home = x\n")
    r = verify(app, src)
    assert r.returncode != 0
    assert "leak.txt" in r.stderr and "pyvenv.cfg" in r.stderr   # 两类问题同报


# ---------------------------------------------------------------- T-packaging-05

def test_verify_passes_clean_fixture(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)
    r = verify(app, src)
    assert r.returncode == 0, r.stderr
    assert "verify-app: OK" in r.stdout


# ---------------------------------------------------------------- T-packaging-06

def test_build_failure_leaves_no_half_product(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    keep = out / "LocalModelDesk.app"
    keep.mkdir()
    (keep / "marker.txt").write_text("上一次完好产物")
    r = run([BUILD, "--output", out, "--adhoc", "--python-version", "cpython-0.0.0-bogus"])
    assert r.returncode != 0
    assert (keep / "marker.txt").read_text() == "上一次完好产物"   # 既有产物未被动
    leftovers = [p.name for p in out.iterdir() if p.name.startswith(".staging")]
    assert leftovers == []                                        # staging 已清


# ---------------------------------------------------------------- T-packaging-07

def test_install_to_tmp_dest(tmp_path):
    src = clean_source_root(tmp_path)
    app = make_fake_bundle(tmp_path)

    dest = tmp_path / "FakeApplications"
    dest.mkdir()
    r = run([INSTALL, "--app", app, "--dest", dest, "--source-root", src])
    assert r.returncode == 0, r.stderr
    installed = dest / "LocalModelDesk.app"
    assert (installed / "Contents/MacOS/LocalModelDesk").exists()
    assert (installed / "Contents/Resources/bundle.json").exists()

    # 已存在同名但异 bundle id → 拒绝且不删
    dest2 = tmp_path / "FakeApplications2"
    dest2.mkdir()
    make_fake_app_dir(dest2, bundle_id="com.other.thing")
    r2 = run([INSTALL, "--app", app, "--dest", dest2, "--source-root", src])
    assert r2.returncode != 0
    assert (dest2 / "LocalModelDesk.app/Contents/Info.plist").exists()

    # 已存在同 id → 覆盖成功（幂等重装）
    r3 = run([INSTALL, "--app", app, "--dest", dest, "--source-root", src])
    assert r3.returncode == 0, r3.stderr


# ---------------------------------------------------------------- T-packaging-08

def _uninstall_env(tmp_path):
    """launchctl 桩：记录调用参数，永远成功。"""
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    log = tmp_path / "launchctl.log"
    lc = stub_bin / "launchctl"
    lc.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    lc.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    return env, log


def _tree_state(root: Path):
    entries = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            st = f"l:{os.readlink(p)}"
        elif p.is_dir():
            st = "d"
        else:
            st = hashlib.sha256(p.read_bytes()).hexdigest()
        entries.append((str(p.relative_to(root)), st))
    return entries


def _basic_layout(tmp_path, bundle_id=BUNDLE_ID):
    apps = tmp_path / "FakeApplications"
    apps.mkdir()
    app = make_fake_app_dir(apps, bundle_id=bundle_id)
    la = tmp_path / "LaunchAgents"
    la.mkdir()
    (la / "com.aa.localmodeldesk.plist").write_text("<plist/>")
    data = tmp_path / "data"
    (data / "models" / "llms").mkdir(parents=True)
    (data / "models" / "llms" / "w.safetensors").write_bytes(b"fake-weights")
    (data / "sessions").mkdir()
    (data / "sessions" / "s1.json").write_text("{}")
    (data / "config.json").write_text(json.dumps({"models_root": str(data / "models")}))
    return app, la, data


def _run_uninstall(app, la, data, env, *extra):
    return subprocess.run(
        [str(UNINSTALL), "--app-path", str(app), "--data-root", str(data),
         "--launch-agents-dir", str(la), *extra],
        capture_output=True, text=True, env=env)


def test_uninstall_removes_app_and_plist(tmp_path):
    env, log = _uninstall_env(tmp_path)
    app, la, data = _basic_layout(tmp_path)
    r = _run_uninstall(app, la, data, env)
    assert r.returncode == 0, r.stderr
    assert not app.exists()
    assert not (la / "com.aa.localmodeldesk.plist").exists()
    logged = log.read_text()
    assert "bootout" in logged and "com.aa.localmodeldesk" in logged


def test_uninstall_keeps_data_by_default(tmp_path):
    env, _ = _uninstall_env(tmp_path)
    app, la, data = _basic_layout(tmp_path)
    before = _tree_state(data)
    r = _run_uninstall(app, la, data, env)
    assert r.returncode == 0, r.stderr
    assert _tree_state(data) == before   # 无 --purge-data ⇒ 数据分毫未动


def test_uninstall_dry_run_touches_nothing(tmp_path):
    env, _ = _uninstall_env(tmp_path)
    app, la, data = _basic_layout(tmp_path)
    before = _tree_state(tmp_path)
    r = _run_uninstall(app, la, data, env, "--purge-data", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "[dry-run]" in r.stdout
    assert _tree_state(tmp_path) == before   # 整树 hash 不变


def test_uninstall_wrong_bundle_id_refuses(tmp_path):
    env, _ = _uninstall_env(tmp_path)
    app, la, data = _basic_layout(tmp_path, bundle_id="com.evil.impostor")
    r = _run_uninstall(app, la, data, env)
    assert r.returncode != 0
    assert app.exists()   # 异 id 不删


# ---------------------------------------------------------------- T-packaging-09

def test_uninstall_purge_never_touches_models(tmp_path):
    env, _ = _uninstall_env(tmp_path)
    apps = tmp_path / "FakeApplications"
    apps.mkdir()
    app = make_fake_app_dir(apps)
    la = tmp_path / "LaunchAgents"
    la.mkdir()
    data = tmp_path / "data"
    external = tmp_path / "external-models"           # config 指向的外部 models_root
    (external / "minimax-h3").mkdir(parents=True)
    (external / "minimax-h3" / "w.safetensors").write_bytes(b"x" * 32)
    (data / "models" / "llms").mkdir(parents=True)    # 默认位置的假权重
    (data / "models" / "llms" / "w.safetensors").write_bytes(b"y" * 32)
    (data / "llms").mkdir()                           # 收编目录被指为 data 邻位（名字兜底）
    (data / "llms" / "z.safetensors").write_bytes(b"z" * 32)
    (data / "sessions").mkdir()
    (data / "sessions" / "s.json").write_text("{}")
    (data / "logs").mkdir()
    (data / "logs" / "desk.log").write_text("log")
    (data / "outputs").mkdir()
    (data / "outputs" / "a.mp4").write_bytes(b"v")
    (data / "history.jsonl").write_text("{}\n")
    (data / "config.json").write_text(json.dumps({"models_root": str(external)}))

    models_before = _tree_state(data / "models")
    external_before = _tree_state(external)
    llms_before = _tree_state(data / "llms")
    r = _run_uninstall(app, la, data, env, "--purge-data")
    assert r.returncode == 0, r.stderr
    assert _tree_state(data / "models") == models_before
    assert _tree_state(external) == external_before
    assert _tree_state(data / "llms") == llms_before
    for gone in ["config.json", "sessions", "logs", "outputs", "history.jsonl"]:
        assert not (data / gone).exists(), f"{gone} 应被 purge"


def test_uninstall_purge_refuses_on_corrupt_config(tmp_path):
    for i, corrupt in enumerate(["{not json", json.dumps({"other": True})]):
        env, _ = _uninstall_env(tmp_path / f"env{i}")
        data = tmp_path / f"data{i}"
        (data / "my-weights" / "llms").mkdir(parents=True)   # 自定义名的模型目录
        (data / "my-weights" / "llms" / "w.safetensors").write_bytes(b"w")
        (data / "sessions").mkdir()
        (data / "sessions" / "s.json").write_text("{}")
        (data / "config.json").write_text(corrupt)
        before = _tree_state(data)
        r = _run_uninstall(tmp_path / f"no-app{i}", tmp_path / f"no-la{i}", data,
                           env, "--purge-data")
        assert r.returncode != 0
        assert "模型根未知" in r.stderr
        assert _tree_state(data) == before   # 整树分毫未动


# ---------------------------------------------------------------- T-packaging-10

def test_readme_states_real_behavior():
    text = (REPO / "README.md").read_text()
    for required in [
        "0.0.0.0:8770",
        "无鉴权",
        "~/Library/Application Support/LocalModelDesk/models",
        "scripts/build-app.sh",
        "/Applications",
        "未公证",
        "菜单栏",
        "不自启",
        "收编",
    ]:
        assert required in text, f"README 缺少事实陈述: {required}"
    for banned in [
        "推理不出门",
        "开机后工作台是活的",
        "开机自启",
        "initModels.sh",
        "run-h3.sh",
        "run-music3.py",
        "unload-llm.sh",
    ]:
        assert banned not in text, f"README 仍含过时表述: {banned}"


# ---------------------------------------------------------------- T-packaging-11

def test_no_legacy_scripts_in_repo():
    for legacy in ["initModels.sh", "run-h3.sh", "run-music3.py",
                   "unload-llm.sh", "media-gui/start.sh"]:
        assert not (REPO / legacy).exists(), f"旧脚本仍在: {legacy}"
```

---

## 任务明细（TDD 步骤）

每个任务的节奏一致：**(a)** 把该任务那组测试加进 `tests/test_packaging.py`（及 fixture），
**(b)** 跑 acceptance_cmd 确认红（脚本/资产尚不存在），**(c)** 落上文对应实现，`chmod +x` 脚本，
**(d)** 跑 acceptance_cmd 绿，**(e)** `git add -A && git commit`。下面只写各任务的特有信息。

### T-packaging-01 静态资产 + plist 模板（R-packaging-03）

- 新建 `packaging/`：`Info.plist.template`、`VERSION`、`python-version.txt`、`entitlements.plist`、
  `icon/icon-1024.png`（用上文生成命令产出后检入）。
- 新建 `tests/packaging_fixture.py`（此时只含 `REPO`、`BUNDLE_ID`、`PY_WRAPPER`、`render_info_plist`）。
- 测试：`test_plist_template_renders_all_keys`、`test_entitlements_is_empty_dict`、`test_icon_source_is_1024_png`。

### T-packaging-02 依赖锁（R-packaging-02 静态半）

- 三个 `.in` + `uv pip compile --no-header --no-annotate` 生成三份全 `==` 锁，检入。
- 测试：`test_requirements_locks_are_pinned`（钉死格式、顶层版本、无 `file://`、`/Users/`、`/opt/`）。

### T-packaging-03 假 bundle fixture + sign-app.sh（R-packaging-04；implements `api:signAppBundle`）

- `tests/packaging_fixture.py` 补 `make_fake_bundle`、`make_fake_app_dir`。
- `scripts/sign-app.sh` 如上：身份解析（`--identity` > `$CODESIGN_IDENTITY` > 唯一 Developer ID）、
  Mach-O magic 过滤、由内向外、`--force` 幂等、`--adhoc` 不静默替代正式签名。
- 测试：`test_sign_adhoc_fixture_verifies`（ad-hoc 签后 `codesign --verify --deep --strict` 过）、
  `test_sign_no_identity_found_errors`（PATH 桩 `security` 无身份 → 非零并打印候选）。
  单元测试**只用 `--adhoc`**，不动真证书、不联网 timestamp。

### T-packaging-04 verify 负路径（R-packaging-05 的 V3/V4 + 全量汇总）

- `scripts/verify-app.sh` 落参数解析 + 临时文件失败收集骨架 + V3 禁串扫描 + V4 venv 残留。
- 测试：`test_verify_flags_homebrew_reference`、`test_verify_flags_checkout_reference`、
  `test_verify_flags_pyvenv_and_bin`、`test_verify_reports_all_failures_at_once`。

### T-packaging-05 verify 正路径（V1/V2/V5/V6/V7；implements `api:verifyAppBundle`）

- 补 V1 签名、V2 plist 逐键、V5 结构、V6 内嵌解释器 `-s` 导入冒烟（桩 python 包装 `/usr/bin/python3`，
  与运行期契约同参）、V7 旧脚本检查（`--source-root` 参数化，测试传干净 tmp 根）。
- 测试：`test_verify_passes_clean_fixture` → 退出码 0。
  同时回归 T-04 四条负测试仍红得正确（种下问题必被指认）。

### T-packaging-06 build-app.sh + 失败无半成品（R-packaging-01/02/03 脚本半）

- `scripts/build-app.sh` 如上（staging + trap、9 步、原子发布）；`.gitignore` 增加 `dist/`。
- 测试：`test_build_failure_leaves_no_half_product` —— 注入 `--python-version cpython-0.0.0-bogus`
  对 tmp 输出跑构建：非零退出、既有 `LocalModelDesk.app` 原封不动、无 `.staging.*` 残留。
  （此测试不需要 `macos/`、`desk/` 就绪：无论失败在第 1 步还是第 3 步，断言都成立且确定。）

### T-packaging-07 install-app.sh（R-packaging-06；implements `api:installApp`）

- 脚本如上：先 verify、异 id 拒绝、`ditto` 落位；`--source-root` 透传给 verify（测试传干净 tmp 根）。
- 测试：`test_install_to_tmp_dest`（tmp dest 落成完整 bundle；异 id 已存在拒绝且不删；同 id 幂等覆盖）。

### T-packaging-08 uninstall 基础（R-packaging-07 前半）

- 脚本如上第 1/2 步 + 护栏 + 汇总（purge 段此时可为空实现，只认 `--purge-data` 参数）。
- 测试：`test_uninstall_removes_app_and_plist`（launchctl PATH 桩记录 bootout）、
  `test_uninstall_keeps_data_by_default`、`test_uninstall_dry_run_touches_nothing`、
  `test_uninstall_wrong_bundle_id_refuses`。

### T-packaging-09 uninstall purge 模型多重保护（R-packaging-07 后半；implements `api:uninstallApp`）

- 补第 3 步：名字兜底（`models`/`llms`/`minimax-h3`/`minimax-music3`）、`config.json` 的
  `models_root` 双向前缀跳过、损坏 config ⇒ 拒绝整个 purge。
- 测试：`test_uninstall_purge_never_touches_models`、`test_uninstall_purge_refuses_on_corrupt_config`。
- 不变量声明：**模型权重在任何路径组合下都不会被本脚本删除**（两条测试即其证明）。

### T-packaging-10 README 改写（R-packaging-09）

先加 `test_readme_states_real_behavior`（跑红），再整篇改写 `README.md`。新 README 必含（骨架）：

```markdown
# 本地模型台（LocalModelDesk）

macOS 菜单栏 App：本地聊天、文生视频、文生歌曲收在一张台上，
并保证同一时刻只有一件重活占着机器。

## 安装

1. `scripts/build-app.sh` 从干净 checkout 构建出 `dist/LocalModelDesk.app`
   （Developer ID 签名 + hardened runtime，**未公证**）。
2. 把 `dist/LocalModelDesk.app` 拷进 `/Applications`（或运行 `scripts/install-app.sh`）。
3. 因未公证，首次启动如被 Gatekeeper 拦下：右键 → 打开，确认一次即可。

## 形态

- **不自启**。双击打开即全部可用；旧的 LaunchAgent 由 `scripts/uninstall-app.sh` 卸除。
- 菜单栏常驻：关掉窗口不退出；菜单栏 Quit 才终止内嵌服务。

## 模型目录

- 默认 `~/Library/Application Support/LocalModelDesk/models`，首次运行可改。
- 机器上已有的权重走**收编**：首运指向既有目录即可，不重新下载。
- 换机器 = 装 App 后在资源面板逐项补下（支持断点续传、删除与磁盘核算）。

## 对外 API（事实陈述）

台面服务在 `0.0.0.0:8770` 提供 OpenAI 与 Anthropic 兼容接口，**无鉴权**：
同一网络上的任何设备、以及本机浏览器里任何知道端口的页面，都能驱动本机模型并读取输出。
需要收紧时在网关加令牌校验（约 20 行改动）。

## 旧脚本去哪了

根目录脚本已全部吸进 App：目录/下载 → 资源面板；出视频/出歌 → 对应面板；
卸载聊天模型 → 状态条。

## 卸载

`scripts/uninstall-app.sh`：移除 App 与旧 LaunchAgent；用户数据仅在 `--purge-data` 时删除；
**模型权重在任何情况下都不会被自动删除**。
```

（成稿保留现 README 中仍为真的产品叙述；上述骨架给出测试断言的全部必含/必亡串：
含 `0.0.0.0:8770`、`无鉴权`、默认模型目录、`scripts/build-app.sh`、`/Applications`、`未公证`、
`菜单栏`、`不自启`、`收编`；不含 `推理不出门`、`开机后工作台是活的`、`开机自启` 与四个旧脚本名。）

### T-packaging-11 删除旧脚本（R-packaging-08 执行半）

- 前置（跨模块 requires，不进 depends_on）：`api:listCatalog`/`api:verifyModel`/`api:startDownload`
  （resources 吸收 initModels.sh）、`api:startVideoJob`（run-h3.sh）、`api:startMusicJob`（run-music3.py）、
  `api:reapLlmPort`+`api:unloadLlm`（unload-llm.sh）、`api:spawnEmbeddedServer`（media-gui/start.sh）
  均已可消费——供给方模块各自的测试即行为可达的证明（design §2.7）。
- 动作：先加 `test_no_legacy_scripts_in_repo`（红），然后
  `git rm initModels.sh run-h3.sh run-music3.py unload-llm.sh media-gui/start.sh`（绿）。
- 顺带跑 census「重跑方式」的 `ls` 行确认全部 `No such file`。

### T-packaging-12 真实全量构建（design §5.2；implements `api:buildAppBundle`）

- 修复构建时 relocation/sanitization 后，以完整机器证明收口：
  `"$MEGASTORM_TEST_PYTHON" -m pytest tests/test_packaging.py && scripts/build-app.sh --output dist && scripts/verify-app.sh dist/LocalModelDesk.app`。构建器优先复用 `MEGASTORM_EMBEDDED_PYTHON` 指向的锁定 standalone CPython 根目录；未提供时才由 `uv` 安装。复制后从 `SRC_PY` 推导并删除真实 source prefix，使用 macOS 可用的 portable 文本遍历净化 `/opt/homebrew`，不得用 runner scratch `HOME` 猜源路径，也不得以 `grep -Z ... || true` 吞掉未执行的净化。`MEGASTORM_OFFLINE_CODESIGN=1` 时仍使用 Developer ID 身份，但明确关闭在线 timestamp；worker 不因此获得公网权限，真实 Gatekeeper/安装由 T-packaging-13 reality gate 收口。
  Developer ID 正式签名（本机证书实测在）、`--timestamp` 走网络、uv 拉 PBS CPython 与三套 PyPI 依赖
  （环境实测网络可用；uv 有缓存，二次构建不重复下载）。
  V1–V7 全绿 = R-packaging-01/02/03/04/05 完成；V6 用内嵌解释器真实导入
  `desk` / `mlx_lm` / `mlx_minimax_music3` / `mlx_h3.cli` / `huggingface_hub.cli.hf`。
- 需要 `macos/*.swift`（shell）、`desk/` 与 `desk/static/`（foundation/ui）、旧脚本已删（T-11，否则 V7 红）。

### T-packaging-13 reality gate：真机安装 / 首运 / 菜单栏 / 卸载（R-packaging-06/07 的真机半）

`reality_gate: true`。acceptance_cmd 只复核产物仍然有效（`verify-app.sh dist/LocalModelDesk.app`）；
真正验收按下述 runbook 由人工执行。runbook 同时检入
`docs/superpowers/runbooks/2026-08-31-packaging-install-runbook.md`（内容如下）。
人工观察另写入
`docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/packaging-reality.md`，通过时单独写
`VERDICT: PASS`；签核路径不在任务 artifact contract 内，agent 无权代写。

#### 人工验收 runbook（不得伪造，不得由 agent 对真实 /Applications 执行）

前置：`dist/LocalModelDesk.app` 存在且 `scripts/verify-app.sh dist/LocalModelDesk.app` 绿。

1. **安装**：人工执行 `scripts/install-app.sh`（默认 `--dest /Applications`）。
   预期：脚本先 verify 再 `ditto`，结束打印 `installed: /Applications/LocalModelDesk.app`。
2. **Gatekeeper（未公证）**：双击若被拦，右键 → 打开 → 确认。预期：确认一次后正常启动。
3. **首运**：预期弹出目录选择（`ui:firstRunPane`/原生 NSOpenPanel），选择既有权重目录可**收编**
   （不复制、不重下 339G）；观察资源面板目录状态与磁盘占用与实际相符。
4. **菜单栏形态**：预期菜单栏出现状态项、Dock 有图标；关闭主窗口 App 不退出（菜单栏项仍在，
   再点可回到窗口）。
5. **Quit 收口**：菜单栏 Quit。预期 App 退出，且
   `lsof -iTCP:8766 -iTCP:8767 -iTCP:8770 -sTCP:LISTEN` 无任何输出（内嵌服务与 mlx-lm 全部收割）。
6. **卸载**：人工执行 `scripts/uninstall-app.sh`。预期：
   - `launchctl print gui/$UID/com.aa.localmodeldesk` 报 not found（旧 LaunchAgent 已卸，census A11）；
   - `/Applications/LocalModelDesk.app` 消失；
   - 模型目录原地未动（`du -sh` 前后一致）；用户数据仍在（未加 `--purge-data`）。

通过标准：6 步全部符合预期。任何一步不符 ⇒ 记 defect 回 packaging/shell，不得改测试凑绿。

---

## 验收命令一览

| 任务 | acceptance_cmd（cwd = 仓库根）|
|---|---|
| T-01 | `python3 -m pytest tests/test_packaging.py::test_plist_template_renders_all_keys tests/test_packaging.py::test_entitlements_is_empty_dict tests/test_packaging.py::test_icon_source_is_1024_png` |
| T-02 | `python3 -m pytest tests/test_packaging.py::test_requirements_locks_are_pinned` |
| T-03 | `python3 -m pytest tests/test_packaging.py::test_sign_adhoc_fixture_verifies tests/test_packaging.py::test_sign_no_identity_found_errors` |
| T-04 | `python3 -m pytest tests/test_packaging.py::test_verify_flags_homebrew_reference tests/test_packaging.py::test_verify_flags_checkout_reference tests/test_packaging.py::test_verify_flags_pyvenv_and_bin tests/test_packaging.py::test_verify_reports_all_failures_at_once` |
| T-05 | `python3 -m pytest tests/test_packaging.py::test_verify_passes_clean_fixture tests/test_packaging.py::test_verify_flags_homebrew_reference` |
| T-06 | `python3 -m pytest tests/test_packaging.py::test_build_failure_leaves_no_half_product` |
| T-07 | `python3 -m pytest tests/test_packaging.py::test_install_to_tmp_dest` |
| T-08 | `python3 -m pytest tests/test_packaging.py::test_uninstall_removes_app_and_plist tests/test_packaging.py::test_uninstall_keeps_data_by_default tests/test_packaging.py::test_uninstall_dry_run_touches_nothing tests/test_packaging.py::test_uninstall_wrong_bundle_id_refuses` |
| T-09 | `python3 -m pytest tests/test_packaging.py::test_uninstall_purge_never_touches_models tests/test_packaging.py::test_uninstall_purge_refuses_on_corrupt_config` |
| T-10 | `python3 -m pytest tests/test_packaging.py::test_readme_states_real_behavior` |
| T-11 | `python3 -m pytest tests/test_packaging.py::test_no_legacy_scripts_in_repo` |
| T-12 | `python3 -m pytest tests/test_packaging.py && scripts/build-app.sh --output dist && scripts/verify-app.sh dist/LocalModelDesk.app` |
| T-13 | `scripts/verify-app.sh dist/LocalModelDesk.app`（真机步骤见 runbook，人工执行）|
