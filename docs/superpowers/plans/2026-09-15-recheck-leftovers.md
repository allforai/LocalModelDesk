# 2026-09-13 复盘余项 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收掉 A–F 计划合并后剩下的余项：安装脚本报错顺序、模型目录扫描越界、首运页不能原样返回台面、长视频参数没有耗时提醒，以及四项还没在真实 app 里看过的检查。

**Architecture:** 三处小的服务端/脚本改动（`install-app.sh` 参数校验顺序；`firstrun._candidate_roots` 在非默认数据根时只扫显式目录；`GET /api/config` 在待设置时多给 `models_root_models`，生产与测试 harness 共用一个 `config_payload`）。两处前端改动（首运页「继续使用当前目录」卡片与可点的发现建议；视频面板按画幅×时长给出耗时提醒，逻辑放纯函数 `pure/video_cost.js`）。最后一个任务在隔离的真实 app 副本上逐项人工复核，结果写回计划索引。

**Tech Stack:** bash · Python 3.13 stdlib · 零依赖 ES modules · pytest · node:test · Playwright · JXA / `screencapture`

**Spec:** `docs/superpowers/plans/2026-09-14-recheck-index.md` §「未拉的线 → 处理」中标为「待产品决定」「未实证」的行，以及 2026-09-15 真机复核总结里「没实测」的两项与「只有 e2e 覆盖」的两项；证据 `docs/cross-exam/2026-09-13-localmodeldesk-recheck/evidence/q16/`（1024×576×15 秒 20 分钟只走 2/16 步）、`q08/`（收编框预填扫描到的真实目录）、`q40/`（2560 宽）。实现合并后 `tests/test_packaging.py::test_install_names_the_missing_dest` 与 `tests/test_foundation_routes.py::test_discover_endpoint_selects_best_local_tree` 在嵌套 worktree 中失败（workflow `wf_31259ec4-6c9` 各实现者报告）。

本计划自拟的产品决定（执行前可改）：

- 首运页：当前模型目录里已有目录中的模型时，显示「继续使用当前目录」卡片与「返回台面」按钮；收编输入框**不再**自动填入扫描结果，扫描结果改为列在输入框上方、每条带「填入」按钮。
- 模型目录扫描：显式设置 `LOCALMODELDESK_MODEL_SCAN_ROOTS` 时只扫它；数据根不是默认的 `~/Library/Application Support/LocalModelDesk` 时（隔离副本、测试 harness）不扫用户主目录和源码检出目录的上级。真实用户的数据根就是默认值，行为不变。
- 视频耗时提醒：只对有实测依据的组合提示——画幅 1024×576 且时长 ≥ 约 10 秒（243 帧）。不给具体分钟数估算。
- 不做：菜单栏图标辨识度与 3 秒轮询（视觉/策略取舍，维持现状）；VPN 下 base URL（`desk/gateway/lan.py` 已跳过 `utun*` 与 100.64/10，`tests/test_gateway_lan.py::test_tunnel_and_loopback_are_never_offered` 覆盖）；看手气的 GitHub issue（功能已随 `7a80f7c` 上线，issue 不再有追踪价值）。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）。
- 前端：零依赖 ES modules；一律 `createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文；机器码不作唯一解释。
- 界面自适应：800–2560 宽无横向溢出。
- 测试命令：`python3 -m pytest -q`、`node --test "tests/js/*.test.js"`、`python3 -m pytest tests/e2e -q`；Swift 改动跑 `python3 -m pytest tests/test_shell_*.py -q`。
- 验证门必须包含 e2e：`desk/static/` 或 `desk/` 任一改动，提交前跑 `python3 -m pytest tests/e2e -q`。
- 测试永不触碰 `~/LocalModelDesk` 模型权重或 `~/Library/Application Support/LocalModelDesk`：一律 `tmp_path`。
- 真机复核只用 `ditto` 出的独立副本、独立数据根、`LMD_SHELL_PORT=8839`；开始前确认没有其它 `LocalModelDesk.app` 进程在跑（同 bundle id 多实例时 System Events 会串到别的实例）；**不删除、不移动**任何模型权重。
- 每个任务结束后提交，commit message 末尾带一行 trailer：
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `scripts/install-app.sh` | 先校验目标目录，再校验应用包 |
| `desk/foundation/paths.py` | 新增 `default_data_root()`，`_static_roots` 复用它 |
| `desk/foundation/firstrun.py` | `_candidate_roots` 收紧扫描范围；抽出 `recognized_model_keys(path)` |
| `desk/foundation/routes.py` | 新增 `config_payload(roots)`，`GET /api/config` 在待设置时带 `models_root_models` |
| `desk/testing/harness.py` | `GET /api/config` 改用 `config_payload`，与生产一致 |
| `desk/static/index.html`、`desk/static/app.css` | 首运页保留卡片、发现列表；视频耗时提醒占位 |
| `desk/static/js/panes/firstrun.js` | 保留卡片、发现建议、不再预填收编框 |
| `desk/static/js/pure/video_cost.js`（新） | `videoCostNote(size, frames)` |
| `desk/static/js/panes/video.js` | 画幅/时长变化时刷新耗时提醒 |
| `docs/superpowers/plans/2026-09-14-recheck-index.md` | 写回余项的处理结果与真机复核结论 |

---

### Task 1: 安装脚本先报目标目录不存在

**Files:**
- Modify: `scripts/install-app.sh:33-34`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `--dest` 指向不存在的目录时，无论 `--app` 是否存在，都以退出码 2 报「目标目录不存在：<路径>」。

- [ ] **Step 1: Write the failing test**

在 `tests/test_packaging.py` 的 `test_install_names_the_missing_dest` 之后插入：

```python
def test_install_reports_the_missing_dest_before_the_missing_app(tmp_path):
    """两个参数都错时先说目标目录——原顺序让没构建过 dist/ 的检出里 test_install_names_the_missing_dest 失败。"""
    out = run([REPO / "scripts" / "install-app.sh",
               "--app", tmp_path / "nope.app", "--dest", tmp_path / "nope"])
    assert out.returncode == 2
    assert "目标目录不存在" in out.stderr
    assert "应用包不存在" not in out.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_packaging.py -k missing_app -q`
Expected: FAIL，stderr 是「应用包不存在：…/nope.app」

- [ ] **Step 3: Swap the two checks**

`scripts/install-app.sh` 中把

```bash
[[ -d "$APP" ]] || die "应用包不存在：$APP"
[[ -d "$DEST" ]] || die "目标目录不存在：${DEST}（请先创建，或用 --dest 指定已存在的目录）"
```

改为

```bash
[[ -d "$DEST" ]] || die "目标目录不存在：${DEST}（请先创建，或用 --dest 指定已存在的目录）"
[[ -d "$APP" ]] || die "应用包不存在：$APP"
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packaging.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/install-app.sh tests/test_packaging.py
git commit -m "fix(packaging): install-app reports a missing dest before a missing app"
```

---

### Task 2: 隔离实例不扫用户真实的模型目录

**Files:**
- Modify: `desk/foundation/paths.py`（新增 `default_data_root`，`_static_roots` 第 68–69 行复用）
- Modify: `desk/foundation/firstrun.py`（`_candidate_roots`、import 行）
- Modify: `tests/test_foundation_routes.py`（收紧 `test_get_config_lists_discovered_roots_only_while_setup_is_needed`）
- Test: `tests/test_foundation_firstrun.py`

**Interfaces:**
- Produces: `paths.default_data_root() -> Path` = `Path.home() / "Library" / "Application Support" / "LocalModelDesk"`（未规范化）
- Produces: `_candidate_roots(roots)`：
  - 总是包含：`LOCALMODELDESK_MODEL_SCAN_ROOTS` 各项、`roots.models_root`、`roots.data_root / "models"`
  - 设置了 `LOCALMODELDESK_MODEL_SCAN_ROOTS`，或 `normalize_user_path(roots.data_root) != normalize_user_path(default_data_root())` 时到此为止
  - 否则再加：真实 `.app` 内时 `home_model_root_candidates()`；`roots.resources_root` 的全部上级目录

- [ ] **Step 1: Write the failing tests**

`tests/test_foundation_firstrun.py` 顶部 import 区加 `from types import SimpleNamespace`，文件末尾追加：

```python
def _tree(path, subtree="minimax-h3"):
    (path / subtree).mkdir(parents=True)
    (path / subtree / "w.bin").write_bytes(b"x")
    return path


