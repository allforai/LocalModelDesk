# Cross-Exam 2026-09-13 修复 · D 构建、原生壳、配置恢复与死契约 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** README 的默认构建能产出新包；配置写坏后能在界面里一键恢复；设置里的网关报错只反映当前状态；菜单栏显示模型名；⌘, 可用、菜单与右键菜单是中文；服务意外退出时错误页给出退出原因；死契约要么接上、要么删掉、要么标明是测试缝。

**Architecture:** 构建脚本在签名前清掉构建期写入的 `__pycache__`，并用 `compileall -s/-p` 去掉字节码里的构建机路径。配置恢复：`reset_config` 只对确实损坏的配置生效；前端把致命错误渲染成独立小组件 `widgets/fatal.js`，损坏时给出「重新设置」按钮。网关把"这次保存失败"（`apply_error`，只随 POST 返回）与"现在没在监听的原因"（`last_error`，仅未监听时给出）分开。原生壳新增纯函数（放 `ShellStatus.swift`，可由 headless harness 测）并在 AppKit 侧接线。

**Tech Stack:** bash · Python 3.13 stdlib · Swift 5 / AppKit / WebKit · 零依赖 ES modules · pytest · node:test · Playwright

**Spec:** `docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md` §缺口清单 G1、G2、G6、G7、G8、G14、G16、J25，§缺陷模式 P1（12 位点），未拉的线「uninstall --launch-agents-dir 仍 bootout 真实域」「bootout 失败被吞」「reset 对合法配置也改名并重开 0.0.0.0 网关」「编辑/窗口菜单混入英文项」「右键菜单英文 Reload」「错误卡片详情只有日志路径」；证据 `evidence/q01/`、`q07/`、`q08/`、`q12/`、`q14/`、`q15/`、`q25/`、`q35/`。需求：`docs/superpowers/specs/2026-08-31-packaging-spec.md` R-packaging-02/03，`2026-08-31-foundation-spec.md` R-foundation-05，`2026-08-31-gateway-spec.md` R-gateway-06，`2026-08-31-shell-spec.md` R-shell-02/05。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）。
- 前端：零依赖 ES modules；`createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文；机器码不作唯一解释。
- 测试命令：`python3 -m pytest -q`、`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`；Swift 改动必须跑 `python3 -m pytest tests/test_shell_*.py -q`。
- 验证门必须包含 e2e（`desk/static/` 改动）。
- 测试永不触碰 `~/LocalModelDesk` 或真实数据根；卸载脚本测试一律假 `HOME` 与假 `launchctl`。
- 构建验证只用 `--output` 指向本计划自己的临时目录或默认 `dist/`；不得覆盖 `/Applications` 里的已装应用。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `scripts/build-app.sh` | 全程 `PYTHONDONTWRITEBYTECODE=1`；签名前清缓存、去路径预编译 |
| `tests/e2e/test_statusbar_memory.py` | 提交工作区里已有的取整读数修正（G6-D） |
| `scripts/uninstall-app.sh` | 只在默认 LaunchAgents 目录时 bootout；bootout 失败要报 |
| `desk/foundation/errors.py`、`config.py`、`routes.py` | `ConfigNotCorruptError`；`reset_config(force=False)` |
| `desk/static/js/widgets/fatal.js`（新）、`main.js`、`api.js`、`index.html`、`app.css` | 致命错误组件与「重新设置」 |
| `desk/gateway/service.py`、`desk/static/js/panes/settings.js` | `apply_error` 与 `last_error` 分离 |
| `desk/arbiter/core.py` | `_public_holder` 用 `Holder.public_view()` |
| `macos/ShellStatus.swift`、`macos/harness/ShellHarness.swift` | 纯函数：`isSettingsShortcut`、`serviceExitDescription`、`logTail`、`errorPageHTML(logTail:)` |
| `macos/AppDelegate.swift`、`MainWindowController.swift`、`ServerController.swift` | ⌘, 监听、右键菜单中文、退出原因 |
| `packaging/Info.plist.template`、`scripts/build-app.sh` | `CFBundleDevelopmentRegion` 与 `zh-Hans.lproj` |
| `desk/llm/service.py`、`desk/testing/harness.py`、`desk/arbiter/core.py`、`desk/resources/http.py`、`desk/llm/routes.py`、`macos/*.swift`、`desk/static/js/panes/resources.js` | 死契约清理 |

---

### Task 1: 默认构建产得出包（字节码不带构建机路径）

**Files:**
- Modify: `scripts/build-app.sh`（顶部 export；第 8 步预编译）
- Modify: `README.md`（构建段落）
- Commit: `tests/e2e/test_statusbar_memory.py`（工作区已有改动）
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: 构建全程环境变量 `PYTHONDONTWRITEBYTECODE=1`；第 8 步命令序列固定为：清 `$RES/python`、`$RES/pylibs`、`$RES/desk` 下全部 `__pycache__`，再 `compileall -q -f -s "$RES" -p "LocalModelDesk.app/Contents/Resources" "$RES/desk"`。

- [ ] **Step 1: Write the failing tests**

在 `tests/test_packaging.py` 末尾追加：

```python
def test_precompiled_bytecode_never_embeds_the_build_directory(tmp_path):
    """dist/ 在仓库里时，pyc 的 co_filename 会带仓库路径，V3 拒绝整个包（cross-exam 2026-09-13 G1）。"""
    import marshal
    import sys

    res = tmp_path / "repo-marker" / "dist" / "LocalModelDesk.app" / "Contents" / "Resources"
    (res / "desk").mkdir(parents=True)
    (res / "desk" / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    subprocess.run([sys.executable, "-s", "-m", "compileall", "-q", "-f",
                    "-s", str(res), "-p", "LocalModelDesk.app/Contents/Resources", str(res / "desk")],
                   check=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    pyc = next((res / "desk" / "__pycache__").glob("mod.*.pyc"))
    assert b"repo-marker" not in pyc.read_bytes()
    code = marshal.loads(pyc.read_bytes()[16:])
    assert code.co_filename == "LocalModelDesk.app/Contents/Resources/desk/mod.py"


def test_build_script_strips_build_paths_from_bytecode():
    text = (REPO / "scripts" / "build-app.sh").read_text(encoding="utf-8")
    assert "export PYTHONDONTWRITEBYTECODE=1" in text
    assert '-s "$RES" -p "LocalModelDesk.app/Contents/Resources" "$RES/desk"' in text
    assert 'find "$RES/python" "$RES/pylibs" "$RES/desk" -type d -name __pycache__ -prune -exec rm -rf {} +' in text
```

（文件顶部已有 `os`、`subprocess` 导入；若没有，补上。）

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_packaging.py -k "bytecode" -q`
Expected: 第一个 PASS（证明 compileall 参数可行），第二个 FAIL（脚本还没改）

- [ ] **Step 3: Edit the build script**

`scripts/build-app.sh` 在 `set -euo pipefail` 下一行加：

```bash
# Any python run during the build (uv probing the embedded interpreter, pip, compileall)
# would otherwise leave __pycache__ files that record this machine's paths (G1).
export PYTHONDONTWRITEBYTECODE=1
```

把第 8 步的预编译两行替换为：

```bash
echo "    precompiling bytecode so a later run cannot write into the signed bundle"
find "$RES/python" "$RES/pylibs" "$RES/desk" -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONDONTWRITEBYTECODE= "$RES/python/bin/python3.13" -s -m compileall -q -f \
  -s "$RES" -p "LocalModelDesk.app/Contents/Resources" "$RES/desk" >/dev/null
```

（`PYTHONDONTWRITEBYTECODE=` 清空变量只作用于这一条，compileall 写 pyc 不受该变量影响，但清空可避免未来 Python 版本改变语义。）

- [ ] **Step 4: README**

`README.md` 的构建段落里，在 `scripts/build-app.sh` 命令示例下补一句：

```markdown
默认输出 `dist/LocalModelDesk.app`；`--output <目录>` 可放到任意位置（仓库内外都行，包内不会留下构建机路径）。
```

- [ ] **Step 5: Run tests and a real default build**

Run: `python3 -m pytest tests/test_packaging.py -q`
Expected: PASS

Run: `LMD_ALLOW_ADHOC=1 ./scripts/build-app.sh --adhoc`（默认输出 `dist/`）
Expected: 以 `built` 行结束、退出码 0；`strings -a dist/LocalModelDesk.app/Contents/Resources/desk/__pycache__/*.pyc | grep -c "$PWD"` 输出 `0`。

- [ ] **Step 6: Commit（含工作区里 statusbar e2e 的取整修正）**

```bash
git add scripts/build-app.sh README.md tests/test_packaging.py tests/e2e/test_statusbar_memory.py
git commit -m "build: default dist build no longer bakes the checkout path into bytecode (G1)"
```

---

### Task 2: 卸载脚本不误伤真实 LaunchAgent，失败要报

**Files:**
- Modify: `scripts/uninstall-app.sh`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `--launch-agents-dir` 为非默认目录时不调用 `launchctl`，打印 `uninstall-app: skip: 自定义 LaunchAgents 目录，不对当前用户域执行 launchctl bootout`；默认目录时先 `launchctl print gui/<uid>/<label>`，已加载才 bootout，bootout 失败走 `fail`（最终退出码 1，不打印 complete）。

- [ ] **Step 1: Update fixtures and write failing tests**

`tests/test_packaging.py`：把 `uninstall` 与 `uninstall_layout` 替换为：

```python
def uninstall(app, launch_agents, data_root, env, *extra, custom_la_dir=True):
    argv = [str(REPO / "scripts" / "uninstall-app.sh"), "--app-path", app, "--data-root", data_root]
    if custom_la_dir:
        argv += ["--launch-agents-dir", launch_agents]
    return subprocess.run([*argv, *extra], capture_output=True, text=True, env=env)


def uninstall_layout(tmp_path, bundle_id=BUNDLE_ID, *, bootout_exit=0):
    apps = tmp_path / "Applications"
    apps.mkdir()
    app = make_fake_bundle(apps, sign=False)
    plist = app / "Contents" / "Info.plist"
    plist.write_bytes(plist.read_bytes().replace(BUNDLE_ID.encode(), bundle_id.encode()))
    home = tmp_path / "home"
    launch_agents = home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    (launch_agents / f"{BUNDLE_ID}.plist").write_text("<plist/>")
    data = tmp_path / "data"
    (data / "models").mkdir(parents=True)
    (data / "models" / "weights.bin").write_bytes(b"weights")
    (data / "sessions").mkdir()
    (data / "sessions" / "session.json").write_text("{}")
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = stub_bin / "launchctl"
    launchctl.write_text(
        f'#!/bin/sh\necho "$@" >> "{launchctl_log}"\n'
        f'if [ "$1" = bootout ]; then exit {bootout_exit}; fi\nexit 0\n')
    launchctl.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    env["HOME"] = str(home)
    return app, launch_agents, data, env, launchctl_log
```

把 `test_uninstall_removes_app_and_plist` 改为默认目录调用并追加两个测试：

```python
def test_uninstall_removes_app_and_plist(tmp_path):
    app, launch_agents, data, env, launchctl_log = uninstall_layout(tmp_path)
    result = uninstall(app, launch_agents, data, env, custom_la_dir=False)
    assert result.returncode == 0, result.stderr
    assert not app.exists()
    assert not (launch_agents / f"{BUNDLE_ID}.plist").exists()
    assert "bootout" in launchctl_log.read_text()


def test_uninstall_with_custom_launch_agents_dir_never_touches_launchctl(tmp_path):
    app, launch_agents, data, env, launchctl_log = uninstall_layout(tmp_path)
    result = uninstall(app, launch_agents, data, env)
    assert result.returncode == 0, result.stderr
    assert not launchctl_log.exists()
    assert "不对当前用户域执行 launchctl bootout" in result.stdout
    assert not (launch_agents / f"{BUNDLE_ID}.plist").exists()


def test_uninstall_reports_a_failed_bootout(tmp_path):
    app, launch_agents, data, env, _log = uninstall_layout(tmp_path, bootout_exit=5)
    result = uninstall(app, launch_agents, data, env, custom_la_dir=False)
    assert result.returncode == 1
    assert "LaunchAgent" in result.stderr
    assert "complete" not in result.stdout
```

`test_uninstall_dry_run_touches_nothing` 保持原调用（自定义目录）不变：它断言 `launchctl_log` 不存在，新行为下同样成立。

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_packaging.py -k uninstall -q`
Expected: 两个新测试 FAIL

- [ ] **Step 3: Edit the script**

`scripts/uninstall-app.sh`：在参数解析前记下默认值：

```bash
DEFAULT_LA_DIR="$HOME/Library/LaunchAgents"
LA_DIR="$DEFAULT_LA_DIR"
```

（替换原来的 `LA_DIR="$HOME/Library/LaunchAgents"`。）把 LaunchAgent 段整个替换为：

```bash
LA_PLIST="$LA_DIR/$BUNDLE_ID.plist"
LA_TARGET="gui/$(id -u)/$BUNDLE_ID"
if [[ "$LA_DIR" != "$DEFAULT_LA_DIR" ]]; then
  echo "uninstall-app: skip: 自定义 LaunchAgents 目录，不对当前用户域执行 launchctl bootout"
elif [[ "$DRY_RUN" == 1 ]]; then
  echo "[dry-run] launchctl bootout $LA_TARGET（若已加载）"
elif launchctl print "$LA_TARGET" >/dev/null 2>&1; then
  launchctl bootout "$LA_TARGET" 2>/dev/null || fail "无法停止旧 LaunchAgent $LA_TARGET；请手动运行 launchctl bootout $LA_TARGET 后重试"
fi
if [[ -e "$LA_PLIST" || -L "$LA_PLIST" ]]; then
  if [[ "$DRY_RUN" == 1 ]]; then
    echo "[dry-run] rm '$LA_PLIST'"
  else
    rm -f -- "$LA_PLIST" || fail "failed to remove $LA_PLIST"
  fi
fi
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packaging.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/uninstall-app.sh tests/test_packaging.py
git commit -m "fix(packaging): uninstall only boots out the real agent for the default dir and reports failures"
```

---

### Task 3: 重设配置只对坏配置生效

**Files:**
- Modify: `desk/foundation/errors.py`
- Modify: `desk/foundation/config.py`（`reset_config`）
- Modify: `desk/foundation/routes.py`（`post_config_reset`）
- Modify: `desk/testing/harness.py:208`（harness 路由表同步传 body）
- Test: `tests/test_foundation_config.py`、`tests/test_foundation_routes.py`

**Interfaces:**
- Produces: `ConfigNotCorruptError(FoundationError)`，`code = "config_not_corrupt"`，`http_status = 409`
- Produces: `reset_config(roots, *, force: bool = False) -> dict`；配置可正常解析且 `force` 为假 → 抛 `ConfigNotCorruptError("配置文件是好的，不需要重新设置")`
- Produces: `POST /api/config/reset` body `{"force": true}` 才能重设合法配置。

- [ ] **Step 1: Write the failing tests**

`tests/test_foundation_config.py` 末尾追加：

```python
def test_reset_refuses_a_healthy_config_unless_forced(tmp_path):
    """误调不能把好配置改名、把网关回落到 0.0.0.0（cross-exam 2026-09-13 G2）。"""
    from desk.foundation.errors import ConfigNotCorruptError

    roots = make_roots(tmp_path)
    config_mod.update_config(roots, first_run_done=True)
    before = roots.config_path.read_bytes()

    with pytest.raises(ConfigNotCorruptError):
        config_mod.reset_config(roots)
    assert roots.config_path.read_bytes() == before

    result = config_mod.reset_config(roots, force=True)
    assert Path(result["backup"]).read_bytes() == before
```

`tests/test_foundation_routes.py` 末尾追加：

```python
def test_config_reset_endpoint_refuses_healthy_config(server, tmp_path):
    http_call(server, "PUT", "/api/config", {"first_run_done": True})
    status, payload = http_call(server, "POST", "/api/config/reset", {})
    assert status == 409
    assert payload["error"]["code"] == "config_not_corrupt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_foundation_config.py tests/test_foundation_routes.py -k reset -q`
Expected: FAIL（`ImportError: cannot import name 'ConfigNotCorruptError'`）

- [ ] **Step 3: Write the implementation**

`desk/foundation/errors.py` 在 `ConfigInvalidError` 之后加：

```python
class ConfigNotCorruptError(FoundationError):
    code = "config_not_corrupt"
    http_status = 409
```

`desk/foundation/config.py`：import 处加入 `ConfigNotCorruptError`，`reset_config` 替换为：

```python
def reset_config(roots, *, force: bool = False) -> dict:
    """Move a broken config aside and start the first-run flow instead of dead-ending.

    A config that still parses is left alone unless ``force`` is set: a stray call must
    not rename a good file and fall back to default gateway settings (G2).
    """
    path = Path(roots.config_path)
    backup = None
    with _LOCK:
        if path.exists() and not force:
            try:
                _load_raw(path)
            except ConfigCorruptError:
                pass
            else:
                raise ConfigNotCorruptError("配置文件是好的，不需要重新设置")
        if path.exists():
            backup = path.with_name(f"config.broken-{time.strftime('%Y%m%d-%H%M%S')}.json")
            path.replace(backup)
    return {"backup": str(backup) if backup else None, "needs_setup": True}
```

`desk/foundation/routes.py`：

```python
def post_config_reset(req) -> dict:
    # Corrupt config must not block recovery: resolve roots with defaults
    # instead of re-raising the same ConfigCorruptError we're here to fix.
    roots = paths_mod.resolve_paths(default_config_on_corrupt=True)
    return config_mod.reset_config(roots, force=bool((req.body or {}).get("force")))
```

`desk/testing/harness.py:208` 改为：

```python
        ("POST", "/api/config/reset", lambda req: config.reset_config(roots, force=bool((req.body or {}).get("force")))),
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_foundation_config.py tests/test_foundation_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/foundation/errors.py desk/foundation/config.py desk/foundation/routes.py desk/testing/harness.py tests/test_foundation_config.py tests/test_foundation_routes.py
git commit -m "fix(config): reset only replaces a config that is actually corrupt (G2)"
```

---

### Task 4: 坏配置时界面给出「重新设置」

**Files:**
- Create: `desk/static/js/widgets/fatal.js`
- Modify: `desk/static/js/api.js`（`resetConfig`）
- Modify: `desk/static/js/main.js`（`fatal` → `showFatal`）
- Modify: `desk/static/index.html:42`、`desk/static/app.css:44`
- Test: `tests/js/fatal.test.js`（新）、`tests/e2e/test_config_recovery.py`（新）

**Interfaces:**
- Consumes: Task 3 的 `/api/config/reset`（坏配置时无需 force）
- Produces: `api.resetConfig() -> Promise<{backup, needs_setup}>`
- Produces: `showFatal(root, error, { resetConfig, reload })` —— `root` 为 `#fatal` 容器；显示 `error.message`；`error.code === "config_corrupt"` 时显示「重新设置」按钮，点击后调 `resetConfig()`，成功则显示「已备份到 <backup>，正在重新进入首次设置…」并调 `reload()`，失败显示失败原因。

- [ ] **Step 1: Write the failing unit test**

新建 `tests/js/fatal.test.js`：

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { showFatal } from "../../desk/static/js/widgets/fatal.js";

class El {
  constructor() { this.hidden = true; this.textContent = ""; this.listeners = {}; this.disabled = false; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
}

function makeRoot() {
  const parts = { "[data-fatal-text]": new El(), "[data-fatal-reset]": new El() };
  const root = new El();
  root.querySelector = (selector) => parts[selector];
  return { root, text: parts["[data-fatal-text]"], reset: parts["[data-fatal-reset]"] };
}

test("坏配置：显示说明与「重新设置」，点击后备份并重新载入（J25）", async () => {
  const { root, text, reset } = makeRoot();
  let reloaded = false;
  showFatal(root, { code: "config_corrupt", message: "配置文件无法读取" }, {
    resetConfig: async () => ({ backup: "/d/config.broken-1.json", needs_setup: true }),
    reload: () => { reloaded = true; },
  });
  assert.equal(root.hidden, false);
  assert.equal(text.textContent, "无法读取配置：配置文件无法读取");
  assert.equal(reset.hidden, false);
  await reset.listeners.click();
  assert.equal(text.textContent, "已备份到 /d/config.broken-1.json，正在重新进入首次设置…");
  assert.equal(reloaded, true);
});

test("其它致命错误不给重设按钮；重设失败时说明原因", async () => {
  const other = makeRoot();
  showFatal(other.root, { code: "timeout", message: "请求超时" }, { resetConfig: async () => ({}), reload() {} });
  assert.equal(other.reset.hidden, true);

  const broken = makeRoot();
  showFatal(broken.root, { code: "config_corrupt", message: "坏了" }, {
    resetConfig: async () => { throw new Error("磁盘只读"); },
    reload() { throw new Error("不应重新载入"); },
  });
  await broken.reset.listeners.click();
  assert.equal(broken.text.textContent, "重新设置失败：磁盘只读");
  assert.equal(broken.reset.disabled, false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/fatal.test.js`
Expected: FAIL（模块不存在）

- [ ] **Step 3: Write the implementation**

新建 `desk/static/js/widgets/fatal.js`：

```javascript
// ui:fatal —— 台面无法进入时的整屏说明；配置损坏时给出唯一的恢复入口（J25）。
export function showFatal(root, error, { resetConfig, reload }) {
  const text = root.querySelector("[data-fatal-text]");
  const reset = root.querySelector("[data-fatal-reset]");
  root.hidden = false;
  text.textContent = `无法读取配置：${error.message}`;
  reset.hidden = error.code !== "config_corrupt";
  reset.addEventListener("click", async () => {
    reset.disabled = true;
    try {
      const result = await resetConfig();
      text.textContent = result.backup
        ? `已备份到 ${result.backup}，正在重新进入首次设置…`
        : "正在重新进入首次设置…";
      reload();
    } catch (failure) {
      text.textContent = `重新设置失败：${failure.message}`;
      reset.disabled = false;
    }
  });
}
```

`desk/static/js/api.js`：`ROUTES` 里 `config: "/api/config",` 后加 `configReset: "/api/config/reset",`；导出区 `writeConfig` 下加：

```javascript
export const resetConfig = () => json(ROUTES.configReset, "POST", {});
```

`desk/static/js/main.js`：import 区加 `import { showFatal } from "./widgets/fatal.js";`；删除 `function fatal(message) {...}` 一行；`boot()` 的 catch 改为：

```javascript
  try { config = await api.readConfig(); } catch (error) {
    showFatal($("#fatal"), error, { resetConfig: api.resetConfig, reload: () => globalThis.location.reload() });
    return;
  }
```

`desk/static/index.html:42` 替换为：

```html
  <div id="fatal" role="alert" hidden><p data-fatal-text></p><button type="button" class="btn-primary" data-fatal-reset hidden>重新设置</button></div>
```

`desk/static/app.css:44` 的 `#fatal` 规则替换为：

```css
#fatal { position:fixed; inset:0; z-index:40; display:grid; place-content:center; justify-items:center; gap:16px; padding:48px; background:var(--bg); } #fatal [data-fatal-text] { color:var(--danger); max-width:40em; text-align:center; margin:0; }
```

- [ ] **Step 4: Run unit tests**

Run: `node --test tests/js/*.test.js`
Expected: PASS

- [ ] **Step 5: Write the e2e test**

新建 `tests/e2e/test_config_recovery.py`：

```python
"""J25: a half-written config.json can be recovered from the window alone."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_corrupt_config_offers_reset_and_lands_in_first_run(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        config_path = harness.data_root / "config.json"
        config_path.write_text('{"config_version": 1, "first_run', encoding="utf-8")

        page.goto(harness.base_url)
        expect(page.locator("#fatal [data-fatal-text]")).to_contain_text("无法读取配置")
        page.get_by_role("button", name="重新设置").click()

        expect(page.locator("#pane-firstrun")).to_be_visible()
        backups = list(harness.data_root.glob("config.broken-*.json"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == '{"config_version": 1, "first_run'
    assert audit_violations == []
```

- [ ] **Step 6: Run e2e**

Run: `python3 -m pytest tests/e2e/test_config_recovery.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add desk/static/js/widgets/fatal.js desk/static/js/api.js desk/static/js/main.js desk/static/index.html desk/static/app.css tests/js/fatal.test.js tests/e2e/test_config_recovery.py
git commit -m "fix(ui): a corrupt config shows a working 重新设置 button (G14, J25)"
```

---

### Task 5: 网关报错只反映当前状态

**Files:**
- Modify: `desk/gateway/service.py`（`apply_config`、`status`）
- Modify: `desk/static/js/panes/settings.js`（`render`）
- Test: `tests/test_gateway_service.py`、`tests/js/settings_pane.test.js`

**Interfaces:**
- Produces: `status()["last_error"]` 仅在 `listening` 为假时非空（启用但没绑上的原因）。
- Produces: `apply_config()` 返回 `{**status(), "apply_error": <本次保存绑定失败的中文原因 | None>}`；`POST /api/gateway/config` 的 `status` 带 `apply_error`，`GET` 不带。
- Produces: 设置面板显示 `status.apply_error ?? status.last_error`。

- [ ] **Step 1: Update and write failing tests**

`tests/test_gateway_service.py` 的 `test_failed_bind_rolls_back_to_the_last_good_config` 末尾两行改为：

```python
    assert status["apply_error"] is not None
    assert "无法绑定" in status["apply_error"]
    assert svc.status()["last_error"] is None
```

末尾追加：

```python
def test_get_status_after_a_rolled_back_save_shows_no_stale_error(service_factory):
    """回滚后已在监听，刷新页面不该再挂着上次的失败横幅（cross-exam 2026-09-13 G7）。"""
    stored = {"gateway": {"enabled": True, "host": "127.0.0.1", "port": 8770}}
    svc = service_factory(lambda: stored, server_factory=_FakeServer)
    svc.on_rollback = lambda cfg: stored.update(gateway=cfg)
    svc.start_from_config()
    stored["gateway"] = {"enabled": True, "host": "10.255.255.1", "port": 8770}
    code, posted = svc.handle_config_request("POST")
    assert posted["status"]["apply_error"]

    code, fetched = svc.handle_config_request("GET")

    assert fetched["status"]["listening"] is True
    assert fetched["status"]["last_error"] is None
    assert "apply_error" not in fetched["status"]
```

`tests/js/settings_pane.test.js` 末尾追加：

```javascript
test("保存失败横幅来自 apply_error；监听中时 GET 不带旧错误；前端校验失败只显示校验文案", async () => {
  const oldFetch = globalThis.fetch;
  let getStatus = { enabled: true, listening: true, host: "127.0.0.1", port: 8815, auth: "none", last_error: null };
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/config" && (options.method ?? "GET") === "GET") return new Response(JSON.stringify({ models_root: "/m" }), { status: 200 });
    if (options.method === "PUT") return new Response("{}", { status: 200 });
    if (options.method === "POST") return new Response(JSON.stringify({
      config: { enabled: true, host: "127.0.0.1", port: 8815 },
      status: { ...getStatus, apply_error: "无法绑定 127.0.0.1:8816——该端口已被占用" },
    }), { status: 200 });
    return new Response(JSON.stringify({ config: { enabled: true, host: "127.0.0.1", port: 8815 }, status: getStatus }), { status: 200 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    const pane = createSettingsPane(root);
    controls.get("[data-settings-host]").value = "127.0.0.1";
    controls.get("[data-settings-port]").value = "8816";
    await controls.get("[data-settings-save]").click();
    assert.equal(controls.get("[data-settings-error]").textContent, "无法绑定 127.0.0.1:8816——该端口已被占用");

    await pane.init();
    assert.equal(controls.get("[data-settings-error]").textContent, "");

    controls.get("[data-settings-port]").value = "70000";
    await controls.get("[data-settings-save]").click();
    assert.equal(controls.get("[data-settings-error]").textContent, "端口须在 1 到 65535 之间");
  } finally { globalThis.fetch = oldFetch; }
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gateway_service.py -q; node --test tests/js/settings_pane.test.js`
Expected: FAIL（没有 `apply_error`；横幅文字不符）

- [ ] **Step 3: Write the implementation**

`desk/gateway/service.py`：

`apply_config` 改为：

```python
    def apply_config(self) -> dict:
        """Re-read configuration and replace the listener when it has changed.

        A bind failure never leaves the gateway parked on the bad config: it rolls back
        to the last address that actually bound and persists that rollback (F12). The
        plain-Chinese reason for *this* save travels as `apply_error`; `status()` alone
        never repeats it once the gateway is listening again (G7).
        """
        cfg = self._gateway_config()
        wanted = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        listening = self._server is not None
        if wanted == self._applied and listening == wanted[0]:
            return {**self.status(), "apply_error": None}
        self.stop()
        self._start(cfg)
        failure = self._last_error if self._server is None and wanted[0] else None
        if self._server is None and wanted[0] and self._last_good is not None and self._last_good != wanted:
            enabled, host, port = self._last_good
            restored = {"enabled": enabled, "host": host, "port": port}
            if self.on_rollback is not None:
                self.on_rollback(restored)
            self._start(restored)
            if self._server is None:
                self._last_error = failure
        return {**self.status(), "apply_error": failure}
```

`status()` 返回字典里的最后一项改为：

```python
            "last_error": None if listening else self._last_error,
```

`desk/static/js/panes/settings.js` 的 `render` 中 `setError(status.last_error);` 改为：

```javascript
    setError(status.apply_error ?? status.last_error);
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_gateway_service.py -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e/test_settings_api.py -q`
Expected: PASS（`test_bind_failure_recorded_not_fatal` 与 `test_bind_errno_49_message_is_plain_chinese` 未监听，`last_error` 仍在）

- [ ] **Step 5: Commit**

```bash
git add desk/gateway/service.py desk/static/js/panes/settings.js tests/test_gateway_service.py tests/js/settings_pane.test.js
git commit -m "fix(gateway): a save failure is reported once; a listening gateway shows no stale error (G7)"
```

---

### Task 6: 菜单栏显示模型名（接上 `Holder.public_view`）

**Files:**
- Modify: `desk/arbiter/core.py`（`_public_holder`）
- Test: `tests/test_arbiter_core.py`

**Interfaces:**
- Consumes: `Holder.public_view()`（`desk/arbiter/state.py`，已存在，P1 零调用点）
- Produces: `/api/state` 的 `holder` 含 `display`（缺省回落 `label`）；壳 `ShellStatus.swift:38` 已解码该键，无需改 Swift。

- [ ] **Step 1: Write the failing test**

```python
def test_public_holder_carries_the_display_name_for_the_menu_bar():
    """菜单栏曾显示目录 key『glm』而非模型名（cross-exam 2026-09-13 G16）。"""
    arbiter = Arbiter(llm_port=43124, reaper=lambda port, **_: ReapResult(ok=True, port=port, killed_pids=[]),
                      clock=lambda: 1.0)
    arbiter.acquire_heavy("llm", "glm", "GLM 4.7 Flash 越狱 4bit")
    assert arbiter.desk_state()["holder"]["display"] == "GLM 4.7 Flash 越狱 4bit"
    arbiter2 = Arbiter(llm_port=43125, reaper=lambda port, **_: ReapResult(ok=True, port=port, killed_pids=[]),
                       clock=lambda: 1.0)
    arbiter2.acquire_heavy("video", "job-1")
    assert arbiter2.desk_state()["holder"]["display"] == "job-1"
```

（文件顶部已导入 `Arbiter` 与 `ReapResult`；若 `reaper` 的调用签名是 `reaper(port)` 不带关键字，`lambda port, **_` 同样兼容。）

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_arbiter_core.py -k display -q`
Expected: FAIL，`KeyError: 'display'`

- [ ] **Step 3: Write the implementation**

```python
    @staticmethod
    def _public_holder(holder: Holder | None) -> dict | None:
        return None if holder is None else holder.public_view()
```

`tests/test_arbiter_core.py:119` 的 `current_holder()` 精确字典断言补 `"display": "job-a"`（Task 10 会把该断言改为走 `desk_state()`）。

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_arbiter_core.py tests/test_production_runtime.py tests/llm -q && python3 -m pytest tests/e2e/test_statusbar_memory.py tests/e2e/test_mutex_ui.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/arbiter/core.py tests/test_arbiter_core.py
git commit -m "fix(arbiter): desk state carries the holder display name to the menu bar (G16, P1)"
```

---

### Task 7: ⌘, 打开设置；右键菜单与系统菜单项中文

**Files:**
- Modify: `macos/ShellStatus.swift`（`isSettingsShortcut`）
- Modify: `macos/harness/ShellHarness.swift`（子命令 `settings-shortcut`）
- Modify: `macos/AppDelegate.swift`（本地按键监听）
- Modify: `macos/MainWindowController.swift`（`DeskWebView` 子类改右键菜单）
- Modify: `packaging/Info.plist.template`、`scripts/build-app.sh`（`zh-Hans.lproj`）
- Test: `tests/test_shell_status.py`、`tests/test_shell_static.py`、`tests/test_packaging.py`

**Interfaces:**
- Produces: `func isSettingsShortcut(command: Bool, option: Bool, control: Bool, shift: Bool, characters: String?) -> Bool`
- Produces: `final class DeskWebView: WKWebView`，`willOpenMenu` 把 `WKMenuItemIdentifierReload` 标题改为「重新载入」，删除 `WKMenuItemIdentifierInspectElement` 以外无关英文项不做（只改 Reload，保持最小）。
- Produces: Info.plist `CFBundleDevelopmentRegion = zh_CN`、`CFBundleLocalizations = [zh-Hans]`；包内 `Contents/Resources/zh-Hans.lproj/InfoPlist.strings`。

- [ ] **Step 1: Write the failing tests**

`tests/test_shell_status.py` 末尾追加：

```python
@pytest.mark.parametrize("mods,chars,expected", [
    ("cmd", ",", "true"),
    ("cmd+shift", ",", "false"),
    ("cmd+opt", ",", "false"),
    ("", ",", "false"),
    ("cmd", "h", "false"),
])
def test_settings_shortcut(mods, chars, expected):
    proc = subprocess.run([harness_path(), "settings-shortcut", mods, chars],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
```

`tests/test_shell_static.py` 末尾追加：

```python
def test_settings_shortcut_is_caught_before_the_web_view():
    """WKWebView 先吞掉 ⌘,，主菜单的快捷键收不到（cross-exam 2026-09-13 G8）。"""
    text = (MACOS / "AppDelegate.swift").read_text(encoding="utf-8")
    assert "NSEvent.addLocalMonitorForEvents(matching: .keyDown)" in text
    assert "isSettingsShortcut(" in text


def test_web_view_context_menu_is_localized():
    text = (MACOS / "MainWindowController.swift").read_text(encoding="utf-8")
    assert "final class DeskWebView: WKWebView" in text
    assert "WKMenuItemIdentifierReload" in text
    assert "重新载入" in text
```

`tests/test_packaging.py` 末尾追加：

```python
def test_bundle_declares_chinese_development_region():
    template = (REPO / "packaging" / "Info.plist.template").read_text(encoding="utf-8")
    assert "<key>CFBundleDevelopmentRegion</key>\n\t<string>zh_CN</string>" in template
    assert "<key>CFBundleLocalizations</key>" in template
    build = (REPO / "scripts" / "build-app.sh").read_text(encoding="utf-8")
    assert 'mkdir -p "$RES/zh-Hans.lproj"' in build
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_shell_status.py -k shortcut tests/test_shell_static.py tests/test_packaging.py -k "shortcut or localized or development_region" -q`
Expected: FAIL

- [ ] **Step 3: Pure function + harness**

`macos/ShellStatus.swift` 末尾追加：

```swift
/// ⌘, with no other modifier opens settings (G8). Pure so the headless harness can test it.
func isSettingsShortcut(command: Bool, option: Bool, control: Bool, shift: Bool, characters: String?) -> Bool {
  command && !option && !control && !shift && characters == ","
}
```

`macos/harness/ShellHarness.swift` 的 `switch` 里 `default:` 之前加：

```swift
    case "settings-shortcut":
      guard args.count >= 3 else { exit(64) }
      let mods = Set(args[1].split(separator: "+").map(String.init))
      print(isSettingsShortcut(command: mods.contains("cmd"), option: mods.contains("opt"),
                               control: mods.contains("ctrl"), shift: mods.contains("shift"),
                               characters: args[2]))
```

- [ ] **Step 4: AppKit wiring**

`macos/AppDelegate.swift`：类里加属性 `private var settingsKeyMonitor: Any?`；在 `buildMainMenu()` 被调用的地方（`applicationDidFinishLaunching` 内）紧随其后调用 `installSettingsShortcut()`，并新增：

```swift
  /// WKWebView consumes ⌘, before the main menu sees its key equivalent (G8).
  private func installSettingsShortcut() {
    settingsKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
      let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
      guard isSettingsShortcut(command: flags.contains(.command), option: flags.contains(.option),
                               control: flags.contains(.control), shift: flags.contains(.shift),
                               characters: event.charactersIgnoringModifiers) else { return event }
      self?.openSettings()
      return nil
    }
  }
```

`macos/MainWindowController.swift`：文件末尾追加：

```swift
/// The default WKWebView context menu is not localized ("Reload"); name it in Chinese.
final class DeskWebView: WKWebView {
  override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
    super.willOpenMenu(menu, with: event)
    for item in menu.items where item.identifier?.rawValue == "WKMenuItemIdentifierReload" {
      item.title = "重新载入"
    }
  }
}
```

并把 `webView = WKWebView(frame: .zero, configuration: config)` 改为 `webView = DeskWebView(frame: .zero, configuration: config)`。

- [ ] **Step 5: Bundle localization**

`packaging/Info.plist.template` 在 `CFBundleName` 条目之后插入：

```xml
	<key>CFBundleDevelopmentRegion</key>
	<string>zh_CN</string>
	<key>CFBundleLocalizations</key>
	<array>
		<string>zh-Hans</string>
	</array>
```

`scripts/build-app.sh` 第 5 步 `plutil -lint` 之后加：

```bash
# System-injected menu items (Writing Tools, AutoFill, Dictation…) follow the bundle's
# declared localizations; without an lproj they fall back to English.
mkdir -p "$RES/zh-Hans.lproj"
printf '"CFBundleName" = "LocalModelDesk";\n' > "$RES/zh-Hans.lproj/InfoPlist.strings"
```

若 `scripts/verify-app.sh` V2 的必填键列表是从模板抽取的，新键会自动被校验；若是写死列表，不改。

- [ ] **Step 6: Run tests**

Run: `python3 -m pytest tests/test_shell_*.py tests/test_packaging.py -q`
Expected: PASS

- [ ] **Step 7: 真机确认**

构建隔离副本（`--output /tmp/lmd-planD`，`ditto` 到 `/tmp/lmd-planD-iso`，数据根 `/tmp/lmd-planD-iso/data`，`LMD_SHELL_PORT=8839`）。按副本壳 pid 用 JXA `NSRunningApplication...activateWithOptions` 激活并以 `lsappinfo front` 核对后：
- 按 ⌘, → 设置抽屉打开；
- 网页空白处右键 → 菜单项为「重新载入」；
- 展开「编辑」菜单 → 系统注入项为中文（如「书写工具」「自动填充」「开始听写」）。若系统项仍为英文，记录截图并在提交说明里注明"系统项未随 lproj 本地化"，不阻塞本任务。
- 清理：`pkill -f 'lmd-planD-iso'; rm -rf /tmp/lmd-planD /tmp/lmd-planD-iso`

- [ ] **Step 8: Commit**

```bash
git add macos/ShellStatus.swift macos/harness/ShellHarness.swift macos/AppDelegate.swift macos/MainWindowController.swift packaging/Info.plist.template scripts/build-app.sh tests/test_shell_status.py tests/test_shell_static.py tests/test_packaging.py
git commit -m "fix(shell): ⌘, opens settings; context menu and system menu items are Chinese (G8)"
```

---

### Task 8: 服务意外退出时错误页说清原因

**Files:**
- Modify: `macos/ShellStatus.swift`（`serviceExitDescription`、`logTail`、`errorPageHTML`）
- Modify: `macos/harness/ShellHarness.swift`（`error-page` 第三参数、`exit-description`、`log-tail`）
- Modify: `macos/ServerController.swift`（暴露 `lastExit`）
- Modify: `macos/AppDelegate.swift:103-114`、`macos/MainWindowController.swift`（`showErrorPage(reason:logPath:logTail:)`）
- Test: `tests/test_shell_status.py`、`tests/test_shell_static.py`

**Interfaces:**
- Produces: `func serviceExitDescription(status: Int32, signaled: Bool) -> String` → `"退出码 3"` / `"被信号 9（SIGKILL）结束"` / `"被信号 15（SIGTERM）结束"` / 其它信号 `"被信号 N 结束"`
- Produces: `func logTail(_ text: String, maxLines: Int) -> String`（纯字符串处理，调用方负责读文件）
- Produces: `func errorPageHTML(reason: String, logPath: String, logTail: String = "") -> String`；`logTail` 非空时在「详情」里以 `<pre>` 显示（HTML 转义）。
- Produces: `ServerController.lastExit: (status: Int32, signaled: Bool)?`（子进程退出后读取 `terminationStatus` 与 `terminationReason == .uncaughtSignal`）

- [ ] **Step 1: Write the failing tests**

`tests/test_shell_status.py` 末尾追加：

```python
@pytest.mark.parametrize("status,signaled,expected", [
    ("3", "false", "退出码 3"),
    ("9", "true", "被信号 9（SIGKILL）结束"),
    ("15", "true", "被信号 15（SIGTERM）结束"),
    ("6", "true", "被信号 6 结束"),
])
def test_service_exit_description(status, signaled, expected):
    proc = subprocess.run([harness_path(), "exit-description", status, signaled],
                          capture_output=True, text=True, timeout=30)
    assert proc.stdout.strip() == expected


def test_log_tail_keeps_last_lines():
    text = "".join(f"line {i}\n" for i in range(50))
    proc = subprocess.run([harness_path(), "log-tail", "3"], input=text,
                          capture_output=True, text=True, timeout=30)
    assert proc.stdout == "line 47\nline 48\nline 49\n"


def test_error_page_shows_escaped_log_tail():
    proc = subprocess.run([harness_path(), "error-page", "台面服务意外退出（被信号 9（SIGKILL）结束）", "/tmp/x.log",
                           "Traceback <boom>"], capture_output=True, text=True, timeout=30)
    assert "<pre>Traceback &lt;boom&gt;</pre>" in proc.stdout
    assert "被信号 9（SIGKILL）结束" in proc.stdout
```

`tests/test_shell_static.py` 中现有断言 `"func errorPageHTML(reason: String, logPath: String) -> String"` 改为：

```python
    assert "func errorPageHTML(reason: String, logPath: String, logTail: String = \"\") -> String" in template
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_shell_status.py tests/test_shell_static.py -q`
Expected: FAIL

- [ ] **Step 3: Pure functions**

`macos/ShellStatus.swift`：

```swift
/// Plain-Chinese exit cause for the error page (cross-exam open thread: details had only a log path).
func serviceExitDescription(status: Int32, signaled: Bool) -> String {
  guard signaled else { return "退出码 \(status)" }
  switch status {
  case 9: return "被信号 9（SIGKILL）结束"
  case 15: return "被信号 15（SIGTERM）结束"
  default: return "被信号 \(status) 结束"
  }
}

func logTail(_ text: String, maxLines: Int) -> String {
  let lines = text.split(separator: "\n", omittingEmptySubsequences: false)
  let trimmed = lines.last == "" ? lines.dropLast() : lines[...]
  return trimmed.suffix(maxLines).map { $0 + "\n" }.joined()
}
```

`errorPageHTML` 签名改为 `func errorPageHTML(reason: String, logPath: String, logTail: String = "") -> String`，把 `<details>` 那一行替换为：

```swift
  <details><summary>详情</summary><p>日志：<code>\(esc(logPath))</code></p>\(logTail.isEmpty ? "" : "<pre>\(esc(logTail))</pre>")</details>
```

并在 `<style>` 里追加 `pre{white-space:pre-wrap;font:12px ui-monospace,Menlo,monospace;color:#9aa3b2;max-height:16em;overflow:auto}`。

`macos/harness/ShellHarness.swift`：`error-page` 分支改为

```swift
    case "error-page":
      guard args.count >= 3 else { exit(64) }
      print(errorPageHTML(reason: args[1], logPath: args[2], logTail: args.count >= 4 ? args[3] : ""))
```

并新增：

```swift
    case "exit-description":
      guard args.count >= 3, let status = Int32(args[1]) else { exit(64) }
      print(serviceExitDescription(status: status, signaled: args[2] == "true"))
    case "log-tail":
      guard args.count >= 2, let count = Int(args[1]) else { exit(64) }
      let input = String(decoding: FileHandle.standardInput.readDataToEndOfFile(), as: UTF8.self)
      print(logTail(input, maxLines: count), terminator: "")
```

- [ ] **Step 4: AppKit wiring**

`macos/ServerController.swift`：加属性

```swift
  /// Filled when the owned child has exited, for the error page.
  var lastExit: (status: Int32, signaled: Bool)? {
    guard let process = child, !process.isRunning else { return nil }
    return (process.terminationStatus, process.terminationReason == .uncaughtSignal)
  }
```

（若 `child` 在退出路径里被置 nil，改为在置 nil 前把值存进 `private(set) var lastExitRecord`，`lastExit` 返回它。）

`macos/MainWindowController.swift` 的 `showErrorPage` 签名改为 `func showErrorPage(reason: String, logPath: String, logTail: String = "")`，内部调用 `errorPageHTML(reason: reason, logPath: logPath, logTail: logTail)`。

`macos/AppDelegate.swift` 的 `.serviceExited` 分支改为：

```swift
      case .serviceExited:
        status.server = .failed(.spawnFailed("服务已退出"))
        let cause = server.lastExit.map { "（\(serviceExitDescription(status: $0.status, signaled: $0.signaled))）" } ?? ""
        let text = (try? String(contentsOf: DeskPaths.serverStdoutLogURL, encoding: .utf8)) ?? ""
        windowController.showErrorPage(
          reason: "台面服务意外退出\(cause)。",
          logPath: DeskPaths.serverStdoutLogURL.path,
          logTail: logTail(text, maxLines: 20))
        poller.stop()
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_shell_*.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add macos/ShellStatus.swift macos/harness/ShellHarness.swift macos/ServerController.swift macos/MainWindowController.swift macos/AppDelegate.swift tests/test_shell_status.py tests/test_shell_static.py
git commit -m "fix(shell): the service-exited page names the exit cause and shows the log tail"
```

---

### Task 9: 删除与"测试缝"对齐的死契约（去掉 harness 与生产的行为漂移）

**Files:**
- Modify: `desk/llm/service.py`（删 `on_heavy_state_changed`）
- Modify: `desk/testing/harness.py:303`（删额外订阅）
- Modify: `tests/llm/test_llm_status_converge.py`
- Modify: `desk/arbiter/core.py`（删 `current_holder`）、`tests/test_arbiter_core.py`
- Modify: `desk/resources/http.py`（删 `match_route`）、`tests/test_resources_http.py`
- Modify: `desk/llm/routes.py`、`desk/llm/__init__.py`（删 `encode_sse`）、`tests/llm/test_llm_routes.py`
- Modify: `macos/MainWindowController.swift`（删 `isWindowVisible`）、`macos/PortGuard.swift`（`ensureFree` 标注测试缝）
- Modify: `desk/static/js/panes/resources.js`（改用 `formatRate`）
- Modify: `desk/foundation/routes.py`、`desk/llm/routes.py`、`desk/resources/http.py`（对外诊断/API 端点注释）

**Interfaces:**
- 生产订阅只剩 `LlmService.__init__` 里的 `_on_desk_state`；harness 与生产一致（驱逐后状态码为 `evicted`）。

- [ ] **Step 1: Rewrite the converge tests against the production subscription**

`tests/llm/test_llm_status_converge.py` 中三个 `test_heavy_state_changed_*` 替换为：

```python
def test_holder_moving_to_media_marks_the_model_evicted(tmp_path):
    testbed = make_loaded(tmp_path)

    testbed.arbiter.emit({"holder": {"kind": "video", "label": "job-1", "phase": "held"}, "media_busy": True})

    got = testbed.service.status()
    assert got["state"]["status"] == "error"
    assert got["state"]["error"]["code"] == "evicted"


def test_holder_still_this_model_is_noop(tmp_path):
    testbed = make_loaded(tmp_path)

    testbed.arbiter.emit({"holder": {"kind": "llm", "label": "glm", "phase": "held"}, "media_busy": False})

    assert testbed.service.status()["state"]["status"] == "loaded"


def test_holder_change_when_not_loaded_is_noop(tmp_path):
    testbed = make_service(tmp_path)

    testbed.arbiter.emit({"holder": None, "media_busy": False})

    assert testbed.service.status()["state"]["status"] == "idle"
    assert testbed.calls == []
```

- [ ] **Step 2: Run to confirm they pass on the production path before deleting**

Run: `python3 -m pytest tests/llm/test_llm_status_converge.py -q`
Expected: PASS（`_on_desk_state` 本来就在订阅）

- [ ] **Step 3: Delete the drifted method and harness subscription**

- 删除 `desk/llm/service.py` 中整个 `on_heavy_state_changed` 方法。
- `desk/testing/harness.py:303` 删除 `unsubscribe = arbiter.subscribe(llm.on_heavy_state_changed)`；`harness.py:354` 的 `_unsubscribe=unsubscribe,` 改为 `_unsubscribe=llm.close,`（关闭 harness 时释放 `LlmService` 自己的订阅与子进程，行为与生产 `runtime.shutdown()` 对齐）。

Run: `python3 -m pytest tests/llm -q && python3 -m pytest tests/e2e/test_mutex_ui.py tests/e2e/test_video_flow.py tests/e2e/test_music_flow.py -q`
Expected: PASS。若某条 e2e 断言驱逐后的界面文案是「加载失败（backend_exited）」，改为断言「已被媒体任务让出内存」——那是 harness 漂移造成的错误期望。

- [ ] **Step 4: `current_holder`**

`tests/test_arbiter_core.py` 中每处 `arbiter.current_holder()` 改为 `arbiter.desk_state()["holder"]`；第 119 行的精确字典断言改为：

```python
    assert arbiter.desk_state()["holder"] == {
        "kind": "video", "label": "job-a", "display": "job-a", "since": 42.0, "phase": "held"
    }
```

然后删除 `desk/arbiter/core.py` 的 `current_holder` 方法。Run: `python3 -m pytest tests/test_arbiter_core.py -q` → PASS。

- [ ] **Step 5: `match_route` 挪进测试文件**

把 `desk/resources/http.py` 中 `match_route` 函数整体剪切到 `tests/test_resources_http.py`，改名为 `_match_route`（放在 `call` 之上），`call` 与 `test_match_route_none_for_unknown_path` 改用 `_match_route`；import 行改为 `from desk.resources.http import build_routes`。生产路由分发由 `DeskApp._find` 负责。Run: `python3 -m pytest tests/test_resources_http.py -q` → PASS。

- [ ] **Step 6: `encode_sse`**

`tests/llm/test_llm_routes.py:41` 的 `self.wfile.write(encode_sse(event))` 改为

```python
                    self.wfile.write(b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n")
```

（顶部补 `import json`，import 行删去 `encode_sse`。）删除 `desk/llm/routes.py` 的 `encode_sse` 函数，以及 `desk/llm/__init__.py` 里对它的导入与 `__all__` 项。Run: `python3 -m pytest tests/llm -q` → PASS。

- [ ] **Step 7: `formatRate` 接上**

`desk/static/js/panes/resources.js`：import 行加入 `formatRate`（与 `formatBytes` 同一 import），把

```javascript
        activeDownload.rate_bps ? `${formatBytes(activeDownload.rate_bps)}/s` : null,
```

改为

```javascript
        activeDownload.rate_bps ? formatRate(activeDownload.rate_bps) : null,
```

Run: `node --test tests/js/*.test.js` → PASS。

- [ ] **Step 8: Swift**

- 删除 `macos/MainWindowController.swift` 的 `var isWindowVisible: Bool { window.isVisible }`。
- `macos/PortGuard.swift` 的 `static func ensureFree` 上一行加 `/// Test seam: used only by macos/harness/ShellHarness.swift (ensure-free).`

Run: `python3 -m pytest tests/test_shell_*.py -q` → PASS。

- [ ] **Step 9: 对外端点标注**

在以下三处路由登记行的上一行各加一行注释：

- `desk/foundation/routes.py` `("GET", "/api/paths", get_paths),` 上：`# Diagnostic endpoint for support/scripts; the UI deliberately does not call it.`
- `desk/llm/routes.py` `Route("POST", "/api/llm/chat", ...)` 上：`# Non-streaming chat for scripts and the gateway contract; the UI streams instead.`
- `desk/resources/http.py` 中 `/api/resources/status/{key}` 登记行上：`# Single-model verify for scripts; the UI refreshes all models at once.`

- [ ] **Step 10: Full run and commit**

Run: `python3 -m pytest -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

```bash
git add desk tests macos
git commit -m "chore: remove dead contracts and the harness-only eviction path (G6, P1)"
```
