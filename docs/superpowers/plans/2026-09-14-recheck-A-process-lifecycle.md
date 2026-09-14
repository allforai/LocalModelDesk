# Cross-Exam 2026-09-13 修复 · A 进程与生命周期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 应用任何方式退出（菜单退出、SIGTERM、壳被 kill -9）都不留孤儿进程；8767 被别的进程占着时加载模型当场给出人话原因，并允许用户取消进行中的加载。

**Architecture:** 服务端负责清理自己派生的一切：`ProductionRuntime.shutdown()` 在关闭 LLM 之外取消在跑的媒体作业；`desk/__main__.py` 让 SIGTERM 与"父进程消失"都走同一条优雅关闭路径，而不是 `os._exit(0)` 直接跳过清理。LLM 加载在收割自己的端口之后，若端口仍被陌生进程监听就立刻失败并点名占用者。壳侧只把启动超时的收割从"只杀组长"改为按进程组收割。

**Tech Stack:** Python 3.13 stdlib（`signal`、`threading`、`subprocess`）· Swift 5 / AppKit · pytest 9 · node:test

**Spec:** `docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md` §缺口清单 G12、G17、G18，§缺陷模式 P4；证据 `evidence/q23/`、`evidence/q45/`、`evidence/q46/`。需求：`docs/superpowers/specs/2026-08-31-shell-spec.md` R-shell-04，`2026-08-31-llm-spec.md` R-llm-04，`2026-08-31-arbiter-spec.md` R-arbiter-03。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）。
- 所有面向用户的字符串是简体中文；机器码永远不作为唯一解释出现。
- 测试命令：`python3 -m pytest -q`（Python）、`node --test tests/js/*.test.js`（JS）、`python3 -m pytest tests/e2e -q`（Playwright，约 2.5 分钟）。Swift 改动必须跑 `python3 -m pytest tests/test_shell_*.py -q`。
- 验证门必须包含 e2e：`desk/static/` 或 `desk/` 任一改动，提交前跑 `python3 -m pytest tests/e2e -q`。
- 测试永不触碰 `~/LocalModelDesk` 模型权重或 `~/Library/Application Support/LocalModelDesk`：一律 `tmp_path` + `LOCALMODELDESK_DATA_ROOT`。
- 真机验证起第二个实例时，必须 `ditto` 出独立副本包；按 pid 定位原生窗口与菜单（`NSRunningApplication.runningApplicationWithProcessIdentifier` + `lsappinfo front`），**不要**用 System Events 按名字或 unix id 寻址（同 bundle 多实例时会串到先启动的实例）。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `desk/media/service.py` | 新增 `close()`：取消在跑作业并等待 worker 退出 |
| `desk/runtime.py` | `ProductionRuntime` 持有 `media`，`shutdown()` 依次关网关、媒体、LLM、HTTP |
| `desk/__main__.py` | 新增 `graceful_exit()`；SIGTERM 与父进程消失都走它 |
| `desk/arbiter/reaper.py` | 新增 `port_listeners(port)`：返回监听者 pid 与命令行 |
| `desk/arbiter/core.py` | 新增 `llm_port_listeners(port)` 透传 |
| `desk/llm/state.py` | 新增错误码 `ERR_PORT_BUSY`、`ERR_LOAD_CANCELLED` |
| `desk/llm/service.py` | 加载前检查陌生占用者；`unload()` 在加载中改为取消加载 |
| `desk/static/js/panes/chat.js` | 加载中「卸载」按钮可用，文案变为「取消加载」 |
| `macos/ServerController.swift` | 启动超时按进程组收割 |
| `tests/llm/llm_fakes.py` | `FakeArbiter` 支持 `llm_port_listeners` |

---

### Task 1: 媒体服务关闭时取消在跑作业

**Files:**
- Modify: `desk/media/service.py`（在 `cancel_job` 之后新增 `close`）
- Modify: `desk/runtime.py:46-76`（`ProductionRuntime` 字段与 `shutdown`，`build_runtime` 返回处）
- Test: `tests/test_media_service.py`、`tests/test_production_runtime.py`

**Interfaces:**
- Produces: `MediaService.close(self) -> None` —— 幂等；有 running 作业时等价于 `cancel_job()`（TERM 进程组，宽限期后 KILL），并等待 worker 线程写完终态（最多 `term_grace_s + 2` 秒）。
- Produces: `ProductionRuntime(app, gateway, llm, media)`，`shutdown()` 顺序：`gateway.stop()` → `media.close()` → `llm.close()` → `app.shutdown()`。

