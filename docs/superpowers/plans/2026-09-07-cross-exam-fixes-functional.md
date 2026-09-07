# Cross-Exam Fix List A · 功能与可靠性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every functional / reliability gap recorded by the 2026-09-06 cross-exam (G-numbers and J-numbers below) so the shipped `LocalModelDesk.app` matches its own requirement registry.

**Architecture:** Python service (`desk/`, stdlib HTTP server, one composition root in `desk/runtime.py`), static ES-module frontend (`desk/static/js`, zero dependencies, `node --test`), Swift AppKit shell (`macos/`, tested through a headless harness compiled by `scripts/shell-lifecycle-test.sh`). Every fix lands with a test at the layer that owns the behaviour: pure Python modules → `pytest`; frontend modules → `node --test tests/js`; Swift decision logic → moved into `ShellStatus.swift` and exercised through the harness.

**Tech Stack:** Python 3.13 stdlib · Node 20+ (`node:test`) · Swift 5 / AppKit · pytest · Playwright e2e (unchanged)

**Spec:** `docs/cross-exam/2026-09-06-localmodeldesk/completion-report.md` (gap list §缺口清单, patterns §缺陷模式) with evidence under `docs/cross-exam/2026-09-06-localmodeldesk/evidence/`. Requirement baseline: `docs/superpowers/specs/2026-08-31-*-spec.md`.

## Global Constraints

