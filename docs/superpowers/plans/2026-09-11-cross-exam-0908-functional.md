# Cross-Exam 2026-09-08 修复 · A 功能与可靠性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关掉 2026-09-08 两轮 cross-exam 记录的全部功能/可靠性缺口（1 条 high、7 条 medium、2 条 low）与 12 条未拉的线里可直接动手的部分，使 `dist/LocalModelDesk.app` 与需求台账一致。

**Architecture:** Python 服务（`desk/`，stdlib HTTP，组合根 `desk/runtime.py`）、零依赖 ES module 前端（`desk/static/js`）、Swift AppKit 壳（`macos/`，通过 `scripts/shell-lifecycle-test.sh` 编译的无头 harness 测试）。每条修复落在拥有该行为的那一层：纯 Python → `pytest`；Swift 决策逻辑 → `ShellStatus.swift`/`PortGuard.swift` 并经 harness 子命令验证；前端 → `node --test`。

**Tech Stack:** Python 3.13 stdlib · Node 20+（`node:test`）· Swift 5 / AppKit · pytest 9 · Playwright 1.62（e2e）

**Spec:** `docs/cross-exam/2026-09-08-localmodeldesk/completion-report.md`（§缺口清单、§未拉的线、§缺陷模式 P1）与 `docs/cross-exam/2026-09-08-localmodeldesk-widewin/completion-report.md`，证据在同目录 `evidence/` 下。需求基准：`docs/superpowers/specs/2026-08-31-*-spec.md`。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only；`huggingface_hub` 只以子进程形式出现）。
- 前端：无构建步骤、无依赖；DOM 只用 `createElement`/`textContent`，永不 `innerHTML`（R-ui-01）。
- 所有面向用户的字符串是简体中文；机器码永远不作为唯一解释出现（视觉基线 C3/F2）。
- 测试命令：`python3 -m pytest -q`（Python）、`node --test tests/js/*.test.js`（JS）、`python3 -m pytest tests/e2e`（Playwright，约 47 秒）。Swift 改动必须跑 `python3 -m pytest tests/test_shell_*.py`（会用 `xcrun swiftc` 编译 harness）。
- **验证门必须包含 e2e**：`desk/static/` 或 `desk/` 任一改动，提交前跑 `python3 -m pytest tests/e2e -q`；假 DOM 单测漏过真实浏览器崩溃有前科（见 `docs/superpowers/plans/2026-09-07-cross-exam-recheck-fixes.md`）。
- 测试永不触碰 `~/LocalModelDesk` 模型权重或 `~/Library/Application Support/LocalModelDesk`：一律用 `tmp_path` + `LOCALMODELDESK_DATA_ROOT`。
- 每个任务结束后提交，commit message 带 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` 与 `Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK` 两行 trailer。

## File Structure（改什么、各自一个职责）

| 文件 | 本计划中触及的职责 |
|---|---|
| `macos/PortGuard.swift` | 新增按进程组查询；`family(matching:)` 退为 harness-only |
| `macos/ServerController.swift` | 退出时只收割自己的进程组；attached/owned 语义不变 |
| `macos/DeskPaths.swift` | 传 `LMD_SERVICE_PGID_MARKER`，不再依赖路径前缀收割 |
| `macos/harness/ShellHarness.swift` | 新增 `family-pgid` 子命令，供测试断言归属 |
| `desk/__main__.py` | 服务启动时自建进程组 + 父进程消失自退 |
| `desk/arbiter/reaper.py` | 端口收割前校验进程归属 |
| `desk/resources/downloader.py` | 续传前清理不可续的残片；`--revision` 固定；attempt 级在途统计 |
| `desk/resources/verify.py` | `.incomplete` 只在下载进行中计入进度，否则报 `stale_bytes` |
| `desk/resources/service.py` | 把"该模型是否正在下载"传给 `verify_tree` |
| `desk/gateway/lan.py`（新建） | 枚举真实网卡、排除隧道/CGNAT，给出候选地址 |
| `desk/gateway/service.py` | 用新模块取 `lan_host`；apply 失败回滚；错误人话化 |
| `desk/foundation/config.py` | 坏配置备份与恢复入口所需的读写 |
| `desk/foundation/routes.py` | `POST /api/config/reset` 恢复入口 |
| `desk/media/memory_estimate.py`（新建） | 按作业参数估内存，常量来自实测日志 |
| `desk/media/service.py` | 预检改用新估算；把 worker 峰值记进历史 |
| `desk/testing/harness.py` | 复用各模块 `build_routes`，不再手抄路由表 |
| `scripts/install-app.sh` / `uninstall-app.sh` | `--help`、`--dest` 不存在时的真实原因 |
| `scripts/verify-app.sh` | V7 名单指向真实存在的遗留目录；新增 V8 封条自检 |
| `scripts/build-app.sh` | 预编译 `.pyc` 封进包 |
| `README.md` | 安装/卸载脚本用法 |
| 删除 `media-gui/` | 遗留原型整目录 |

---

### Task 1: 壳退出只收割自己的进程组（F10 high · P1 位点 1/11）

**缺口原文：** 同包第二实例与任何用包内 python 跑的无关进程在退出时被 TERM→KILL。源码链：`ServerController.swift:110` → `PortGuard.family(pgrep -f <包内 python 绝对路径>)` → `reap`。证据 `docs/cross-exam/2026-09-08-localmodeldesk/evidence/q30/`。

**Files:**
- Modify: `desk/__main__.py`
- Modify: `macos/PortGuard.swift:11-16`
- Modify: `macos/ServerController.swift:93-128`
- Modify: `macos/harness/ShellHarness.swift:21-35`
- Test: `tests/test_foundation_main.py`, `tests/test_shell_portguard.py`, `tests/test_shell_lifecycle.py`

**Interfaces:**
- Produces: `PortGuard.processGroup(of:) -> Int32?`、`PortGuard.familyByGroup(pgid:) -> [Int32]`、harness 子命令 `family-pgid <pgid> [psTool]`
- Consumes（Task 2）：服务自建进程组这一事实

- [x] **Step 1: 写失败测试 —— 服务进程自建进程组**

`tests/test_foundation_main.py` 末尾追加：

```python
def test_service_becomes_its_own_process_group_leader(tmp_path):
    """壳靠 pgid 收割；服务必须是自己进程组的组长（R-shell-04）。"""
    import os
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent(
        """
        import os, sys
        sys.path.insert(0, %r)
        from desk.__main__ import ensure_own_process_group
        ensure_own_process_group()
        print(os.getpid(), os.getpgid(0))
        """
    ) % str(REPO)
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    pid, pgid = (int(x) for x in out.stdout.split())
    assert pid == pgid
```

若该文件顶部没有 `REPO`，加上 `REPO = Path(__file__).resolve().parent.parent`（`from pathlib import Path`）。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_foundation_main.py::test_service_becomes_its_own_process_group_leader -q`
Expected: FAIL, `ImportError: cannot import name 'ensure_own_process_group'`

- [x] **Step 3: 实现自建进程组**

`desk/__main__.py` 在 `main()` 之前插入：

```python
def ensure_own_process_group() -> None:
    """Become our own process group leader so the shell can reap us by pgid, never by path."""
    try:
        if os.getpgid(0) != os.getpid():
            os.setpgrp()
    except OSError:
        pass  # already a leader, or a platform without process groups
```

在 `main()` 的第一行调用 `ensure_own_process_group()`，并确保文件顶部 `import os`。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_foundation_main.py -q`
Expected: PASS

- [x] **Step 5: 写失败测试 —— PortGuard 按进程组查询**

`tests/test_shell_portguard.py` 末尾追加：

```python
def test_family_pgid_lists_only_the_group(tmp_path):
    """按 pgid 查询只返回同组进程，不碰路径相同的无关进程（P1）。"""
    import os
    import signal
    import subprocess
    import time

    mine = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        time.sleep(0.3)
        out = subprocess.run(
            [harness_path(), "family-pgid", str(mine.pid)], capture_output=True, text=True
        )
        pids = {int(x) for x in out.stdout.split()}
        assert mine.pid in pids
        assert stranger.pid not in pids
    finally:
        for proc in (mine, stranger):
            proc.kill()
            proc.wait()