def test_scan_roots_env_replaces_every_guess(tmp_path, monkeypatch):
    """显式扫描目录时不许再把检出目录的上级带进来（嵌套 worktree 里发现了真实检出）。"""
    outer = _tree(tmp_path / "outer")
    repo = outer / "repo"
    repo.mkdir()
    chosen = _tree(tmp_path / "chosen", "minimax-music3")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(chosen))
    data_root = home / "Library" / "Application Support" / "LocalModelDesk"
    roots = SimpleNamespace(data_root=data_root, models_root=data_root / "models", resources_root=repo)

    assert [item["path"] for item in firstrun.discover_model_roots(roots)] == [str(chosen)]


def test_isolated_data_root_never_offers_the_real_home_or_checkout_tree(tmp_path, monkeypatch):
    """测试副本与 harness 不许把用户真实的模型树列成候选（2026-09-13 未拉的线）。"""
    home = tmp_path / "home"
    real_tree = _tree(home / "LocalModelDesk")
    checkout = _tree(tmp_path / "checkout", "llms")
    bundle = checkout / "LocalModelDesk.app" / "Contents" / "Resources"
    bundle.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", raising=False)

    isolated_data = tmp_path / "isolated-data"
    isolated = SimpleNamespace(data_root=isolated_data, models_root=isolated_data / "models", resources_root=bundle)
    assert firstrun.discover_model_roots(isolated) == []

    default_data = home / "Library" / "Application Support" / "LocalModelDesk"
    real = SimpleNamespace(data_root=default_data, models_root=default_data / "models", resources_root=bundle)
    found = {item["path"] for item in firstrun.discover_model_roots(real)}
    assert str(real_tree) in found
    assert str(checkout) in found
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_foundation_firstrun.py -k "scan_roots_env or isolated_data_root" -q`
Expected: 2 failed —— 第一个多出 `outer`，第二个 `isolated` 返回了 home 与 checkout

- [ ] **Step 3: Write the implementation**

`desk/foundation/paths.py` 在 `home_model_root_candidates` 之前加：

```python
def default_data_root() -> Path:
    """Where a real install keeps its data; any other data root is an isolated instance."""
    return Path.home() / "Library" / "Application Support" / "LocalModelDesk"
```

并把 `_static_roots` 中

```python
        data_root = Path(env_root) if env_root else Path.home() / "Library" / "Application Support" / "LocalModelDesk"
```

改为

```python
        data_root = Path(env_root) if env_root else default_data_root()
```

`desk/foundation/firstrun.py`：import 行改为 `from .paths import default_data_root, home_model_root_candidates, normalize_user_path`，`_candidate_roots` 整个替换为：

```python
def _candidate_roots(roots) -> list[Path]:
    """Return a bounded set of likely roots; never crawl the user's whole disk.

    An explicit LOCALMODELDESK_MODEL_SCAN_ROOTS replaces the guesses, and an instance on a
    non-default data root (a test copy or the e2e harness) never looks at the real home or
    the checkout around it: it must not offer, or adopt, the user's real model tree.
    """
    raw = os.environ.get("LOCALMODELDESK_MODEL_SCAN_ROOTS", "")
    explicit = [Path(item) for item in raw.split(os.pathsep) if item]
    candidates = [
        *explicit,
        getattr(roots, "models_root", roots.data_root / "models"),
        roots.data_root / "models",
    ]
    isolated = normalize_user_path(roots.data_root) != normalize_user_path(default_data_root())
    if explicit or isolated:
        return candidates
    resources_root = getattr(roots, "resources_root", None)
    if resources_root:
        resources = Path(resources_root)
        if any(parent.suffix == ".app" for parent in resources.parents):
            candidates.extend(home_model_root_candidates())
        candidates.extend(resources.parents)
    return candidates
```

- [ ] **Step 4: Tighten the route test that had to tolerate the leak**

`tests/test_foundation_routes.py` 的 `test_get_config_lists_discovered_roots_only_while_setup_is_needed` 中，删除以 `# Membership rather than equality:` 开头的 5 行注释，并把

```python
    assert str(tree) in payload["discovered"]
```

改为

```python
    assert payload["discovered"] == [str(tree)]
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_foundation_firstrun.py tests/test_foundation_routes.py tests/test_foundation_paths.py tests/test_foundation_adopt.py -q && python3 -m pytest tests/e2e/test_firstrun.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desk/foundation/paths.py desk/foundation/firstrun.py tests/test_foundation_firstrun.py tests/test_foundation_routes.py
git commit -m "fix(firstrun): isolated instances only scan explicit roots, never the real home or checkout"
```