- Python: no third-party packages in `desk/` (stdlib only; `huggingface_hub` is only ever a subprocess).
- Frontend: no build step, no dependencies; DOM via `createElement`/`textContent` only, never `innerHTML` (ui-spec R-ui-01).
- All user-facing strings are Simplified Chinese; machine codes never render as the only explanation (C3/F2 of the confirmed visual baseline).
- Tests: `python3 -m pytest -q` for Python, `node --test tests/js` for JS, `python3 -m pytest tests/test_shell_*.py` for Swift (compiles harness via `xcrun swiftc`).
- Commit after every task with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK` trailers.
- Never touch `~/LocalModelDesk` model weights or `~/Library/Application Support/LocalModelDesk` from tests: every test uses `tmp_path` and `LOCALMODELDESK_DATA_ROOT`.

## File Structure (what changes, one responsibility each)

| File | Responsibility touched |
|---|---|
| `desk/foundation/errors.py` | add `ConfigInvalidError` (400) |
| `desk/foundation/config.py` | validate before write; typed errors for bad field types |
| `desk/foundation/firstrun.py` | split discovery (read-only) from apply (explicit) |
| `desk/foundation/routes.py` | `/api/config` exposes `discovered`; `/api/models/discover` applies |
| `desk/runtime.py` | no startup rewrite; corrupt-config-safe gateway callback; serve_forever robustness |
| `desk/gateway/service.py` | `lan_host` in status |
| `desk/resources/downloader.py` | attempt-scoped incomplete accounting, stale cleanup, hf env |
| `desk/foundation/paths.py` | `hf_env` |
| `desk/media/service.py` | memory pre-check, failure log tail |
| `desk/media/routes.py` | lyrics validation, `force` flag |
| `desk/llm/service.py` | keep arbiter reason code |
| `desk/library/http.py`, `desk/library/outputs.py` | reveal-in-Finder endpoint |
| `desk/static/js/api.js` | request timeout, new endpoints |
| `desk/static/js/main.js` | tick polls llm status, sessions refresh, drawer/tab coupling, hash tab |
| `desk/static/js/panes/*.js`, `widgets/jobview.js`, `pure/*.js` | behaviour fixes listed per task |
| `macos/ShellStatus.swift`, `macos/AppDelegate.swift`, `macos/ServerController.swift`, `macos/MainWindowController.swift`, `macos/FirstRunFlow.swift`, `macos/harness/ShellHarness.swift` | hang detection, attach-safe quit, dark error page, retry loop |
| `scripts/sign-app.sh`, `scripts/build-app.sh` | refuse silent adhoc signing |

---

### Task 1: Config — validate before writing, typed errors (G7, P3)

**Files:**
- Modify: `desk/foundation/errors.py`
- Modify: `desk/foundation/config.py:81-163`
- Test: `tests/test_foundation_config.py`

**Interfaces:**
- Produces: `ConfigInvalidError(FoundationError)` with `code="config_invalid"`, `http_status=400`, payload `{"field": str, "reason": str}`; `update_config(roots, **fields)` raises it and leaves `config.json` untouched; `read_config` raises `ConfigCorruptError` (not `ValueError`) for wrong on-disk types.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_foundation_config.py
from desk.foundation.errors import ConfigInvalidError


def test_update_config_rejects_bad_port_type_and_keeps_file_untouched(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"first_run_done": True, "gateway": {"port": 8770}}), encoding="utf-8")
    before = roots.config_path.read_bytes()
    with pytest.raises(ConfigInvalidError) as exc:
        config_mod.update_config(roots, gateway={"port": "not-a-number"})
    assert exc.value.code == "config_invalid"
    assert exc.value.payload["field"] == "gateway.port"
    assert roots.config_path.read_bytes() == before


@pytest.mark.parametrize("fields,field", [
    ({"gateway": {"port": 0}}, "gateway.port"),
    ({"gateway": {"port": 70000}}, "gateway.port"),
    ({"gateway": {"host": ""}}, "gateway.host"),
    ({"gateway": {"enabled": "yes"}}, "gateway.enabled"),
    ({"first_run_done": "false"}, "first_run_done"),
    ({"models_root": 12}, "models_root"),
])
def test_update_config_rejects_each_bad_field(tmp_path, fields, field):
    roots = make_roots(tmp_path)
    with pytest.raises(ConfigInvalidError) as exc:
        config_mod.update_config(roots, **fields)
    assert exc.value.payload["field"] == field
    assert not roots.config_path.exists()


def test_read_config_reports_wrong_type_on_disk_as_corrupt(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"gateway": {"port": "abc"}}), encoding="utf-8")
    with pytest.raises(ConfigCorruptError) as exc:
        config_mod.read_config(roots)
    assert "gateway.port" in exc.value.payload["parse_error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_foundation_config.py -q -k "bad_port or bad_field or wrong_type"`
Expected: FAIL — `ImportError: cannot import name 'ConfigInvalidError'`

- [ ] **Step 3: Implement**

`desk/foundation/errors.py` — append:

```python
class ConfigInvalidError(FoundationError):
    code = "config_invalid"
    http_status = 400
```

`desk/foundation/config.py` — replace `_from_raw` and `update_config`:

```python
from .errors import ConfigCorruptError, ConfigInvalidError


def _validate(merged: dict, gateway: dict) -> None:
    """Raise ConfigInvalidError naming the first offending field."""
    def bad(field: str, reason: str) -> None:
        raise ConfigInvalidError(f"invalid {field}: {reason}", field=field, reason=reason)
    if not isinstance(merged["config_version"], int) or isinstance(merged["config_version"], bool):
        bad("config_version", "must be an integer")
    if not isinstance(merged["first_run_done"], bool):
        bad("first_run_done", "must be true or false")
    for key in ("models_root", "outputs_root"):
        if not isinstance(merged[key], str) or not merged[key]:
            bad(key, "must be a non-empty path string")
    if not isinstance(gateway["enabled"], bool):
        bad("gateway.enabled", "must be true or false")
    if not isinstance(gateway["host"], str) or not gateway["host"].strip():
        bad("gateway.host", "must be a non-empty host string")
    port = gateway["port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        bad("gateway.port", "must be an integer between 1 and 65535")


def _from_raw(raw: dict | None, data_root: Path, *, source: str = "file") -> DeskConfig:
    defaults = _defaults(data_root)
    merged = dict(defaults)
    file_gateway: dict = {}
    if raw:
        for key, value in raw.items():
            if key == "gateway" and isinstance(value, dict):
                file_gateway = value
            elif key in _KNOWN_KEYS:
                merged[key] = value
    gateway = dict(defaults["gateway"])
    gateway.update({key: value for key, value in file_gateway.items() if key in _GATEWAY_KEYS})
    try:
        _validate(merged, gateway)
    except ConfigInvalidError as exc:
        if source == "file":
            raise ConfigCorruptError(
                f"config.json is corrupt: {exc.message}",
                path="config.json", parse_error=f"{exc.payload['field']}: {exc.payload['reason']}",
            ) from exc
        raise
    extra = {key: value for key, value in (raw or {}).items() if key not in _KNOWN_KEYS}
    return DeskConfig(
        config_version=merged["config_version"],
        first_run_done=merged["first_run_done"],
        models_root=Path(merged["models_root"]),
        outputs_root=Path(merged["outputs_root"]),
        gateway=GatewayConfig(enabled=gateway["enabled"], host=gateway["host"], port=gateway["port"]),
        needs_setup=(raw is None) or not merged["first_run_done"],
        extra=extra,
    )


def update_config(roots, **fields) -> DeskConfig:
    """Locked read-validate-write: nothing reaches disk unless it parses back."""
    with _LOCK:
        raw = _load_raw(roots.config_path)
        current = _from_raw(raw, roots.data_root)
        merged = current.to_json()
        for key, value in fields.items():
            if key == "gateway" and isinstance(value, dict):
                gateway = dict(merged["gateway"])
                gateway.update({key: val for key, val in value.items() if key in _GATEWAY_KEYS})
                merged["gateway"] = gateway
            elif isinstance(value, Path):
                merged[key] = str(value)
            else:
                merged[key] = value
        validated = _from_raw(merged, roots.data_root, source="update")
        _atomic_write(roots.config_path, merged)
        return validated
```

Also delete the old `int(...)`/`bool(...)` coercions (they were the bug: `int("8770")` silently accepted strings, `bool("false")` became `True`).

- [ ] **Step 4: Run the whole config suite**

Run: `python3 -m pytest tests/test_foundation_config.py tests/test_foundation_routes.py -q`
Expected: PASS. If an existing test wrote a numeric string port and expected it accepted, update that test to send an integer — strings are now invalid by design.

- [ ] **Step 5: Commit**

```bash
git add desk/foundation/errors.py desk/foundation/config.py tests/test_foundation_config.py
git commit -m "fix(foundation): validate config fields before writing; typed config_invalid error (G7)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 2: Startup never rewrites config; discovery suggests, only the explicit action applies (G5, G6, J9, P4)

**Files:**
- Modify: `desk/foundation/firstrun.py:92-110`
- Modify: `desk/foundation/routes.py:22-24,74-80`
- Modify: `desk/runtime.py:101-105`
- Modify: `desk/static/js/panes/firstrun.js`, `desk/static/js/main.js:22-33`
- Test: `tests/test_foundation_firstrun.py`, `tests/test_foundation_routes.py`, `tests/js/firstrun_pane.test.js`

**Interfaces:**
- Produces: `firstrun.discover_model_roots(roots) -> list[dict]` (unchanged, read-only); `firstrun.apply_discovered(roots) -> tuple[DeskConfig, list[dict]]` (renamed from `auto_configure_discovered`; writes only when called); `GET /api/config` gains `"discovered": [path, …]` when `needs_setup` is true; `build_runtime` no longer calls any writer.

- [ ] **Step 1: Write the failing tests**

Replace `test_discovery_ranks_known_local_model_tree_and_auto_configures` in `tests/test_foundation_firstrun.py` with:

```python
def _seed_trees(tmp_path):
    partial = tmp_path / "partial"
    complete = tmp_path / "complete"
    (partial / "minimax-h3").mkdir(parents=True)
    (partial / "minimax-h3" / "weight.safetensors").write_bytes(b"x")
    for relpath in ("minimax-h3", "minimax-music3",
                    "llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit"):
        directory = complete / relpath
        directory.mkdir(parents=True)
        (directory / "weight.safetensors").write_bytes(b"x")
    return partial, complete


def test_discovery_is_read_only_and_ranks_complete_tree_first(roots, tmp_path, monkeypatch):
    partial, complete = _seed_trees(tmp_path)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", os.pathsep.join((str(partial), str(complete))))
    candidates = firstrun.discover_model_roots(roots)
    assert candidates[0]["path"] == str(complete)
    assert set(candidates[0]["model_keys"]) == {"h3", "music3", "glm"}
    assert not roots.config_path.exists()


def test_apply_discovered_writes_only_when_called_explicitly(roots, tmp_path, monkeypatch):
    partial, complete = _seed_trees(tmp_path)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", os.pathsep.join((str(partial), str(complete))))
    config, candidates = firstrun.apply_discovered(roots)
    assert config.models_root == complete
    assert config.first_run_done is True
    assert candidates[0]["path"] == str(complete)


def test_explicit_empty_models_root_survives_discovery(roots, tmp_path, monkeypatch):
    _partial, complete = _seed_trees(tmp_path)
    chosen = tmp_path / "fresh-empty"
    chosen.mkdir()
    firstrun.complete_first_run(roots, chosen)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(complete))
    assert firstrun.discover_model_roots(roots)[0]["path"] == str(complete)
    from desk.foundation import config as config_mod
    assert config_mod.read_config(roots).models_root == chosen.resolve()
```

Append to `tests/test_foundation_routes.py` (use that file's existing `roots`/app fixtures; the route functions take a `req` with `.body`):

```python
def test_get_config_lists_discovered_roots_only_while_setup_is_needed(roots, tmp_path, monkeypatch):
    tree = tmp_path / "legacy"
    (tree / "minimax-h3").mkdir(parents=True)
    (tree / "minimax-h3" / "w.bin").write_bytes(b"x")
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(tree))
    payload = routes.get_config(SimpleNamespace(body={}))
    assert payload["needs_setup"] is True
    assert payload["discovered"] == [str(tree)]
    routes.post_first_run(SimpleNamespace(body={"models_root": str(tmp_path / "chosen")}))
    payload = routes.get_config(SimpleNamespace(body={}))
    assert payload["needs_setup"] is False
    assert "discovered" not in payload
```

Append to `tests/test_production_runtime.py`:

```python
def test_runtime_startup_does_not_rewrite_persisted_config(tmp_path, monkeypatch):
    data_root = _configured_data_root(tmp_path, monkeypatch)
    legacy = tmp_path / "legacy"
    (legacy / "minimax-h3").mkdir(parents=True)
    (legacy / "minimax-h3" / "w.bin").write_bytes(b"x")
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(legacy))
    before = (data_root / "config.json").read_bytes()
    runtime = build_runtime(port=0)
    try:
        assert (data_root / "config.json").read_bytes() == before
    finally:
        runtime.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_foundation_firstrun.py tests/test_foundation_routes.py tests/test_production_runtime.py -q -k "discover or survives or rewrite"`
Expected: FAIL — `AttributeError: module 'desk.foundation.firstrun' has no attribute 'apply_discovered'` and config bytes differ.

- [ ] **Step 3: Implement**

`desk/foundation/firstrun.py` — rename and simplify:

```python
def apply_discovered(roots) -> tuple[config_mod.DeskConfig, list[dict]]:
    """User-initiated: adopt the best discovered tree and mark setup complete."""
    try:
        config = config_mod.read_config(roots)
    except ConfigCorruptError:
        return config_mod.default_config(roots.data_root), []
    candidates = discover_model_roots(roots)
    if not candidates:
        return config, []
    best = candidates[0]
    config = config_mod.update_config(roots, models_root=Path(best["path"]), first_run_done=True)
    return config, candidates
```

Delete `auto_configure_discovered` entirely (grep shows callers: `runtime.py:104`, `routes.py:75`, `desk/testing/harness.py:167` — update all three).

`desk/foundation/routes.py`:

```python
def get_config(_req) -> dict:
    roots = _roots()
    cfg = config_mod.read_config(roots)
    result = _config_json(cfg)
    if cfg.needs_setup:
        result["discovered"] = [item["path"] for item in firstrun.discover_model_roots(roots)]
    return result


def post_discover(_req) -> dict:
    config, candidates = firstrun.apply_discovered(_roots())
    return {"models_root": str(config.models_root), "candidates": candidates, "found": bool(candidates)}
```

`desk/runtime.py` `build_runtime` — delete lines 104-105 (`firstrun.auto_configure_discovered(roots)` and the second `resolve_paths`); keep the single `roots = paths.resolve_paths(default_config_on_corrupt=True)`. Remove the now-unused `firstrun` import.

`desk/testing/harness.py:167-169` — replace `firstrun.auto_configure_discovered(roots)[0].models_root` with `firstrun.apply_discovered(roots)[0].models_root`.

`desk/static/js/panes/firstrun.js` `init` — prefill the adopt field with the first discovered tree:

```js
  function init(config) {
    els.modelsRoot.value = config?.models_root ?? "";
    const first = config?.discovered?.[0];
    if (first && !els.legacyRoot.value) els.legacyRoot.value = first;
  }
```

Add to `tests/js/firstrun_pane.test.js` (follow its existing `makePane` double):

```js
test("首运页把发现到的旧模型树预填进收编输入框", async () => {
  const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
  const { root, controls } = makePane();
  const pane = createFirstRunPane(root, { onDone() {} });
  pane.init({ models_root: "/data/models", discovered: ["/Users/me/LocalModelDesk"] });
  assert.equal(controls.get("[data-fr-legacy]").value, "/Users/me/LocalModelDesk");
});
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_foundation_firstrun.py tests/test_foundation_routes.py tests/test_production_runtime.py tests/test_e2e_harness_assembly.py -q && node --test tests/js/firstrun_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/foundation/firstrun.py desk/foundation/routes.py desk/runtime.py desk/testing/harness.py desk/static/js/panes/firstrun.js tests/test_foundation_firstrun.py tests/test_foundation_routes.py tests/test_production_runtime.py tests/js/firstrun_pane.test.js
git commit -m "fix(foundation): startup never overwrites models_root; discovery only suggests (G5 G6 J9)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 3: Corrupt config must not hang the service (G8, P3)

**Files:**
- Modify: `desk/runtime.py:36-42,125-130`
- Modify: `desk/foundation/routes.py:22-28` (GET config returns 500 `config_corrupt`, already; keep)
- Test: `tests/test_production_runtime.py`

**Interfaces:**
- Produces: gateway `read_config` callback returns defaults when `config.json` is corrupt; `ProductionRuntime.serve_forever()` / `start_background()` log and continue when the gateway fails to start.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_production_runtime.py
import logging


def test_runtime_serves_state_when_config_is_broken_json(tmp_path, monkeypatch, caplog):
    data_root = _configured_data_root(tmp_path, monkeypatch)
    (data_root / "config.json").write_text("{broken", encoding="utf-8")
    runtime = build_runtime(port=0)
    with caplog.at_level(logging.ERROR):
        runtime.start_background()
    try:
        status, state = http_call(runtime, "GET", "/api/state")
        assert status == 200 and state["holder"] is None
        status, payload = http_call(runtime, "GET", "/api/config")
        assert status == 500 and payload["error"]["code"] == "config_corrupt"
        status, gateway = http_call(runtime, "GET", "/api/gateway/config")
        assert status == 200 and gateway["status"]["listening"] is False
    finally:
        runtime.shutdown()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_production_runtime.py -q -k broken_json`
Expected: FAIL — `ConfigCorruptError` raised out of `start_background()` (or the request times out).

- [ ] **Step 3: Implement**

`desk/runtime.py`:

```python
import logging

from .foundation.errors import ConfigCorruptError

log = logging.getLogger(__name__)


def _gateway_config_reader():
    def read() -> dict:
        roots = paths.resolve_paths(default_config_on_corrupt=True)
        try:
            return config.read_config(roots).to_json()
        except ConfigCorruptError:
            log.error("config.json is corrupt; gateway falls back to defaults with listening disabled")
            defaults = config.default_config(roots.data_root).to_json()
            defaults["gateway"]["enabled"] = False
            return defaults
    return read


@dataclass
class ProductionRuntime:
    ...
    def _start_gateway(self) -> None:
        try:
            self.gateway.start_from_config()
        except Exception:  # the gateway is optional; the desk must still serve
            log.exception("gateway failed to start; continuing without it")

    def start_background(self) -> None:
        self._start_gateway()
        self.app.start_background()

    def serve_forever(self) -> None:
        self._start_gateway()
        self.app.serve_forever()
```

and in `build_runtime` replace the lambda with `GatewayService(DeskGatewayBackend(llm, arbiter), _gateway_config_reader())`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_production_runtime.py tests/test_gateway_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/runtime.py tests/test_production_runtime.py
git commit -m "fix(runtime): corrupt config no longer hangs startup; gateway falls back to disabled (G8)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 4: Frontend request timeout so the offline banner can ever appear (G31 web side)

**Files:**
- Modify: `desk/static/js/api.js:39-48`
- Test: `tests/js/api.test.js`

**Interfaces:**
- Produces: `request()` aborts non-stream requests after `REQUEST_TIMEOUT_MS` (default 8000) and throws `DeskApiError(0, "timeout", …)`; `export function setRequestTimeout(ms)` for tests.

- [ ] **Step 1: Write the failing test**

```js
// append to tests/js/api.test.js
test("挂起的请求在超时后以 timeout 错误拒绝，而不是永远等待", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = (_url, options = {}) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  });
  api.setRequestTimeout(20);
  try {
    await assert.rejects(api.deskState(), (error) => error.name === "DeskApiError" && error.code === "timeout");
  } finally { api.setRequestTimeout(8000); globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/api.test.js`
Expected: FAIL — `api.setRequestTimeout is not a function`

- [ ] **Step 3: Implement**

```js
// api.js — replace request()
let REQUEST_TIMEOUT_MS = 8000;
export function setRequestTimeout(ms) { REQUEST_TIMEOUT_MS = ms; }

async function request(path, { method = "GET", body, stream = false } = {}) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  let timer = null;
  if (!stream && typeof AbortController === "function") {
    const controller = new AbortController();
    options.signal = controller.signal;
    timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  }
  let response;
  try {
    response = await globalThis.fetch(path, options);
  } catch (error) {
    if (error?.name === "AbortError") throw new DeskApiError(0, "timeout", `请求超时（${REQUEST_TIMEOUT_MS / 1000} 秒无响应）`);
    throw error;
  } finally { if (timer) clearTimeout(timer); }
  if (!response.ok) throw await toError(response);
  return stream ? response.body : response.json();
}
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/api.test.js tests/js/chat_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/api.js tests/js/api.test.js
git commit -m "fix(ui): abort hung requests after 8s so the offline banner can trigger (G31)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 5: Shell shows the error page for an unresponsive service and retry replaces the child (G19, G31)

**Files:**
- Modify: `macos/ShellStatus.swift` (add pure decision)
- Modify: `macos/harness/ShellHarness.swift` (add `poll-failure` command)
- Modify: `macos/AppDelegate.swift:73-88` (use decision; retry terminates first)
- Test: `tests/test_shell_status.py`

**Interfaces:**
- Produces:
  ```swift
  enum PollFailureAction: Equatable { case keepWaiting, serviceExited, serviceUnresponsive }
  func pollFailureAction(consecutiveFailures: Int, childRunning: Bool, threshold: Int = 3) -> PollFailureAction
  ```
  Harness: `shellharness poll-failure <failures> <childRunning:true|false>` prints `keepWaiting|serviceExited|serviceUnresponsive`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_shell_status.py
@pytest.mark.parametrize("failures,child,expected", [
    (1, "true", "keepWaiting"),
    (2, "false", "keepWaiting"),
    (3, "false", "serviceExited"),
    (3, "true", "serviceUnresponsive"),
    (7, "true", "serviceUnresponsive"),
])
def test_poll_failure_action(failures, child, expected):
    proc = subprocess.run([harness_path(), "poll-failure", str(failures), child],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_shell_status.py -q -k poll_failure`
Expected: FAIL — harness prints `unknown subcommand poll-failure`, exit 64.

- [ ] **Step 3: Implement**

`macos/ShellStatus.swift` — append:

```swift
enum PollFailureAction: Equatable { case keepWaiting, serviceExited, serviceUnresponsive }

/// After `threshold` consecutive poll failures the shell must surface a problem whether or not
/// the child is alive: a hung service is as unusable as an exited one (cross-exam G19/G31).
func pollFailureAction(consecutiveFailures: Int, childRunning: Bool, threshold: Int = 3) -> PollFailureAction {
  if consecutiveFailures < threshold { return .keepWaiting }
  return childRunning ? .serviceUnresponsive : .serviceExited
}
```

`macos/harness/ShellHarness.swift` — add a case in the `switch command`:

```swift
    case "poll-failure":
      guard args.count >= 3, let failures = Int(args[1]) else { exit(64) }
      switch pollFailureAction(consecutiveFailures: failures, childRunning: args[2] == "true") {
      case .keepWaiting: print("keepWaiting")
      case .serviceExited: print("serviceExited")
      case .serviceUnresponsive: print("serviceUnresponsive")
      }
```

`macos/AppDelegate.swift` — replace the failure branch of `handlePoll` and the retry hookup:

```swift
    case .failure(let error):
      status.desk = nil
      status.lastPollError = error.message
      switch pollFailureAction(consecutiveFailures: poller.consecutiveFailures,
                               childRunning: server.isChildRunning) {
      case .keepWaiting:
        break
      case .serviceExited:
        status.server = .failed(.spawnFailed("服务已退出"))
        windowController.showErrorPage(
          reason: "台面服务意外退出（连续 \(poller.consecutiveFailures) 次状态拉取失败）。",
          logPath: DeskPaths.serverStdoutLogURL.path)
        poller.stop()
      case .serviceUnresponsive:
        status.server = .failed(.spawnFailed("服务无响应"))
        windowController.showErrorPage(
          reason: "台面服务无响应（连续 \(poller.consecutiveFailures) 次状态拉取超时）。点「重试」将重启服务。",
          logPath: DeskPaths.serverStdoutLogURL.path)
        poller.stop()
      }
```

and in `applicationDidFinishLaunching`:

```swift
    windowController.onRetry = { [weak self] in
      guard let self else { return }
      _ = self.server.terminateEmbeddedServer()   // a hung child would otherwise trip portConflict
      self.startServer()
    }
```

- [ ] **Step 4: Run tests and build the app**

Run: `python3 -m pytest tests/test_shell_status.py tests/test_shell_lifecycle.py -q && scripts/build-shell-app.sh`
Expected: PASS; the shell compiles.

- [ ] **Step 5: Manual verification (no harness for AppKit)**

Launch `dist/LocalModelDesk.app`, run `kill -STOP $(pgrep -f 'python3.13 -s -m desk')`; within ~15 s the window must show 「服务无响应…」; click 重试; `curl -s http://127.0.0.1:8766/api/state` returns 200 within 10 s. Record the result in the commit body.

- [ ] **Step 6: Commit**

```bash
git add macos/ShellStatus.swift macos/harness/ShellHarness.swift macos/AppDelegate.swift tests/test_shell_status.py
git commit -m "fix(shell): unresponsive service surfaces the error page; retry replaces the child (G19 G31)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 6: Quitting an attached shell must not kill a service it did not start (G20)

**Files:**
- Modify: `macos/ServerController.swift:93-122`
- Test: `tests/test_shell_lifecycle.py`

**Interfaces:**
- Produces: `terminateEmbeddedServer()` only calls `PortGuard.ensureFree` when `wasOwned`; for attached state it reports `portFree = listeners.isEmpty` without signalling.

- [ ] **Step 1: Write the failing test** (uses the harness `run` command and `FAKE_DESK_SERVER` from `tests/shell_helpers.py`; mirror the existing attach test in `tests/test_shell_lifecycle.py` for fixture wiring)

```python
def test_terminate_in_attached_mode_leaves_foreign_service_alive(tmp_path):
    port = free_port()
    fake = start_fake_desk_server(port, tmp_path)          # helper already used by the attach test
    try:
        proc = subprocess.Popen([harness_path(), "run", "--port", str(port), "--launcher", sys.executable,
                                 "--launcher-arg", "-c", "--launcher-arg", "pass"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wait_for_line(proc.stdout, "state=attached")
        proc.send_signal(signal.SIGTERM)                    # harness terminates then exits
        proc.wait(timeout=20)
        assert fake.poll() is None, "attached service was killed on quit"
        assert not _connect_refused("127.0.0.1", port)
    finally:
        fake.terminate()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_shell_lifecycle.py -q -k attached_mode_leaves`
Expected: FAIL — `fake.poll()` is not `None` (the fake server was reaped by `ensureFree`).

- [ ] **Step 3: Implement**

```swift
    let portFree: Bool
    if wasOwned {
      portFree = PortGuard.ensureFree(port: spec.port, grace: 2.0)
    } else {
      // Attached: the listener belongs to someone else; observe, never signal.
      portFree = PortGuard.listeners(onPort: spec.port).isEmpty
    }
```

(replace the single `let portFree = PortGuard.ensureFree(...)` line).

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_shell_lifecycle.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add macos/ServerController.swift tests/test_shell_lifecycle.py
git commit -m "fix(shell): do not reap a foreign service when quitting in attached mode (G20)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 7: Download progress counts only this attempt; stale partials cleaned when a file completes (G11, G13)

**Files:**
- Modify: `desk/resources/downloader.py:51-84,119-173`
- Modify: `desk/resources/service.py:35-68` (`_InjectableDownloader.start` duplicates `start`; make it call a shared `_begin()`)
- Test: `tests/test_resources_downloader.py`

**Interfaces:**
- Produces: `DownloadProgress.stale_bytes: int` (bytes in `.incomplete` files older than the attempt, excluded from `bytes_done`); after `state == "finished"` every `.incomplete` under `<model>/.cache/huggingface/download` is deleted.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_resources_downloader.py
import os


def test_progress_ignores_incomplete_files_from_earlier_attempts(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    cache = tmp_path / "models" / "minimax-h3" / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    stale = cache / "old.incomplete"
    stale.write_bytes(b"x" * 5)
    past = time.time() - 3600
    os.utime(stale, (past, past))
    downloader.start("h3")
    fresh = cache / "new.incomplete"
    fresh.write_bytes(b"x" * 3)
    _wait_for(lambda: downloader.progress().bytes_done == 3)
    assert downloader.progress().stale_bytes == 5
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
    assert not stale.exists() and not fresh.exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_resources_downloader.py -q -k earlier_attempts`
Expected: FAIL — `bytes_done == 8` (stale counted) / `AttributeError: stale_bytes`.

- [ ] **Step 3: Implement**

`desk/resources/downloader.py`:

```python
@dataclass
class DownloadProgress:
    ...
    error: dict | None = None
    stale_bytes: int = 0
```

In `start()` (both the base class and `_InjectableDownloader.start`) record the wall-clock attempt start right after spawning:

```python
            self._attempt_wall = time.time()
```

(add `self._attempt_wall = 0.0` in `__init__`).

Replace the incomplete accounting inside `_sample()`:

```python
            incomplete_root = root / ".cache" / "huggingface" / "download"
            incomplete_bytes, stale_bytes = 0, 0
            try:
                for path in incomplete_root.rglob("*.incomplete"):
                    if not path.is_file():
                        continue
                    stat = path.stat()
                    if stat.st_mtime + 1 >= self._attempt_wall:
                        incomplete_bytes += stat.st_size
                    else:
                        stale_bytes += stat.st_size
            except OSError:
                pass
            done = min(done + incomplete_bytes, total)
            ...
            self._progress.stale_bytes = stale_bytes
```

Add cleanup in `_finish()` right after setting `state = "finished"`:

```python
                if code == 0:
                    self._progress.state = "finished"
                    self._purge_incomplete()
```

```python
    def _purge_incomplete(self) -> None:
        model = self._model
        if model is None:
            return
        cache = Path(self._resolve_paths().models_root) / model.relpath / ".cache" / "huggingface" / "download"
        try:
            for path in cache.rglob("*.incomplete"):
                path.unlink(missing_ok=True)
        except OSError:
            pass
```

Refactor `desk/resources/service.py` `_InjectableDownloader.start` to delegate: keep its lock/precheck, then call a new base-class helper `self._begin(model, roots, manifest, handle)` that sets `_progress`, `_handle`, `_attempt_wall`, counters — so the attempt timestamp cannot drift between the two copies. (Move lines 60-66 of `service.py` and 76-82 of `downloader.py` into `Downloader._begin`.)

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_resources_downloader.py tests/test_resources_service.py tests/test_resources_http.py -q`
Expected: PASS (existing `bytes_done == 7` test still passes because its file is written after start).

- [ ] **Step 5: Commit**

```bash
git add desk/resources/downloader.py desk/resources/service.py tests/test_resources_downloader.py
git commit -m "fix(resources): progress counts only the current attempt; purge stale partials on finish (G11 G13)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 8: hf subprocess carries its own PYTHONPATH (G12)

**Files:**
- Modify: `desk/foundation/paths.py:94-130` (add `hf_env` to `PathRoots`)
- Modify: `desk/resources/downloader.py`, `desk/resources/service.py` (`spawn(cmd, cwd=None, extra_env=None)`)
- Modify: `desk/testing/fakes.py:227`, `desk/testing/scripts.py` (`DownloadControl`)
- Test: `tests/test_foundation_paths.py`, `tests/test_resources_downloader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_foundation_paths.py (append; bundle fixture already exists in this file — reuse the helper that fakes bundle.json)
def test_bundle_hf_env_points_at_pylibs_desk(bundle_roots):
    assert bundle_roots.hf_env == {"PYTHONPATH": str(bundle_roots.resources_root / "pylibs" / "desk")}
```

```python
# tests/test_resources_downloader.py (append)
def test_start_download_passes_hf_env_to_executor(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    downloader._resolve_paths = lambda: SimpleNamespace(
        models_root=tmp_path / "models", hf_cmd=(sys.executable,), hf_env={"PYTHONPATH": "/pylibs/desk"})
    downloader.start("h3")
    assert control.envs[-1] == {"PYTHONPATH": "/pylibs/desk"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_foundation_paths.py tests/test_resources_downloader.py -q -k hf_env`
Expected: FAIL — `AttributeError: hf_env` / `envs`.

- [ ] **Step 3: Implement**

`desk/foundation/paths.py`: add field `hf_env: dict` to `PathRoots`; in bundle branch `hf_env = {"PYTHONPATH": str(static.resources_root / "pylibs" / "desk")}`, dev branch `hf_env = {}`; pass `hf_env=hf_env` when constructing `PathRoots`. Add `"hf_env": dict(roots.hf_env)` to `routes.get_paths`.

`desk/testing/scripts.py` (`DownloadControl.__init__`): add `self.envs: list[dict] = []`.

`desk/testing/fakes.py`:

```python
...
    def spawn(self, cmd: list[str], cwd=None, extra_env=None) -> FakeDownloadHandle:
        handle = FakeDownloadHandle()
        self.ctl.spawns.append(list(cmd))
        self.ctl.envs.append(dict(extra_env or {}))
        self.ctl.handles.append(handle)
        return handle
```

`desk/resources/service.py`:

```python
class _SubprocessExecutor:
    def spawn(self, cmd, cwd=None, extra_env=None):
        env = dict(os.environ)
        env.update(extra_env or {})
        return subprocess.Popen(cmd, cwd=cwd, env=env)
```

Both `start()` implementations: `self._executor.spawn(command, cwd=None, extra_env=dict(getattr(roots, "hf_env", {}) or {}))`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_foundation_paths.py tests/test_foundation_routes.py tests/test_resources_downloader.py tests/test_resources_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/foundation/paths.py desk/foundation/routes.py desk/resources/downloader.py desk/resources/service.py desk/testing/fakes.py tests/test_foundation_paths.py tests/test_resources_downloader.py
git commit -m "fix(resources): hf download subprocess gets its own PYTHONPATH in bundle mode (G12)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 9: Media jobs pre-check memory; UI confirms before forcing (G23, J2)

**Files:**
- Modify: `desk/media/service.py:97-103` (in `_start`)
- Modify: `desk/media/routes.py:34-47` (pass `force`)
- Modify: `desk/static/js/panes/video.js:66-101`, `desk/static/js/panes/music.js:11-17`
- Test: `tests/test_media_service.py`, `tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `MediaService.start_video_job(..., force=False)` / `start_music_job(..., force=False)`; when `arbiter.can_start_heavy(kind, estimated_bytes=<catalog gb × 1024³>)` returns `memory_warning` and `force` is false → `MediaError("insufficient_memory", message, 409, warning)`. Panes: on `error.code === "insufficient_memory"` show `confirmDialog` and resubmit with `force: true`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_media_service.py — reuse this file's fake arbiter/service builders; add:
def test_video_job_refuses_when_memory_warning_unless_forced(service_factory):
    warning = {"code": "insufficient_memory", "required_bytes": 10, "available_bytes": 1,
               "message": "model requires about 0.0 GB; 0.0 GB is currently available"}
    svc, arbiter = service_factory(memory_warning=warning)
    with pytest.raises(MediaError) as exc:
        svc.start_video_job(prompt="x", width=512, height=288, frames=49, steps=16)
    assert exc.value.code == "insufficient_memory" and exc.value.http_status == 409
    assert arbiter.precheck_calls[-1][1] == int(103.0 * 1024 ** 3)   # h3 catalog gb
    job = svc.start_video_job(prompt="x", width=512, height=288, frames=49, steps=16, force=True)
    assert job["status"] == "running"
```

(`service_factory` must accept `memory_warning` and the fake arbiter must record `precheck_calls.append((kind, estimated_bytes))` in `can_start_heavy` — extend the existing fake in `tests/media_fakes.py` accordingly.)

```js
// tests/js/media_panes.test.js (append)
test("内存不足被拒时先确认再以 force 重提", async () => {
  const video = pane({ "video-prompt": "海边", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const doc = video.ownerDocument; doc.body = new Element();
  const confirmed = []; globalThis.__confirmForTest = async () => { confirmed.push(1); return true; };
  const responses = [
    { ok: false, status: 409, json: async () => ({ error: { code: "insufficient_memory", message: "需 103 GB，可用 60 GB" } }) },
    { ok: true, status: 200, json: async () => ({ job_id: 1, status: "running" }) },
  ];
  const previous = globalThis.fetch; const calls = [];
  globalThis.fetch = async (url, options = {}) => { calls.push({ url, options }); return responses.shift(); };
  try {
    createVideoPane(video, { confirm: globalThis.__confirmForTest });
    await video.parts["video-start"].click();
    assert.equal(confirmed.length, 1);
    assert.equal(JSON.parse(calls[1].options.body).force, true);
  } finally { globalThis.fetch = previous; delete globalThis.__confirmForTest; }
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_media_service.py -q -k memory_warning && node --test tests/js/media_panes.test.js`
Expected: FAIL — `TypeError: unexpected keyword 'force'`; JS: second fetch never happens.

- [ ] **Step 3: Implement**

`desk/media/service.py` in `_start(kind, params, force=False)` after the `pre` refusal check:

```python
            estimated = int({e.key: e.gb for e in self._list_catalog()}[catalog_key] * 1024 ** 3)
            pre = self._arbiter.can_start_heavy(kind, estimated_bytes=estimated)
            if not pre.get("ok"):
                reason = pre.get("reason") or {}
                raise MediaError(reason.get("code", "refused"), reason.get("message", "arbiter refused"), 409, reason)
            warning = pre.get("memory_warning")
            if warning and not force:
                required = warning["required_bytes"] / 1024 ** 3
                available = warning["available_bytes"] / 1024 ** 3
                raise MediaError("insufficient_memory",
                                 f"生成约需 {required:.1f} GiB 内存，当前可用 {available:.1f} GiB，可能失败或拖慢整机",
                                 409, warning)
```

Thread `force` through `start_video_job(..., force=False)` / `start_music_job(..., force=False)` → `_start(kind, params, force=force)` (do not put `force` into `params`). `desk/media/routes.py`: pass `force=bool(payload.get("force", False))` in both handlers.

`desk/static/js/panes/video.js`: accept `ctx.confirm` (default `(doc, opts) => confirmDialog(doc, opts)`; import `confirmDialog` from `../widgets/confirm.js`). Wrap the submit:

```js
    async function submit(params) {
      try { return await api.startVideoJob(params); }
      catch (error) {
        if (error.code !== "insufficient_memory") throw error;
        const ok = await (ctx.confirm ?? confirmDialog)(root.ownerDocument, { title: "内存可能不足", message: error.message, confirmLabel: "仍要生成" });
        if (!ok) return null;
        return api.startVideoJob({ ...params, force: true });
      }
    }
```

and replace `const job = await api.startVideoJob(params);` with `const job = await submit(params); if (!job) return;`. Same shape in `music.js` with `api.startMusicJob`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_routes.py -q && node --test tests/js/media_panes.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/media/service.py desk/media/routes.py desk/static/js/panes/video.js desk/static/js/panes/music.js tests/media_fakes.py tests/test_media_service.py tests/js/media_panes.test.js
git commit -m "feat(media): memory pre-check before generation with explicit force confirmation (G23 J2)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 10: LLM refusals keep the arbiter's code; UI maps codes to Chinese (G15, G9, J16)

**Files:**
- Modify: `desk/llm/service.py:128-134`
- Modify: `desk/static/js/pure/desk_state.js:3-8`
- Test: `tests/llm/test_llm_load_rejections.py`, `tests/js/desk_state.test.js`

- [ ] **Step 1: Write the failing tests**

```python
# tests/llm/test_llm_load_rejections.py (append; reuse this file's service/arbiter fakes)
def test_load_rejection_keeps_arbiter_reason_code(service_with_arbiter_refusing):
    svc = service_with_arbiter_refusing(code="evict_failed", message="LLM eviction failed")
    with pytest.raises(LlmRejected) as exc:
        svc.load("glm")
    assert exc.value.code == "evict_failed"
```

```js
// tests/js/desk_state.test.js (append)
test("拒绝码翻译成中文原因，llm_already_held 指向卸载动作", () => {
  const state = { can_start: { llm: { ok: false, reason: { code: "llm_already_held" } }, media: { ok: true } } };
  assert.deepEqual(heavyAvailability(state, "llm"), { allowed: false, reason: "已有聊天模型驻留：先卸载，再加载另一个" });
  const evicted = { can_start: { llm: { ok: false, reason: { code: "evict_failed" } } } };
  assert.equal(heavyAvailability(evicted, "llm").reason, "让出内存失败，请重试或先手动卸载");
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/llm/test_llm_load_rejections.py -q -k keeps_arbiter && node --test tests/js/desk_state.test.js`
Expected: FAIL — code is `media_busy`; JS reason is the raw code.

- [ ] **Step 3: Implement**

`desk/llm/service.py`:

```python
        if not acquired.get("ok"):
            reason = acquired.get("reason") or {}
            code = reason.get("code") if isinstance(reason, dict) else None
            message = reason.get("message") if isinstance(reason, dict) else None
            with self._lock:
                if generation == self._load_generation:
                    self._state = previous_state
            raise LlmRejected(code or ERR_MEDIA_BUSY, message or "媒体任务正在运行")
```

`desk/static/js/pure/desk_state.js`:

```js
const REASON_TEXT = {
  media_busy: "媒体作业进行中",
  llm_loaded: "聊天模型驻留中",
  llm_already_held: "已有聊天模型驻留：先卸载，再加载另一个",
  transition_in_progress: "重活交接进行中",
  evict_failed: "让出内存失败，请重试或先手动卸载",
  memory_low: "可用内存不足",
  insufficient_memory: "可用内存不足",
};
```

and in `heavyAvailability` fall back to `code ? \`暂不可用（${code}）\` : ""` instead of the bare code.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/llm -q && node --test tests/js/desk_state.test.js tests/js/chat_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/llm/service.py desk/static/js/pure/desk_state.js tests/llm/test_llm_load_rejections.py tests/js/desk_state.test.js
git commit -m "fix(llm/ui): keep arbiter refusal codes and translate them for people (G15 G9)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 11: Gateway reports a usable LAN address; settings validates the port (J8, G17, G18)

**Files:**
- Modify: `desk/gateway/service.py:72-89`
- Modify: `desk/static/js/pure/base_url.js`, `desk/static/js/panes/settings.js:29-58`
- Test: `tests/test_gateway_service.py`, `tests/js/base_url.test.js`, `tests/js/settings_pane.test.js`

**Interfaces:**
- Produces: status gains `lan_host` (string IPv4 of the primary interface, or `"127.0.0.1"` when unresolvable) and `openai_base_url`/`anthropic_base_url` are built from `lan_host` when `host == "0.0.0.0"`; `baseUrls({host, port, lanHost})` uses `lanHost` for `0.0.0.0`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gateway_service.py (append)
def test_status_exposes_lan_host_for_wildcard_bind(service_factory):
    _holder, read = _config(enabled=True, host="0.0.0.0", port=0)
    svc = service_factory(read)
    status = svc.status()
    assert status["lan_host"] and status["lan_host"] != "0.0.0.0"
    assert status["openai_base_url"] == f"http://{status['lan_host']}:{status['port']}/v1"


def test_status_keeps_explicit_host(service_factory):
    _holder, read = _config(enabled=True, host="127.0.0.1", port=0)
    svc = service_factory(read)
    assert svc.status()["lan_host"] == "127.0.0.1"
```

```js
// tests/js/base_url.test.js (append)
test("0.0.0.0 用后端给的局域网地址，而不是占位符", () => {
  const urls = baseUrls({ host: "0.0.0.0", port: 8770, lanHost: "192.168.31.68" });
  assert.equal(urls.openai, "http://192.168.31.68:8770/v1");
  assert.equal(urls.note, "监听所有网卡；其他设备用 192.168.31.68 访问，本机也可用 127.0.0.1");
});
```

```js
// tests/js/settings_pane.test.js (append)
test("端口越界时不发请求并给出中文错误", async () => {
  const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls += 1; return new Response("{}", { status: 200 }); };
  try {
    const pane = createSettingsPane(root);
    controls.get("[data-settings-port]").value = "99999";
    await controls.get("[data-settings-save]").click();
    assert.equal(calls, 0);
    assert.equal(controls.get("[data-settings-error]").textContent, "端口须在 1 到 65535 之间");
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_gateway_service.py -q -k lan_host && node --test tests/js/base_url.test.js tests/js/settings_pane.test.js`
Expected: FAIL — `KeyError: 'lan_host'`; placeholder URL; a PUT is sent.

- [ ] **Step 3: Implement**

`desk/gateway/service.py`:

```python
import socket


def _lan_host(host: str) -> str:
    if host != "0.0.0.0":
        return host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))   # no packet is sent; picks the default route's interface
            return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
```

and in `status()`:

```python
        lan_host = _lan_host(host)
        return {
            "enabled": enabled, "listening": listening, "host": host, "port": port, "lan_host": lan_host,
            "openai_base_url": f"http://{lan_host}:{port}/v1",
            "anthropic_base_url": f"http://{lan_host}:{port}",
            "auth": "none", "last_error": self._last_error,
        }
```

`desk/static/js/pure/base_url.js`:

```js
export function baseUrls({ host, port, lanHost }) {
  const all = host === "0.0.0.0";
  const displayHost = all ? (lanHost || "127.0.0.1") : host;
  return {
    openai: `http://${displayHost}:${port}/v1`,
    anthropic: `http://${displayHost}:${port}`,
    displayHost,
    note: all ? `监听所有网卡；其他设备用 ${displayHost} 访问，本机也可用 127.0.0.1` : null,
  };
}
```

`desk/static/js/panes/settings.js` `render`: `baseUrls({ host: …, port: …, lanHost: status.lan_host })`. In `save()` before the request:

```js
    const port = Number(els.port.value);
    if (!Number.isInteger(port) || port < 1 || port > 65535) { setError("端口须在 1 到 65535 之间"); return; }
    if (!els.host.value.trim()) { setError("主机不能为空"); return; }
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_gateway_service.py -q && node --test tests/js/base_url.test.js tests/js/settings_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/gateway/service.py desk/static/js/pure/base_url.js desk/static/js/panes/settings.js tests/test_gateway_service.py tests/js/base_url.test.js tests/js/settings_pane.test.js
git commit -m "feat(gateway/ui): real LAN base URL and client-side port validation (J8 G17 G18)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 12: Music lyrics are required — say so before the job runs (G35)

**Files:**
- Modify: `desk/media/service.py` (`start_music_job` validation)
- Modify: `desk/static/index.html:30`, `desk/static/js/panes/music.js:11-17`
- Test: `tests/test_media_routes.py`, `tests/js/media_panes.test.js`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_media_routes.py (append; use the file's route-table builder with its fake service, or the real MediaService with fakes)
def test_music_without_lyrics_is_a_400_with_chinese_message(routes_with_real_service):
    handler = dict(((m, p), h) for m, p, h in routes_with_real_service)[("POST", "/api/media/music")]
    status, payload = handler({"caption": "民谣", "lyrics": "   ", "duration": 10}, {})
    assert status == 400
    assert payload["error"]["code"] == "lyrics_required"
    assert payload["error"]["message"] == "请填写歌词：Music 3 需要歌词才能生成"
```

```js
// tests/js/media_panes.test.js (append)
test("音乐面板空歌词时本地拦截并提示", async () => {
  const music = pane({ "music-caption": "民谣", "music-lyrics": "", "music-duration": "10", "music-start": "" });
  const previous = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls += 1; return { ok: true, json: async () => ({}) }; };
  try {
    createMusicPane(music, {});
    await music.parts["music-start"].click();
    assert.equal(calls, 0);
    assert.equal(music.parts["music-error"].textContent, "请填写歌词：Music 3 需要歌词才能生成");
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_media_routes.py -q -k lyrics && node --test tests/js/media_panes.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`desk/media/service.py` at the top of `start_music_job` (before `_start`):

```python
        if not isinstance(lyrics, str) or not lyrics.strip():
            raise MediaError("lyrics_required", "请填写歌词：Music 3 需要歌词才能生成", 400)
```

`desk/static/index.html`: change the lyrics textarea to `<textarea data-music-lyrics placeholder="歌词（必填）" aria-label="歌词（必填）" required></textarea>`.

`desk/static/js/panes/music.js` click handler, before calling the API:

```js
      if (!els.lyrics.value.trim()) throw new Error("请填写歌词：Music 3 需要歌词才能生成");
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_routes.py tests/test_media_service.py -q && node --test tests/js/media_panes.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/media/service.py desk/static/index.html desk/static/js/panes/music.js tests/test_media_routes.py tests/js/media_panes.test.js
git commit -m "fix(media): lyrics are required and validated before spawning Music 3 (G35)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 13: Failed jobs explain themselves in Chinese; corrupt images rejected at upload (G32, G21-adjacent)

**Files:**
- Modify: `desk/media/service.py:145-147` (attach log tail), `desk/media/inputs.py:42-53` (full decode check)
- Create: `desk/static/js/pure/job_error.js`
- Modify: `desk/static/js/widgets/jobview.js:27`
- Test: `tests/test_media_service.py`, `tests/test_media_inputs.py`, `tests/js/job_error.test.js`

**Interfaces:**
- Produces: job `error` becomes `{"code": "exit_nonzero", "message": "exit 1", "log_tail": "<last 5 non-empty log lines>"}`; `describeJobError(error) -> {title, detail}` (pure); `save_input` runs `ffmpeg -v error -i <file> -frames:v 1 -f null -` for images and rejects with `图片文件已损坏，无法解码` on failure.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_media_service.py (append)
def test_nonzero_exit_records_log_tail(service_factory):
    svc, _arbiter = service_factory()
    job = svc.start_video_job(prompt="x", width=512, height=288, frames=49, steps=16)
    handle = svc._handle
    handle.emit("step 1/16\n"); handle.emit("Traceback\n"); handle.emit("mlx_h3.memory.BudgetExceeded: SWAPPING\n")
    handle.exit(1)
    final = wait_until(lambda: svc.job_status(), lambda s: s["status"] == "error")
    assert final["error"]["code"] == "exit_nonzero"
    assert final["error"]["log_tail"].splitlines()[-1] == "mlx_h3.memory.BudgetExceeded: SWAPPING"
```

(`service_factory`, `handle.emit/exit`, `wait_until` follow the fakes in `tests/media_fakes.py`; add `emit`/`exit` there if the fake handle lacks them.)

```python
# tests/test_media_inputs.py (append)
def test_truncated_png_is_rejected(tmp_path, monkeypatch):
    png = make_valid_png(64, 64)              # helper in this file that writes a real PNG via zlib
    data = base64.b64encode(png[: len(png) // 3]).decode()
    with pytest.raises(ValueError) as exc:
        save_input(tmp_path, "a.png", data)
    assert str(exc.value) == "图片文件已损坏，无法解码"
    assert not list((tmp_path / ".inputs").glob("*")) if (tmp_path / ".inputs").exists() else True
```

```js
// tests/js/job_error.test.js (new)
import test from "node:test";
import assert from "node:assert/strict";
import { describeJobError } from "../../desk/static/js/pure/job_error.js";

test("常见失败原因翻成人话，原始码放进详情", () => {
  assert.deepEqual(describeJobError({ code: "exit_nonzero", message: "exit 1", log_tail: "mlx_h3.memory.BudgetExceeded: SWAPPING" }),
    { title: "内存不足，生成被中止", detail: "exit_nonzero: exit 1\nmlx_h3.memory.BudgetExceeded: SWAPPING" });
  assert.equal(describeJobError({ code: "exit_nonzero", message: "exit 1", log_tail: "ffmpeg ... load_rgb_image" }).title, "素材无法解码，请换一张图片或视频");
  assert.equal(describeJobError({ code: "lyrics_required", message: "请填写歌词" }).title, "请填写歌词");
  assert.equal(describeJobError({ code: "no_output", message: "exit 0 but output file missing" }).title, "生成结束但没有产出文件");
  assert.equal(describeJobError({ code: "weird", message: "?" }).title, "生成失败（weird）");
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_inputs.py -q -k "log_tail or truncated" ; node --test tests/js/job_error.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`desk/media/service.py` `_worker`: keep the last lines while streaming:

```python
                else: status, error = "error", {"code": "exit_nonzero", "message": f"exit {code}", "log_tail": self._log_tail(5)}
```

```python
    def _log_tail(self, n: int) -> str:
        lines = [line for line in self._log.splitlines() if line.strip()]
        return "\n".join(lines[-n:])
```

`desk/media/inputs.py` after the ffprobe checks, for images:

```python
        if EXTENSIONS[suffix] == "image":
            ffmpeg = shutil.which("ffmpeg") or probe.replace("ffprobe", "ffmpeg")
            decode = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"],
                                    capture_output=True, timeout=30)
            if decode.returncode != 0:
                raise ValueError("图片文件已损坏，无法解码")
```

`desk/static/js/pure/job_error.js`:

```js
// 作业失败对象 → {title, detail}。title 是人话；detail 保留原始码与日志尾部供「详情」展开。
const RULES = [
  [/BudgetExceeded|out of memory|SWAPPING/i, "内存不足，生成被中止"],
  [/load_rgb_image|ffmpeg|decode|Invalid data/i, "素材无法解码，请换一张图片或视频"],
  [/lyrics must be a non-empty/i, "请填写歌词"],
];
const CODE_TITLE = { lyrics_required: null, no_output: "生成结束但没有产出文件", spawn_failed: "无法启动生成程序", worker_failed: "生成程序意外退出", insufficient_memory: "可用内存不足" };

export function describeJobError(error) {
  if (!error) return { title: "", detail: "" };
  const tail = typeof error.log_tail === "string" ? error.log_tail : "";
  const detail = [`${error.code}: ${error.message}`, tail].filter(Boolean).join("\n");
  const hit = RULES.find(([re]) => re.test(tail) || re.test(error.message ?? ""));
  if (hit) return { title: hit[1], detail };
  if (error.code in CODE_TITLE) return { title: CODE_TITLE[error.code] ?? error.message, detail };
  return { title: `生成失败（${error.code}）`, detail };
}
```

`desk/static/js/widgets/jobview.js` line 27:

```js
    if (payload.status === "error" && payload.error) {
      const { title, detail } = describeJobError(payload.error);
      els.error.replaceChildren();
      const strong = root.ownerDocument.createElement("strong"); strong.textContent = title;
      const details = root.ownerDocument.createElement("details");
      const summary = root.ownerDocument.createElement("summary"); summary.textContent = "详情";
      const pre = root.ownerDocument.createElement("pre"); pre.textContent = detail;
      details.append(summary, pre); els.error.append(strong, details);
    }
```

(import `describeJobError`; `els.error` is a `<p>` — change both `<p class="inline-error" data-job-error>` in `index.html` to `<div class="inline-error" data-job-error>`.)

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_inputs.py -q && node --test tests/js/job_error.test.js tests/js/media_panes.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/media/service.py desk/media/inputs.py desk/static/js/pure/job_error.js desk/static/js/widgets/jobview.js desk/static/index.html tests/test_media_service.py tests/test_media_inputs.py tests/js/job_error.test.js
git commit -m "fix(media/ui): human-readable job failures with log tail; reject undecodable images (G32)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 14: Job view re-syncs when its pane is shown; running jobs show elapsed time (G22, G25)

**Files:**
- Modify: `desk/static/js/widgets/jobview.js`, `desk/static/js/main.js:54-60`
- Test: `tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `jobView.sync()` → fetches `/api/media/job?log_from=0` and applies it (re-renders the player for a finished job); `jobView.tickElapsed(now)` updates status text `生成中…（已用 N 秒）` while running; `main.showTab` calls `panes.video.jobView.sync()` / `panes.music.jobView.sync()`.

- [ ] **Step 1: Write the failing test**

```js
// tests/js/media_panes.test.js (append)
test("回到面板时 sync 会补画已完成作业的播放器，并显示已用时长", async () => {
  const video = pane({ "video-prompt": "", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const p = createVideoPane(video, {});
  await withFetch([{ job_id: 3, status: "done", output: "h3-1.mp4", started_at: 10, finished_at: 87 }], async () => { await p.jobView.sync(); });
  assert.equal(video.parts["job-player"].firstChild.tagName, "video");
  p.jobView.apply({ job_id: 4, status: "running", started_at: 100 });
  p.jobView.tickElapsed(112);
  assert.equal(video.parts["job-status"].textContent, "生成中…（已用 12秒）");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/media_panes.test.js`
Expected: FAIL — `sync is not a function`.

- [ ] **Step 3: Implement**

`jobview.js`:

```js
  let lastPayload = null;
  function apply(payload) { lastPayload = payload; ...existing body...; if (payload.status === "done" && payload.output && els.player.firstChild?.src !== api.serveOutput(payload.output)) { els.player.replaceChildren(); /* then existing create+append */ } }
  async function sync() {
    try { apply(await api.jobStatus(0, null)); } catch { /* offline: keep what we have */ }
  }
  function tickElapsed(nowSeconds) {
    if (lastPayload?.status !== "running" || !lastPayload.started_at) return;
    els.status.textContent = `生成中…（已用 ${formatDuration(nowSeconds - lastPayload.started_at)}）`;
  }
  return { reset, apply, start, sync, tickElapsed };