- [ ] **Step 1: Write the failing test（媒体关闭）**

在 `tests/test_media_service.py` 末尾追加（复用文件内已有的 `make_service`、`FakeExecutor`）：

```python
def test_close_cancels_running_job_and_waits_for_terminal_state(tmp_path):
    """应用退出时在跑的媒体作业不能变成孤儿（R-shell-04，cross-exam 2026-09-13 G12）。"""
    service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
    service._term_grace_s = 0.01
    service.start_video_job(prompt="rain", width=512, height=288, frames=73, steps=10)
    assert service.job_status()["status"] == "running"

    service.close()

    snap = service.job_status()
    assert snap["status"] == "cancelled"
    assert deps.arbiter.released == ["permit-1"]


def test_close_without_running_job_is_a_noop(tmp_path):
    service, deps = make_service(tmp_path)
    service.close()
    service.close()
    assert service.job_status()["status"] == "idle"
    assert deps.arbiter.released == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_media_service.py -k close -q`
Expected: FAIL，`AttributeError: 'MediaService' object has no attribute 'close'`

- [ ] **Step 3: Write minimal implementation**

在 `desk/media/service.py` 的 `cancel_job` 方法之后插入：

```python
    def close(self) -> None:
        """Cancel any running job on shutdown so its worker never outlives the service."""
        with self._lock:
            running = self._state["status"] == "running"
        if not running:
            return
        try:
            self.cancel_job()
        except MediaError:
            return  # finished between the check and the cancel
        deadline = time.monotonic() + self._term_grace_s + 2.0
        while time.monotonic() < deadline:
            with self._lock:
                if self._state["status"] != "running":
                    return
            time.sleep(0.02)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_media_service.py -k close -q`
Expected: PASS（2 passed）

- [ ] **Step 5: Write the failing test（运行时关闭顺序）**

在 `tests/test_production_runtime.py` 末尾追加：

```python
def test_shutdown_closes_media_before_llm(tmp_path, monkeypatch):
    _configured_data_root(tmp_path, monkeypatch)
    runtime = build_runtime(port=0)
    order = []
    runtime.gateway.stop = lambda: order.append("gateway")
    runtime.media.close = lambda: order.append("media")
    runtime.llm.close = lambda: order.append("llm")
    real_app_shutdown = runtime.app.shutdown
    runtime.app.shutdown = lambda: (order.append("app"), real_app_shutdown())
    runtime.start_background()
    runtime.shutdown()
    runtime.shutdown()
    assert order == ["gateway", "media", "llm", "app"]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python3 -m pytest tests/test_production_runtime.py -k media_before_llm -q`
Expected: FAIL，`AttributeError: 'ProductionRuntime' object has no attribute 'media'`

- [ ] **Step 7: Write minimal implementation**

`desk/runtime.py`：给 dataclass 加字段并改 `shutdown`：

```python
class ProductionRuntime:
    app: DeskApp
    gateway: GatewayService
    llm: LlmService
    media: MediaService
    _closed: bool = False
```

```python
    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.gateway.stop()
        self.media.close()
        self.llm.close()
        self.app.shutdown()
```

`build_runtime` 末尾返回处改为：

```python
    return ProductionRuntime(app, gateway, llm, media)
```

（`MediaService` 已在文件顶部导入。）

- [ ] **Step 8: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_production_runtime.py tests/test_media_service.py -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add desk/media/service.py desk/runtime.py tests/test_media_service.py tests/test_production_runtime.py
git commit -m "fix(media): cancel the running job when the service shuts down (G12)"
```

---

### Task 2: SIGTERM 与父进程消失走同一条优雅关闭

**Files:**
- Modify: `desk/__main__.py`
- Test: `tests/test_foundation_main.py`

**Interfaces:**
- Consumes: `ProductionRuntime.shutdown()`（Task 1）
- Produces: `graceful_exit(runtime, *, exit=os._exit) -> None` —— 调 `runtime.shutdown()`（异常吞掉并记日志），然后 `exit(0)`；多次调用只关闭一次。
- Produces: `install_termination(runtime, *, exit=os._exit) -> None` —— 为 SIGTERM、SIGINT 安装处理器，处理器在**后台线程**里调 `graceful_exit`（主线程正在 `serve_forever`，在信号处理器里同步 `shutdown()` 会互等死锁）。

- [ ] **Step 1: Write the failing test**

在 `tests/test_foundation_main.py` 末尾追加：

```python
def test_graceful_exit_shuts_down_once_then_exits():
    from desk.__main__ import graceful_exit

    calls = []
    runtime = type("R", (), {"shutdown": lambda self: calls.append("shutdown")})()
    graceful_exit(runtime, exit=lambda code: calls.append(("exit", code)))
    assert calls == ["shutdown", ("exit", 0)]