---

### Task 3: `GET /api/config` 告诉首运页当前目录里已有哪些模型

**Files:**
- Modify: `desk/foundation/firstrun.py`（抽出 `recognized_model_keys`）
- Modify: `desk/foundation/routes.py`（`config_payload`、`get_config`）
- Modify: `desk/testing/harness.py:203-206`（`GET /api/config` 处理器）
- Test: `tests/test_foundation_routes.py`、`tests/test_foundation_firstrun.py`

**Interfaces:**
- Consumes: Task 2 的 `_candidate_roots`
- Produces: `firstrun.recognized_model_keys(path) -> list[str]` —— 目录中已有文件的目录项 key，按 `list_catalog()` 顺序；路径不存在返回 `[]`
- Produces: `routes.config_payload(roots) -> dict` —— 配置 JSON + `needs_setup`；待设置时另加 `discovered: list[str]` 与 `models_root_models: list[str]`
- Produces: `GET /api/config` 与 harness 的同名路由都返回 `config_payload(roots)`

- [ ] **Step 1: Write the failing tests**

`tests/test_foundation_firstrun.py` 末尾追加：

```python
def test_recognized_model_keys_lists_catalog_models_with_files(tmp_path):
    root = _tree(tmp_path / "models", "minimax-music3")
    (root / "minimax-h3").mkdir()  # empty directory does not count
    assert firstrun.recognized_model_keys(root) == ["music3"]
    assert firstrun.recognized_model_keys(tmp_path / "missing") == []
```

`tests/test_foundation_routes.py` 末尾追加：

```python
def test_get_config_says_which_models_the_current_root_already_has(server, tmp_path):
    kept = tmp_path / "kept"
    (kept / "minimax-music3").mkdir(parents=True)
    (kept / "minimax-music3" / "w.bin").write_bytes(b"x")
    http_call(server, "PUT", "/api/config", {"models_root": str(kept), "first_run_done": False})

    status, payload = http_call(server, "GET", "/api/config")

    assert status == 200
    assert payload["needs_setup"] is True
    assert payload["models_root_models"] == ["music3"]

    http_call(server, "PUT", "/api/config", {"first_run_done": True})
    status, payload = http_call(server, "GET", "/api/config")
    assert "models_root_models" not in payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_foundation_firstrun.py -k recognized tests/test_foundation_routes.py -k current_root -q`
Expected: FAIL（`AttributeError: ... recognized_model_keys`；`KeyError: 'models_root_models'`）

- [ ] **Step 3: Write the implementation**

`desk/foundation/firstrun.py`：在 `_nonempty_directory` 之后加：

```python
def recognized_model_keys(path) -> list[str]:
    """Catalog models that already have files under ``path``."""
    root = normalize_user_path(path)
    return [model.key for model in list_catalog() if _nonempty_directory(root / model.relpath)]
```

并在 `discover_model_roots` 中把

```python
        model_keys = [
            model.key for model in list_catalog()
            if _nonempty_directory(path / model.relpath)
        ]
```

改为

```python
        model_keys = recognized_model_keys(path)
```

`desk/foundation/routes.py`：把 `get_config` 替换为：

```python
def config_payload(roots) -> dict:
    """GET /api/config body, shared by the production route and the e2e harness."""
    cfg = config_mod.read_config(roots)
    result = _config_json(cfg)
    if cfg.needs_setup:
        result["discovered"] = [item["path"] for item in firstrun.discover_model_roots(roots)]
        result["models_root_models"] = firstrun.recognized_model_keys(cfg.models_root)
    return result


def get_config(_req) -> dict:
    return config_payload(_roots())
```

`desk/testing/harness.py`：import 区加 `from desk.foundation.routes import config_payload`，把表中

```python
        ("GET", "/api/config", lambda _req: {
            **config.read_config(roots).to_json(),
            "needs_setup": config.read_config(roots).needs_setup,
        }),
```

改为

```python
        ("GET", "/api/config", lambda _req: config_payload(roots)),
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_foundation_firstrun.py tests/test_foundation_routes.py tests/test_e2e_harness_assembly.py -q && python3 -m pytest tests/e2e/test_firstrun.py tests/e2e/test_config_recovery.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/foundation/firstrun.py desk/foundation/routes.py desk/testing/harness.py tests/test_foundation_firstrun.py tests/test_foundation_routes.py
git commit -m "feat(config): setup payload lists the models already in the current root; harness shares it"
```

---

### Task 4: 首运页可以原样返回台面，扫描结果不再悄悄填进收编框

**Files:**
- Modify: `desk/static/index.html:38-41`（首运页）
- Modify: `desk/static/app.css`（`.fr-found`）
- Modify: `desk/static/js/panes/firstrun.js`
- Test: `tests/js/firstrun_pane.test.js`、`tests/e2e/test_firstrun.py`

**Interfaces:**
- Consumes: Task 3 的 `config.models_root_models`、`config.discovered`
- Produces: 首运页新元素 `[data-fr-keep-card]`（`models_root_models` 为空时隐藏）、`[data-fr-keep-note]`、`button[data-fr-keep]`「返回台面」、`ul[data-fr-found]`
- Produces: 点击「返回台面」= `api.completeFirstRun(config.models_root)` 后 `ctx.onDone()`
- Produces: `[data-fr-legacy]` 初始为空；`discovered` 中除当前目录外的每条渲染为 `li`（路径文字 + `button`「填入」）

- [ ] **Step 1: Update the test helper and write the failing tests**

`tests/js/firstrun_pane.test.js`：把文件开头的 `class Element` 与 `function makePane` 替换为：

```javascript
class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.value = ""; this.textContent = ""; this.listeners = {};
    this.hidden = false; this.children = []; this.className = "";
  }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
}

function makePane(mode = "point") {
  const controls = new Map();
  for (const name of ["models-root", "complete", "legacy", "adopt", "error", "keep-card", "keep-note", "keep", "found"]) {
    controls.set(`[data-fr-${name}]`, new Element());
  }
  const selectedMode = new Element();
  selectedMode.value = mode;
  return {
    controls,
    root: {
      ownerDocument: { createElement: (tag) => new Element(tag) },
      querySelector: (selector) => selector === 'input[name="fr-mode"]:checked' ? selectedMode : controls.get(selector),
    },
  };
}
```

把 `test("首运页把发现到的旧模型树预填进收编输入框", ...)` 整个替换为：