```

`main.js`:

```js
function showTab(name) {
  ...existing...
  if (name === "video") panes.video.jobView.sync();
  if (name === "music") panes.music.jobView.sync();
}
```

and in `tick()` after `tickJob()`: `for (const pane of [panes.video, panes.music]) pane.jobView.tickElapsed(Date.now() / 1000 - (store.get().clockSkew ?? 0));` — the server's `started_at` is `time.monotonic()`, so instead compute elapsed from the payload itself: change `tickElapsed(payload)` to use `payload.elapsed_s` and add `state["elapsed_s"] = self._clock() - state["started_at"] if state["status"] == "running" else None` in `MediaService.job_status`. Adjust the test to `p.jobView.apply({ job_id: 4, status: "running", elapsed_s: 12 })` and drop `tickElapsed` (the 2 s tick already re-applies). Keep whichever is simpler: **use `elapsed_s` from the server** (one source of time).

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_service.py -q && node --test tests/js/media_panes.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/widgets/jobview.js desk/static/js/main.js desk/media/service.py tests/js/media_panes.test.js tests/test_media_service.py
git commit -m "fix(ui): job view resyncs on tab show and shows elapsed time while running (G22 G25)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 15: Chat pane follows live server state (G9, J4, J16, G28 — pattern P5)

**Files:**
- Modify: `desk/static/js/main.js:80-88`, `desk/static/js/panes/chat.js:54-66,254-260`
- Test: `tests/js/chat_pane.test.js`

**Interfaces:**
- Produces: `panes.chat.applyLlmStatus(payload)` (public; called from `tick` with `/api/llm/status`); `panes.chat.refreshSessionsIfStale()` (called every 5th tick); `setHeavyAllowed(allowed, reason)` renders the reason in a `hint` next to the load button (`[data-load-hint]`) instead of the red `[data-chat-error]`, and sets `loadBtn.title = reason`.

- [ ] **Step 1: Write the failing tests**

```js
// tests/js/chat_pane.test.js (append)
test("驱逐后 tick 推送的 llm 状态会把『已加载』改成失败说明", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.equal(controls.get("[data-model-state]").textContent, "已加载：GLM");
  pane.applyLlmStatus({ state: { status: "error", model_key: "glm", error: { code: "evicted", message: "LLM 已被媒体任务驱逐" } }, loaded_model: null });
  assert.equal(controls.get("[data-model-state]").textContent, "加载失败（evicted）：LLM 已被媒体任务驱逐");
});