```

文件顶部若无 `import sys` 请补上。

- [x] **Step 6: 跑测试确认失败**

Run: `python3 -m pytest tests/test_shell_portguard.py::test_family_pgid_lists_only_the_group -q`
Expected: FAIL（harness 未识别 `family-pgid`，退出码 64，stdout 为空）

- [x] **Step 7: 实现 PortGuard 的进程组查询**

`macos/PortGuard.swift` 中 `family(matching:pgrepTool:)` 之后插入：

```swift
  /// Lists every live process in one process group — the only ownership-safe reap set.
  static func familyByGroup(pgid: Int32, psTool: String = "/bin/ps") -> [Int32] {
    parsePids(runCapture(psTool, ["-o", "pid=", "-g", String(pgid)]))
      .filter { $0 != ProcessInfo.processInfo.processIdentifier }
  }

  /// Reads one process's group id; nil when the process is gone.
  static func processGroup(of pid: Int32, psTool: String = "/bin/ps") -> Int32? {
    parsePids(runCapture(psTool, ["-o", "pgid=", "-p", String(pid)])).first
  }
```

并把 `family(matching:)` 的文档注释改成：

```swift
  /// Path-prefix match. Test/diagnostic only: it cannot tell our own children from a
  /// second instance of the same bundle, so it must never drive a reap (P1, 2026-09-08).
```

- [x] **Step 8: 加 harness 子命令**

`macos/harness/ShellHarness.swift` 的 `case "family":` 之前插入：

```swift
    case "family-pgid":
      guard args.count >= 2, let pgid = Int32(args[1]) else { exit(64) }
      let psTool = args.count >= 3 ? args[2] : "/bin/ps"
      for pid in PortGuard.familyByGroup(pgid: pgid, psTool: psTool) { print(pid) }
```

- [x] **Step 9: 跑测试确认通过**

Run: `python3 -m pytest tests/test_shell_portguard.py -q`
Expected: PASS

- [x] **Step 10: 写失败测试 —— 退出不再杀同路径的陌生进程**

`tests/test_shell_lifecycle.py` 末尾追加：

```python
def test_owned_sigterm_spares_same_path_stranger(tmp_path):
    """同一可执行路径、不属于本实例进程组的进程必须存活（P1 回归闸）。"""
    import subprocess
    import sys
    import time

    stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        time.sleep(0.3)
        assert stranger.poll() is None
        out = subprocess.run(
            [harness_path(), "family-pgid", str(stranger.pid)], capture_output=True, text=True
        )
        assert str(stranger.pid) in out.stdout
        other = subprocess.run(
            [harness_path(), "family-pgid", "1"], capture_output=True, text=True
        )
        assert str(stranger.pid) not in other.stdout.split()
    finally:
        stranger.kill()
        stranger.wait()
```

- [x] **Step 11: 跑测试确认失败，然后改收割路径**

Run: `python3 -m pytest tests/test_shell_lifecycle.py::test_owned_sigterm_spares_same_path_stranger -q`
Expected: 先 FAIL（`family-pgid` 尚未被 ServerController 使用时此测试其实会过，若已过则直接进入下一步；重点是下面的实现改动）。

`macos/ServerController.swift:108-113` 整段替换：

```swift
    if wasOwned, let leader = killed.first, let pgid = PortGuard.processGroup(of: leader) {
      let stragglers = PortGuard.familyByGroup(pgid: pgid)
      if !stragglers.isEmpty {
        killed.append(contentsOf: PortGuard.reap(pids: stragglers, grace: 2.0))
      }
    }
```

注意：`killed.first` 是我们自己 `kill` 过的子进程 pid；`processGroup(of:)` 必须在子进程退出前取到，所以把取 pgid 的动作提前——在 `if let process = child, process.isRunning {` 块内、`kill(pid, SIGTERM)` 之前插入：

```swift
      ownedGroup = PortGuard.processGroup(of: pid)
```

并在函数顶部 `var killed: [Int32] = []` 旁声明 `var ownedGroup: Int32?`，随后把上面那段改用 `ownedGroup`：

```swift
    if wasOwned, let pgid = ownedGroup {
      let stragglers = PortGuard.familyByGroup(pgid: pgid)
      if !stragglers.isEmpty {
        killed.append(contentsOf: PortGuard.reap(pids: stragglers, grace: 2.0))
      }
    }
```

- [x] **Step 12: 端口收割也校验归属**

同文件 `portFree` 分支替换为：

```swift
    let portFree: Bool
    if wasOwned, let pgid = ownedGroup {
      let ours = Set(PortGuard.familyByGroup(pgid: pgid) + killed)
      let occupants = PortGuard.listeners(onPort: spec.port).filter { ours.contains($0) }
      if !occupants.isEmpty { PortGuard.reap(pids: occupants, grace: 2.0) }
      portFree = PortGuard.listeners(onPort: spec.port).isEmpty
    } else {
      portFree = PortGuard.listeners(onPort: spec.port).isEmpty
    }
```

- [x] **Step 13: 跑全部 shell 测试**

Run: `python3 -m pytest tests/test_shell_portguard.py tests/test_shell_lifecycle.py tests/test_foundation_main.py -q`
Expected: PASS（包含既有的 `test_owned_sigterm_reaps_child_family_and_ports` 与 `test_attached_sigterm_leaves_foreign_service_alive`）

**同时解释掉未拉的线 #1：** 盘问开始前 dist 实例（pid 58196）无故消失、无崩溃报告——本次盘问中隔离探针实例退出时两次杀掉用户 dist 实例的服务，就是同一个路径前缀收割。本任务修好后，把那条线标记为"已由 P1 修复解释"，不需要单独调查。

- [x] **Step 14: 提交**

```bash
git add desk/__main__.py macos/PortGuard.swift macos/ServerController.swift macos/harness/ShellHarness.swift tests/test_foundation_main.py tests/test_shell_portguard.py tests/test_shell_lifecycle.py
git commit -m "fix(shell): reap only our own process group on quit (P1/F10)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 2: 壳被强杀后服务自退（未拉的线 #12）

**缺口原文：** 首运弹窗打开时对壳发 SIGTERM，壳停在 SN 状态不退出而服务继续监听；壳被 `kill -9` 后服务成为孤儿仍占端口。证据 `evidence/q09/`（q09-r2 清理阶段）。

**Files:**
- Modify: `desk/__main__.py`
- Modify: `macos/DeskPaths.swift:22-29`
- Test: `tests/test_foundation_main.py`

**Interfaces:**
- Consumes: Task 1 的 `ensure_own_process_group`
- Produces: 环境变量契约 `LMD_PARENT_PID`

- [x] **Step 1: 写失败测试**

`tests/test_foundation_main.py` 追加：

```python
def test_parent_watchdog_stops_when_parent_disappears():
    """壳消失后服务不许继续占端口（R-shell-04 非正常退出路径）。"""
    import threading
    from desk.__main__ import watch_parent

    stopped = threading.Event()
    watch_parent(parent_pid=-1, interval=0.01, on_gone=stopped.set)
    assert stopped.wait(2.0)
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_foundation_main.py::test_parent_watchdog_stops_when_parent_disappears -q`
Expected: FAIL, `ImportError: cannot import name 'watch_parent'`

- [x] **Step 3: 实现看门狗**

`desk/__main__.py` 加入：

```python
def watch_parent(parent_pid: int, *, interval: float = 3.0, on_gone=None) -> threading.Thread:
    """Exit with the shell: a force-killed parent must not leave the service holding ports."""

    def loop() -> None:
        while True:
            try:
                os.kill(parent_pid, 0)
            except OSError:
                (on_gone or (lambda: os._exit(0)))()
                return
            time.sleep(interval)

    thread = threading.Thread(target=loop, name="parent-watchdog", daemon=True)
    thread.start()
    return thread
```

顶部补 `import threading`、`import time`。在 `main()` 里 `ensure_own_process_group()` 之后加：

```python
    parent = os.environ.get("LMD_PARENT_PID")
    if parent and parent.isdigit():
        watch_parent(int(parent))
```

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_foundation_main.py -q`
Expected: PASS

- [x] **Step 5: 壳传自己的 pid**

`macos/DeskPaths.swift` 的 `embeddedEnvironment(resources:)` 返回字典里加一项：

```swift
      "LMD_PARENT_PID": String(ProcessInfo.processInfo.processIdentifier),
```

- [x] **Step 6: 跑壳契约测试**

Run: `python3 -m pytest tests/test_shell_static.py tests/test_shell_lifecycle.py -q`
Expected: PASS

- [x] **Step 7: 提交**

```bash
git add desk/__main__.py macos/DeskPaths.swift tests/test_foundation_main.py
git commit -m "fix(shell): service exits when its parent shell disappears

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 3: 仲裁者按端口收割也要校验归属（P1 位点 2/11）

**缺口原文：** `desk/arbiter/reaper.py` 的 `reap_port` 按端口杀监听者，与壳的路径前缀收割同属一类（"不校验归属"）。

**Files:**
- Modify: `desk/arbiter/reaper.py`
- Test: `tests/test_arbiter_reaper.py`

**Interfaces:**
- Produces: `reap_port(port, *, owned_pids)`——只杀集合内的 pid

- [x] **Step 1: 写失败测试**

`tests/test_arbiter_reaper.py` 追加（沿用该文件既有的 fake 注入风格；若既有测试用别的注入名，按文件内实际签名调整）：

```python
def test_reap_port_spares_processes_we_do_not_own():
    """端口上的陌生进程不是我们的孩子，不许杀（P1）。"""
    killed = []
    reap_port(
        8767,
        owned_pids={101},
        listeners=lambda port: [101, 202],
        signal_pid=lambda pid, sig: killed.append((pid, sig)),
        alive=lambda pid: False,
    )
    assert {pid for pid, _ in killed} == {101}
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_arbiter_reaper.py -q`
Expected: FAIL（`reap_port` 不接受 `owned_pids`）

- [x] **Step 3: 实现**

在 `desk/arbiter/reaper.py` 的 `reap_port` 签名里加关键字参数 `owned_pids: set[int] | None = None`，并在取到监听者列表之后、发信号之前插入：

```python
    if owned_pids is not None:
        pids = [pid for pid in pids if pid in owned_pids]
```

在调用点（`desk/llm/service.py` 里收 8767 的地方）传入本进程 spawn 过的 pid 集合；若该处目前无记录，用 `{self._proc.pid}`（已存在的子进程句柄）。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_arbiter_reaper.py tests/llm -q`
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add desk/arbiter/reaper.py desk/llm/service.py tests/test_arbiter_reaper.py
git commit -m "fix(arbiter): port reaping verifies process ownership (P1)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 4: 续传不再从零重下且不虚报进度（J18 high）

**缺口原文：** 取消于 42.08% 后点"续传"：磁盘上新增三个同分片、不同 hash 后缀的 `.incomplete` 从 0 字节长起，旧的三个一字节未动；面板百分比却从 42% 继续涨到 49%——`verify.py:_in_flight_bytes` 把陈旧 `.incomplete` 也算进度。证据 `evidence/q18/`。

**Files:**
- Modify: `desk/resources/verify.py:39-86`
- Modify: `desk/resources/downloader.py:53-81,191-200`
- Modify: `desk/resources/service.py`
- Test: `tests/test_resources_verify.py`, `tests/test_resources_downloader.py`

**Interfaces:**
- Produces: `verify_tree(entry, manifest, models_root, *, active_since: float | None = None)`；`ModelStatus.stale_bytes: int`；`Downloader._purge_incomplete()` 在新一次 attempt 开始前调用

- [x] **Step 1: 写失败测试 —— 陈旧残片不计进度**

`tests/test_resources_verify.py` 追加：

```python
def test_stale_incomplete_is_reported_not_counted(tmp_path):
    """没有下载在跑时，.incomplete 是上次的死数据，不许算成进度（J18）。"""
    entry = ModelEntry(key="m", name="M", relpath="m", hf_repo="o/m", gb=1.0)
    manifest = Manifest(files=(ManifestFile(path="a.bin", size=1000),), total_bytes=1000,
                        source="cached", fetched_at=None)
    model_dir = tmp_path / "m"
    cache = model_dir / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "a.bin.deadbeef.incomplete").write_bytes(b"x" * 400)

    status = verify_tree(entry, manifest, tmp_path, active_since=None)
    assert status.bytes_in_flight == 0
    assert status.stale_bytes == 400
    assert status.percent == 0.0