```javascript
test("发现的目录列成可点的建议，不再悄悄填进收编框", async () => {
  const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
  const { root, controls } = makePane();
  const pane = createFirstRunPane(root, { onDone() {} });
  pane.init({ models_root: "/data/models", discovered: ["/data/models", "/Users/me/LocalModelDesk"], models_root_models: [] });

  const legacy = controls.get("[data-fr-legacy]");
  assert.equal(legacy.value, "");
  const items = controls.get("[data-fr-found]").children;
  assert.equal(items.length, 1);
  assert.equal(items[0].children[0].textContent, "/Users/me/LocalModelDesk");
  assert.equal(items[0].children[1].textContent, "填入");
  items[0].children[1].click();
  assert.equal(legacy.value, "/Users/me/LocalModelDesk");
  assert.equal(controls.get("[data-fr-keep-card]").hidden, true);
});

test("当前目录已有模型时可以原样返回台面", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.body]);
    return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    let done = 0;
    const pane = createFirstRunPane(root, { onDone: () => { done += 1; } });
    pane.init({ models_root: "/Users/me/LocalModelDesk", discovered: ["/Users/me/LocalModelDesk"], models_root_models: ["glm", "music3"] });

    assert.equal(controls.get("[data-fr-keep-card]").hidden, false);
    assert.equal(controls.get("[data-fr-keep-note]").textContent, "/Users/me/LocalModelDesk 里已有 2 个模型，可以不改目录直接回去。");
    assert.equal(controls.get("[data-fr-found]").children.length, 0);
    controls.get("[data-fr-models-root]").value = "/somewhere/else";
    await controls.get("[data-fr-keep]").click();

    assert.deepEqual(calls, [["/api/first-run", JSON.stringify({ models_root: "/Users/me/LocalModelDesk" })]]);
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/firstrun_pane.test.js`
Expected: 2 个新测试 FAIL（收编框被预填；没有保留卡片逻辑）

- [ ] **Step 3: Markup and CSS**

`desk/static/index.html` 第 38–41 行首运页 `<section id="pane-firstrun" ...>…</section>` 整段替换为：

```html
  <section id="pane-firstrun" hidden><div class="firstrun-wrap"><h1>LocalModelDesk 首次运行</h1><p class="hint">选择模型存放目录，或收编一份已有的模型目录树。</p>
    <div class="card" data-fr-keep-card hidden><h3>继续使用当前目录</h3><p class="hint" data-fr-keep-note></p><div class="settings-actions"><button data-fr-keep data-icon-name="check" class="btn-primary">返回台面</button></div></div>
    <div class="card"><h3>选择 models 目录</h3><label>目录 <input data-fr-models-root></label><div class="settings-actions"><button data-fr-complete data-icon-name="folder" class="btn-primary">使用该目录</button></div></div>
    <div class="card"><h3>收编既有目录树</h3><ul class="fr-found" data-fr-found></ul><label>已有根目录 <input data-fr-legacy placeholder="/path/to/existing/models"></label><label class="check-row"><input type="radio" name="fr-mode" value="point" checked><span>指向：原地使用旧目录</span></label><label class="check-row"><input type="radio" name="fr-mode" value="move"><span>移动：搬进新的 models 根</span></label><div class="settings-actions"><button data-fr-adopt data-icon-name="import" class="btn-primary">收编</button></div></div>
    <p class="inline-error" data-fr-error></p></div></section>
```

`desk/static/app.css` 在 `.firstrun-wrap input:not([type=radio]){width:100%}` 之后加：

```css
.fr-found{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.fr-found li{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.fr-found code{overflow-wrap:anywhere;min-width:0}
.fr-found:empty{display:none}
```

- [ ] **Step 4: Pane logic**

`desk/static/js/panes/firstrun.js` 中 `els` 增加四项，并用下面的 `init` 与保留按钮监听替换原 `init`：

```javascript
    keepCard: root.querySelector("[data-fr-keep-card]"),
    keepNote: root.querySelector("[data-fr-keep-note]"),
    keepBtn: root.querySelector("[data-fr-keep]"),
    found: root.querySelector("[data-fr-found]"),
```

```javascript
  let currentRoot = null;

  // Found trees are suggestions the user picks, never a silent prefill: a stray 收编
  // must not move the models root onto whatever the scan happened to find.
  function renderFound(paths) {
    if (!els.found) return;
    const doc = root.ownerDocument;
    els.found.replaceChildren(...paths.map((path) => {
      const li = doc.createElement("li");
      const text = doc.createElement("code");
      text.textContent = path;
      const use = doc.createElement("button");
      use.type = "button";
      use.className = "btn-sm";
      use.textContent = "填入";
      use.addEventListener("click", () => { els.legacyRoot.value = path; });
      li.append(text, use);
      return li;
    }));
  }

  function init(config) {
    currentRoot = config?.models_root ?? null;
    els.modelsRoot.value = currentRoot ?? "";
    const kept = config?.models_root_models ?? [];
    if (els.keepCard) {
      els.keepCard.hidden = kept.length === 0;
      els.keepNote.textContent = kept.length ? `${currentRoot} 里已有 ${kept.length} 个模型，可以不改目录直接回去。` : "";
    }
    renderFound((config?.discovered ?? []).filter((path) => path !== currentRoot));
  }

  els.keepBtn?.addEventListener("click", async () => {
    setError("");
    try {
      await api.completeFirstRun(currentRoot);
      ctx.onDone();
    } catch (error) { setError(error.message); }
  });
```

- [ ] **Step 5: Run unit tests**

Run: `node --test "tests/js/*.test.js"`
Expected: PASS

- [ ] **Step 6: Write the e2e test**

`tests/e2e/test_firstrun.py` 末尾追加：

```python
def test_reset_models_root_can_return_to_the_desk_unchanged(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.request.put(f"{harness.base_url}/api/config", data={"first_run_done": False})
        page.goto(harness.base_url)

        expect(page.locator("#pane-firstrun [data-fr-keep-note]")).to_contain_text("个模型")
        expect(page.locator("#pane-firstrun [data-fr-legacy]")).to_have_value("")
        page.locator("#pane-firstrun").get_by_role("button", name="返回台面").click()

        expect(page.locator("#pane-firstrun")).to_be_hidden()
        expect(page.locator("main")).to_be_visible()
        config = page.request.get(f"{harness.base_url}/api/config").json()
        assert config["first_run_done"] is True
        assert config["models_root"] == str(harness.models_root)
    assert audit_violations == []
```

- [ ] **Step 7: Run e2e**