def test_graceful_exit_still_exits_when_shutdown_raises():
    from desk.__main__ import graceful_exit

    calls = []

    class Broken:
        def shutdown(self):
            raise RuntimeError("boom")

    graceful_exit(Broken(), exit=lambda code: calls.append(code))
    assert calls == [0]


def test_install_termination_runs_graceful_exit_off_the_signal_thread():
    import signal
    import threading

    from desk.__main__ import install_termination

    finished = threading.Event()
    seen = {}

    class Runtime:
        def shutdown(self):
            seen["thread"] = threading.current_thread().name

    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        install_termination(Runtime(), exit=lambda code: finished.set())
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        assert finished.wait(2.0)
        assert seen["thread"] != threading.main_thread().name
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_foundation_main.py -q`
Expected: FAIL，`ImportError: cannot import name 'graceful_exit'`

- [ ] **Step 3: Write minimal implementation**

把 `desk/__main__.py` 的 `main` 及其上方补充为：

```python
import logging
import signal

log = logging.getLogger(__name__)
_exit_lock = threading.Lock()


def graceful_exit(runtime, *, exit=os._exit) -> None:
    """Close every service (and the children they own) before the process leaves."""
    with _exit_lock:
        try:
            runtime.shutdown()
        except Exception:  # an exit path must never be blocked by a cleanup error
            log.exception("shutdown failed during exit")
        exit(0)


def install_termination(runtime, *, exit=os._exit) -> None:
    """SIGTERM/SIGINT shut down on a worker thread: the main thread is inside serve_forever."""

    def handler(_signum, _frame) -> None:
        threading.Thread(
            target=graceful_exit, args=(runtime,), kwargs={"exit": exit},
            name="graceful-exit", daemon=True,
        ).start()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def main() -> None:
    ensure_own_process_group()
    runtime = build_runtime(port=runtime_port())
    install_termination(runtime)
    parent = os.environ.get("LMD_PARENT_PID")
    if parent and parent.isdigit():
        watch_parent(int(parent), on_gone=lambda: graceful_exit(runtime))
    try:
        runtime.serve_forever()
    finally:
        runtime.shutdown()
```

（`import os`、`threading`、`time` 已在文件顶部；把新增的 `logging`、`signal` import 放进 import 区。）

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_foundation_main.py -q`
Expected: PASS

- [ ] **Step 5: 真机验证壳被 kill -9 不留 mlx_lm 孤儿**

构建仓库外副本并复现 q45 场景：

```bash
./scripts/build-app.sh --output /tmp/lmd-planA && ditto /tmp/lmd-planA/LocalModelDesk.app /tmp/lmd-planA-iso/LocalModelDesk.app
mkdir -p /tmp/lmd-planA-iso/data && printf '{"config_version":1,"first_run_done":true,"models_root":"%s","gateway":{"enabled":false,"host":"127.0.0.1","port":8845}}' "$HOME/LocalModelDesk" > /tmp/lmd-planA-iso/data/config.json
LOCALMODELDESK_DATA_ROOT=/tmp/lmd-planA-iso/data LMD_SHELL_PORT=8839 /tmp/lmd-planA-iso/LocalModelDesk.app/Contents/MacOS/LocalModelDesk &
sleep 8; curl -s -X POST 127.0.0.1:8839/api/llm/load -H 'Content-Type: application/json' -d '{"key":"superqwen"}'
for i in $(seq 1 60); do curl -s 127.0.0.1:8839/api/llm/status | grep -q '"loaded"' && break; sleep 3; done
kill -9 "$(pgrep -f 'lmd-planA-iso/LocalModelDesk.app/Contents/MacOS/LocalModelDesk')"
sleep 15; lsof -iTCP:8767 -sTCP:LISTEN -P; pgrep -fl 'lmd-planA-iso'
```

Expected: 最后两条命令都没有输出（8767 无监听、副本无残留进程）。有残留则按 pid 手动清理并回到 Step 3 排查。

- [ ] **Step 6: Commit**

```bash
git add desk/__main__.py tests/test_foundation_main.py
git commit -m "fix(shell): SIGTERM and a vanished parent both shut down cleanly (G17)"
```