```

按该测试文件里已有的构造器名调整 `ModelEntry`/`Manifest`/`ManifestFile` 的字段（以文件内既有用例为准）。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_resources_verify.py::test_stale_incomplete_is_reported_not_counted -q`
Expected: FAIL, `TypeError: verify_tree() got an unexpected keyword argument 'active_since'`

- [x] **Step 3: 实现 verify_tree 的 attempt 感知**

`desk/resources/verify.py`：`_in_flight_bytes` 改为按时间戳分桶：

```python
def _incomplete_bytes(model_dir: Path, active_since: float | None) -> tuple[int, int]:
    """Split hf's .incomplete blobs into (this attempt's in-flight, previous attempts' stale)."""
    cache = model_dir / ".cache" / "huggingface" / "download"
    fresh = stale = 0
    try:
        for path in cache.rglob("*.incomplete"):
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            if active_since is not None and stat.st_mtime + 1 >= active_since:
                fresh += stat.st_size
            else:
                stale += stat.st_size
    except OSError:
        return 0, 0
    return fresh, stale
```

`verify_tree` 签名加 `*, active_since: float | None = None`，并把中段替换为：

```python
    fresh, stale = _incomplete_bytes(model_dir, active_since)
    in_flight = 0 if not gaps else min(fresh, max(expected_total - local_total, 0))
    counted = local_total + in_flight
```

`ModelStatus` 增加字段 `stale_bytes: int = 0`，在 `verify_tree` 的返回里传 `stale_bytes=stale`，`unknown_status` 里传 `stale_bytes=0`，`to_json` 里带上该键。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_resources_verify.py -q`
Expected: PASS

- [x] **Step 5: 服务层把"是否正在下载"传进去**

`desk/resources/service.py` 里所有调用 `verify_tree(...)` 的地方，传入当前 attempt 的墙钟：

```python
        progress = self._downloader.progress()
        active_since = self._downloader.attempt_wall if (
            progress.state == "running" and progress.key == entry.key
        ) else None
        status = verify_tree(entry, manifest, Path(roots.models_root), active_since=active_since)
```

在 `Downloader` 上暴露只读属性：

```python
    @property
    def attempt_wall(self) -> float:
        with self._lock:
            return self._attempt_wall
```

- [x] **Step 6: 写失败测试 —— 新 attempt 开始前清掉不可续的残片**

`tests/test_resources_downloader.py` 追加：

```python
def test_start_purges_unresumable_leftovers(tmp_path, downloader_factory):
    """hf 换新临时文件名重下时，旧残片是纯占盘死数据，必须在新 attempt 前清掉（J18）。"""
    cache = tmp_path / "m" / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    leftover = cache / "a.bin.old.incomplete"
    leftover.write_bytes(b"x" * 4096)

    downloader = downloader_factory(models_root=tmp_path)
    downloader.start("m")

    assert not leftover.exists()
```

`downloader_factory` 用该测试文件已有的 fake executor/manifest 构造方式（照搬文件内既有用例的 fixture 名与参数）。

- [x] **Step 7: 跑测试确认失败**

Run: `python3 -m pytest tests/test_resources_downloader.py::test_start_purges_unresumable_leftovers -q`
Expected: FAIL（文件仍在）

- [x] **Step 8: 实现 —— 起跑前清场并固定 revision**

`desk/resources/downloader.py` 的 `start()` 中，`destination = ...` 之后、`command = [...]` 之前插入：

```python
            self._model = model
            self._purge_incomplete()
            command = [*hf_cmd, "download", model.hf_repo, "--local-dir", str(destination)]
            revision = getattr(manifest, "revision", None) if manifest is not None else None
            if revision:
                command += ["--revision", revision]
```

（把原来那行 `command = [...]` 删掉，避免重复。）`desk/resources/service.py` 里的 `_InjectableDownloader.start` 做同样改动——两处必须一致。

- [x] **Step 9: 跑测试确认通过**

Run: `python3 -m pytest tests/test_resources_downloader.py tests/test_resources_service.py tests/test_resources_http.py -q`
Expected: PASS

- [x] **Step 10: 跑全量 + e2e**

Run: `python3 -m pytest -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [x] **Step 11: 提交**