Run: `python3 -m pytest tests/e2e/test_firstrun.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS（若 `config["models_root"]` 与 `str(harness.models_root)` 只差符号链接展开，改为比较 `Path(...).resolve()`）

- [ ] **Step 8: Commit**

```bash
git add desk/static/index.html desk/static/app.css desk/static/js/panes/firstrun.js tests/js/firstrun_pane.test.js tests/e2e/test_firstrun.py
git commit -m "feat(ui): first-run can return to the desk with the current root; found trees are suggestions"
```

---

### Task 5: 视频面板对极慢的参数组合给出提醒

**Files:**
- Create: `desk/static/js/pure/video_cost.js`
- Modify: `desk/static/js/panes/video.js`
- Modify: `desk/static/index.html:29`（时长下拉之后加提示占位）
- Test: `tests/js/video_cost.test.js`（新）、`tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `videoCostNote(size: string, frames: number|string) -> string` —— `size === "1024x576"` 且 `Number(frames) >= 243` 时返回提醒文案，否则 `""`
- Produces: 视频面板 `p[data-video-cost-note]` 在 `fill()`、画幅或时长 `change` 后更新

- [ ] **Step 1: Write the failing tests**

新建 `tests/js/video_cost.test.js`：

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { videoCostNote } from "../../desk/static/js/pure/video_cost.js";