---

### Task 3: 8767 被陌生进程占用时加载立刻失败并点名占用者

**Files:**
- Modify: `desk/arbiter/reaper.py`（新增 `port_listeners`）
- Modify: `desk/arbiter/core.py`（新增 `llm_port_listeners`）
- Modify: `desk/llm/state.py`（新增 `ERR_PORT_BUSY`）
- Modify: `desk/llm/service.py:153-172`（`_load_worker` 在 reap 之后）
- Modify: `tests/llm/llm_fakes.py`（`FakeArbiter`）
- Test: `tests/test_arbiter_reaper.py`、`tests/llm/test_llm_load_failures.py`

**Interfaces:**
- Produces: `reaper.port_listeners(port: int) -> list[dict]`，每项 `{"pid": int, "command": str}`，不含当前进程。
- Produces: `Arbiter.llm_port_listeners(port: int) -> list[dict]`
- Produces: `ERR_PORT_BUSY = "port_busy"`；错误消息格式：`端口 {port} 被其他程序占用（pid {pid}：{command 前 80 字}），请先结束它再加载`

- [ ] **Step 1: Write the failing test（reaper）**

在 `tests/test_arbiter_reaper.py` 末尾追加：

```python
def test_port_listeners_reports_pid_and_command_of_a_real_listener():
    import socket
    import subprocess
    import sys
    import time

    from desk.arbiter.reaper import port_listeners

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        found = []
        while time.monotonic() < deadline and not found:
            found = port_listeners(port)
            time.sleep(0.1)
        assert [item["pid"] for item in found] == [server.pid]
        assert "http.server" in found[0]["command"]
    finally:
        server.terminate()
        server.wait(5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_arbiter_reaper.py -k port_listeners -q`
Expected: FAIL，`ImportError: cannot import name 'port_listeners'`

- [ ] **Step 3: Write minimal implementation（reaper + arbiter）**

`desk/arbiter/reaper.py` 在 `_listening_pids` 之后追加：

```python
def port_listeners(port: int) -> list[dict]:
    """Who is listening on ``port`` (excluding us), with the command line for a human message."""
    listeners = []
    for pid in _listening_pids(port):
        proc = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
        listeners.append({"pid": pid, "command": proc.stdout.strip()})
    return listeners
```

`desk/arbiter/core.py` 顶部 `from .reaper import ReapResult, reap_port` 改为 `from .reaper import ReapResult, port_listeners, reap_port`，并在 `reap_llm_port` 之后追加：

```python
    def llm_port_listeners(self, port: int) -> list[dict]:
        """Listeners still on the LLM port after reaping — strangers the arbiter will not kill."""
        return port_listeners(port)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_arbiter_reaper.py -q`
Expected: PASS

- [ ] **Step 5: Write the failing test（加载）**

`tests/llm/llm_fakes.py`：`FakeArbiter.__init__` 增加关键字参数 `listeners: Iterable[dict] = ()` 并保存为 `self._listeners = list(listeners)`；新增方法：

```python
    def llm_port_listeners(self, port: int) -> list[dict]:
        _record(self.calls, "listeners", port)
        return list(self._listeners)
```

在 `tests/llm/test_llm_load_failures.py` 末尾追加：

```python
def test_stranger_on_llm_port_fails_before_spawn_with_its_pid(tmp_path):
    from desk.llm.state import ERR_PORT_BUSY

    testbed = make_service(
        tmp_path,
        arbiter_kw={"listeners": [{"pid": 4242, "command": "python3 -m http.server 8767"}]},
    )

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["status"] == "error"
    assert final["error"]["code"] == ERR_PORT_BUSY
    assert "4242" in final["error"]["message"]
    assert "http.server" in final["error"]["message"]
    names = [call[0] for call in testbed.calls]
    assert "spawn" not in names
    assert ("release", "tok-1") in testbed.calls
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python3 -m pytest tests/llm/test_llm_load_failures.py -k stranger -q`
Expected: FAIL，`ImportError: cannot import name 'ERR_PORT_BUSY'`

- [ ] **Step 7: Write minimal implementation**

`desk/llm/state.py` 错误码区追加：

```python
ERR_PORT_BUSY = "port_busy"
```

`desk/llm/service.py`：import 列表加入 `ERR_PORT_BUSY`；在 `_load_worker` 里 `reap = ...` 失败分支之后、`proc = self._backend.spawn(...)` 之前插入：