```bash
git add desk/resources/ tests/test_resources_verify.py tests/test_resources_downloader.py
git commit -m "fix(resources): resume purges dead shards and stops counting them as progress (J18)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 5: 局域网地址不再取 VPN 隧道地址（J8 + J19 medium，一处修两条旅程）

**缺口原文：** 设置面板展示并可复制的 base URL 主机是 `100.64.100.6`——utun8 的 VPN 点对点地址；真正的局域网地址是 `192.168.31.68`。根因 `desk/gateway/service.py:12-21` 用默认路由出口。证据 `evidence/q08/`、`evidence/q19/`。

**Files:**
- Create: `desk/gateway/lan.py`
- Create: `tests/test_gateway_lan.py`
- Modify: `desk/gateway/service.py:12-21,85-105`

**Interfaces:**
- Produces: `lan_candidates(ifconfig_output: str) -> list[str]`、`pick_lan_host(ifconfig_output: str) -> str | None`
- Consumes（B 计划设置面板）：`status()["lan_host"]`、新增 `status()["lan_candidates"]`

- [x] **Step 1: 写失败测试**

新建 `tests/test_gateway_lan.py`：

```python
from desk.gateway.lan import lan_candidates, pick_lan_host

SAMPLE = """lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
utun8: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1350
\tinet 100.64.100.6 --> 100.64.100.5 netmask 0xffffffff
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.168.31.68 netmask 0xffffff00 broadcast 192.168.31.255
bridge100: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 10.37.129.2 netmask 0xffffff00 broadcast 10.37.129.255
"""


def test_tunnel_and_loopback_are_never_offered():
    assert "100.64.100.6" not in lan_candidates(SAMPLE)
    assert "127.0.0.1" not in lan_candidates(SAMPLE)


def test_real_lan_interface_wins():
    assert pick_lan_host(SAMPLE) == "192.168.31.68"


def test_candidates_keep_every_usable_address_in_preference_order():
    assert lan_candidates(SAMPLE) == ["192.168.31.68", "10.37.129.2"]


def test_no_usable_interface_returns_none():
    assert pick_lan_host("lo0:\n\tinet 127.0.0.1 netmask 0xff000000\n") is None
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_gateway_lan.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'desk.gateway.lan'`

- [x] **Step 3: 实现**

新建 `desk/gateway/lan.py`：

```python
"""Pick a LAN address other devices can actually reach.

The default-route probe (connect() to a far address) returns the tunnel address on any
machine with a VPN up — a 100.64.0.0/10 CGNAT address that nothing on the LAN can reach
(cross-exam 2026-09-08, J8/J19). Enumerate the real interfaces instead.
"""
from __future__ import annotations

import re
import subprocess

_IFACE = re.compile(r"^(?P<name>[a-z0-9]+):", re.MULTILINE)
_INET = re.compile(r"^\s+inet (?P<addr>\d+\.\d+\.\d+\.\d+)(?P<rest>[^\n]*)", re.MULTILINE)
_SKIP_PREFIXES = ("lo", "utun", "ppp", "ipsec", "gif", "stf", "awdl", "llw")


def _private_rank(addr: str) -> int | None:
    """Lower is better; None means unusable from another device on the LAN."""
    octets = [int(part) for part in addr.split(".")]
    if octets[0] == 127 or (octets[0] == 169 and octets[1] == 254):
        return None
    if octets[0] == 100 and 64 <= octets[1] <= 127:  # CGNAT: VPN tunnels live here
        return None
    if octets[0] == 192 and octets[1] == 168:
        return 0
    if octets[0] == 10:
        return 1
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return 2
    return 3


def lan_candidates(ifconfig_output: str) -> list[str]:
    """Every reachable IPv4 address on a non-tunnel interface, best first."""
    found: list[tuple[int, int, str]] = []
    blocks = list(_IFACE.finditer(ifconfig_output))
    for index, match in enumerate(blocks):
        name = match.group("name")
        if name.startswith(_SKIP_PREFIXES):
            continue
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(ifconfig_output)
        for inet in _INET.finditer(ifconfig_output[match.end():end]):
            if "-->" in inet.group("rest"):  # point-to-point link, not a LAN
                continue
            addr = inet.group("addr")
            rank = _private_rank(addr)
            if rank is not None:
                found.append((rank, len(found), addr))
    found.sort()
    seen, ordered = set(), []
    for _, _, addr in found:
        if addr not in seen:
            seen.add(addr)
            ordered.append(addr)
    return ordered


def pick_lan_host(ifconfig_output: str) -> str | None:
    candidates = lan_candidates(ifconfig_output)
    return candidates[0] if candidates else None