test("互斥原因显示在加载按钮旁的提示里，不再是红色错误", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const pane = createChatPane(root);
  pane.setHeavyAllowed(false, "已有聊天模型驻留：先卸载，再加载另一个");
  assert.equal(controls.get("[data-load-hint]").textContent, "已有聊天模型驻留：先卸载，再加载另一个");
  assert.equal(controls.get("[data-chat-error]").textContent, "");
  assert.equal(controls.get("[data-load]").disabled, true);
  pane.setHeavyAllowed(true, "");
  assert.equal(controls.get("[data-load-hint]").textContent, "");
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL — `applyLlmStatus is not a function`; hint empty / error filled.

- [ ] **Step 3: Implement**

`index.html` chat model row: add `<span class="hint" data-load-hint></span>` after the unload button.

`chat.js`:

```js
    loadHint: root.querySelector("[data-load-hint]"),
  ...
  function setHeavyAllowed(allowed, reason = "") {
    els.loadBtn.disabled = !allowed;
    els.loadBtn.title = allowed ? "" : reason;
    if (els.loadHint) els.loadHint.textContent = allowed ? "" : reason;
  }
  let sessionsTick = 0;
  async function refreshSessionsIfStale() {
    sessionsTick += 1;
    if (sessionsTick % 5 !== 0 || streaming) return;
    const latest = sortSessions(await api.listChatSessions());
    if (latest.length !== sessions.length || latest.some((s, i) => s.id !== sessions[i].id || s.updated !== sessions[i].updated)) {
      sessions = latest; renderSessionList();
    }
  }
  return { init, refreshModels, setHeavyAllowed, applyLlmStatus: renderLlm, refreshSessionsIfStale };
```

`main.js` `tick()`:

```js
    const [deskState, memory, llm] = await Promise.all([api.deskState(), api.memorySnapshot(), api.llmStatus()]);
    ...
    panes.chat.applyLlmStatus(llm);
    await panes.chat.refreshSessionsIfStale();
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/chat_pane.test.js tests/js/desk_state.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/index.html desk/static/js/main.js desk/static/js/panes/chat.js tests/js/chat_pane.test.js
git commit -m "fix(ui): chat pane tracks live llm status, session list, and shows mutex reason as a hint (G9 J4 J16 G28)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 16: 「重新校验」really revalidates and shows it (G16, G3)

**Files:**
- Modify: `desk/static/js/panes/resources.js:21-34,120`
- Create: `tests/js/resources_pane.test.js`

- [ ] **Step 1: Write the failing test**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { createResourcesPane } from "../../desk/static/js/panes/resources.js";

class Element { constructor(tag = "div") { this.tagName = tag; this.dataset = {}; this.textContent = ""; this.children = []; this.listeners = {}; this.disabled = false; this.className = ""; this.title = ""; this.hidden = false; }
  append(...n) { this.children.push(...n); } replaceChildren(...n) { this.children = n; }
  addEventListener(t, l) { this.listeners[t] = l; } click() { return this.listeners.click?.(); } }
function makePane() {
  const parts = { "res-refresh": new Element("button"), "res-list": new Element("ul"), "res-error": new Element("p"), "res-disk": new Element("span") };
  return { parts, root: { ownerDocument: { body: new Element("body"), createElement: (t) => new Element(t) }, querySelector: (s) => parts[s.match(/^\[data-([\w-]+)\]$/)[1]] } };
}

test("点『重新校验』发 refresh=1，按钮期间禁用并显示校验中", async () => {
  const { root, parts } = makePane();
  const urls = []; let release;
  const previous = globalThis.fetch;
  globalThis.fetch = (url) => { urls.push(String(url)); return new Promise((resolve) => { release = () => resolve({ ok: true, status: 200, json: async () => (String(url).includes("catalog") ? [] : { models: [], disk: { free_bytes: 1, total_bytes: 2 } }) }); }); };
  try {
    const pane = createResourcesPane(root);
    const clicking = parts["res-refresh"].click();
    assert.equal(parts["res-refresh"].disabled, true);
    assert.equal(parts["res-refresh"].textContent, "校验中…");
    while (urls.length < 4) { release(); await Promise.resolve(); await Promise.resolve(); }
    while (release) { const r = release; release = null; r(); await new Promise((res) => setTimeout(res, 0)); }
    await clicking;
    assert.ok(urls.some((u) => u.includes("/api/resources/status?refresh=1")));
    assert.equal(parts["res-refresh"].disabled, false);
    assert.equal(parts["res-refresh"].textContent, "重新校验");
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/resources_pane.test.js`
Expected: FAIL — no `refresh=1` request; button never disabled.

- [ ] **Step 3: Implement**

```js
  async function refresh({ revalidate = false } = {}) {
    if (els.error) els.error.textContent = "";
    if (revalidate && els.refreshBtn) { els.refreshBtn.disabled = true; els.refreshBtn.textContent = "校验中…"; }
    try {
      const [catalogPayload, statusPayload, disk] = await Promise.all([
        api.listCatalog(), api.verifyAllModels(revalidate), api.diskUsage(),
      ]);
      ...unchanged...
    } catch (err) { if (els.error) els.error.textContent = err.message; }
    finally { if (revalidate && els.refreshBtn) { els.refreshBtn.disabled = false; els.refreshBtn.textContent = "重新校验"; } }
  }
  els.refreshBtn?.addEventListener("click", () => refresh({ revalidate: true }));
  return { refresh: () => refresh() };
```

(Keep `addIcon` decoration intact: set `textContent` only on a `<span data-label>` child if the button already carries an icon; if `addIcon` re-runs on hydrate, wrap the label in a span in `index.html`: `<button data-res-refresh data-icon-name="refresh"><span data-label>重新校验</span></button>` and update the label span instead of the button's `textContent`.)

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/resources_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/resources.js desk/static/index.html tests/js/resources_pane.test.js
git commit -m "fix(ui): revalidate button sends refresh=1 and shows a busy state (G16 G3)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 17: 「在访达中显示」for outputs (J17)

**Files:**
- Modify: `desk/library/outputs.py`, `desk/library/http.py:118-131`
- Modify: `desk/static/js/api.js`, `desk/static/js/panes/library.js:96-121`
- Modify: `macos/StatusItemController.swift:19-38`, `macos/DeskAPI.swift` (menu item 「打开成品目录」 → `POST /api/outputs/reveal`)
- Test: `tests/test_library_http.py`, `tests/js/library_pane.test.js`

**Interfaces:**
- Produces: `POST /api/outputs/{name}/reveal` and `POST /api/outputs/reveal` (folder) → `{"revealed": "<abs path>"}`; `OutputsStore.reveal(name: str | None, opener=subprocess.run)` runs `["open", "-R", path]` (file) or `["open", path]` (folder); `api.revealOutput(name)`; library rows get a 「在访达中显示」 button.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_library_http.py (append; use this file's service fixture with tmp outputs root)
def test_reveal_output_runs_open_minus_R_and_refuses_escape(library_service, tmp_path):
    calls = []
    library_service.outputs.set_opener(lambda argv, **kw: calls.append(argv))
    (library_service.outputs._root / "h3-1.mp4").write_bytes(b"x")
    result = dispatch(library_service, handle_reveal_output, LibRequest(path_params={"name": "h3-1.mp4"}))
    assert result.status == 200 and json.loads(result.body)["revealed"].endswith("h3-1.mp4")
    assert calls == [["open", "-R", str(library_service.outputs._root / "h3-1.mp4")]]
    result = dispatch(library_service, handle_reveal_output, LibRequest(path_params={"name": "../config.json"}))
    assert result.status == 404
    result = dispatch(library_service, handle_reveal_folder, LibRequest())
    assert calls[-1] == ["open", str(library_service.outputs._root)]
```

```js
// tests/js/library_pane.test.js (append; reuse its DOM double and fetch stub)
test("每条成品有『在访达中显示』并调用 reveal 接口", async () => {
  const { root, parts, calls } = makeLibrary([{ name: "h3-1.mp4", kind: "video", bytes: 1, ts: "2026-09-07T01:00:00" }], []);
  const pane = createLibraryPane(root, { applyFill() {} });
  await pane.refresh();
  const buttons = parts["lib-list"].children[0].children[1].children.map((b) => b.textContent);
  assert.ok(buttons.includes("在访达中显示"));
  await parts["lib-list"].children[0].children[1].children.find((b) => b.textContent === "在访达中显示").click();
  assert.ok(calls.some(([url, method]) => url === "/api/outputs/h3-1.mp4/reveal" && method === "POST"));
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_library_http.py -q -k reveal && node --test tests/js/library_pane.test.js`
Expected: FAIL — handlers/functions missing.

- [ ] **Step 3: Implement**

`desk/library/outputs.py` (`OutputsStore`):

```python
import subprocess

    def set_opener(self, opener) -> None:
        self._opener = opener

    def reveal(self, name: str | None) -> Path:
        opener = getattr(self, "_opener", None) or (lambda argv, **kw: subprocess.run(argv, check=False, timeout=10))
        if name is None:
            opener(["open", str(self._root)])
            return self._root
        path = (self._root / name).resolve()
        if path.parent != self._root.resolve() or not path.is_file():
            raise NotFoundError("output not found")
        opener(["open", "-R", str(path)])
        return path
```

`desk/library/http.py`:

```python
def handle_reveal_output(service, request: LibRequest) -> Response:
    path = service.outputs.reveal(request.path_params.get("name"))
    return _json_response(200, {"revealed": str(path)})


def handle_reveal_folder(service, request: LibRequest) -> Response:
    return _json_response(200, {"revealed": str(service.outputs.reveal(None))})
```

and in `routes()` add before the `{name}` GET: `("POST", "/api/outputs/reveal", bind(handle_reveal_folder))`, `("POST", "/api/outputs/{name}/reveal", bind(handle_reveal_output))`. (`DeskApp._find` matches literal segments before `{param}`; verify with the routes test.)

`api.js`: `export const revealOutput = (name) => json(name ? \`${ROUTES.outputs}/${encoded(name)}/reveal\` : \`${ROUTES.outputs}/reveal\`, "POST");`

`library.js` in `rowNode`, after the play button:

```js
      const reveal = doc.createElement("button");
      reveal.textContent = "在访达中显示";
      addIcon(reveal, "folder", doc);
      reveal.addEventListener("click", async (event) => {
        event.stopPropagation();
        try { await api.revealOutput(playable.name); } catch (error) { els.error.textContent = error.message; }
      });
      actions.append(reveal);
```

`macos/DeskAPI.swift`: add `static let revealOutputsPath = "/api/outputs/reveal"` and `func revealOutputs(completion:)` posting to it. `StatusItemController.swift`: insert a menu item `打开成品目录` (action `revealOutputs`) between 打开窗口 and 设置…, wired in `AppDelegate` to `api.revealOutputs { _ in }`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_library_http.py tests/test_library_outputs.py -q && node --test tests/js/library_pane.test.js tests/js/api.test.js && scripts/build-shell-app.sh`
Expected: PASS; shell builds. (Update the api.test.js contract table with `revealOutput`.)

- [ ] **Step 5: Commit**

```bash
git add desk/library/outputs.py desk/library/http.py desk/static/js/api.js desk/static/js/panes/library.js macos/DeskAPI.swift macos/StatusItemController.swift macos/AppDelegate.swift tests/test_library_http.py tests/js/library_pane.test.js tests/js/api.test.js
git commit -m "feat(library/shell): reveal outputs in Finder from the library and the menu bar (J17)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 18: Settings drawer behaves like a drawer (G40, G30, G27)

**Files:**
- Modify: `desk/static/js/main.js:42-44,54-60`, `desk/static/js/panes/settings.js:29-45`
- Modify: `desk/static/app.css` (body scroll lock + mask)
- Test: `tests/js/settings_pane.test.js`, `tests/js/main_drawer.test.js` (new, imports only pure helpers)

**Interfaces:**
- Produces: `main.js` exports nothing new; drawer open/close is centralised in `setDrawerOpen(open)` which toggles `document.body.classList.toggle("drawer-open", open)` and `#pane-settings.hidden`; `showTab` calls `setDrawerOpen(false)`; `settings.render` hides `[data-settings-auth-warning]`, URLs and copy buttons when `!status.listening`.

- [ ] **Step 1: Write the failing test**

```js
// tests/js/settings_pane.test.js (append)
test("未监听时隐藏无鉴权警告与 base URL 区", async () => {
  const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => new Response(JSON.stringify(
    path === "/api/config" ? { models_root: "/m" } : { config: { enabled: false, host: "0.0.0.0", port: 8770 }, status: { enabled: false, listening: false, host: "0.0.0.0", port: 8770, lan_host: "192.168.1.2", auth: "none", last_error: null } }), { status: 200 });
  try {
    const pane = createSettingsPane(root); await pane.init();
    assert.equal(controls.get("[data-settings-auth-warning]").hidden, true);
    assert.equal(controls.get("[data-settings-openai-url]").hidden, true);
    assert.equal(controls.get("[data-settings-copy-openai]").hidden, true);
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/settings_pane.test.js`
Expected: FAIL — elements not hidden.

- [ ] **Step 3: Implement**

`settings.js` `render`:

```js
    const listening = Boolean(status.listening);
    for (const el of [els.authWarning, els.openaiUrl, els.anthropicUrl, els.copyOpenai, els.copyAnthropic, els.lanNote]) if (el) el.hidden = !listening;
    els.authWarning.textContent = listening ? "当前为无鉴权监听：同一网络任何设备都能调用本机模型" : "";
```

`main.js`:

```js
function setDrawerOpen(open) {
  $("#pane-settings").hidden = !open;
  document.body.classList.toggle("drawer-open", open);
  if (open) settings.init();
}
...
    $("[data-open-settings]").addEventListener("click", () => setDrawerOpen(true));
    $("[data-close-settings]").addEventListener("click", () => setDrawerOpen(false));
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") setDrawerOpen(false); });
...
function showTab(name) { setDrawerOpen(false); ...existing... }
```

`app.css` append:

```css
body.drawer-open{overflow:hidden}
body.drawer-open::before{content:"";position:fixed;inset:0;background:#0009;z-index:24}
```

- [ ] **Step 4: Run tests and e2e**

Run: `node --test tests/js/settings_pane.test.js && python3 -m pytest tests/e2e/test_settings_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/main.js desk/static/js/panes/settings.js desk/static/app.css tests/js/settings_pane.test.js
git commit -m "fix(ui): settings drawer locks page scroll, masks, closes on tab/Esc, hides URLs when not listening (G40 G30 G27)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 19: Library playback stays in view (G39)

**Files:**
- Modify: `desk/static/js/panes/library.js:124-132`
- Test: `tests/js/library_pane.test.js`

- [ ] **Step 1: Write the failing test**

```js
test("播放时播放器滚入视野且标注正在播放的记录", async () => {
  const { root, parts } = makeLibrary([{ name: "m.wav", kind: "music", bytes: 1, ts: "2026-09-07T01:00:00" }], []);
  let scrolled = 0; parts["lib-player"].scrollIntoView = () => { scrolled += 1; };
  const pane = createLibraryPane(root, { applyFill() {} }); await pane.refresh();
  await parts["lib-list"].children[0].click();
  assert.equal(scrolled, 1);
  assert.equal(parts["lib-player"].children[1].textContent, "正在播放：m.wav");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/library_pane.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

```js
  function playOutput(output) {
    els.player.replaceChildren();
    const isVideo = output.kind === "video" || /\.(mp4|webm)$/i.test(output.name);
    const media = doc.createElement(isVideo ? "video" : "audio");
    media.controls = true; media.autoplay = true; media.src = api.serveOutput(output.name);
    const caption = doc.createElement("p"); caption.className = "hint"; caption.textContent = `正在播放：${output.name}`;
    els.player.append(media, caption);
    els.player.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/library_pane.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/library.js tests/js/library_pane.test.js
git commit -m "fix(ui): keep the library player in view and label what is playing (G39)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 20: Dark, themed error page that restores the last tab (G29, G37)

**Files:**
- Modify: `macos/MainWindowController.swift:55-67,44-46`
- Modify: `desk/static/js/main.js` (hash ↔ tab)
- Test: `tests/test_shell_window.py` (static assertions on the HTML template), `tests/js/main_hash.test.js` (new; pure helper)

**Interfaces:**
- Produces: `errorPageHTML(reason:logPath:) -> String` (static, testable through the harness command `error-page`); `main.js` exports `tabFromHash(hash) -> "chat"|"video"|…` in `desk/static/js/pure/tab_hash.js`; `showTab` writes `location.hash = "#tab=<name>"`; `MainWindowController` remembers `webView.url?.fragment` before showing the error page and appends it to `baseURL` in `loadDeskShell()`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_shell_window.py (append)
def test_error_page_is_dark_themed_and_names_the_reason():
    proc = subprocess.run([harness_path(), "error-page", "服务无响应", "/tmp/x.log"], capture_output=True, text=True, timeout=30)
    html = proc.stdout
    assert "background:#14161a" in html and "color:#e7e9ee" in html
    assert "<h1>服务未运行</h1>" in html and "服务无响应" in html
    assert 'onclick="window.webkit.messageHandlers.shellRetry.postMessage' in html
```

```js
// tests/js/main_hash.test.js
import test from "node:test"; import assert from "node:assert/strict";
import { tabFromHash } from "../../desk/static/js/pure/tab_hash.js";
test("hash 解析成合法 tab，否则回到聊天", () => {
  assert.equal(tabFromHash("#tab=music"), "music");
  assert.equal(tabFromHash("#tab=bogus"), "chat");
  assert.equal(tabFromHash(""), "chat");
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_shell_window.py -q -k dark_themed; node --test tests/js/main_hash.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`macos/ShellStatus.swift` (keep AppKit out of the harness) — add:

```swift
func errorPageHTML(reason: String, logPath: String) -> String {
  func esc(_ s: String) -> String {
    s.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;")
     .replacingOccurrences(of: ">", with: "&gt;").replacingOccurrences(of: "\"", with: "&quot;")
  }
  return """
  <!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>LocalModelDesk</title>
  <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#14161a;color:#e7e9ee;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
  main{max-width:36em;padding:32px;background:#1d2026;border:1px solid #2c313a;border-radius:8px}h1{font-size:20px;margin:0 0 12px}
  code{font:13px ui-monospace,Menlo,monospace;color:#9aa3b2;word-break:break-all}
  button{margin-top:16px;padding:8px 12px;border-radius:6px;border:1px solid #4f8cff;background:#4f8cff;color:#fff;font:inherit;cursor:pointer}</style></head>
  <body><main><h1>服务未运行</h1><p id="reason">\(esc(reason))</p><p>日志：<code>\(esc(logPath))</code></p>
  <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button></main></body></html>
  """
}
```

`MainWindowController.showErrorPage` → `lastFragment = webView.url?.fragment; webView.loadHTMLString(errorPageHTML(reason: reason, logPath: logPath), baseURL: nil); showWindow()`; `loadDeskShell()` → `var url = baseURL; if let f = lastFragment, var c = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) { c.fragment = f; url = c.url ?? baseURL }; webView.load(URLRequest(url: url))`. Harness: `case "error-page": print(errorPageHTML(reason: args[1], logPath: args[2]))`.

`desk/static/js/pure/tab_hash.js`:

```js
const TABS = new Set(["chat", "video", "music", "resources", "library"]);
export function tabFromHash(hash) {
  const m = /^#tab=([a-z]+)$/.exec(hash ?? "");
  return m && TABS.has(m[1]) ? m[1] : "chat";
}
```

`main.js`: in `enterDesk` after wiring, `showTab(tabFromHash(globalThis.location?.hash))`; in `showTab` set `if (globalThis.location) globalThis.history?.replaceState(null, "", \`#tab=${name}\`)`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_shell_window.py -q && node --test tests/js/main_hash.test.js && scripts/build-shell-app.sh`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add macos/ShellStatus.swift macos/MainWindowController.swift macos/harness/ShellHarness.swift desk/static/js/pure/tab_hash.js desk/static/js/main.js tests/test_shell_window.py tests/js/main_hash.test.js
git commit -m "fix(shell/ui): themed error page and tab restored after retry (G29 G37)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 21: Native first-run keeps asking until it succeeds or the user cancels (G21)

**Files:**
- Modify: `macos/FirstRunFlow.swift:10-68`

- [ ] **Step 1: Read the current flow** (`sed -n 1,70p macos/FirstRunFlow.swift`) and identify every `return false` that follows a failed `post(...)`.

- [ ] **Step 2: Implement** — inside `run()`'s `while true`, replace each `if !post(...) { return false }` with `if !post(...) { continue }` so a failed submission re-presents the chooser; keep `return false` only for the explicit cancel/close branch. Give the failure alert two buttons: 「重选」 (continue) and 「稍后再说」 (return false).

- [ ] **Step 3: Verify manually** — build, quit the app, set `first_run_done=false` in a copy of the data root (`LOCALMODELDESK_DATA_ROOT` env when launching from Terminal), choose a non-writable directory such as `/System`, confirm the alert offers 重选 and returns to the chooser; choose a writable dir; the desk loads.

- [ ] **Step 4: Commit**

```bash
git add macos/FirstRunFlow.swift
git commit -m "fix(shell): first-run retries after a failed submission instead of dropping into the desk (G21)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 22: One unit everywhere — GiB, from real bytes (G2, N10, P2)

**Files:**
- Modify: `desk/static/js/pure/format.js:6-12`, `desk/static/js/pure/desk_state.js:26-30`, `desk/static/js/pure/model_status.js:29`, `desk/static/js/panes/chat.js:46`
- Test: `tests/js/format.test.js`, `tests/js/desk_state.test.js`, `tests/js/media_panes.test.js`, `tests/e2e/test_statusbar_memory.py` (update expectations)

- [ ] **Step 1: Write the failing tests**

```js
// format.test.js (append)
test("formatBytes 用 GiB/MiB 标签，与 1024 进制一致", () => {
  assert.equal(formatBytes(16878224220), "15.7 GiB");
  assert.equal(formatBytes(5 * 1024 ** 2), "5 MiB");
});
// desk_state.test.js (append)
test("状态条内存文案标 GiB", () => {
  const view = renderState({ can_start: { llm: { ok: true } } }, { total_bytes: 128 * 1024 ** 3, used_bytes: 64 * 1024 ** 3, available_bytes: 64 * 1024 ** 3 });
  assert.equal(view.memText, "已用 64.0 / 总 128.0 GiB（可用 64.0 GiB）");
});
```

and in `media_panes.test.js`/`resources_pane.test.js` expect `sizeText` from `status.bytes_expected` (`formatBytes(status.bytes_expected)`) and only fall back to `${entry.gb} GB` label → now `${entry.gb} GiB（目录）` when `bytes_expected` is missing.

- [ ] **Step 2: Run to verify they fail** — `node --test tests/js/format.test.js tests/js/desk_state.test.js`

- [ ] **Step 3: Implement**

```js
// format.js
export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes >= GB) return `${(bytes / GB).toFixed(1)} GiB`;
  if (bytes >= MB) return `${Math.round(bytes / MB)} MiB`;
  if (bytes >= KB) return `${Math.round(bytes / KB)} KiB`;
  return `${bytes} B`;
}
```

`desk_state.js`: `已用 ${gb(used)} / 总 ${gb(total)} GiB（可用 ${gb(avail)} GiB）`. `model_status.js`: `sizeText: Number.isFinite(status.bytes_expected) ? formatBytes(status.bytes_expected) : \`${entry.gb} GiB（目录）\``. `chat.js:46`: use `formatBytes(byKey.get(entry.key)?.bytes_expected)` with the same fallback. Update `tests/e2e/test_statusbar_memory.py` string expectations from `GB` to `GiB`.

- [ ] **Step 4: Run** — `node --test tests/js && python3 -m pytest tests/test_ui_static.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/format.js desk/static/js/pure/desk_state.js desk/static/js/pure/model_status.js desk/static/js/panes/chat.js tests/js tests/e2e/test_statusbar_memory.py
git commit -m "fix(ui): GiB everywhere, model size from manifest bytes (G2 N10)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 23: Resources row renders each field once (G1, P1)

**Files:**
- Modify: `desk/static/js/panes/resources.js:48-61`
- Test: `tests/js/resources_pane.test.js`

- [ ] **Step 1: Write the failing test**

```js
test("每行只渲染一次名称与状态", async () => {
  const { root, parts } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (url) => ({ ok: true, status: 200, json: async () => String(url).includes("catalog") ? [{ key: "glm", name: "GLM", gb: 16.9 }] : String(url).includes("download") ? { state: "idle" } : { models: [{ key: "glm", state: "present", disk_bytes: 10, bytes_expected: 10 }], disk: { free_bytes: 1, total_bytes: 2 } } });
  try {
    const pane = createResourcesPane(root); await pane.refresh();
    const li = parts["res-list"].children[0];
    assert.equal(li.textContent, "");
    assert.equal(li.children.filter((c) => c.textContent.includes("GLM")).length, 1);
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/resources_pane.test.js`

- [ ] **Step 3: Implement** — delete line 54 (`li.textContent = ...`) in `rowNode`; keep the `<p>` title and `res-meta` children. Check `tests/e2e/test_resources_panel.py` still passes (it addresses rows by `data-model`).

- [ ] **Step 4: Run** — `node --test tests/js/resources_pane.test.js && python3 -m pytest tests/e2e/test_resources_panel.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/resources.js tests/js/resources_pane.test.js
git commit -m "fix(ui): resources row no longer paints every field twice (G1)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 24: Signing never silently falls back to adhoc (G4)

**Files:**
- Modify: `scripts/build-app.sh` (where it invokes `sign-app.sh`), `scripts/verify-app.sh`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test** (static, no build): assert `build-app.sh` only passes `--adhoc` when `LMD_ALLOW_ADHOC=1` is set, and that `verify-app.sh` runs `spctl --assess --type execute` and fails when it prints `rejected` unless `LMD_ALLOW_ADHOC=1`.

```python
def test_build_refuses_silent_adhoc_and_verify_checks_gatekeeper():
    build = (REPO / "scripts" / "build-app.sh").read_text(encoding="utf-8")     # REPO from packaging_fixture
    verify = (REPO / "scripts" / "verify-app.sh").read_text(encoding="utf-8")
    assert 'LMD_ALLOW_ADHOC' in build and '--adhoc' in build
    assert "spctl --assess --type execute" in verify and "LMD_ALLOW_ADHOC" in verify
```

- [ ] **Step 2: Run to verify it fails** — `python3 -m pytest tests/test_packaging.py -q -k adhoc`

- [ ] **Step 3: Implement** — in `build-app.sh`, replace the sign call with:

```bash
if [[ "${LMD_ALLOW_ADHOC:-0}" == "1" ]]; then
  "$ROOT/scripts/sign-app.sh" "$APP" --adhoc
  echo "警告：adhoc 签名仅供本机调试，Gatekeeper 会拒绝在其他机器上打开" >&2
else
  "$ROOT/scripts/sign-app.sh" "$APP"     # 找不到 Developer ID 时 sign-app.sh 已经会失败退出
fi
```

In `verify-app.sh` append:

```bash
if ! spctl --assess --type execute "$APP" 2>&1 | grep -qv rejected; then
  if [[ "${LMD_ALLOW_ADHOC:-0}" != "1" ]]; then echo "错误：Gatekeeper 拒绝了该包（未用 Developer ID 签名）" >&2; exit 1; fi
fi
```

Document in README 安装 section: obtaining a Developer ID Application certificate, `security find-identity -v -p codesigning`, and `LMD_ALLOW_ADHOC=1` for local-only builds.

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_packaging.py -q`

- [ ] **Step 5: Commit**

```bash
git add scripts/build-app.sh scripts/verify-app.sh README.md tests/test_packaging.py
git commit -m "build: refuse silent adhoc signing; Gatekeeper check in verify (G4)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 25: Music panel reachable by assistive tech (G36)

**Files:**
- Modify: `desk/static/index.html:30` (music form)
- Test: manual with `orca computer get-app-state`

- [ ] **Step 1: Reproduce** — with the app running, `orca computer get-app-state --app com.aa.localmodeldesk --json` after clicking 音乐: confirm treeText lacks the caption/lyrics/duration/生成歌曲 nodes while 聊天 exposes its controls.

- [ ] **Step 2: Implement the difference that exists in markup** — the chat and video forms wrap controls in `<label>`/`aria-label`; the music textareas have only placeholders. Change to:

```html
<div class="form" role="form" aria-label="生成歌曲"><label>风格描述 <textarea data-music-caption placeholder="例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速"></textarea></label><label>歌词（必填） <textarea data-music-lyrics required></textarea></label><label>时长（秒） <input data-music-duration type="number" value="60" min="10" max="300"></label><button data-music-start data-icon-name="sparkles">生成歌曲</button><div class="inline-error" data-music-error role="alert"></div></div>
```

- [ ] **Step 3: Verify** — rebuild static (no build step: just restart the app), re-run the `get-app-state` probe; treeText must now list `风格描述`, `歌词（必填）`, `时长（秒）`, `生成歌曲`. If it still does not, capture the treeText into the commit message and open an issue titled 「WKWebView AX tree drops music form」 with the two treeText files attached — do not mark this task done in that case.

- [ ] **Step 4: Run** — `node --test tests/js/media_panes.test.js && python3 -m pytest tests/test_ui_static.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/index.html
git commit -m "fix(ui): label every music form control so it reaches the accessibility tree (G36)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 26: Full regression and cross-exam re-run hook

- [ ] **Step 1:** `python3 -m pytest -q` (all Python incl. shell harness), `node --test tests/js`, `python3 -m pytest tests/e2e -q` (Playwright; requires `tests/e2e/requirements.txt`).
- [ ] **Step 2:** `scripts/build-app.sh && scripts/verify-app.sh dist/LocalModelDesk.app` (with `LMD_ALLOW_ADHOC=1` if no Developer ID on this machine).
- [ ] **Step 3:** Install to `dist/`, launch, and re-run the cross-exam journeys that were gaps: J2, J4, J8, J9, J16, J17 (`/cross-exam` continuation from `docs/cross-exam/2026-09-06-localmodeldesk/ledger.json` open threads). Record the new run under `docs/cross-exam/<date>-localmodeldesk-fixes/`.

---

## Self-Review

- Spec coverage: every high/medium gap in the report maps to a task (G5/G6/J9 → T2; G7 → T1; G8 → T3; G11/G13 → T7; G19/G31 → T4/T5; G20 → T6; G1 → T23; G4 → T24; G9/J16/J4/G28 → T10/T15; J8/G17/G18 → T11; G16/G3 → T16; G22/G25 → T14; G23/J2 → T9; J17 → T17; G32 → T13; G35 → T12; G36 → T25; G39 → T19; G40/G30/G27 → T18; G2 → T22; G12 → T8; G15 → T10; G21 → T21; G29/G37 → T20). Low gaps G10, G14, G24, G26 and the reviewer findings are visual and live in Plan B.
- Placeholder scan: no TBD/TODO; each code step shows the code. Task 21 and 25 are manual-verification tasks because no headless harness covers AppKit/WKWebView; they state the exact commands and pass/fail criteria.
- Type consistency: `apply_discovered`, `ConfigInvalidError`, `hf_env`, `stale_bytes`, `elapsed_s`, `applyLlmStatus`, `revealOutput`, `setDrawerOpen`, `pollFailureAction`, `errorPageHTML`, `tabFromHash`, `describeJobError` are each defined in exactly one task and used with the same names afterwards.