```python
        strangers = self._arbiter.llm_port_listeners(self._port)
        if strangers:
            first = strangers[0]
            message = (f"端口 {self._port} 被其他程序占用（pid {first['pid']}："
                       f"{first['command'][:80]}），请先结束它再加载")
            with self._lock:
                if generation != self._load_generation:
                    return
                token = self._token
                self._token = None
                self._state = LlmState(status=STATUS_ERROR, model_key=entry.key,
                                       error=LlmError(ERR_PORT_BUSY, message))
            if token is not None:
                self._arbiter.release_heavy(token)
            return
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python3 -m pytest tests/llm tests/test_arbiter_reaper.py tests/test_arbiter_core.py -q`
Expected: PASS（若其他测试用的 `FakeArbiter` 缺 `llm_port_listeners`，它们现在也有默认空列表）

- [ ] **Step 9: Commit**

```bash
git add desk/arbiter/reaper.py desk/arbiter/core.py desk/llm/state.py desk/llm/service.py tests/llm/llm_fakes.py tests/llm/test_llm_load_failures.py tests/test_arbiter_reaper.py
git commit -m "fix(llm): name the stranger on the LLM port instead of timing out after 180s (G18)"
```

---

### Task 4: 加载进行中可以取消

**Files:**
- Modify: `desk/llm/state.py`（新增 `ERR_LOAD_CANCELLED`，仅作日志/状态说明备用，不进入 error）
- Modify: `desk/llm/service.py:320-353`（`unload`）
- Modify: `desk/static/js/panes/chat.js:95-102`（`renderLlm` 末尾按钮状态）
- Test: `tests/llm/test_llm_unload.py`（替换 `test_unload_during_loading_rejected_worker_unaffected`）、`tests/js/chat_pane.test.js`

**Interfaces:**
- Produces: `LlmService.unload()` 在 `STATUS_LOADING` 时：递增 `_load_generation`（让加载线程丢弃结果）、终止已派生的进程、释放许可、状态回到 `idle`，返回 `{"status": "idle", ...}`。不再抛 `ERR_LOAD_IN_PROGRESS`。
- Produces: 聊天面板在 `loading` 时「卸载」按钮可点，文字为「取消加载」；其它状态文字为「卸载」。

- [ ] **Step 1: Write the failing test（服务）**

把 `tests/llm/test_llm_unload.py` 里的 `test_unload_during_loading_rejected_worker_unaffected` 整个替换为（旧测试钉的正是 cross-exam 要改掉的行为）：

```python
def test_unload_while_loading_cancels_the_load_and_releases(tmp_path):
    testbed = make_service(tmp_path, load_timeout_s=30)
    testbed.backend.hold_health = True

    testbed.service.load("glm")
    assert testbed.service.status()["state"]["status"] == "loading"

    result = testbed.service.unload()
    testbed.backend.health_release.set()

    assert result["status"] == "idle"
    assert ("release", "tok-1") in testbed.calls
    assert testbed.service.wait_settled()["status"] == "idle"
    assert "terminate" in [call[0] for call in testbed.calls]
```