def read_ifconfig(run=subprocess.run) -> str:
    try:
        done = run(["/sbin/ifconfig", "-a"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout or ""
```

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_gateway_lan.py -q`
Expected: PASS

- [x] **Step 5: 接进 gateway status**

`desk/gateway/service.py`：删掉 `_lan_host`，改为

```python
from .lan import lan_candidates, pick_lan_host, read_ifconfig


def _lan_host(host: str) -> tuple[str, list[str]]:
    """Resolve a reachable LAN address for a wildcard bind, else echo the explicit host."""
    if host != "0.0.0.0":
        return host, [host]
    output = read_ifconfig()
    candidates = lan_candidates(output)
    return (pick_lan_host(output) or "127.0.0.1"), candidates
```

`status()` 内相应改为：

```python
        lan_host, candidates = _lan_host(host)
        return {
            ...
            "lan_host": lan_host,
            "lan_candidates": candidates,
            ...
        }
```

- [x] **Step 6: 跑测试确认通过**

Run: `python3 -m pytest tests/test_gateway_service.py tests/test_gateway_lan.py -q && node --test tests/js/base_url.test.js`
Expected: PASS

- [x] **Step 7: 提交**

```bash
git add desk/gateway/lan.py desk/gateway/service.py tests/test_gateway_lan.py
git commit -m "fix(gateway): advertise a reachable LAN address, never the VPN tunnel (J8/J19)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 6: 网关绑定失败回滚配置并说人话（F12 medium）

**缺口原文：** 不可绑定地址 `10.255.255.1` 被持久化为坏主机，网关整体停掉且不回退到上一次好配置，界面直出 OS 原文 `bind ... [errno 49] Can't assign requested address`。证据 `evidence/q36/`。

**Files:**
- Modify: `desk/gateway/service.py:40-71`
- Test: `tests/test_gateway_service.py`

**Interfaces:**
- Produces: `apply_config()` 在绑定失败时恢复上一次成功的 `(enabled, host, port)` 并回写 config

- [x] **Step 1: 写失败测试**

`tests/test_gateway_service.py` 追加：

```python
def test_failed_bind_rolls_back_to_the_last_good_config():
    """一次误填的主机不许把网关写死成关闭态（F12）。"""
    stored = {"enabled": True, "host": "127.0.0.1", "port": 8770}
    writes = []

    def factory(address, backend):
        if address[0] == "10.255.255.1":
            raise OSError(49, "Can't assign requested address")
        return _FakeServer(address)

    service = GatewayService(object(), lambda: dict(stored), server_factory=factory)
    service.on_rollback = lambda cfg: writes.append(cfg)
    service.start_from_config()

    stored["host"] = "10.255.255.1"
    status = service.apply_config()

    assert status["listening"] is True
    assert status["host"] == "127.0.0.1"
    assert writes == [{"enabled": True, "host": "127.0.0.1", "port": 8770}]
    assert "无法绑定" in status["last_error"]
```

`_FakeServer` 用该文件里已有的假服务器类（照搬既有用例的名字）。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_gateway_service.py::test_failed_bind_rolls_back_to_the_last_good_config -q`
Expected: FAIL（`listening` 为 False、`host` 仍是坏地址）

- [x] **Step 3: 实现**

`desk/gateway/service.py`：`__init__` 里加 `self._last_good: tuple | None = None`、`self.on_rollback = None`。

`start_from_config` 的成功路径末尾（`self._thread.start()` 之后）加：

```python
        self._last_good = self._applied
```

错误路径里把 `self._last_error` 的赋值改为人话优先：

```python
        except OSError as exc:
            self._server = None
            self._last_error = _bind_message(cfg["host"], cfg["port"], exc)
            return
```

文件顶部加：

```python
_BIND_HINTS = {
    48: "该端口已被占用，换一个端口再试",
    49: "本机没有这个地址，请填 0.0.0.0、127.0.0.1 或本机网卡地址",
    13: "该端口需要更高权限，请改用 1024 以上的端口",
}


def _bind_message(host: str, port: int, exc: OSError) -> str:
    hint = _BIND_HINTS.get(exc.errno, "请检查主机与端口")
    detail = exc.strerror or str(exc)
    return f"无法绑定 {host}:{port}——{hint}（系统报告：{detail}）"
```

`apply_config` 改为失败即回滚：

```python
    def apply_config(self) -> dict:
        """Re-read configuration and replace the listener when it has changed."""
        cfg = self._gateway_config()
        wanted = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        listening = self._server is not None
        if wanted == self._applied and listening == wanted[0]:
            return self.status()
        previous, previous_error = self._last_good, self._last_error
        self.stop()
        self.start_from_config()
        if self._server is None and wanted[0] and previous is not None and previous != wanted:
            failure = self._last_error
            enabled, host, port = previous
            restored = {"enabled": enabled, "host": host, "port": port}
            if self.on_rollback is not None:
                self.on_rollback(restored)
            self._applied = previous
            self.start_from_config()
            self._last_error = failure
        return self.status()
```

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_gateway_service.py -q`
Expected: PASS

- [x] **Step 5: 接上回写**

`desk/runtime.py` 组装 `GatewayService` 之后加：

```python
    gateway.on_rollback = lambda cfg: config_mod.update_config(roots, gateway=cfg)
```

（`config_mod` 用该文件里已有的导入名。）

- [x] **Step 6: 跑测试与 e2e**

Run: `python3 -m pytest tests/test_gateway_service.py tests/test_production_runtime.py -q && python3 -m pytest tests/e2e/test_settings_api.py -q`
Expected: PASS

- [x] **Step 7: 提交**

```bash
git add desk/gateway/service.py desk/runtime.py tests/test_gateway_service.py
git commit -m "fix(gateway): roll back a failed bind and explain it in plain Chinese (F12)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 7: 坏配置有恢复入口（J25 medium + 未拉的线 #4）

**缺口原文：** 损坏 config 下服务可起但 `/api/config` 500 `config_corrupt`，坏文件未被覆盖也无备份；界面只剩一行红字（原样透出 Python json 报错），没有重设/修复入口。证据 `evidence/q25/`。

**Files:**
- Modify: `desk/foundation/config.py:62-78`
- Modify: `desk/foundation/errors.py`
- Modify: `desk/foundation/routes.py`
- Test: `tests/test_foundation_config.py`, `tests/test_foundation_routes.py`

**Interfaces:**
- Produces: `ConfigCorruptError.payload` 带 `backup_hint`；`POST /api/config/reset` → `{"backup": "<路径>", "needs_setup": true}`

- [x] **Step 1: 写失败测试**

`tests/test_foundation_config.py` 追加：

```python
def test_reset_backs_up_the_broken_file_and_starts_over(tmp_path):
    """坏配置必须可一键重设，且坏文件留一份备份（J25）。"""
    roots = make_roots(tmp_path)
    roots.config_path.write_text("{not json", encoding="utf-8")

    result = reset_config(roots)

    assert Path(result["backup"]).read_text(encoding="utf-8") == "{not json"
    assert result["needs_setup"] is True
    assert read_config(roots).first_run_done is False
```

`make_roots` 用该文件已有的构造 helper。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_foundation_config.py::test_reset_backs_up_the_broken_file_and_starts_over -q`
Expected: FAIL, `NameError: name 'reset_config' is not defined`

- [x] **Step 3: 实现**

`desk/foundation/config.py` 追加：

```python
def reset_config(roots) -> dict:
    """Move a broken config aside and start the first-run flow instead of dead-ending."""
    path = Path(roots.config_path)
    backup = None
    if path.exists():
        backup = path.with_name(f"config.broken-{time.strftime('%Y%m%d-%H%M%S')}.json")
        path.replace(backup)
    return {"backup": str(backup) if backup else None, "needs_setup": True}
```

顶部补 `import time`。同文件 `_load_raw` 抛 `ConfigCorruptError` 的两处，payload 里加恢复提示：

```python
        raise ConfigCorruptError(
            "配置文件无法读取（内容不是合法 JSON）；可以点「重新设置」重建一份，坏文件会自动备份。",
            path="config.json",
            parse_error=str(exc),
            recoverable=True,
        )
```

`desk/foundation/errors.py` 的 `ConfigCorruptError.__init__` 接受并透传 `recoverable`。

- [x] **Step 4: 加路由**

`desk/foundation/routes.py` 的 `build_routes()` 里加一条：

```python
    def post_config_reset(req):
        return config_mod.reset_config(roots)
    ...
        ("POST", "/api/config/reset", post_config_reset),
```

`tests/test_foundation_routes.py` 追加断言该路由返回 200 且 body 含 `needs_setup`。

- [x] **Step 5: 跑测试确认通过**

Run: `python3 -m pytest tests/test_foundation_config.py tests/test_foundation_routes.py -q`
Expected: PASS

- [x] **Step 6: 提交**

```bash
git add desk/foundation/ tests/test_foundation_config.py tests/test_foundation_routes.py
git commit -m "feat(foundation): recover from a corrupt config instead of dead-ending (J25)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 7b: 「重新设置模型目录」需要二次确认（未拉的线 #3）

**缺口原文：** 「重新设置模型目录…」无二次确认即把台面切回首运（`needs_setup` 持久化），误点一次就离开主界面。证据 `evidence/q26/q26-03-reconfigure-clicked.png`。

**Files:**
- Modify: `desk/static/js/panes/settings.js`
- Test: `tests/js/settings_pane.test.js`

**Interfaces:**
- Consumes: `desk/static/js/widgets/confirm.js` 的 `confirmDialog(doc, {title, message, confirmLabel})`（会话删除已在用）

- [ ] **Step 1: 写失败测试**

`tests/js/settings_pane.test.js` 追加：

```js
test("reconfigure asks before dropping the user back into first-run", async () => {
  const asked = [];
  const pane = makeSettings({ confirm: async (_doc, opts) => { asked.push(opts); return false; } });
  await clickReconfigure(pane);
  assert.equal(asked.length, 1);
  assert.ok(asked[0].message.includes("首次运行"));
  assert.equal(pane.calls.filter((c) => c.name === "updateConfig").length, 0);
});
```

`makeSettings` 的 `confirm` 注入口、`clickReconfigure` 按该文件既有写法实现（会话删除的测试里已有同形状的注入）。

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/settings_pane.test.js`
Expected: FAIL（`asked.length` 为 0，配置已被直接改写）

- [ ] **Step 3: 实现**

`settings.js` 的「重新设置模型目录」按钮回调改为：

```js
  const ok = await (ctx.confirm ?? confirmDialog)(root.ownerDocument, {
    title: "重新设置模型目录",
    message: "台面会回到首次运行，重新选择模型目录后才能继续使用。已下载的模型不会被删除。",
    confirmLabel: "回到首次运行",
  });
  if (!ok) return;
```

- [ ] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/settings_pane.test.js && python3 -m pytest tests/e2e/test_settings_api.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/settings.js tests/js/settings_pane.test.js
git commit -m "fix(ui): confirm before sending the desk back to first-run

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 8: 安装脚本说明真实原因并支持 --help（J22 medium + 未拉的线 #2）

**缺口原文：** `--dest` 指向不存在的目录时脚本只打印 usage（退出码 2）而不说明"目标目录不存在"；`--help/-h` 也走 usage 分支；README 未写明两脚本用法。证据 `evidence/q22/`。

**Files:**
- Modify: `scripts/install-app.sh:5-22`
- Modify: `scripts/uninstall-app.sh:13-27`
- Modify: `README.md`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `--help` → 退出码 0；`--dest` 不存在 → stderr 含"目标目录不存在"且退出码 2

- [x] **Step 1: 写失败测试**

`tests/test_packaging.py` 追加：

```python
def test_install_help_exits_zero():
    out = subprocess.run([str(REPO / "scripts" / "install-app.sh"), "--help"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "--dest" in out.stdout


def test_install_names_the_missing_dest(tmp_path):
    missing = tmp_path / "nope"
    out = subprocess.run(
        [str(REPO / "scripts" / "install-app.sh"), "--dest", str(missing)],
        capture_output=True, text=True)
    assert out.returncode == 2
    assert "目标目录不存在" in out.stderr
    assert str(missing) in out.stderr
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_packaging.py -q -k install`
Expected: FAIL（`--help` 返回 2；缺失目录只打 usage）

- [x] **Step 3: 实现**

`scripts/install-app.sh` 的 `usage()` 之后加：

```bash
help() { usage_text; exit 0; }
die() { echo "install-app: $*" >&2; exit 2; }
```

把原 `usage()` 拆成 `usage_text`（只打印用法，含一行 `--dest DIR   安装目标目录（必须已存在），默认 /Applications`）与 `usage() { usage_text >&2; exit 2; }`。

arg loop 里加一条 `--help|-h) help ;;`。

第 22 行的合并校验拆开：

```bash
[[ -d "$APP" ]] || die "应用包不存在：$APP"
[[ -d "$DEST" ]] || die "目标目录不存在：$DEST（请先创建，或用 --dest 指定已存在的目录）"
```

`scripts/uninstall-app.sh` 做同样的 `--help|-h` 与 `die` 处理（对 `--app-path`、`--data-root` 的不存在给出人话，但**不**因不存在而失败——卸载允许目标已消失，只打印 `skip:`）。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_packaging.py -q`
Expected: PASS

- [x] **Step 5: 补 README**

`README.md` 的"### 安装后的实际行为"之前插入：

```markdown
### 安装与卸载

```bash
# 安装（目标目录必须已存在；默认装到 /Applications）
./scripts/install-app.sh --app dist/LocalModelDesk.app

# 卸载（先看要删什么，再真删；模型目录永远保留）
./scripts/uninstall-app.sh --dry-run
./scripts/uninstall-app.sh
```

`--help` 可列出全部参数。卸载默认保留 `~/Library/Application Support/LocalModelDesk` 下的数据；加 `--purge-data` 才会清除（模型目录仍保留）。
```

- [x] **Step 6: 提交**

```bash
git add scripts/install-app.sh scripts/uninstall-app.sh README.md tests/test_packaging.py
git commit -m "fix(scripts): real failure reasons and --help for install/uninstall (J22)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 9: 删除遗留原型 media-gui（F17 medium + 未拉的线 #5）

**缺口原文：** `media-gui/`（server.py 1066 行 + macos/App.swift + 16.7MB desk.log）仍在仓库，绑定 `127.0.0.1:8766`（与新台面同端口）；`verify-app.sh` V7 只检查从不存在的 `media-gui/start.sh`；tests 把 `media-gui/server.py` 列为容忍的遗留 catalog 副本；`.gitignore` 注释仍引用已删的 `initModels.sh`。证据 `evidence/q32/`。

**Files:**
- Delete: `media-gui/`（整目录）
- Modify: `scripts/verify-app.sh:118-123`
- Modify: `tests/test_packaging.py:49-56`
- Modify: `tests/test_resources_invariants.py:1-6,25-26,88-92`
- Modify: `.gitignore:18,29`

- [x] **Step 1: 改测试，让"目录还在"变成失败**

`tests/test_packaging.py` 的 `test_no_legacy_scripts_in_repo` 名单里把 `"media-gui/start.sh"` 换成 `"media-gui"`，并把断言改成同时覆盖文件与目录：

```python
LEGACY_PATHS = ("initModels.sh", "run-h3.sh", "run-music3.py", "unload-llm.sh", "media-gui")


def test_no_legacy_scripts_in_repo():
    for relative in LEGACY_PATHS:
        assert not (REPO / relative).exists(), f"遗留原型仍在仓库：{relative}"
```

`tests/test_resources_invariants.py`：把 `LEGACY = {"initModels.sh", "media-gui/server.py"}` 改成 `LEGACY: set[str] = set()`，并把模块 docstring 改为：

```python
"""R-resources-01 and census A01/A02/A20/A21 repository-wide guards.

`desk/resources/catalog.py` is the single catalog definition. No legacy copy is
tolerated any more (the media-gui prototype was deleted 2026-09-11).
"""
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_packaging.py tests/test_resources_invariants.py -q`
Expected: FAIL, `遗留原型仍在仓库：media-gui`

- [x] **Step 3: 删除目录并修 verify-app 与 .gitignore**

```bash
git rm -r --cached media-gui
rm -rf media-gui
```

`scripts/verify-app.sh:119` 的名单改为：

```bash
for script in initModels.sh run-h3.sh run-music3.py unload-llm.sh media-gui; do
```

并把失败文案改成 `fail "V7 遗留原型仍存在: $SOURCE_ROOT/$script"`。

`.gitignore`：删掉第 18 行 `media-gui/chat-history.json`；第 29 行注释改为 `# Downloaded model trees — 由应用内「资源」面板下载`。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_packaging.py tests/test_resources_invariants.py tests/test_shell_static.py -q`
Expected: PASS

- [x] **Step 5: 跑打包校验**

Run: `./scripts/verify-app.sh --app dist/LocalModelDesk.app`
Expected: `verify-app: OK`

- [x] **Step 6: 提交**

```bash
git add -A
git commit -m "chore: delete the media-gui prototype that squatted port 8766 (F17)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 10: e2e harness 复用生产路由表（F19 medium）

**缺口原文：** 生产 37 条 vs harness 34 条；只在生产的 `GET /api/resources/status/{key}`、`POST /api/outputs/reveal`、`POST /api/outputs/{name}/reveal`、`GET /api/outputs/{name}` 的 Range 分段在 e2e 里测不到；`/api/paths` harness 3 键 vs 生产 19 键（lambda 假造）。证据 `evidence/q33/`。

**Files:**
- Modify: `desk/testing/harness.py:129-207`
- Test: `tests/test_e2e_harness_assembly.py`

**Interfaces:**
- Produces: harness 的路由集合 ⊇ 生产路由集合（除有意排除者，且排除项必须在测试里逐条列名）

- [ ] **Step 1: 写失败测试**

`tests/test_e2e_harness_assembly.py` 追加：

```python
def test_harness_mirrors_every_production_route(tmp_path):
    """harness 少一条路由，e2e 就有一整块测不到（R-e2e-01）。"""
    from desk import runtime
    from desk.testing.harness import launch_test_harness

    with launch_test_harness(tmp_path) as harness:
        harness_routes = {(m, p) for m, p, _ in harness.app._routes}
    production_routes = production_route_table()

    missing = production_routes - harness_routes
    assert missing == set(), f"harness 缺少生产路由：{sorted(missing)}"
```

`production_route_table()` 在同文件里实现为：把 `desk/foundation/routes.py`、`desk/resources/http.py`、`desk/llm/routes.py`、`desk/media/routes.py`、`desk/library/http.py` 的 `build_routes`/`routes` 用假 service 调一遍，收集 `(method, pattern)`，再并上 `desk/runtime.py` 里直接挂的四条（`/api/state`、`/api/memory`、`GET|POST /api/gateway/config`）。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_e2e_harness_assembly.py -q`
Expected: FAIL，列出 `/api/resources/status/{key}`、`/api/outputs/reveal`、`/api/outputs/{name}/reveal` 等缺失项

- [ ] **Step 3: 实现 —— 用 build_routes 取代手抄**

`desk/testing/harness.py` 的 `_mount_routes` 里，把手写的 foundation/resources/llm/library 条目换成各模块的 `build_routes`：

```python
    from desk.foundation import routes as foundation_routes
    from desk.library import http as library_http
    from desk.llm import routes as llm_routes
    from desk.resources import http as resources_http

    table = [
        *foundation_routes.build_routes(roots_provider),
        *resources_http.build_routes(resources),
        *llm_routes.build_routes(llm),
        *build_media_routes(media),
        *library_http.routes(library),
        ("GET", "/api/state", lambda _req: arbiter.state()),
        ("GET", "/api/memory", lambda _req: memory_snapshot()),
        ("GET", "/api/gateway/config", lambda _req: gateway.handle_config_request("GET")),
        ("POST", "/api/gateway/config", lambda req: gateway.handle_config_request("POST", req.body)),
    ]
```

删除 `/api/paths` 的 lambda 假造与 `GET /api/resources/status/`（尾斜杠那条永不可达）。保留 `dispatch_with_static` 的 SSE 特判，但在它上方加一行注释说明它有意抢在路由表之前，并把路由表里同名的 `POST /api/llm/chat/stream` 保留（由 `build_routes` 提供，不再是死代码，因为非浏览器调用会走它）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_e2e_harness_assembly.py tests/test_e2e_fakes.py tests/test_e2e_seed.py -q`
Expected: PASS

- [ ] **Step 5: 新增 e2e 覆盖 reveal 与 Range**

新建 `tests/e2e/test_outputs_range.py`：

```python
"""R-e2e-09：成品要能拖动播放，访达入口要真存在。"""
from desk.testing import launch_test_harness


def test_partial_content_and_reveal(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.get_by_role("button", name="素材库").click()
        page.wait_for_selector("[data-lib-list] li")
        name = page.evaluate(
            "() => document.querySelector('[data-lib-list] [data-output-name]')?.dataset.outputName"
        )
        assert name
        response = page.request.get(f"{harness.base_url}/api/outputs/{name}",
                                    headers={"Range": "bytes=0-0"})
        assert response.status == 206
        assert response.headers["content-range"].startswith("bytes 0-0/")
        assert response.headers["accept-ranges"] == "bytes"
        reveal = page.request.post(f"{harness.base_url}/api/outputs/{name}/reveal")
        assert reveal.status == 200
```

若素材库行没有 `data-output-name`，在 `desk/static/js/panes/library.js` 的 `rowNode` 里给 `li` 加 `(li.dataset ??= {}).outputName = entry.output;`（并在 `tests/js/library_pane.test.js` 补一条断言）。

- [ ] **Step 6: 跑 e2e**

Run: `python3 -m pytest tests/e2e -q`
Expected: PASS（19 passed）

- [ ] **Step 7: 提交**

```bash
git add desk/testing/harness.py desk/static/js/panes/library.js tests/test_e2e_harness_assembly.py tests/e2e/test_outputs_range.py tests/js/library_pane.test.js
git commit -m "test(e2e): harness reuses production route builders; cover reveal and Range (F19)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 11: 内存预检按作业参数估算（F4 low）

**缺口原文：** 两次不同画幅/时长的提交都写"生成约需 103.0 GiB 内存"，数字与参数无关；实测草稿档峰值 27.0 GiB（`evidence/q20/q20-job-poll-01.json` 等三份日志），清晰档 1024×576 才真的因 BudgetExceeded 失败。根因 `desk/media/service.py:100` 用 `catalog.gb`（磁盘体积 102.7 GiB）当预估。

**Files:**
- Create: `desk/media/memory_estimate.py`
- Create: `tests/test_media_memory_estimate.py`
- Modify: `desk/media/service.py:97-113`

**Interfaces:**
- Produces: `estimate_bytes(kind: str, params: dict) -> int`

- [x] **Step 1: 写失败测试**

新建 `tests/test_media_memory_estimate.py`：

```python
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3
DRAFT = {"width": 512, "height": 288, "frames": 49, "steps": 16}
SHARP = {"width": 1024, "height": 576, "frames": 73, "steps": 16}


def test_draft_matches_the_measured_peak():
    """实测 2026-09-08：草稿档 peak 27.0 GiB（evidence/q20、q24、q12 三份日志一致）。"""
    assert 25 * GIB <= estimate_bytes("video", DRAFT) <= 31 * GIB


def test_sharper_preset_estimates_more_than_draft():
    assert estimate_bytes("video", SHARP) > estimate_bytes("video", DRAFT)


def test_estimate_is_monotonic_in_every_dimension():
    base = estimate_bytes("video", DRAFT)
    for field in ("width", "height", "frames"):
        bigger = dict(DRAFT, **{field: DRAFT[field] * 2})
        assert estimate_bytes("video", bigger) > base


def test_music_has_its_own_baseline():
    assert estimate_bytes("music", {"duration": 10}) < 40 * GIB
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_media_memory_estimate.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'desk.media.memory_estimate'`

- [x] **Step 3: 实现**

新建 `desk/media/memory_estimate.py`：

```python
"""Estimate a media job's peak memory from its parameters, not from the model's disk size.

Calibration (cross-exam 2026-09-08, worker logs in
docs/cross-exam/2026-09-08-localmodeldesk/evidence/q20, q24, q12):

  h3 512x288x49 frames, 16 steps -> peak 27.0 GiB (text-encoder stage dominates)
  h3 1024x576x73 frames, 16 steps -> exceeded the worker's own budget while active 21.2 /
                                      peak 33.9 GiB (evidence/q23)

So: a fixed stage cost plus a term that grows with the latent volume. Reporting the
model's 102.7 GiB on-disk size for every job made the warning meaningless (F4).
"""
from __future__ import annotations

GIB = 1024 ** 3

_DRAFT_VOLUME = 512 * 288 * 49

# (fixed stage bytes, bytes added per draft-volume unit above the first)
_VIDEO = (27.0 * GIB, 1.4 * GIB)
_MUSIC_BASE = 27.0 * GIB
_MUSIC_PER_SECOND = 0.05 * GIB


def estimate_bytes(kind: str, params: dict) -> int:
    """Peak resident bytes this job is expected to need."""
    if kind == "music":
        duration = float(params.get("duration") or 10)
        return int(_MUSIC_BASE + _MUSIC_PER_SECOND * duration)
    fixed, per_unit = _VIDEO
    width = float(params.get("width") or 512)
    height = float(params.get("height") or 288)
    frames = float(params.get("frames") or 49)
    volume = (width * height * frames) / _DRAFT_VOLUME
    return int(fixed + per_unit * max(volume - 1.0, 0.0))
```

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_media_memory_estimate.py -q`
Expected: PASS

- [x] **Step 5: 接进服务**

`desk/media/service.py:97-101` 替换：

```python
        from .memory_estimate import estimate_bytes

        catalog_key = "h3" if kind == "video" else "music3"
        catalog = list(self._list_catalog())
        model_root = Path(roots.models_root) / {e.key: e.relpath for e in catalog}[catalog_key]
        estimated = estimate_bytes(kind, params)
```

（`params` 是该方法里已有的作业参数字典；若变量名不同，用实际名字。）

- [x] **Step 6: 跑测试确认通过**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_routes.py -q && node --test tests/js/mem_warn.test.js`
Expected: PASS

- [x] **Step 7: 提交**

```bash
git add desk/media/memory_estimate.py desk/media/service.py tests/test_media_memory_estimate.py
git commit -m "fix(media): estimate memory from job parameters, not model disk size (F4)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 12: 清掉 10 个零调用点契约（F13 low）

**缺口原文：** `GET /api/paths`、`POST /api/llm/chat`、`GET /api/resources/status/{key}`、`api.setRequestTimeout`、`OutputsStore.set_opener`、`LlmService.wait_settled`、`MediaService.on_job_finished`、`ResourceEvents.subscribe_*`、`store.get/subscribe`、`build_app` 全部只有 tests/ 调用点。

**决策（写进代码注释，供后续 census 复核）：** 三个 HTTP 端点保留（它们是对外 API 面，Task 10 之后 harness 也镜像了）；其余七项分两类——`wait_settled`/`on_job_finished`/`set_opener` 是测试专用 seam，保留但标注；`ResourceEvents.subscribe_*`、`store.get/subscribe`、`api.setRequestTimeout`、`build_app` 是真死代码，删除。

**Files:**
- Modify: `desk/resources/events.py`, `desk/static/js/store.js`, `desk/static/js/api.js`, `desk/__main__.py`
- Modify: `desk/llm/service.py`, `desk/media/service.py`, `desk/library/outputs.py`（只加注释）
- Test: `tests/js/store.test.js`, `tests/js/api.test.js`, `tests/test_foundation_main.py`, `tests/test_resources_events.py`

- [x] **Step 1: 先删测试里的调用点，确认红**

把 `tests/js/store.test.js` 里针对 `get`/`subscribe` 的用例删除；`tests/js/api.test.js` 里 `setRequestTimeout` 的三处删除；`tests/test_foundation_main.py:23` 的 `build_app` 用例删除；`tests/test_resources_events.py` 里 `subscribe_*` 的用例删除。

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/test_foundation_main.py tests/test_resources_events.py -q`
Expected: PASS（删掉测试后仍绿，说明这些符号确实没有别的消费者）

- [x] **Step 2: 删实现**

- `desk/static/js/store.js`：删除 `get` 与 `subscribe`，只留 `set` 与内部状态；
- `desk/static/js/api.js:40`：删除 `setRequestTimeout` 及其内部变量（若超时值只此一处使用，改为模块常量）；
- `desk/__main__.py:18-22`：删除 `build_app`；
- `desk/resources/events.py`：删除 `subscribe_progress`/`subscribe_finished`，并把 `emit_*` 的文档注释改为 `"""Fan-out hook: no in-process subscriber today; kept as the seam downloads publish through."""`

- [x] **Step 3: 给保留的测试 seam 标注**

在 `LlmService.wait_settled`、`MediaService.on_job_finished`、`OutputsStore.set_opener` 三处的 docstring 末尾各加一句：

```python
    """... Test seam: production code never calls this (census 2026-09-08, F13)."""
```

- [x] **Step 4: 跑全量**

Run: `python3 -m pytest -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add -A
git commit -m "chore: delete dead contracts, label the remaining test seams (F13)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 13: 包内 __pycache__ 不再破坏签名封条（未拉的线 #6）

**缺口原文：** 任何以包内 python 直接起的进程（无 `PYTHONDONTWRITEBYTECODE=1`）都会向签名包写 `__pycache__`，`codesign --verify` 随即失败。本次盘问就因此误伤过一次（`evidence/q34/`）。

**Files:**
- Modify: `scripts/build-app.sh`
- Modify: `scripts/verify-app.sh`
- Test: `tests/test_packaging.py`

- [x] **Step 1: 写失败测试**

`tests/test_packaging.py` 追加：

```python
def test_verify_app_flags_a_broken_seal(tmp_path):
    """包内多出 .pyc 就等于封条破了，verify 必须报出来而不是让 codesign 裸奔（V8）。"""
    bundle = make_fake_bundle(tmp_path)  # 该文件已有的假包构造器
    intruder = bundle / "Contents" / "Resources" / "desk" / "__pycache__"
    intruder.mkdir(parents=True)
    (intruder / "app.cpython-313.pyc").write_bytes(b"\x00")

    out = subprocess.run([str(REPO / "scripts" / "verify-app.sh"), "--app", str(bundle)],
                         capture_output=True, text=True)
    assert out.returncode == 1
    assert "封条" in out.stdout + out.stderr
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_packaging.py -q -k seal`
Expected: FAIL

- [x] **Step 3: 实现 —— 构建时预编译，校验时查封条**

`scripts/build-app.sh` 在签名步骤之前插入：

```bash
echo "[x/9] precompiling bytecode so a later run cannot write into the signed bundle"
"$RES/python/bin/python3.13" -s -m compileall -q -f "$RES/desk" "$RES/pylibs" >/dev/null
```

`scripts/verify-app.sh` 在 V7 之后追加：

```bash
# V8: 任何运行期写入的 __pycache__ 都会让 codesign 失败——先于用户发现它。
STRAY_PYC="$(find "$APP/Contents/Resources/desk" -name '__pycache__' -newer "$APP/Contents/Info.plist" 2>/dev/null | head -5)"
if [[ -n "$STRAY_PYC" ]]; then
  fail "V8 封条已破：包内出现签名后写入的字节码 $STRAY_PYC"
fi
```

注意 V4 已禁止 `pylibs` 下的 `__pycache__`；V8 补的是 `desk/` 且带"晚于签名"的判据。

- [x] **Step 4: 跑测试与真实校验**

Run: `python3 -m pytest tests/test_packaging.py -q && ./scripts/verify-app.sh --app dist/LocalModelDesk.app`
Expected: PASS / `verify-app: OK`

- [x] **Step 5: 提交**

```bash
git add scripts/build-app.sh scripts/verify-app.sh tests/test_packaging.py
git commit -m "build: precompile bytecode and detect a broken code-signing seal

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 14: 关于面板补版权行、关掉系统标签页（未拉的线 #8）

**缺口原文：** "关于"面板有一行空文本（Info.plist 无 `NSHumanReadableCopyright`）；窗口菜单里出现应用没有的"标签页"系统项。证据 `evidence/q35/`。

**Files:**
- Modify: `scripts/build-app.sh`（Info.plist 写入处）
- Modify: `macos/`（`NSWindow` 创建处，文件名以实际为准，通常是 `AppDelegate.swift` 或 `MainWindow.swift`）
- Test: `tests/test_packaging.py`, `tests/test_shell_window.py`

- [x] **Step 1: 写失败测试**

`tests/test_packaging.py` 的 Info.plist 必备键测试里，把 `NSHumanReadableCopyright` 加进名单。
`tests/test_shell_window.py` 追加一条静态断言：源码里出现 `tabbingMode = .disallowed`。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_packaging.py tests/test_shell_window.py -q`
Expected: FAIL

- [x] **Step 3: 实现**

`scripts/build-app.sh` 写 Info.plist 的地方加一行：

```bash
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string '© 2026 LocalModelDesk'" "$APP/Contents/Info.plist"
```

窗口创建处加：

```swift
    window.tabbingMode = .disallowed
```

- [x] **Step 4: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/test_packaging.py tests/test_shell_window.py -q`
Expected: PASS

```bash
git add scripts/build-app.sh macos/ tests/
git commit -m "fix(shell): copyright line in About, no phantom Tab menu

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 15: 公证与重新出包（未拉的线 #7）

**缺口原文：** 当前 `spctl` 报 Unnotarized Developer ID；分发到其他机器前需 notarytool 公证 + stapler。

**⚠️ 这一步需要用户的 Apple ID 凭据，实现者不要猜测或代填。**

**Files:**
- Modify: `scripts/build-app.sh`（新增可选公证段）
- Modify: `README.md`

- [ ] **Step 1: 加公证段（凭据从环境变量读，缺失就跳过并明说）**

`scripts/build-app.sh` 末尾、verify 之前插入：

```bash
if [[ -n "${LMD_NOTARY_PROFILE:-}" ]]; then
  echo "[9/9] notarizing with keychain profile $LMD_NOTARY_PROFILE"
  DITTO_ZIP="$(mktemp -d)/LocalModelDesk.zip"
  ditto -c -k --keepParent "$APP" "$DITTO_ZIP"
  xcrun notarytool submit "$DITTO_ZIP" --keychain-profile "$LMD_NOTARY_PROFILE" --wait
  xcrun stapler staple "$APP"
  xcrun stapler validate "$APP"
else
  echo "[9/9] skip notarization: set LMD_NOTARY_PROFILE to a 'xcrun notarytool store-credentials' profile name"
fi
```

- [ ] **Step 2: README 写清一次性准备步骤**

在"### 安装与卸载"之后加：

```markdown
### 分发给其他机器（需要 Apple 开发者账号）

一次性准备：

```bash
xcrun notarytool store-credentials LocalModelDesk \
  --apple-id <你的 Apple ID> --team-id <Team ID> --password <App 专用密码>
```

之后出包时带上 `LMD_NOTARY_PROFILE=LocalModelDesk ./scripts/build-app.sh`，脚本会自动提交公证并 staple。不设该变量时只做 Developer ID 签名，本机可用、别的机器会被 Gatekeeper 拦。
```

- [ ] **Step 3: 提交（不执行公证）**

```bash
git add scripts/build-app.sh README.md
git commit -m "build: optional notarization step gated on LMD_NOTARY_PROFILE

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

- [ ] **Step 4: 交回用户**

告诉用户：公证需要他们的 Apple ID/Team ID/App 专用密码，脚本已就绪，跑一次 `store-credentials` 后重新出包即可。不要代跑。

---

## 收尾：整包回归

- [ ] **Step 1: 全量测试**

```bash
python3 -m pytest -q
node --test tests/js/*.test.js
python3 -m pytest tests/e2e -q
```

- [ ] **Step 2: 重新出包并校验**

```bash
./scripts/build-app.sh
./scripts/verify-app.sh --app dist/LocalModelDesk.app
```

- [ ] **Step 3: 手工确认两条最危险的修复**

1. 同时开两个实例（一个从 `dist/`，一个从 scratch 副本），退出其中一个，确认另一个的 `curl http://127.0.0.1:8766/api/state` 仍 200。
2. 在资源面板对最小模型点下载 → 20 秒后取消 → 点续传，确认磁盘上 `.incomplete` 数量不增长、面板百分比不虚涨。
</content>