test("只有清晰画幅加 10 秒以上才提醒（有实测依据的组合）", () => {
  const slow = videoCostNote("1024x576", 243);
  assert.match(slow, /20 分钟只走完 2\/16 步/);
  assert.equal(videoCostNote("1024x576", "362"), slow);
  assert.equal(videoCostNote("1024x576", 192), "");
  assert.equal(videoCostNote("768x448", 362), "");
  assert.equal(videoCostNote("512x288", 49), "");
});
```

`tests/js/media_panes.test.js` 末尾追加：

```javascript
test("清晰画幅加 10 秒以上时视频面板提示很慢，改小后提示消失", () => {
  const video = pane({ "video-prompt": "", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "", "video-cost-note": "" });
  const videoPane = createVideoPane(video);
  assert.equal(video.parts["video-cost-note"].textContent, "");

  videoPane.fill({ width: 1024, height: 576, frames: 362 });
  assert.match(video.parts["video-cost-note"].textContent, /20 分钟只走完 2\/16 步/);

  video.parts["video-size"].value = "512x288";
  video.parts["video-size"].listeners.change();
  assert.equal(video.parts["video-cost-note"].textContent, "");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/video_cost.test.js tests/js/media_panes.test.js`
Expected: FAIL（模块不存在；提示为空）

- [ ] **Step 3: Pure function**

新建 `desk/static/js/pure/video_cost.js`：

```javascript
// 视频参数 → 提交前的耗时提醒。只提醒有实测依据的组合：cross-exam 2026-09-13 q16，
// 1024×576 × 15 秒在 128 GB 机器上 20 分钟只走完 2/16 步。不编造分钟数估算。
const SLOW_SIZE = "1024x576";
const SLOW_FRAMES = 243; // 「约 10 秒」档

export function videoCostNote(size, frames) {
  if (size === SLOW_SIZE && Number(frames) >= SLOW_FRAMES) {
    return "清晰画幅加 10 秒以上会非常慢：实测曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。";
  }
  return "";
}
```

- [ ] **Step 4: Pane wiring and markup**

`desk/static/js/panes/video.js`：import 区加 `import { videoCostNote } from "../pure/video_cost.js";`。在 `mode?.addEventListener("change", updateMode);` 之后加：

```javascript
  const costNote = root.querySelector("[data-video-cost-note]");
  function updateCost() {
    if (costNote) costNote.textContent = videoCostNote(els.size.value, els.frames.value);
  }
  els.size.addEventListener("change", updateCost);
  els.frames.addEventListener("change", updateCost);
  updateCost();
```

在 `fill(fields)` 函数体最后一行（`if (fields.steps != null) els.steps.value = String(fields.steps);`）之后加 `updateCost();`。

`desk/static/index.html:29` 中 `<label>视频时长 <select data-video-frames></select></label>` 之后紧接插入：

```html
<p class="hint hint-busy" data-video-cost-note></p>
```

- [ ] **Step 5: Run tests**

Run: `node --test "tests/js/*.test.js" && python3 -m pytest tests/e2e/test_video_flow.py tests/e2e/test_prompt_assist.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/pure/video_cost.js desk/static/js/panes/video.js desk/static/index.html tests/js/video_cost.test.js tests/js/media_panes.test.js
git commit -m "feat(ui): warn before the video size and length combination measured to take over an hour"
```

---

### Task 6: 真实 app 复核余下四项，并写回索引

**Files:**
- Modify: `docs/superpowers/plans/2026-09-14-recheck-index.md`（「未拉的线 → 处理」表）

本任务不写产品代码。每一步把观察（截图路径、读到的菜单项文字、结论）记在 `/tmp/lmd-g/notes.md`，最后汇总进索引。截图只存 `/tmp/lmd-g/`，不入库。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest -q && node --test "tests/js/*.test.js" && python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 2: 构建并起隔离副本**

```bash
pgrep -fl 'LocalModelDesk.app/Contents/MacOS/LocalModelDesk' && echo "先退出其它 LocalModelDesk 实例再继续" && exit 1
./scripts/build-app.sh
mkdir -p /tmp/lmd-g/data /tmp/lmd-g/app
printf '{"config_version":1,"first_run_done":true,"models_root":"%s","gateway":{"enabled":false,"host":"127.0.0.1","port":8845}}' "$HOME/LocalModelDesk" > /tmp/lmd-g/data/config.json
ditto dist/LocalModelDesk.app /tmp/lmd-g/app/LocalModelDesk.app
(LOCALMODELDESK_DATA_ROOT=/tmp/lmd-g/data LMD_SHELL_PORT=8839 nohup /tmp/lmd-g/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk > /tmp/lmd-g/shell.log 2>&1 &)
for i in $(seq 1 40); do curl -sf 127.0.0.1:8839/api/state >/dev/null && break; sleep 1; done
SH=$(pgrep -f '^/tmp/lmd-g/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk'); echo "shell=$SH"
```

Expected: `built:` 行；`/api/state` 可达；`shell=` 后是一个 pid。以下步骤里的 `$SH` 都指它。

- [ ] **Step 3: 编辑 / 窗口菜单项是否中文**

```bash
osascript -l JavaScript -e "ObjC.import('AppKit'); \$.NSRunningApplication.runningApplicationWithProcessIdentifier($SH).activateWithOptions(3); 'ok'"
sleep 1; lsappinfo info -only pid "$(lsappinfo front)"
osascript -l JavaScript -e "
var p = Application('System Events').processes.whose({unixId: $SH})[0];
['编辑','窗口'].map(function(m){ return m + ': ' + p.menuBars[0].menuBarItems.byName(m).menus[0].menuItems.name().join(' | '); }).join('\n');"
```

Expected: 第二条输出的 pid 等于 `$SH`；两行菜单项里没有 `Writing Tools`、`AutoFill`、`Start Dictation`、`Center`、`Minimize All` 等英文项。
若仍有英文：记录原文，在索引中写「系统注入项仍为英文（lproj 未生效）」并单列为待办，不在本计划内修。

- [ ] **Step 4: 网页右键菜单「重新载入」**

```bash
cat > /tmp/lmd-g/rightclick.js <<'EOF'
ObjC.import('CoreGraphics');
function run(argv) {
  var x = parseFloat(argv[0]), y = parseFloat(argv[1]);
  var pt = $.CGPointMake(x, y);
  $.CGEventPost(0, $.CGEventCreateMouseEvent(null, 3, pt, 1));
  delay(0.05);
  $.CGEventPost(0, $.CGEventCreateMouseEvent(null, 4, pt, 1));
  return 'ok';
}
EOF
BOUNDS=$(osascript -l JavaScript -e "var w = Application('System Events').processes.whose({unixId: $SH})[0].windows[0]; var p = w.position(), s = w.size(); [p[0] + Math.round(s[0]/2), p[1] + Math.round(s[1]*0.6)].join(' ')")
osascript -l JavaScript /tmp/lmd-g/rightclick.js $BOUNDS
sleep 1; screencapture -x /tmp/lmd-g/contextmenu.png
osascript -e 'tell application "System Events" to key code 53'
```

Expected: 打开 `/tmp/lmd-g/contextmenu.png`，右键菜单里是「重新载入」而不是 `Reload`。

- [ ] **Step 5: WKWebView 里的键盘操作**

```bash
curl -s -X POST 127.0.0.1:8839/api/sessions -H 'Content-Type: application/json' -d '{"title":"键盘测试一"}' >/dev/null
curl -s -X POST 127.0.0.1:8839/api/sessions -H 'Content-Type: application/json' -d '{"title":"键盘测试二"}' >/dev/null
WID=$(osascript -l JavaScript -e "ObjC.import('CoreGraphics'); var l = ObjC.castRefToObject(\$.CGWindowListCopyWindowInfo(1,0)); var r=''; for (var i=0;i<l.count;i++){var w=l.objectAtIndex(i); if (w.objectForKey('kCGWindowOwnerPID').intValue==$SH && w.objectForKey('kCGWindowLayer').intValue==0){r=w.objectForKey('kCGWindowNumber').intValue; break;}} r")
osascript -l JavaScript -e "ObjC.import('AppKit'); \$.NSRunningApplication.runningApplicationWithProcessIdentifier($SH).activateWithOptions(3); 'ok'"
sleep 11   # 会话列表每 5 个 2 秒 tick 刷新一次，等新会话出现
lsappinfo info -only pid "$(lsappinfo front)"   # 必须仍是 $SH，否则不要发按键
for n in 1 2 3; do osascript -e 'tell application "System Events" to key code 48'; sleep 0.3; screencapture -x -o -l "$WID" "/tmp/lmd-g/tab-$n.png"; done
osascript -e 'tell application "System Events" to key code 36'; sleep 1; screencapture -x -o -l "$WID" /tmp/lmd-g/tab-enter.png
```

Expected: `tab-*.png` 中能看到焦点环依次落在「新会话」按钮与会话卡片上；`tab-enter.png` 中按 Enter 后当前高亮的会话变成焦点所在的那张卡片。
若焦点环不可见：记录截图，写入索引待办「WKWebView 中卡片焦点不可见」。

素材文件选择的键盘路径（图生视频的「选择首帧图片」）不在真机上测：切换生成方式需要操作原生下拉菜单，按键容易发错目标。该项记为「由 `tests/e2e/test_video_flow.py::test_first_frame_picker_is_reachable_by_keyboard` 覆盖，真机未测」。

- [ ] **Step 6: 宽窗口留白与窗口/网页高度**

```bash
system_profiler SPDisplaysDataType | grep "UI Looks like"
osascript -l JavaScript -e "var w = Application('System Events').processes.whose({unixId: $SH})[0].windows[0]; w.position = [0, 25]; w.size = [1920, 1050]; 'ok'"
sleep 1; screencapture -x -o -l "$WID" /tmp/lmd-g/wide.png
sips -g pixelWidth -g pixelHeight /tmp/lmd-g/wide.png
```

Expected: 显示器逻辑宽度若小于 2560，记录「真机最大 1920 宽，2560 由 `tests/e2e/test_chat_layout.py` 覆盖」。打开 `wide.png`：消息列两侧空白合计目测不超过窗口宽的 40%（1920 宽时 e2e 实测约 24%）；网页背景一直铺到窗口底边，底部没有系统灰色空带（旧线索「内容区 832 / 视口 696」若无空带即关闭）。

- [ ] **Step 7: 首运页返回台面与耗时提醒（本计划新功能）**

页面只在启动时读一次配置，改完配置要重开副本：

```bash
curl -s -X PUT 127.0.0.1:8839/api/config -H 'Content-Type: application/json' -d '{"first_run_done": false}' >/dev/null
kill -TERM "$SH"; for i in $(seq 1 20); do pgrep -f 'lmd-g/app' >/dev/null || break; sleep 1; done
(LOCALMODELDESK_DATA_ROOT=/tmp/lmd-g/data LMD_SHELL_PORT=8839 nohup /tmp/lmd-g/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk > /tmp/lmd-g/shell2.log 2>&1 &)
for i in $(seq 1 40); do curl -sf 127.0.0.1:8839/api/state >/dev/null && break; sleep 1; done
SH=$(pgrep -f '^/tmp/lmd-g/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk'); sleep 3
WID=$(osascript -l JavaScript -e "ObjC.import('CoreGraphics'); var l = ObjC.castRefToObject(\$.CGWindowListCopyWindowInfo(1,0)); var r=''; for (var i=0;i<l.count;i++){var w=l.objectAtIndex(i); if (w.objectForKey('kCGWindowOwnerPID').intValue==$SH && w.objectForKey('kCGWindowLayer').intValue==0){r=w.objectForKey('kCGWindowNumber').intValue; break;}} r")
screencapture -x -o -l "$WID" /tmp/lmd-g/firstrun.png
curl -s 127.0.0.1:8839/api/config | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["needs_setup"], d["models_root_models"], d["discovered"])'
```

Expected: `firstrun.png` 顶部有「继续使用当前目录」卡片，文案含「已有 N 个模型」；收编框为空；`discovered` 只含 `~/LocalModelDesk`（数据根是 `/tmp/lmd-g/data`，属隔离实例，不应出现检出目录的上级）。点「返回台面」后回到聊天页，`models_root` 不变：

```bash
curl -s 127.0.0.1:8839/api/config | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["first_run_done"], d["models_root"])'
```

（点按钮用坐标：从 `firstrun.png` 读出按钮中心，按窗口位置换算后用 `osascript -e 'tell application "System Events" to click at {x, y}'`；若换算不确定，改为直接 `curl -X POST .../api/first-run -d '{"models_root":"'$HOME'/LocalModelDesk"}'` 并在记录中注明按钮本身由 e2e 覆盖。）

- [ ] **Step 8: 清理副本**

```bash
kill -TERM "$SH"; for i in $(seq 1 20); do pgrep -f 'lmd-g/app' >/dev/null || break; sleep 1; done
pgrep -fl 'lmd-g/app' || echo stopped
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(8839|8767)\b' || echo "ports free"
rm -rf /tmp/lmd-g/app /tmp/lmd-g/data
```

Expected: `stopped`、`ports free`。**不删除** `~/LocalModelDesk`。

- [ ] **Step 9: 写回索引**

在 `docs/superpowers/plans/2026-09-14-recheck-index.md` 的「未拉的线 → 处理」表里，把下列行的「处理」列改写为结论（按 Step 3–7 的实际观察填写，示例是期望通过时的写法）：

| 线 | 处理 |
|---|---|
| 首运页无「返回台面」、收编框预填扫描路径 | 2026-09-15 余项计划 Task 3–4：保留卡片「返回台面」；扫描结果改为「填入」建议 |
| 隔离数据根时 `discovered` 仍扫真实 `$HOME` | 2026-09-15 余项计划 Task 2：非默认数据根只扫显式目录 |
| 视频长参数耗时预期 | 2026-09-15 余项计划 Task 5：1024×576 且 ≥10 秒时提醒，不给分钟数 |
| VPN 隧道地址时 base URL 选哪个 | 不改：`lan.py` 跳过 `utun*` 与 100.64/10，单测覆盖；真机无隧道环境 |
| 菜单栏图标辨识度、状态滞后约 2 秒 | 不改：视觉与轮询策略取舍 |
| 原生窗口内容区 832 与 WebView 696 | 真机 2026-09-15：网页铺满窗口，无空带，关闭 |
| 编辑/窗口菜单混入英文系统项 | 真机 2026-09-15：<Step 3 观察> |
| 右键菜单英文 Reload | 真机 2026-09-15：<Step 4 观察> |

（最后两行尖括号里填 Step 3、Step 4 的实际结果原文，例如「全部中文」或「仍有 Writing Tools、AutoFill」。）

并在索引末尾「执行后复核」段前追加一行：`余项计划：docs/superpowers/plans/2026-09-15-recheck-leftovers.md`。

- [ ] **Step 10: Commit**

```bash
git add docs/superpowers/plans/2026-09-14-recheck-index.md
git commit -m "docs: record the leftover recheck results in the plan index"
```

---

## 追加任务（2026-09-15 真机复核后）

Task 6 在真实 app 里发现：系统「键盘导航」关闭（macOS 默认）时，WKWebView 的 Tab 跳过 `<button>`（「新会话」「发送」），只停在输入框和 `tabindex=0` 的卡片；`tests/e2e` 用的 Chromium 测不出。另「返回台面」按钮因会在 `~/LocalModelDesk` 顶层写探针文件而未在真机点击。

WebKit 在 macOS 上按 `KeyboardAccessTabsToLinks` 决定 Tab 是否经过全部表单控件（与 Safari「按下 Tab 键以高亮显示网页上的每个项目」同源）；`WKPreferences.tabFocusesLinks = true` 打开它，不改用户的系统设置。

### Task 7: 真实 app 里 Tab 能停在按钮上

**Files:**
- Modify: `macos/MainWindowController.swift:19-22`
- Test: `tests/test_shell_static.py`

**Interfaces:**
- Produces: 主窗口 WKWebView 配置 `config.preferences.tabFocusesLinks = true`，在创建 `DeskWebView` 之前设置。

- [ ] **Step 1: Write the failing test**

在 `tests/test_shell_static.py` 的 `test_web_view_context_menu_is_localized` 之后插入：

```python
def test_web_view_tab_key_reaches_buttons_without_system_keyboard_navigation():
    """macOS 默认关闭「键盘导航」时，WebKit 的 Tab 跳过按钮，只停在文本框与 tabindex 元素（2026-09-15 真机复核）。"""
    text = (MACOS / "MainWindowController.swift").read_text(encoding="utf-8")
    line = "config.preferences.tabFocusesLinks = true"
    assert line in text
    assert text.index(line) < text.index("DeskWebView(frame:")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_shell_static.py -k tab_key -q`
Expected: FAIL（`assert line in text`）

- [ ] **Step 3: Write the implementation**

`macos/MainWindowController.swift` 中，在 `config.userContentController.add(self, name: "shellRetry")` 之后、`webView = DeskWebView(frame: .zero, configuration: config)` 之前插入：

```swift
    // With macOS keyboard navigation off (the default) WebKit's Tab skips buttons. Tab-to-links
    // makes Tab visit every control, like Safari's "Press Tab to highlight each item", without
    // touching the user's system setting.
    config.preferences.tabFocusesLinks = true
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_shell_*.py -q`
Expected: PASS（含 `test_swiftc_parse`）

- [ ] **Step 5: Commit**

```bash
git add macos/MainWindowController.swift tests/test_shell_static.py
git commit -m "fix(shell): Tab reaches buttons in the web view with system keyboard navigation off"
```

---

### Task 8: 真实 app 复核 Tab 到按钮与「返回台面」，写回索引

**Files:**
- Modify: `docs/superpowers/plans/2026-09-14-recheck-index.md`（「未拉的线 → 处理」表中「首运页无「返回台面」…」与「WKWebView 中 Tab 跳过按钮…」两行）

本任务不写产品代码。模型根用 `/tmp/lmd-h/mroot`：其中 `llms`、`minimax-h3`、`minimax-music3` 是指向 `~/LocalModelDesk` 同名子树的符号链接，完成首运时的探针文件只写在 `/tmp/lmd-h/mroot` 顶层。**不向 `~/LocalModelDesk` 写任何东西**；不加载模型、不下载、不删除。观察记在 `/tmp/lmd-h/notes.md`，截图只存 `/tmp/lmd-h/`。

- [ ] **Step 1: 构建并以待设置状态起隔离副本**

```bash
pgrep -fl 'LocalModelDesk.app/Contents/MacOS/LocalModelDesk' && echo "先退出其它 LocalModelDesk 实例再继续" && exit 1
./scripts/build-app.sh
mkdir -p /tmp/lmd-h/data /tmp/lmd-h/app /tmp/lmd-h/mroot
for d in llms minimax-h3 minimax-music3; do ln -sfn "$HOME/LocalModelDesk/$d" "/tmp/lmd-h/mroot/$d"; done
printf '{"config_version":1,"first_run_done":false,"models_root":"/tmp/lmd-h/mroot","gateway":{"enabled":false,"host":"127.0.0.1","port":8845}}' > /tmp/lmd-h/data/config.json
ditto dist/LocalModelDesk.app /tmp/lmd-h/app/LocalModelDesk.app
touch /tmp/lmd-h/started
(LOCALMODELDESK_DATA_ROOT=/tmp/lmd-h/data LMD_SHELL_PORT=8839 nohup /tmp/lmd-h/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk > /tmp/lmd-h/shell.log 2>&1 &)
for i in $(seq 1 40); do curl -sf 127.0.0.1:8839/api/state >/dev/null && break; sleep 1; done
SH=$(pgrep -f '^/tmp/lmd-h/app/LocalModelDesk.app/Contents/MacOS/LocalModelDesk'); echo "shell=$SH"
curl -s 127.0.0.1:8839/api/config | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["needs_setup"], d["models_root_models"])'
```

Expected: `built:`；`shell=` 一个 pid；`True` 与非空模型 key 列表。

- [ ] **Step 2: 只用键盘点「返回台面」**

```bash
WID=$(osascript -l JavaScript -e "ObjC.import('CoreGraphics'); var l = ObjC.castRefToObject(\$.CGWindowListCopyWindowInfo(1,0)); var r=''; for (var i=0;i<l.count;i++){var w=l.objectAtIndex(i); if (w.objectForKey('kCGWindowOwnerPID').intValue==$SH && w.objectForKey('kCGWindowLayer').intValue==0){r=w.objectForKey('kCGWindowNumber').intValue; break;}} r")
osascript -l JavaScript -e "ObjC.import('AppKit'); \$.NSRunningApplication.runningApplicationWithProcessIdentifier($SH).activateWithOptions(3); 'ok'"
sleep 8; lsappinfo info -only pid "$(lsappinfo front)"
screencapture -x -o -l "$WID" /tmp/lmd-h/firstrun.png
osascript -e 'tell application "System Events" to key code 48'; sleep 0.5
screencapture -x -o -l "$WID" /tmp/lmd-h/firstrun-tab1.png
```

Expected: 前台 pid 等于 `$SH`；读 `firstrun-tab1.png`：焦点环在「返回台面」按钮上（它是页面第一个控件）。若焦点不在该按钮，继续按 Tab（每次截图 `firstrun-tabN.png`）直到焦点落在它上面，最多 6 次；仍到不了则记「Tab 到不了按钮：不通过」并跳到 Step 4。

焦点在「返回台面」上时：

```bash
osascript -e 'tell application "System Events" to key code 49'; sleep 3
screencapture -x -o -l "$WID" /tmp/lmd-h/after-keep.png
curl -s 127.0.0.1:8839/api/config | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["first_run_done"], d["models_root"])'
find "$HOME/LocalModelDesk" -maxdepth 1 -newer /tmp/lmd-h/started -print
```

Expected: `after-keep.png` 为聊天台面；输出 `True /tmp/lmd-h/mroot`（或其规范化形式）；`find` 无输出（`~/LocalModelDesk` 顶层无新文件）。

- [ ] **Step 3: 台面里 Tab 经过「新会话」与「发送」**

```bash
for n in 1 2 3 4 5 6 7 8; do osascript -e 'tell application "System Events" to key code 48'; sleep 0.4; screencapture -x -o -l "$WID" "/tmp/lmd-h/desk-tab-$n.png"; osascript -l JavaScript -e "var p = Application('System Events').processes.whose({unixId: $SH})[0]; var f = p.attributes.byName('AXFocusedUIElement').value(); [f.role(), f.description ? f.description() : '', f.title ? f.title() : ''].join(' | ')" 2>/dev/null | sed "s/^/tab $n: /"; done
```

Expected: 读截图，至少一张焦点环在「新会话」按钮上、至少一张在「发送」按钮上；对应行的 AX 角色为 `AXButton`。

- [ ] **Step 4: 清理副本**

```bash
kill -TERM "$SH"; for i in $(seq 1 20); do pgrep -f 'lmd-h/app' >/dev/null || break; sleep 1; done
pgrep -fl 'lmd-h/app' || echo stopped
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(8839|8767)\b' || echo "ports free"
rm -f /tmp/lmd-h/mroot/llms /tmp/lmd-h/mroot/minimax-h3 /tmp/lmd-h/mroot/minimax-music3
rm -rf /tmp/lmd-h/app /tmp/lmd-h/data
```

Expected: `stopped`、`ports free`。删除符号链接用 `rm -f <链接>`（不带尾部斜杠，不带 `-r`），不会影响链接指向的真实目录。

- [ ] **Step 5: 写回索引并提交**

在 `docs/superpowers/plans/2026-09-14-recheck-index.md` 中：
- 「首运页无「返回台面」、收编框预填扫描路径」一行：把「「返回台面」按钮真机未测：…覆盖」改为 Step 2 的实际结论（例如「真机 2026-09-15：Tab 到「返回台面」按 Space 回到台面，models_root 不变，`~/LocalModelDesk` 无新文件」）。
- 「WKWebView 中 Tab 跳过按钮」一行：处理列改为「2026-09-15 余项计划 Task 7：`tabFocusesLinks`；真机：<Step 3 实际结论>」。

```bash
git add docs/superpowers/plans/2026-09-14-recheck-index.md
git commit -m "docs: record Tab-to-button and return-to-desk results from the real app"
```