（加载线程在 `_load_worker` 里若发现 generation 已变，会自己 `proc.terminate()` 然后返回；本任务负责的是加载线程已把 `_proc` 登记之后的那一段。替换后若 `pytest` 导入不再被使用，删掉该 import。）

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/llm/test_llm_unload.py -k cancels -q`
Expected: FAIL，`LlmRejected: 加载进行中，等状态落定后再卸载`

- [ ] **Step 3: Write minimal implementation（服务）**

替换 `desk/llm/service.py` 中 `unload` 开头的加载中分支：

```python
    def unload(self) -> dict[str, Any]:
        """Unload a settled model, or cancel a load that is still in progress."""
        token = None
        proc = None
        with self._lock:
            if self._state.status == STATUS_LOADING:
                self._load_generation += 1
                proc, token = self._proc, self._token
                self._proc = None
                self._token = None
                self._entry = None
                self._state = LlmState(status=STATUS_IDLE)
                result = self._state.to_dict()
            elif self._state.status == STATUS_IDLE:
                return self._state.to_dict()
            elif self._teardown_proc_locked():
                token = self._token
                self._token = None
                self._entry = None
                self._state = LlmState(status=STATUS_IDLE)
                result = self._state.to_dict()
            else:
                self._state = LlmState(
                    status=STATUS_ERROR,
                    model_key=self._state.model_key,
                    error=LlmError(ERR_PORT_NOT_RELEASED, f"卸载后端口 {self._port} 仍被占用"),
                )
                result = self._state.to_dict()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(self._term_grace_s)
            except Exception:
                proc.kill()
        if token is not None:
            self._arbiter.release_heavy(token)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/llm -q`
Expected: PASS

- [ ] **Step 5: Write the failing test（前端）**

在 `tests/js/chat_pane.test.js` 末尾追加：

```javascript
test("加载中卸载按钮可用并显示『取消加载』，其余状态显示『卸载』", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loading", model_key: "glm" }, loaded_model: null });
  assert.equal(controls.get("[data-unload]").disabled, false);
  assert.equal(controls.get("[data-unload]").textContent, "取消加载");
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.equal(controls.get("[data-unload]").textContent, "卸载");
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（`disabled` 为 true）

- [ ] **Step 7: Write minimal implementation（前端）**

`desk/static/js/panes/chat.js` 的 `renderLlm` 中把

```javascript
    els.unloadBtn.disabled = state.status === "idle" || state.status === "loading";
```

替换为：

```javascript
    els.unloadBtn.disabled = state.status === "idle";
    setButtonLabel(els.unloadBtn, state.status === "loading" ? "取消加载" : "卸载");
```

`desk/static/index.html` 里 `<button data-unload data-icon-name="power">卸载</button>` 改为 `<button data-unload data-icon-name="power"><span data-label>卸载</span></button>`，保证换文案不抹掉图标。

- [ ] **Step 8: Run tests to verify they pass**

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add desk/llm/service.py desk/static/js/panes/chat.js desk/static/index.html tests/llm/test_llm_unload.py tests/js/chat_pane.test.js
git commit -m "feat(llm): a load in progress can be cancelled from the chat pane"
```

---

### Task 5: 壳启动超时按进程组收割

**Files:**
- Modify: `macos/ServerController.swift:88`
- Test: 现有 `tests/test_shell_lifecycle.py`、`tests/test_shell_portguard.py`

**Interfaces:**
- Consumes: `PortGuard.processGroup(of:)`、`PortGuard.familyByGroup(pgid:)`、`PortGuard.reap(pids:grace:)`（均已存在）

- [ ] **Step 1: Write the implementation**

把 `macos/ServerController.swift` 中

```swift
    PortGuard.reap(pids: [process.processIdentifier], grace: 2.0)
```

替换为：

```swift
    let leader = process.processIdentifier
    let group = PortGuard.processGroup(of: leader).map { PortGuard.familyByGroup(pgid: $0) } ?? []
    PortGuard.reap(pids: Array(Set(group + [leader])), grace: 2.0)
```

- [ ] **Step 2: Run shell tests**

Run: `python3 -m pytest tests/test_shell_*.py -q`
Expected: PASS（harness 能编译，现有生命周期断言不变）

- [ ] **Step 3: Commit**

```bash
git add macos/ServerController.swift
git commit -m "fix(shell): a startup timeout reaps the service's whole process group (P4)"
```

---

### Task 6: 端到端复核孤儿场景

**Files:** 无代码改动；只做验证并在计划里勾选。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 2: 真机复现 q23（音乐作业中从菜单退出）**

用 Task 2 Step 5 的副本包与数据根，起实例后在 `http://127.0.0.1:8839/#tab=music` 提交最短时长歌曲，确认 `pgrep -fl music3_cli` 有进程；用 JXA 按 pid 激活副本（`$.NSRunningApplication.runningApplicationWithProcessIdentifier(<壳pid>).activateWithOptions(0)`，`lsappinfo front` 核对），⌘Q 退出。

Run: `sleep 10; pgrep -fl 'lmd-planA-iso'; lsof -iTCP:8839 -sTCP:LISTEN -P`
Expected: 两条都无输出。

- [ ] **Step 3: 真机复现 q46（8767 被陌生进程占用）**

```bash
python3 -m http.server 8767 --bind 127.0.0.1 & OCC=$!
curl -s -X POST 127.0.0.1:8839/api/llm/load -H 'Content-Type: application/json' -d '{"key":"glm"}'
sleep 3; curl -s 127.0.0.1:8839/api/llm/status; kill $OCC
```

Expected: 3 秒内 status 为 `error`，`code` 为 `port_busy`，message 含占用者 pid 与 `http.server`。

- [ ] **Step 4: 清理副本**

```bash
pkill -f 'lmd-planA-iso' ; rm -rf /tmp/lmd-planA /tmp/lmd-planA-iso
```
