# 实施计划：shell —— macOS App 外壳与内嵌服务生命周期

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-shell-spec.md`（R-shell-01 … R-shell-08）
**设计** `docs/superpowers/specs/2026-08-31-shell-design.md`
**决策依据** D-0002（窗口级行为用 `orca computer` + pytest 自动验收；menubar/dock/dialogs 表面留人工）

## 约定（每个任务都遵守）

- T-shell-10/11 的精确 acceptance 由 runner 在 trusted host 的候选接纳阶段执行，以使用 Orca desktop runtime；失败候选不发布。
- T-shell-10 的 pytest 必须通过 `"$MEGASTORM_TEST_PYTHON"` 选择锁定 CPython 3.13，不能依赖宿主 `/bin/sh` 的 `python3` 解析。
- 严格 TDD：先写失败测试 → 跑一次确认失败 → 实现 → 跑通过 → 提交。
- 所有测试使用**随机空闲端口**与 `tmp_path`；绝不触碰真实 8766/8767、绝不触碰
  `llms/`、`minimax-h3/`、`minimax-music3/`、`outputs/` 与任何权重目录。
- 所有命令从仓库根 `/Users/aa/LocalModelDesk` 运行；acceptance_cmd 用绝对路径，不依赖 cwd。
- Swift 侧无第三方依赖；Python 侧只用标准库 + pytest（已装 9.0.3）。
- 错误就是错误：任何失败路径不伪造成功、不静默回退。
- git push 不在授权范围内；只做本地 commit。

## 需求 → 任务覆盖

| 需求 | 自动验收 | 人工（reality gate） |
|---|---|---|
| R-shell-01 | T-05 静态断言（大小写敏感 grep）+ attach-only 机制 | — |
| R-shell-02 | T-01 menuTitle 表驱动 + T-07 机制断言（NSStatusItem 创建） | T-11 菜单栏外观 |
| R-shell-03 | T-06/T-09 静态断言 + T-10 orca Cmd+W | T-11 菜单「打开窗口」唤回 |
| R-shell-04 | T-04 harness 收割（含全家收割）+ T-09 信号处理 + T-10 orca Cmd+Q | — |
| R-shell-05 | T-09 静态断言（setActivationPolicy(.regular)、无 LSUIElement） | T-11 Dock 图标外观 |
| R-shell-06 | T-05/T-09 静态断言（无 LaunchAgents/SMAppService/登录项） | — |
| R-shell-07 | T-08 静态断言（NSOpenPanel 参数、三分支编排） | T-11 NSOpenPanel 真实交互 |
| R-shell-08 | T-06 错误页机制 + T-10 orca 读无障碍树错误文案 | — |

## 文件终态

```
macos/
  main.swift                   # 入口 + SIGTERM/SIGINT 收割（T-09）
  AppDelegate.swift            # 生命周期编排（T-09）
  DeskPaths.swift              # Swift 侧唯一路径/端口常量点（T-05）
  DeskAPI.swift                # 唯一 HTTP 客户端，路由字符串单点（T-05）
  ServerController.swift       # spawn/terminate，无 AppKit（T-03/T-04）
  PortGuard.swift              # 端口探测 + TERM→KILL + 全家收割，无 AppKit（T-02）
  ShellStatus.swift            # data:shellStatus + menuTitle 纯映射（T-01）
  StatusItemController.swift   # ui:menuBarItem（T-07）
  StatusPoller.swift           # 3s deskState 轮询（T-07）
  MainWindowController.swift   # ui:mainWindow + 错误页（T-06）
  FirstRunFlow.swift           # R-shell-07 原生首运编排（T-08）
  ModelsDirectoryChooser.swift # api:chooseModelsDirectory（T-08）
  harness/ShellHarness.swift   # headless 测试 CLI，不进 App 产物（T-01…T-04）
scripts/
  shell-lifecycle-test.sh      # 编译 harness（T-01）
  build-shell-app.sh           # 编译整机 App 二进制供窗口级测试（T-10）
tests/
  shell_helpers.py             # 假服务 / 端口工具 / harness 编译缓存（T-01/T-02/T-03）
  test_shell_status.py         # T-01
  test_shell_portguard.py      # T-02
  test_shell_lifecycle.py      # T-03/T-04
  test_shell_static.py         # T-05…T-09 增量生长
  test_shell_window.py         # T-10（orca computer 驱动）
```

注：`swiftc` 为 Swift 6.3.3 工具链，裸 `swiftc` 默认 Swift 5 语言模式；harness 编译不含
AppKit 文件（`main.swift` 顶层代码与 `@main` 不能同编译单元）。

---

## T-shell-01 data:shellStatus：状态模型 + menuTitle 纯映射（harness map-status）

**实现** `data:shellStatus`；**消费** `data:deskState`（arbiter 合同：`holder/media_busy/can_start` 三键，
`holder == null` ⇒ 空闲；`needs_setup` 单独来自 `data:deskConfig`）。

### 1. 失败测试 `tests/test_shell_status.py`

```python
"""R-shell-02 的纯逻辑面：menuTitle 七行文案，表驱动（design §5 表）。"""
import json
import subprocess

import pytest

from shell_helpers import harness_path

HELD_LLM = {"holder": {"kind": "llm", "label": "qwen3-30b", "since": 1.0, "phase": "held"},
            "media_busy": False, "can_start": {}}
HELD_VIDEO = {"holder": {"kind": "video", "label": "h3", "since": 1.0, "phase": "held"},
              "media_busy": True, "can_start": {}}
HELD_MUSIC = {"holder": {"kind": "music", "label": "music3", "since": 1.0, "phase": "held"},
              "media_busy": True, "can_start": {}}
IDLE = {"holder": None, "media_busy": False, "can_start": {}}

CASES = [
    ({"server": "starting", "needs_setup": False, "desk_state": None}, "启动中…"),
    ({"server": "failed", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "stopped", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "owned", "needs_setup": True, "desk_state": IDLE}, "待设置"),
    ({"server": "owned", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "attached", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM}, "已加载 qwen3-30b"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_VIDEO}, "出片中"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_MUSIC}, "出歌中"),
    # deskState 拉取失败但进程还在 ⇒ 状态不可读
    ({"server": "owned", "needs_setup": False, "desk_state": None}, "状态不可读"),
    # shape 不可读（缺 holder 键）⇒ 状态不可读，不冒充空闲
    ({"server": "owned", "needs_setup": False, "desk_state": {"unexpected": True}}, "状态不可读"),
]


@pytest.mark.parametrize("fixture,expected", CASES)
def test_menu_title(fixture, expected):
    proc = subprocess.run([harness_path(), "map-status"], input=json.dumps(fixture),
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
```

### 2. `tests/shell_helpers.py`（首版）

```python
"""shell 测试共享工具。全部使用随机空闲端口与临时目录——绝不触碰真实 8766/8767 与权重目录。"""
import functools
import pathlib
import socket
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


@functools.lru_cache(maxsize=1)
def harness_path() -> str:
    """编译一次 headless harness，整个 pytest 进程内复用。"""
    scratch = tempfile.mkdtemp(prefix="shellharness-")
    proc = subprocess.run([str(ROOT / "scripts" / "shell-lifecycle-test.sh"), scratch],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"harness 编译失败:\n{proc.stderr}"
    return proc.stdout.strip().splitlines()[-1]


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
```

### 3. `scripts/shell-lifecycle-test.sh`

```bash
#!/bin/bash
# 编译 headless harness（无 AppKit），把二进制路径打到 stdout 最后一行。
# 用法: shell-lifecycle-test.sh <scratch-dir>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${1:?usage: shell-lifecycle-test.sh <scratch-dir>}"
mkdir -p "$SCRATCH"
OUT="$SCRATCH/shellharness"
SOURCES=("$ROOT/macos/ShellStatus.swift" "$ROOT/macos/harness/ShellHarness.swift")
# PortGuard/ServerController 落地后自动纳入（T-02/T-03 起恒存在，编译集合确定）。
for extra in PortGuard.swift ServerController.swift; do
  if [ -f "$ROOT/macos/$extra" ]; then SOURCES+=("$ROOT/macos/$extra"); fi
done
xcrun swiftc -O -o "$OUT" "${SOURCES[@]}" 1>&2
echo "$OUT"
```

`chmod +x scripts/shell-lifecycle-test.sh`。

### 4. 跑失败

`python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_status.py`
——编译失败（`macos/ShellStatus.swift` 不存在）即为红。

### 5. 实现 `macos/ShellStatus.swift`

```swift
import Foundation

/// 服务失败原因（错误页文案按此分流，R-shell-08）。
enum ServerFailure: Error, Equatable {
  case noEmbeddedRuntime
  case portConflict(pids: [Int32])
  case healthTimeout(lastError: String)
  case spawnFailed(String)
}

/// 内嵌服务状态。
enum ServerState: Equatable {
  case stopped
  case starting
  case runningOwned(pid: Int32)
  case runningAttached
  case failed(ServerFailure)
}

/// data:deskState 的消费投影（arbiter 合同，design A-4）。
struct DeskStateSnapshot: Equatable {
  var holderKind: String?   // nil ⇒ 空闲
  var holderLabel: String?

  /// 防御式解析：多余字段忽略；缺 holder 键或 holder 形状不对 ⇒ nil（上层显示「状态不可读」）。
  static func parse(_ object: Any) -> DeskStateSnapshot? {
    guard let dict = object as? [String: Any], let holderValue = dict["holder"] else { return nil }
    if holderValue is NSNull {
      return DeskStateSnapshot(holderKind: nil, holderLabel: nil)
    }
    guard let holder = holderValue as? [String: Any], let kind = holder["kind"] as? String else {
      return nil
    }
    return DeskStateSnapshot(holderKind: kind, holderLabel: holder["label"] as? String)
  }
}

/// data:shellStatus —— shell 对外暴露的自身状态模型。
struct ShellStatus {
  var server: ServerState
  var desk: DeskStateSnapshot?   // 最近一次成功拉到的 deskState；拉不到为 nil
  var needsSetup: Bool           // 来自最近一次 api:readConfig（data:deskConfig.needs_setup）
  var lastPollError: String?
}

/// R-shell-02 文案唯一来源（design §5 的七行表）。
func menuTitle(for status: ShellStatus) -> String {
  switch status.server {
  case .starting: return "启动中…"
  case .stopped, .failed: return "服务未运行"
  case .runningOwned, .runningAttached: break
  }
  if status.needsSetup { return "待设置" }
  guard let desk = status.desk else { return "状态不可读" }
  guard let kind = desk.holderKind else { return "空闲" }
  switch kind {
  case "llm": return "已加载 \(desk.holderLabel ?? "?")"
  case "video": return "出片中"
  case "music": return "出歌中"
  default: return "状态不可读"
  }
}
```

### 6. 实现 `macos/harness/ShellHarness.swift`（首版，仅 map-status）

```swift
import Foundation

/// 仅测试脚本编译的 headless CLI，不进 App 产物。
@main
struct ShellHarness {
  static func main() {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let cmd = args.first else {
      FileHandle.standardError.write(Data("usage: shellharness <map-status>\n".utf8))
      exit(64)
    }
    switch cmd {
    case "map-status":
      runMapStatus()
    default:
      FileHandle.standardError.write(Data("unknown subcommand \(cmd)\n".utf8))
      exit(64)
    }
  }

  /// stdin 吃 fixture JSON（server/needs_setup/desk_state 三键），stdout 打 menuTitle。
  static func runMapStatus() {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard let obj = try? JSONSerialization.jsonObject(with: data),
          let fx = obj as? [String: Any] else {
      FileHandle.standardError.write(Data("map-status: bad fixture JSON\n".utf8))
      exit(65)
    }
    let server: ServerState
    switch fx["server"] as? String {
    case "starting": server = .starting
    case "stopped": server = .stopped
    case "failed": server = .failed(.spawnFailed("fixture"))
    case "attached": server = .runningAttached
    default: server = .runningOwned(pid: 1)
    }
    var desk: DeskStateSnapshot? = nil
    if let ds = fx["desk_state"], !(ds is NSNull) {
      desk = DeskStateSnapshot.parse(ds)
    }
    let status = ShellStatus(server: server, desk: desk,
                             needsSetup: fx["needs_setup"] as? Bool ?? false,
                             lastPollError: fx["poll_error"] as? String)
    print(menuTitle(for: status))
  }
}
```

### 7. 跑通过 → 提交 `shell: T-01 data:shellStatus 状态模型与 menuTitle 映射`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_status.py`

---

## T-shell-02 PortGuard：按端口探测/收割 + 按路径全家收割

`unload-llm.sh` 的按端口语义（census A06）在 Swift 侧的对应物；退出收割（A-5）的机制底座。

### 1. 失败测试 `tests/test_shell_portguard.py`

```python
"""PortGuard：listeners/ensure-free/family/reap-family。全部随机端口 + tmp_path。"""
import subprocess

from shell_helpers import (harness_path, free_port, start_script,
                           port_listening, FAKE_DESK_SERVER)


def test_listeners_sees_fake_server():
    port = free_port()
    proc = start_script(FAKE_DESK_SERVER, port)
    try:
        out = subprocess.run([harness_path(), "listeners", str(port)],
                             capture_output=True, text=True, timeout=30)
        assert proc.pid in [int(x) for x in out.stdout.split()]
    finally:
        proc.kill()
        proc.wait()


def test_listeners_empty_on_idle_port():
    out = subprocess.run([harness_path(), "listeners", str(free_port())],
                         capture_output=True, text=True, timeout=30)
    assert out.stdout.strip() == ""


def test_ensure_free_kills_listener():
    port = free_port()
    proc = start_script(FAKE_DESK_SERVER, port)
    try:
        r = subprocess.run([harness_path(), "ensure-free", str(port)], timeout=60)
        assert r.returncode == 0
        proc.wait(timeout=10)                    # 监听者已被 TERM/KILL
        assert not port_listening(port)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_ensure_free_on_idle_port():
    assert subprocess.run([harness_path(), "ensure-free", str(free_port())],
                          timeout=60).returncode == 0


def test_family_and_reap(tmp_path):
    # 模拟「内嵌解释器路径」：路径唯一的假可执行，cmdline 含该路径。
    fake = tmp_path / "python3.13-fake"
    fake.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(300)\n")
    fake.chmod(0o755)
    procs = [subprocess.Popen([str(fake)]) for _ in range(2)]
    try:
        out = subprocess.run([harness_path(), "family", str(fake)],
                             capture_output=True, text=True, timeout=30)
        assert {p.pid for p in procs} <= {int(x) for x in out.stdout.split()}
        r = subprocess.run([harness_path(), "reap-family", str(fake)], timeout=60)
        assert r.returncode == 0
        for p in procs:
            p.wait(timeout=10)
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
                p.wait()
```

### 2. `tests/shell_helpers.py` 增补

```python
import sys
import textwrap
import time

# 假台面服务：/api/state|/api/memory|/api/config 全部 200 JSON；/ 是可读的假 deskShell 页。
FAKE_DESK_SERVER = textwrap.dedent("""\
    import http.server, json, sys
    PAYLOADS = {
        "/api/state": {"holder": None, "media_busy": False, "can_start": {}},
        "/api/memory": {"total_bytes": 137438953472, "used_bytes": 8589934592,
                        "available_bytes": 128849018880, "pressure": "normal",
                        "page_size": 16384, "captured_at": 0.0},
        "/api/config": {"needs_setup": False},
    }
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = b"<!doctype html><meta charset=utf-8><title>fake desk</title><h1>fake desk shell</h1>"
                ctype = "text/html; charset=utf-8"; code = 200
            elif self.path in PAYLOADS:
                body = json.dumps(PAYLOADS[self.path]).encode(); ctype = "application/json"; code = 200
            else:
                body = b'{"error": {"code": "not_found", "message": "no such route"}}'
                ctype = "application/json"; code = 404
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
""")

# 占着端口但不是台面服务（健康检查 500）——PORT_CONFLICT 场景。
FAKE_BAD_LISTENER = textwrap.dedent("""\
    import http.server, sys
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"not a desk"
            self.send_response(500)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
""")


def port_listening(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
        return True
    except OSError:
        return False


def wait_port(port: int, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_listening(port):
            return
        time.sleep(0.05)
    raise RuntimeError(f"port {port} never started listening")


def start_script(source: str, port: int) -> subprocess.Popen:
    proc = subprocess.Popen([sys.executable, "-c", source, str(port)])
    try:
        wait_port(port)
    except RuntimeError:
        proc.kill()
        raise
    return proc


def start_fake_desk(port: int) -> subprocess.Popen:
    return start_script(FAKE_DESK_SERVER, port)
```

（`import socket` 首版已有。）

### 3. 跑失败 → 实现 `macos/PortGuard.swift`

```swift
import Foundation

/// 端口监听探测 + TERM→KILL 收割 + 按可执行路径全家收割。无 AppKit 依赖。
/// 服务活着时 8767 的收割权威是 arbiter 的 api:reapLlmPort；
/// PortGuard 只在退出路径、desk 进程已死之后使用（design A-5）。
enum PortGuard {
  /// lsof -tiTCP:<port> -sTCP:LISTEN —— 与 unload-llm.sh 相同的按端口语义（census A06）。
  static func listeners(onPort port: Int) -> [Int32] {
    parsePids(runCapture("/usr/sbin/lsof", ["-tiTCP:\(port)", "-sTCP:LISTEN"]))
  }

  /// pgrep -f <可执行路径> —— 找出仍在跑该解释器的所有进程（媒体子进程 setsid 起，不随父死）。
  static func family(matching pathPrefix: String) -> [Int32] {
    parsePids(runCapture("/usr/bin/pgrep", ["-f", pathPrefix]))
      .filter { $0 != ProcessInfo.processInfo.processIdentifier }
  }

  /// TERM → 等 grace → 仍活着 KILL → 短暂等待。返回发过信号的 pid 列表。
  @discardableResult
  static func reap(pids: [Int32], grace: TimeInterval) -> [Int32] {
    guard !pids.isEmpty else { return [] }
    for pid in pids { kill(pid, SIGTERM) }
    let deadline = Date().addingTimeInterval(grace)
    while Date() < deadline && pids.contains(where: { kill($0, 0) == 0 }) {
      usleep(100_000)
    }
    for pid in pids where kill(pid, 0) == 0 { kill(pid, SIGKILL) }
    usleep(200_000)
    return pids
  }

  /// 确保端口无监听：对监听者 TERM→KILL→复查。true = 已确认无监听。
  static func ensureFree(port: Int, grace: TimeInterval = 2.0) -> Bool {
    let pids = listeners(onPort: port)
    if pids.isEmpty { return true }
    reap(pids: pids, grace: grace)
    return listeners(onPort: port).isEmpty
  }

  private static func parsePids(_ text: String) -> [Int32] {
    text.split(whereSeparator: \.isNewline)
      .compactMap { Int32($0.trimmingCharacters(in: .whitespaces)) }
  }

  private static func runCapture(_ tool: String, _ args: [String]) -> String {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: tool)
    p.arguments = args
    let pipe = Pipe()
    p.standardOutput = pipe
    p.standardError = FileHandle.nullDevice
    do { try p.run() } catch { return "" }
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    p.waitUntilExit()
    return String(data: data, encoding: .utf8) ?? ""
  }
}
```

### 4. harness 增补子命令（`macos/harness/ShellHarness.swift` 的 switch 加四个 case）

```swift
    case "listeners":
      guard args.count >= 2, let port = Int(args[1]) else { exit(64) }
      for pid in PortGuard.listeners(onPort: port) { print(pid) }
    case "ensure-free":
      guard args.count >= 2, let port = Int(args[1]) else { exit(64) }
      exit(PortGuard.ensureFree(port: port) ? 0 : 3)
    case "family":
      guard args.count >= 2 else { exit(64) }
      for pid in PortGuard.family(matching: args[1]) { print(pid) }
    case "reap-family":
      guard args.count >= 2 else { exit(64) }
      PortGuard.reap(pids: PortGuard.family(matching: args[1]), grace: 2.0)
      exit(PortGuard.family(matching: args[1]).isEmpty ? 0 : 3)
```

### 5. 跑通过 → 提交 `shell: T-02 PortGuard 按端口/按路径收割`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_portguard.py`

---

## T-shell-03 api:spawnEmbeddedServer：spawn / attach / 失败分类

design §1 spawn 流程四步：健康 200+JSON ⇒ attach；端口被占但不健康 ⇒ portConflict（**绝不杀**）；
端口空闲无 launch ⇒ noEmbeddedRuntime；否则 spawn + 0.2s 健康轮询直到超时。

### 1. 失败测试 `tests/test_shell_lifecycle.py`（首版：spawn 面）

```python
"""ServerController 生命周期：spawn/attach/失败分类（T-03）与终止收割（T-04）。"""
import json
import os
import signal
import subprocess

import pytest

from shell_helpers import (harness_path, free_port, start_script, start_fake_desk,
                           port_listening, FAKE_BAD_LISTENER, FAKE_DESK_SERVER)


def write_launcher(tmp_path, name="fake-desk-launcher"):
    """把假台面服务落成可执行文件（launcher 形态，argv[1] = 端口）。"""
    path = tmp_path / name
    path.write_text("#!/usr/bin/env python3\n" + FAKE_DESK_SERVER)
    path.chmod(0o755)
    return path


def probe(*extra, timeout=60):
    return subprocess.run([harness_path(), "spawn-probe", *extra],
                          capture_output=True, text=True, timeout=timeout)


def test_attach_to_existing_service():
    port = free_port()
    fake = start_fake_desk(port)
    try:
        r = probe("--port", str(port))
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "ATTACHED"
        assert fake.poll() is None          # attach 不动现役服务
    finally:
        fake.kill()
        fake.wait()


def test_port_conflict_never_kills_stranger():
    port = free_port()
    stranger = start_script(FAKE_BAD_LISTENER, port)
    try:
        r = probe("--port", str(port))
        assert r.returncode == 1
        assert r.stdout.startswith("PORT_CONFLICT")
        assert stranger.poll() is None      # 不是我们的服务，绝不杀
        assert port_listening(port)
    finally:
        stranger.kill()
        stranger.wait()


def test_no_runtime_without_launcher():
    r = probe("--port", str(free_port()))
    assert r.returncode == 1
    assert r.stdout.strip() == "NO_RUNTIME"


def test_health_timeout_terminates_child(tmp_path):
    marker = "987654321"                     # 独一无二的 sleep 参数，pgrep 不会误伤
    r = probe("--port", str(free_port()),
              "--launcher", "/bin/sleep", "--launcher-arg", marker,
              "--log", str(tmp_path / "server.log"), "--spawn-timeout", "2")
    assert r.returncode == 1
    assert r.stdout.startswith("HEALTH_TIMEOUT")
    left = subprocess.run(["pgrep", "-f", f"sleep {marker}"], capture_output=True, text=True)
    assert left.stdout.strip() == ""        # 超时后子进程已被终止


def test_spawn_writes_log(tmp_path):
    log = tmp_path / "logs" / "server.log"  # 目录不存在，spawn 要自己建
    r = probe("--port", str(free_port()),
              "--launcher", "/bin/sleep", "--launcher-arg", "123456789",
              "--log", str(log), "--spawn-timeout", "1")
    assert r.returncode == 1
    assert log.exists()
```

### 2. 跑失败 → 实现 `macos/ServerController.swift`

```swift
import Foundation

/// packaging §1.3 契约的 Swift 形状。
struct ServerLaunchCommand {
  var executableURL: URL             // App 内 = <Resources>/python/bin/python3.13
  var arguments: [String]            // App 内 = ["-s", "-m", "desk"]
  var environment: [String: String]  // App 内 = PYTHONPATH=<Resources>:<Resources>/pylibs/desk
  var familyPathPrefix: String?      // 退出时按此可执行路径收割全家
}

/// 全部可注入，测试用假值。healthPath 无默认值——路由字符串单点在 DeskAPI（静态断言 5）。
struct ServerLaunchSpec {
  var launch: ServerLaunchCommand?   // nil ⇒ attach-only（bundle.json 缺失的开发模式）
  var port: Int                      // App 内 = DeskPaths.port
  var llmPort: Int?                  // App 内 = 8767；退出时一并验证无监听
  var healthPath: String
  var logFileURL: URL                // 子进程 stdout/stderr 落盘处
  var spawnTimeout: TimeInterval = 15
  var termGrace: TimeInterval = 5
}

struct TerminateReport {
  var portFree: Bool
  var llmPortFree: Bool?             // 仅 owned 模式复查；attach 模式为 nil
  var killedPids: [Int32]
}

/// api:spawnEmbeddedServer / api:terminateEmbeddedServer。无 AppKit 依赖，harness 直接驱动。
final class ServerController {
  private let spec: ServerLaunchSpec
  private var child: Process?
  private(set) var state: ServerState = .stopped

  init(spec: ServerLaunchSpec) { self.spec = spec }

  var isChildRunning: Bool { child?.isRunning ?? false }

  /// 同步阻塞（最长 spawnTimeout）；App 侧放后台队列调用，harness 直接调。
  func spawnEmbeddedServer() -> Result<ServerState, ServerFailure> {
    state = .starting
    // 1. 现役服务 ⇒ attach 收编（二次启动 App、或上次被 SIGKILL 留下的服务）。
    if healthCheckOK() {
      state = .runningAttached
      return .success(state)
    }
    // 2. 端口被占但健康检查不过 ⇒ 不是我们的服务，绝不杀。
    let occupants = PortGuard.listeners(onPort: spec.port)
    if !occupants.isEmpty {
      return fail(.portConflict(pids: occupants))
    }
    // 3. 端口空闲：无 launch ⇒ 无内嵌运行时。
    guard let launch = spec.launch else {
      return fail(.noEmbeddedRuntime)
    }
    let p = Process()
    p.executableURL = launch.executableURL
    p.arguments = launch.arguments
    var env = ProcessInfo.processInfo.environment
    for (k, v) in launch.environment { env[k] = v }
    p.environment = env
    do {
      let dir = spec.logFileURL.deletingLastPathComponent()
      try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
      if !FileManager.default.fileExists(atPath: spec.logFileURL.path) {
        FileManager.default.createFile(atPath: spec.logFileURL.path, contents: nil)
      }
      let log = try FileHandle(forWritingTo: spec.logFileURL)
      log.seekToEndOfFile()
      p.standardOutput = log
      p.standardError = log
      try p.run()
    } catch {
      return fail(.spawnFailed(String(describing: error)))
    }
    child = p
    // 4. 0.2s 健康轮询直到 200 或超时。
    let deadline = Date().addingTimeInterval(spec.spawnTimeout)
    while Date() < deadline {
      if healthCheckOK() {
        state = .runningOwned(pid: p.processIdentifier)
        return .success(state)
      }
      if !p.isRunning {
        child = nil
        return fail(.spawnFailed("服务进程在启动期退出；日志见 \(spec.logFileURL.path)"))
      }
      usleep(200_000)
    }
    PortGuard.reap(pids: [p.processIdentifier], grace: 2.0)
    child = nil
    return fail(.healthTimeout(lastError: "\(Int(spec.spawnTimeout))s 内未从 \(spec.healthPath) 拿到 200 JSON"))
  }

  private func fail(_ f: ServerFailure) -> Result<ServerState, ServerFailure> {
    state = .failed(f)
    return .failure(f)
  }

  /// GET :port<healthPath> —— 200 且 body 是 JSON 才算健康。
  private func healthCheckOK() -> Bool {
    guard let url = URL(string: "http://127.0.0.1:\(spec.port)\(spec.healthPath)") else { return false }
    var request = URLRequest(url: url)
    request.timeoutInterval = 1.0
    let sem = DispatchSemaphore(value: 0)
    var ok = false
    URLSession.shared.dataTask(with: request) { data, response, _ in
      if let http = response as? HTTPURLResponse, http.statusCode == 200,
         let data, (try? JSONSerialization.jsonObject(with: data)) != nil {
        ok = true
      }
      sem.signal()
    }.resume()
    sem.wait()
    return ok
  }
}
```

### 3. harness 增补（`spawn-probe` 与共享的 spec 解析）

```swift
    case "spawn-probe":
      runSpawn(Array(args.dropFirst()), probeOnly: true)
```

```swift
  /// 解析 run/spawn-probe 共用的 flags。
  static func parseSpec(_ args: [String]) -> ServerLaunchSpec {
    var port: Int? = nil
    var launcher: String? = nil
    var launcherArgs: [String] = []
    var familyPath: String? = nil
    var llmPort: Int? = nil
    var logPath = NSTemporaryDirectory() + "shellharness-server.log"
    var spawnTimeout: TimeInterval = 15
    var i = 0
    func value() -> String { i += 2; return args[i - 1] }
    while i < args.count {
      switch args[i] {
      case "--port": port = Int(value())
      case "--launcher": launcher = value()
      case "--launcher-arg": launcherArgs.append(value())
      case "--family-path": familyPath = value()
      case "--llm-port": llmPort = Int(value())
      case "--log": logPath = value()
      case "--spawn-timeout": spawnTimeout = TimeInterval(value()) ?? 15
      default:
        FileHandle.standardError.write(Data("unknown flag \(args[i])\n".utf8))
        exit(64)
      }
    }
    guard let port else {
      FileHandle.standardError.write(Data("--port is required\n".utf8))
      exit(64)
    }
    var launch: ServerLaunchCommand? = nil
    if let launcher {
      launch = ServerLaunchCommand(executableURL: URL(fileURLWithPath: launcher),
                                   arguments: launcherArgs, environment: [:],
                                   familyPathPrefix: familyPath)
    }
    return ServerLaunchSpec(launch: launch, port: port, llmPort: llmPort,
                            healthPath: "/api/state",
                            logFileURL: URL(fileURLWithPath: logPath),
                            spawnTimeout: spawnTimeout)
  }

  /// probeOnly：打印 spawn 结果即退出（仅用于失败/attach 场景；owned 场景走 run）。
  static func runSpawn(_ args: [String], probeOnly: Bool) {
    let controller = ServerController(spec: parseSpec(args))
    switch controller.spawnEmbeddedServer() {
    case .failure(let failure):
      switch failure {
      case .noEmbeddedRuntime: print("NO_RUNTIME")
      case .portConflict(let pids):
        print("PORT_CONFLICT \(pids.map(String.init).joined(separator: ","))")
      case .healthTimeout: print("HEALTH_TIMEOUT")
      case .spawnFailed(let why): print("SPAWN_FAILED \(why)")
      }
      fflush(stdout)
      exit(1)
    case .success(.runningAttached):
      print("ATTACHED")
    case .success(.runningOwned(let pid)):
      print("RUNNING \(pid)")
    case .success(let other):
      print("UNEXPECTED \(String(describing: other))")
      fflush(stdout)
      exit(70)
    }
    fflush(stdout)
    if probeOnly { exit(0) }
    waitForSignalThenTerminate(controller)   // T-04 落地
  }
```

（T-03 时 `waitForSignalThenTerminate` 先实现为 `exit(0)` 之外的空等？不——T-03 只注册
`spawn-probe`，`run` 子命令与 `waitForSignalThenTerminate` 留到 T-04 一并加入，
T-03 的 switch 里没有 `"run"` case。）

### 4. 跑通过 → 提交 `shell: T-03 api:spawnEmbeddedServer spawn/attach/失败分类`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_lifecycle.py`

---

## T-shell-04 api:terminateEmbeddedServer：TERM→KILL + 全家收割 + 端口复查

R-shell-04 的机器可证明面；design terminate 流程 4 步 + A-5 裁定（孤儿保证由 shell 规范承担）。

### 1. 失败测试（`tests/test_shell_lifecycle.py` 增补）

```python
FAMILY_LAUNCHER = """\
#!/usr/bin/env python3
# 假「内嵌解释器」：先 setsid 起一个同路径分离孙进程（模拟 media 的 start_new_session=True），
# 再应答健康检查。孙进程不会随父进程死——正是 R-shell-04 要收割的对象。
import http.server, json, subprocess, sys, time
if "--worker" in sys.argv:
    time.sleep(300)
    sys.exit(0)
port = int(sys.argv[1])
subprocess.Popen([sys.executable, sys.argv[0], "--worker"], start_new_session=True)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"holder": None, "media_busy": False, "can_start": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""


def run_harness(*extra):
    return subprocess.Popen([harness_path(), "run", *extra],
                            stdout=subprocess.PIPE, text=True)


def read_line(proc):
    line = proc.stdout.readline().strip()
    assert line, "harness 没有输出状态行"
    return line


def test_owned_sigterm_reaps_child_and_port(tmp_path):
    port = free_port()
    launcher = write_launcher(tmp_path)
    h = run_harness("--port", str(port), "--launcher", str(launcher),
                    "--launcher-arg", str(port), "--log", str(tmp_path / "server.log"))
    try:
        line = read_line(h)
        assert line.startswith("RUNNING "), line
        child_pid = int(line.split()[1])
        assert port_listening(port)
        h.send_signal(signal.SIGTERM)
        assert h.wait(timeout=60) == 0
        report = json.loads(h.stdout.readline())
        assert report["port_free"] is True
        assert child_pid in report["killed_pids"]
        assert not port_listening(port)
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)                    # 子进程消失
    finally:
        if h.poll() is None:
            h.kill()


def test_attached_sigterm_frees_port():
    port = free_port()
    fake = start_fake_desk(port)
    h = run_harness("--port", str(port))
    try:
        assert read_line(h) == "ATTACHED"
        h.send_signal(signal.SIGTERM)
        assert h.wait(timeout=60) == 0
        assert not port_listening(port)              # attach 模式退出也不留监听
        fake.wait(timeout=10)
    finally:
        for p in (h, fake):
            if p.poll() is None:
                p.kill()


def test_family_reap_kills_detached_grandchild(tmp_path):
    port = free_port()
    launcher = tmp_path / "python3.13-embedded"      # 路径唯一 ⇒ 杀伤半径受限
    launcher.write_text(FAMILY_LAUNCHER)
    launcher.chmod(0o755)
    h = run_harness("--port", str(port), "--launcher", str(launcher),
                    "--launcher-arg", str(port), "--family-path", str(launcher),
                    "--log", str(tmp_path / "server.log"))
    try:
        assert read_line(h).startswith("RUNNING ")
        # 孙进程（--worker）已在跑
        workers = subprocess.run(["pgrep", "-f", f"{launcher} --worker"],
                                 capture_output=True, text=True)
        assert workers.stdout.strip() != ""
        h.send_signal(signal.SIGTERM)
        assert h.wait(timeout=60) == 0
        left = subprocess.run(["pgrep", "-f", str(launcher)], capture_output=True, text=True)
        assert left.stdout.strip() == ""             # 全家（含 setsid 孙进程）都没了
        assert not port_listening(port)
    finally:
        if h.poll() is None:
            h.kill()
        subprocess.run(["pkill", "-f", str(launcher)], capture_output=True)
```

### 2. 跑失败 → 实现（`macos/ServerController.swift` 增补 terminate）

```swift
  /// 同步，退出路径专用（R-shell-04）。
  /// 1) 子进程 TERM→termGrace→KILL→收尸；2) owned 模式按内嵌解释器路径收割全家；
  /// 3) ensureFree(port)（attach 模式下不是我们 spawn 的监听者也收）；4) owned 复查 llmPort。
  func terminateEmbeddedServer() -> TerminateReport {
    var wasOwned = false
    if case .runningOwned = state { wasOwned = true }
    var killed: [Int32] = []
    if let p = child, p.isRunning {
      let pid = p.processIdentifier
      kill(pid, SIGTERM)
      let deadline = Date().addingTimeInterval(spec.termGrace)
      while Date() < deadline && p.isRunning { usleep(100_000) }
      if p.isRunning { kill(pid, SIGKILL) }
      p.waitUntilExit()
      killed.append(pid)
    }
    child = nil
    if wasOwned, let prefix = spec.launch?.familyPathPrefix {
      let stragglers = PortGuard.family(matching: prefix)
      if !stragglers.isEmpty {
        killed.append(contentsOf: PortGuard.reap(pids: stragglers, grace: 2.0))
      }
    }
    let portFree = PortGuard.ensureFree(port: spec.port, grace: 2.0)
    var llmPortFree: Bool? = nil
    if wasOwned, let llmPort = spec.llmPort {
      llmPortFree = PortGuard.listeners(onPort: llmPort).isEmpty
    }
    state = .stopped
    return TerminateReport(portFree: portFree, llmPortFree: llmPortFree, killedPids: killed)
  }
```

### 3. harness 增补（`run` 子命令 + 信号等待）

switch 加：

```swift
    case "run":
      runSpawn(Array(args.dropFirst()), probeOnly: false)
```

```swift
  /// 等 SIGTERM/SIGINT → terminate → JSON 报告 → 按报告定退出码（不谎报成功）。
  static func waitForSignalThenTerminate(_ controller: ServerController) -> Never {
    signal(SIGTERM, SIG_IGN)
    signal(SIGINT, SIG_IGN)
    let onSignal: () -> Void = {
      let report = controller.terminateEmbeddedServer()
      var obj: [String: Any] = ["port_free": report.portFree,
                                "killed_pids": report.killedPids.map(Int.init)]
      obj["llm_port_free"] = report.llmPortFree.map { $0 as Any } ?? NSNull()
      if let data = try? JSONSerialization.data(withJSONObject: obj) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
      }
      exit(report.portFree && report.llmPortFree != false ? 0 : 3)
    }
    let sigTerm = DispatchSource.makeSignalSource(signal: SIGTERM)
    let sigInt = DispatchSource.makeSignalSource(signal: SIGINT)
    sigTerm.setEventHandler(handler: onSignal)
    sigInt.setEventHandler(handler: onSignal)
    sigTerm.resume()
    sigInt.resume()
    dispatchMain()
  }
```

`runSpawn` 尾部把 `if probeOnly { exit(0) }` 之后接 `waitForSignalThenTerminate(controller)`。

### 4. 跑通过（全文件，含 T-03 用例回归）→ 提交 `shell: T-04 api:terminateEmbeddedServer 收割与全家清扫`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_lifecycle.py`

---

## T-shell-05 DeskPaths + DeskAPI：常量单点与唯一 HTTP 客户端（静态断言启动）

R-shell-01 的正面（Swift 只出现 bundle 相对路径）+ 静态断言 1/2/5/6 落地。

### 1. 失败测试 `tests/test_shell_static.py`（首版）

```python
"""shell 静态断言：R-shell-01/03/05/06 的机器可证明面 + swiftc 语法门。
本文件随 T-05…T-09 增量生长；每个断言只在对应文件落地的任务里加入。"""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
MACOS = ROOT / "macos"


def app_sources():
    files = sorted(MACOS.glob("*.swift"))
    assert files, "macos/*.swift 不存在"
    return files


def all_sources():
    return app_sources() + sorted((MACOS / "harness").glob("*.swift"))


def read_all(files):
    return {f: f.read_text(encoding="utf-8") for f in files}


# 静态断言 1（R-shell-01，census A10）：大小写敏感——
# DeskPaths 里 "Application Support/LocalModelDesk" 的大写拼写合法，不得放宽为大小写不敏感。
def test_no_checkout_paths():
    for f, text in read_all(all_sources()).items():
        for needle in ("localModelDesk", "media-gui", "homeDirectoryForCurrentUser", "/opt/homebrew"):
            assert needle not in text, f"{f.name} 含被禁字符串 {needle!r}"


# 静态断言 2（R-shell-06）：不注册登录项、不写 LaunchAgent。
def test_no_launch_agent_writes():
    for f, text in read_all(all_sources()).items():
        for needle in ("LaunchAgents", "SMAppService", "LSSharedFileList", "loginItem"):
            assert needle not in text, f"{f.name} 含被禁字符串 {needle!r}"


# 静态断言 5：路由字符串 "/api/" 只出现在 DeskAPI.swift（harness 是测试件，另论）。
def test_routes_only_in_deskapi():
    for f, text in read_all(app_sources()).items():
        if f.name == "DeskAPI.swift":
            continue
        assert '"/api/' not in text, f"{f.name} 内出现路由字符串，应集中在 DeskAPI.swift"


# A-2：路径构造 API 只在 DeskPaths.swift。
def test_path_construction_only_in_deskpaths():
    for f, text in read_all(app_sources()).items():
        if f.name == "DeskPaths.swift":
            continue
        assert "applicationSupportDirectory" not in text, f"{f.name} 内出现用户数据根构造"
        assert "Bundle.main.resourceURL" not in text, f"{f.name} 内出现 bundle 根构造"


def test_deskpaths_declares_frozen_contract():
    text = (MACOS / "DeskPaths.swift").read_text(encoding="utf-8")
    assert "python/bin/python3.13" in text          # packaging §1.3 内嵌解释器
    assert '"-s", "-m", "desk"' in text             # packaging §1.3 参数
    assert "pylibs/desk" in text                    # PYTHONPATH 契约
    assert "bundle.json" in text                    # packaging §1.4 运行时存在性判据
    assert "8766" in text and "8767" in text


# 静态断言 6：swiftc 语法门（几秒内）。
def test_swiftc_parse():
    r = subprocess.run(["xcrun", "swiftc", "-parse"] + [str(f) for f in all_sources()],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
```

### 2. 跑失败 → 实现 `macos/DeskPaths.swift`

```swift
import Foundation

/// Swift 侧唯一允许出现路径/端口常量与路径构造的文件（design A-1/A-2；静态断言把关）。
enum DeskPaths {
  /// 台面端口。默认 8766；窗口级自动化测试用 LMD_SHELL_PORT 注入随机端口——
  /// 测试绝不触碰真实台面（决策 D-0002 的自动验收前提），常量点仍只有这一处。
  static let port: Int =
    ProcessInfo.processInfo.environment["LMD_SHELL_PORT"].flatMap(Int.init) ?? 8766
  static let llmPort: Int = 8767

  static var baseURL: URL { URL(string: "http://127.0.0.1:\(port)")! }

  /// bundle 资源根（App 内 = .app/Contents/Resources）。
  static var resourcesURL: URL? { Bundle.main.resourceURL }

  /// 内嵌运行时存在性判据 = <Resources>/bundle.json（packaging §1.4，与 foundation 共用同一标记）。
  static var bundleMarkerURL: URL? { resourcesURL?.appendingPathComponent("bundle.json") }
  static var embeddedPythonURL: URL? {
    resourcesURL?.appendingPathComponent("python/bin/python3.13")
  }
  /// packaging §1.3 冻结的启动参数与环境（-s：禁用用户 site-packages）。
  static let embeddedServerArguments = ["-s", "-m", "desk"]
  static func embeddedEnvironment(resources: URL) -> [String: String] {
    ["PYTHONPATH": "\(resources.path):\(resources.path)/pylibs/desk"]
  }

  /// 用户数据根：shell 只用于子进程 stdout 落盘（与服务自己的 desk.log 分开，避免双写）。
  static var userDataRoot: URL {
    FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
      .appendingPathComponent("LocalModelDesk")
  }
  static var serverStdoutLogURL: URL {
    userDataRoot.appendingPathComponent("logs/server-stdout.log")
  }

  /// bundle.json 在 ⇒ owned 启动；不在 ⇒ attach-only（开发模式，R-shell-01 在开发态也成立）。
  static func makeLaunchSpec() -> ServerLaunchSpec {
    var launch: ServerLaunchCommand? = nil
    if let marker = bundleMarkerURL, FileManager.default.fileExists(atPath: marker.path),
       let python = embeddedPythonURL, let resources = resourcesURL {
      launch = ServerLaunchCommand(executableURL: python,
                                   arguments: embeddedServerArguments,
                                   environment: embeddedEnvironment(resources: resources),
                                   familyPathPrefix: python.path)
    }
    return ServerLaunchSpec(launch: launch, port: port, llmPort: llmPort,
                            healthPath: DeskAPI.statePath,
                            logFileURL: serverStdoutLogURL)
  }
}
```

### 3. 实现 `macos/DeskAPI.swift`

```swift
import Foundation

struct DeskAPIError: Error {
  let code: String
  let message: String
}

struct ConfigSnapshot {
  var needsSetup: Bool
}

struct MemoryLine {
  var usedBytes: Int64
  var totalBytes: Int64
}

/// 唯一的 HTTP 客户端；全部路由字符串集中在本文件（design A-3，foundation §2.6 路由表）。
/// 响应解析全部防御式：未知字段忽略、缺字段报 bad_shape——不因服务端 shape 演进而崩。
final class DeskAPI {
  static let statePath = "/api/state"          // data:deskState
  static let memoryPath = "/api/memory"        // api:memorySnapshot
  static let configPath = "/api/config"        // api:readConfig
  static let firstRunPath = "/api/first-run"   // api:completeFirstRun
  static let adoptPath = "/api/adopt"          // api:adoptLegacyModels

  let baseURL: URL
  private let session: URLSession

  init(baseURL: URL) {
    self.baseURL = baseURL
    let cfg = URLSessionConfiguration.ephemeral
    cfg.timeoutIntervalForRequest = 5
    self.session = URLSession(configuration: cfg)
  }

  func deskState(completion: @escaping (Result<DeskStateSnapshot, DeskAPIError>) -> Void) {
    request("GET", Self.statePath, body: nil) { result in
      completion(result.flatMap { obj in
        guard let snap = DeskStateSnapshot.parse(obj) else {
          return .failure(DeskAPIError(code: "bad_shape", message: "deskState 形状不可读"))
        }
        return .success(snap)
      })
    }
  }

  func memorySnapshot(completion: @escaping (Result<MemoryLine, DeskAPIError>) -> Void) {
    request("GET", Self.memoryPath, body: nil) { result in
      completion(result.flatMap { obj in
        guard let dict = obj as? [String: Any],
              let total = (dict["total_bytes"] as? NSNumber)?.int64Value,
              let used = (dict["used_bytes"] as? NSNumber)?.int64Value else {
          return .failure(DeskAPIError(code: "bad_shape", message: "memorySnapshot 缺 total/used"))
        }
        return .success(MemoryLine(usedBytes: used, totalBytes: total))
      })
    }
  }

  func readConfig(completion: @escaping (Result<ConfigSnapshot, DeskAPIError>) -> Void) {
    request("GET", Self.configPath, body: nil) { result in
      completion(result.map { obj in
        ConfigSnapshot(needsSetup: ((obj as? [String: Any])?["needs_setup"] as? Bool) ?? false)
      })
    }
  }

  /// body 不带 models_root 时服务端用默认目录（foundation 路由合同）。
  func completeFirstRun(modelsRoot: String?,
                        completion: @escaping (Result<Void, DeskAPIError>) -> Void) {
    var body: [String: Any] = [:]
    if let modelsRoot { body["models_root"] = modelsRoot }
    request("POST", Self.firstRunPath, body: body) { completion($0.map { _ in () }) }
  }

  func adoptLegacyModels(legacyRoot: String, mode: String,
                         completion: @escaping (Result<Void, DeskAPIError>) -> Void) {
    request("POST", Self.adoptPath, body: ["legacy_root": legacyRoot, "mode": mode]) {
      completion($0.map { _ in () })
    }
  }

  private func request(_ method: String, _ path: String, body: [String: Any]?,
                       completion: @escaping (Result<Any, DeskAPIError>) -> Void) {
    guard let url = URL(string: baseURL.absoluteString + path) else {
      completion(.failure(DeskAPIError(code: "bad_url", message: path)))
      return
    }
    var req = URLRequest(url: url)
    req.httpMethod = method
    if let body {
      req.setValue("application/json", forHTTPHeaderField: "Content-Type")
      req.httpBody = try? JSONSerialization.data(withJSONObject: body)
    }
    session.dataTask(with: req) { data, response, error in
      if let error {
        completion(.failure(DeskAPIError(code: "transport", message: error.localizedDescription)))
        return
      }
      guard let http = response as? HTTPURLResponse else {
        completion(.failure(DeskAPIError(code: "transport", message: "无 HTTP 响应")))
        return
      }
      let obj = data.flatMap { try? JSONSerialization.jsonObject(with: $0) }
      guard (200..<300).contains(http.statusCode) else {
        // foundation 错误信封：{"error": {"code", "message", ...}}；解不出则原样报状态码。
        if let envelope = (obj as? [String: Any])?["error"] as? [String: Any],
           let code = envelope["code"] as? String {
          completion(.failure(DeskAPIError(code: code,
                                           message: envelope["message"] as? String ?? code)))
        } else {
          completion(.failure(DeskAPIError(code: "http_\(http.statusCode)",
                                           message: "HTTP \(http.statusCode)")))
        }
        return
      }
      guard let obj else {
        completion(.failure(DeskAPIError(code: "bad_json", message: "响应不是 JSON")))
        return
      }
      completion(.success(obj))
    }.resume()
  }
}
```

### 4. 跑通过 → 提交 `shell: T-05 DeskPaths/DeskAPI 常量与路由单点 + 静态断言`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_static.py`

---

## T-shell-06 ui:mainWindow：WKWebView 主窗口 + 错误页

R-shell-03（关窗只隐藏）+ R-shell-08（错误页是 Swift 内嵌字符串，不依赖服务活着）。

### 1. 失败测试（`tests/test_shell_static.py` 增补）

```python
# ---- T-06 ui:mainWindow ----
def _read(name):
    return (MACOS / name).read_text(encoding="utf-8")


def test_main_window_close_hides_not_quits():
    text = _read("MainWindowController.swift")
    assert "windowShouldClose" in text
    assert "orderOut" in text
    assert "return false" in text


def test_main_window_error_page_mechanism():
    text = _read("MainWindowController.swift")
    assert "loadHTMLString" in text                  # 错误页不依赖服务活着
    assert "shellRetry" in text                      # 唯一的 JS 桥（design A-8）
    assert "didFailProvisionalNavigation" in text
    assert "服务未运行" in text                       # orca 无障碍树可读的固定文案锚点
```

### 2. 跑失败 → 实现 `macos/MainWindowController.swift`

```swift
import AppKit
import WebKit

/// ui:mainWindow —— 承载 ui:deskShell 的 WKWebView 主窗口 + 本地错误页（R-shell-03/08）。
final class MainWindowController: NSObject, NSWindowDelegate, WKNavigationDelegate,
                                  WKScriptMessageHandler {
  private let window: NSWindow
  private let webView: WKWebView
  private let baseURL: URL
  var onRetry: (() -> Void)?

  init(baseURL: URL) {
    self.baseURL = baseURL
    let config = WKWebViewConfiguration()
    webView = WKWebView(frame: .zero, configuration: config)
    window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
                      styleMask: [.titled, .closable, .miniaturizable, .resizable],
                      backing: .buffered, defer: false)
    super.init()
    window.title = "LocalModelDesk"
    window.center()
    window.contentView = webView
    window.isReleasedWhenClosed = false
    window.delegate = self
    webView.navigationDelegate = self
    // 错误页唯一的 JS 桥；不对 ui:deskShell 注入任何东西（design A-8）。
    config.userContentController.add(self, name: "shellRetry")
  }

  func showWindow() {
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
  }

  var isWindowVisible: Bool { window.isVisible }

  /// 加载 ui:deskShell（台面网页根）。
  func loadDeskShell() {
    webView.load(URLRequest(url: baseURL))
  }

  /// R-shell-03：关窗只隐藏，App 与服务继续活。
  func windowShouldClose(_ sender: NSWindow) -> Bool {
    window.orderOut(nil)
    return false
  }

  /// R-shell-08：错误页是内嵌字符串。含原因、日志路径、「重试」。
  func showErrorPage(reason: String, logPath: String) {
    let html = """
    <!doctype html><html><head><meta charset="utf-8"><title>LocalModelDesk</title></head>
    <body style="font-family: -apple-system, sans-serif; padding: 2em; max-width: 40em; margin: auto;">
      <h1>服务未运行</h1>
      <p id="reason">\(Self.escapeHTML(reason))</p>
      <p>日志：<code>\(Self.escapeHTML(logPath))</code></p>
      <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button>
    </body></html>
    """
    webView.loadHTMLString(html, baseURL: nil)
    showWindow()
  }

  func userContentController(_ userContentController: WKUserContentController,
                             didReceive message: WKScriptMessage) {
    if message.name == "shellRetry" { onRetry?() }
  }

  func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!,
               withError error: Error) {
    showErrorPage(reason: "页面加载失败：\(error.localizedDescription)",
                  logPath: DeskPaths.serverStdoutLogURL.path)
  }

  private static func escapeHTML(_ s: String) -> String {
    s.replacingOccurrences(of: "&", with: "&amp;")
      .replacingOccurrences(of: "<", with: "&lt;")
      .replacingOccurrences(of: ">", with: "&gt;")
  }
}
```

### 3. 跑通过 → 提交 `shell: T-06 ui:mainWindow 主窗口与错误页`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_static.py`

---

## T-shell-07 ui:menuBarItem：NSStatusItem + 3s 轮询

R-shell-02。数据只来自 `data:deskState`（3s 轮询）+ 菜单展开时拉 `api:memorySnapshot`
（`data:memorySnapshot` 载荷）。菜单仅四类项（YAGNI）。

### 1. 失败测试（`tests/test_shell_static.py` 增补）

```python
# ---- T-07 ui:menuBarItem ----
def test_status_item_mechanism():
    text = _read("StatusItemController.swift")
    assert "NSStatusBar.system.statusItem" in text   # D-0002：NSStatusItem 创建的机制断言
    assert "menuTitle(for:" in text                  # 文案唯一来源是纯映射函数
    assert "打开窗口" in text
    assert "退出" in text
    assert "menuWillOpen" in text                    # 菜单展开时刷新内存行


def test_status_poller_interval():
    text = _read("StatusPoller.swift")
    assert "3.0" in text                             # 3s 轮询（design A-9：轮询而非 SSE）
    assert "consecutiveFailures" in text             # R-shell-08 的触发计数
```

### 2. 跑失败 → 实现 `macos/StatusPoller.swift`

```swift
import Foundation

/// 每 3s 拉一次 data:deskState（design A-9：轮询而非事件通道）。
final class StatusPoller {
  private let api: DeskAPI
  private var timer: Timer?
  private(set) var consecutiveFailures = 0
  var onUpdate: ((Result<DeskStateSnapshot, DeskAPIError>) -> Void)?

  init(api: DeskAPI) { self.api = api }

  func start(interval: TimeInterval = 3.0) {
    stop()
    let t = Timer(timeInterval: interval, repeats: true) { [weak self] _ in self?.pollOnce() }
    RunLoop.main.add(t, forMode: .common)
    timer = t
    pollOnce()
  }

  func stop() {
    timer?.invalidate()
    timer = nil
  }

  private func pollOnce() {
    api.deskState { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .failure = result {
          self.consecutiveFailures += 1
        } else {
          self.consecutiveFailures = 0
        }
        self.onUpdate?(result)
      }
    }
  }
}
```

### 3. 实现 `macos/StatusItemController.swift`

```swift
import AppKit

/// ui:menuBarItem —— NSStatusItem 实时台面状态（R-shell-02）。
/// 菜单只有四类项：状态详情（禁用）、内存行（禁用）、「打开窗口」、「退出」。
final class StatusItemController: NSObject, NSMenuDelegate {
  private let statusItem: NSStatusItem
  private let api: DeskAPI
  private let detailItem = NSMenuItem(title: "状态：启动中…", action: nil, keyEquivalent: "")
  private let memoryItem = NSMenuItem(title: "内存 —", action: nil, keyEquivalent: "")
  var onOpenWindow: (() -> Void)?
  var onMenuOpened: (() -> Void)?   // AppDelegate 借此在 needsSetup 时重拉 config

  init(api: DeskAPI) {
    self.api = api
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    super.init()
    statusItem.button?.title = "启动中…"
    let menu = NSMenu()
    menu.autoenablesItems = false
    menu.delegate = self
    detailItem.isEnabled = false
    memoryItem.isEnabled = false
    menu.addItem(detailItem)
    menu.addItem(memoryItem)
    menu.addItem(.separator())
    let openItem = NSMenuItem(title: "打开窗口", action: #selector(openWindow), keyEquivalent: "")
    openItem.target = self
    menu.addItem(openItem)
    let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "")
    quitItem.target = self
    menu.addItem(quitItem)
    statusItem.menu = menu
  }

  /// 文案唯一来源是 menuTitle(for:)（R-shell-02，T-01 已表驱动验证）。
  func render(_ status: ShellStatus) {
    let title = menuTitle(for: status)
    statusItem.button?.title = title
    detailItem.title = "状态：\(title)"
  }

  /// 菜单展开时拉 api:memorySnapshot 刷新内存行（data:memorySnapshot 载荷）。
  func menuWillOpen(_ menu: NSMenu) {
    api.memorySnapshot { [weak self] result in
      DispatchQueue.main.async {
        switch result {
        case .success(let line):
          let gib = 1073741824.0
          self?.memoryItem.title = String(format: "内存 已用 %.1f / 共 %.0f GiB",
                                          Double(line.usedBytes) / gib,
                                          Double(line.totalBytes) / gib)
        case .failure:
          self?.memoryItem.title = "内存 不可读"
        }
      }
    }
    onMenuOpened?()
  }

  @objc private func openWindow() { onOpenWindow?() }

  /// 走 NSApp.terminate ⇒ applicationWillTerminate 收割（R-shell-04）。
  @objc private func quit() { NSApp.terminate(nil) }
}
```

### 4. 跑通过 → 提交 `shell: T-07 ui:menuBarItem 状态项与轮询`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_static.py`

---

## T-shell-08 api:chooseModelsDirectory + FirstRunFlow

R-shell-07。App 内首运由 shell 原生驱动；浏览器直访走 ui 的 `ui:firstRunPane`——
两条路径调同一组 foundation API（`/api/first-run`、`/api/adopt`），无第二份逻辑（design A-7）。

### 1. 失败测试（`tests/test_shell_static.py` 增补）

```python
# ---- T-08 api:chooseModelsDirectory + FirstRunFlow ----
def test_chooser_panel_configuration():
    text = _read("ModelsDirectoryChooser.swift")
    assert "NSOpenPanel" in text
    assert "canChooseDirectories = true" in text
    assert "canChooseFiles = false" in text
    assert "canCreateDirectories = true" in text


def test_first_run_three_branches():
    text = _read("FirstRunFlow.swift")
    assert "使用默认目录" in text
    assert "选择其他目录…" in text
    assert "收编既有目录树…" in text
    assert "point" in text and "move" in text        # adopt 两种模式
    assert "completeFirstRun" in text and "adoptLegacyModels" in text
    assert "重选" in text                             # 错误路径可重来，绝不静默回退
```

### 2. 跑失败 → 实现 `macos/ModelsDirectoryChooser.swift`

```swift
import AppKit

/// api:chooseModelsDirectory —— NSOpenPanel 封装。仅 Swift 内 API，不注入网页（design A-7）。
enum ModelsDirectoryChooser {
  static func choose(prompt: String) -> URL? {
    let panel = NSOpenPanel()
    panel.message = prompt
    panel.canChooseDirectories = true
    panel.canChooseFiles = false
    panel.canCreateDirectories = true
    panel.allowsMultipleSelection = false
    panel.prompt = "选择"
    return panel.runModal() == .OK ? panel.url : nil
  }
}
```

### 3. 实现 `macos/FirstRunFlow.swift`

```swift
import AppKit

/// R-shell-07：原生首运编排。只在 api:readConfig 报 needs_setup 时进入。
final class FirstRunFlow {
  private let api: DeskAPI

  init(api: DeskAPI) { self.api = api }

  /// 同步跑完首运（NSAlert runModal 阻塞主线程）。
  /// true = 配置已落地；false = 用户放弃（服务端仍 needs-setup，网页端 ui:firstRunPane 兜底）。
  func run() -> Bool {
    while true {
      let alert = NSAlert()
      alert.messageText = "首次设置：模型放在哪？"
      alert.informativeText = "默认位置是「资源库/Application Support/LocalModelDesk/models」。"
      alert.addButton(withTitle: "使用默认目录")
      alert.addButton(withTitle: "选择其他目录…")
      alert.addButton(withTitle: "收编既有目录树…")
      switch alert.runModal() {
      case .alertFirstButtonReturn:
        // 不带 models_root ⇒ 服务端用默认值（foundation 路由合同）。
        if post({ self.api.completeFirstRun(modelsRoot: nil, completion: $0) }) { return true }
      case .alertSecondButtonReturn:
        guard let dir = ModelsDirectoryChooser.choose(prompt: "选择模型存放目录") else { return false }
        if post({ self.api.completeFirstRun(modelsRoot: dir.path, completion: $0) }) { return true }
      case .alertThirdButtonReturn:
        guard let legacy = ModelsDirectoryChooser.choose(prompt: "选择既有模型目录树的根") else {
          return false
        }
        let modeAlert = NSAlert()
        modeAlert.messageText = "收编方式"
        modeAlert.informativeText = "指向：模型留在原地；移动：搬到默认目录。"
        modeAlert.addButton(withTitle: "指向该目录")
        modeAlert.addButton(withTitle: "移动到默认目录")
        let mode = modeAlert.runModal() == .alertFirstButtonReturn ? "point" : "move"
        if post({ self.api.adoptLegacyModels(legacyRoot: legacy.path, mode: mode, completion: $0) }) {
          return true
        }
      default:
        return false
      }
      // 失败路径：错误已原样展示，循环回到起点（「重选」）。绝不静默回退（R-foundation-03/04 语义）。
    }
  }

  /// 同步等一个 POST；失败时 NSAlert 原样透出服务端错误文案（错误不吞）。
  private func post(_ op: (@escaping (Result<Void, DeskAPIError>) -> Void) -> Void) -> Bool {
    let sem = DispatchSemaphore(value: 0)
    var outcome: Result<Void, DeskAPIError> =
      .failure(DeskAPIError(code: "no_response", message: "服务无响应"))
    op { r in
      outcome = r
      sem.signal()
    }
    sem.wait()
    switch outcome {
    case .success:
      return true
    case .failure(let err):
      let alert = NSAlert()
      alert.messageText = "设置失败"
      alert.informativeText = "\(err.code)：\(err.message)"
      alert.addButton(withTitle: "重选")
      alert.runModal()
      return false
    }
  }
}
```

### 4. 跑通过 → 提交 `shell: T-08 api:chooseModelsDirectory 与原生首运`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_static.py`

---

## T-shell-09 AppDelegate + main.swift：编排、激活策略、信号收割（静态断言收口）

R-shell-03/04/05/06 的编排面；静态断言 3/4 + 全量 typecheck 门在此收口。

### 1. 失败测试（`tests/test_shell_static.py` 增补）

```python
# ---- T-09 AppDelegate + main ----
# 静态断言 3（R-shell-05）。
def test_activation_policy_regular():
    combined = "\n".join(read_all(app_sources()).values())
    assert "setActivationPolicy(.regular)" in combined
    assert "LSUIElement" not in combined
    assert ".accessory" not in combined


# 静态断言 4（R-shell-03 的可静态半面）。
def test_last_window_closed_does_not_terminate():
    text = _read("AppDelegate.swift")
    assert "applicationShouldTerminateAfterLastWindowClosed" in text
    import re
    m = re.search(r"applicationShouldTerminateAfterLastWindowClosed[^{]*\{[^}]*\}", text)
    assert m and "false" in m.group(0)


def test_signal_paths_reap(  ):
    main_text = _read("main.swift")
    assert "SIGTERM" in main_text and "SIGINT" in main_text          # R-shell-04 异常终止路径
    assert "makeSignalSource" in main_text
    app_text = _read("AppDelegate.swift")
    assert "applicationWillTerminate" in app_text
    assert "terminateEmbeddedServer" in app_text
    assert "applicationShouldHandleReopen" in app_text               # Dock 点击唤回
    assert "performClose" in app_text                                # Cmd+W 菜单接线


# 类型门：App 全量 typecheck（harness 由 lifecycle 脚本单独编译成二进制验证）。
def test_swiftc_typecheck_app():
    r = subprocess.run(["xcrun", "swiftc", "-typecheck"] + [str(f) for f in app_sources()],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
```

（`test_signal_paths_reap` 的括号笔误在落地时写成 `def test_signal_paths_reap():`。）

### 2. 跑失败 → 实现 `macos/AppDelegate.swift`

```swift
import AppKit

/// 生命周期编排：启动→健康→首运→加载 UI；退出→收割（design §3 启动编排图）。
final class AppDelegate: NSObject, NSApplicationDelegate {
  private var server: ServerController!
  private var api: DeskAPI!
  private var windowController: MainWindowController!
  private var statusController: StatusItemController!
  private var poller: StatusPoller!
  private var status = ShellStatus(server: .stopped, desk: nil, needsSetup: false,
                                   lastPollError: nil)

  func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.regular)   // R-shell-05：Dock 图标 + 正常激活切换
    buildMainMenu()
    api = DeskAPI(baseURL: DeskPaths.baseURL)
    server = ServerController(spec: DeskPaths.makeLaunchSpec())
    windowController = MainWindowController(baseURL: DeskPaths.baseURL)
    statusController = StatusItemController(api: api)
    poller = StatusPoller(api: api)
    statusController.onOpenWindow = { [weak self] in self?.windowController.showWindow() }
    statusController.onMenuOpened = { [weak self] in
      guard let self, self.status.needsSetup else { return }
      self.refreshConfig()               // 首运完成后文案自动退出「待设置」
    }
    windowController.onRetry = { [weak self] in self?.startServer() }
    poller.onUpdate = { [weak self] result in self?.handlePoll(result) }
    status.server = .starting
    statusController.render(status)
    windowController.showWindow()
    startServer()
  }

  private func startServer() {
    status.server = .starting
    statusController.render(status)
    DispatchQueue.global().async { [weak self] in
      guard let self else { return }
      let result = self.server.spawnEmbeddedServer()
      DispatchQueue.main.async { self.handleSpawn(result) }
    }
  }

  private func handleSpawn(_ result: Result<ServerState, ServerFailure>) {
    switch result {
    case .failure(let failure):
      status.server = .failed(failure)
      statusController.render(status)
      windowController.showErrorPage(reason: Self.describe(failure),
                                     logPath: DeskPaths.serverStdoutLogURL.path)
    case .success(let state):
      status.server = state
      statusController.render(status)
      refreshConfigThenLoad()
    }
  }

  private func refreshConfigThenLoad() {
    api.readConfig { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .success(let cfg) = result, cfg.needsSetup {
          self.status.needsSetup = true
          self.statusController.render(self.status)
          if FirstRunFlow(api: self.api).run() {
            self.refreshConfig()         // 成功后重新 readConfig 确认 first_run_done
          }
          // 用户放弃 ⇒ 仍加载 UI，网页端 ui:firstRunPane 兜底（design A-7）。
        }
        self.windowController.loadDeskShell()
        self.poller.start()
      }
    }
  }

  private func refreshConfig() {
    api.readConfig { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .success(let cfg) = result { self.status.needsSetup = cfg.needsSetup }
        self.statusController.render(self.status)
      }
    }
  }

  private func handlePoll(_ result: Result<DeskStateSnapshot, DeskAPIError>) {
    switch result {
    case .success(let snap):
      status.desk = snap
      status.lastPollError = nil
    case .failure(let err):
      status.desk = nil
      status.lastPollError = err.message
      // R-shell-08：连续 3 次拉不到且子进程已退出 ⇒ 错误说明页，不留空白 WebView。
      if poller.consecutiveFailures >= 3 && !server.isChildRunning {
        status.server = .failed(.spawnFailed("服务已退出"))
        windowController.showErrorPage(
          reason: "台面服务意外退出（连续 \(poller.consecutiveFailures) 次状态拉取失败）。",
          logPath: DeskPaths.serverStdoutLogURL.path)
        poller.stop()
      }
    }
    statusController.render(status)
  }

  /// R-shell-03：关最后一个窗口不退出。
  func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
    return false
  }

  /// 点 Dock 图标 ⇒ 唤回主窗口。
  func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
    if !flag { windowController.showWindow() }
    return true
  }

  /// R-shell-04：Quit 唯一会停服务的路径；收不干净时如实上报，不谎报成功。
  func applicationWillTerminate(_ notification: Notification) {
    reportTerminate(server?.terminateEmbeddedServer())
  }

  /// SIGTERM/SIGINT 异常终止路径（main.swift 接管后调用）。
  func shutdownNow() {
    reportTerminate(server?.terminateEmbeddedServer())
    exit(0)
  }

  private func reportTerminate(_ report: TerminateReport?) {
    guard let report else { return }
    if !report.portFree || report.llmPortFree == false {
      FileHandle.standardError.write(
        Data("shell: terminate incomplete portFree=\(report.portFree) llmPortFree=\(String(describing: report.llmPortFree))\n".utf8))
    }
  }

  /// 最小主菜单：Cmd+Q 退出、Cmd+W 关窗（performClose ⇒ windowShouldClose ⇒ 只隐藏）。
  private func buildMainMenu() {
    let mainMenu = NSMenu()
    let appMenuItem = NSMenuItem()
    let appMenu = NSMenu()
    appMenu.addItem(withTitle: "退出 LocalModelDesk",
                    action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
    appMenuItem.submenu = appMenu
    mainMenu.addItem(appMenuItem)
    let fileMenuItem = NSMenuItem()
    let fileMenu = NSMenu(title: "文件")
    fileMenu.addItem(withTitle: "关闭窗口",
                     action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
    fileMenuItem.submenu = fileMenu
    mainMenu.addItem(fileMenuItem)
    NSApp.mainMenu = mainMenu
  }

  private static func describe(_ f: ServerFailure) -> String {
    switch f {
    case .noEmbeddedRuntime:
      return "未找到内嵌运行时（Resources/bundle.json 缺失）。开发模式请先手动启动 python -m desk。"
    case .portConflict(let pids):
      return "端口 \(DeskPaths.port) 被其他进程占用（pid \(pids.map(String.init).joined(separator: ", "))），不属于台面服务，不会代为终止。"
    case .healthTimeout(let last):
      return "服务启动超时：\(last)"
    case .spawnFailed(let why):
      return "服务启动失败：\(why)"
    }
  }
}
```

### 3. 实现 `macos/main.swift`

```swift
import AppKit

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate

// R-shell-04 异常终止路径：SIGTERM/SIGINT 也走同一收割逻辑，不留孤儿。
signal(SIGTERM, SIG_IGN)
signal(SIGINT, SIG_IGN)
let sigTerm = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
let sigInt = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
for source in [sigTerm, sigInt] {
  source.setEventHandler { delegate.shutdownNow() }
  source.resume()
}

app.run()
```

### 4. 跑通过 → 提交 `shell: T-09 AppDelegate/main 编排与信号收割`

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_static.py`

---

## T-shell-10 窗口级自动验收：orca computer 驱动真 App（决策 D-0002）

R-shell-03（Cmd+W 后进程与端口活着）、R-shell-04（Cmd+Q 后进程消失、端口无监听）、
R-shell-08（杀服务后无障碍树读到错误文案）。App 用 `LMD_SHELL_PORT` 注入随机端口 attach
到假台面服务——**绝不触碰真实 8766**。窗口唤回（菜单栏/Dock 表面）orca 不可达，留 T-11 人工。

### 1. `scripts/build-shell-app.sh`

```bash
#!/bin/bash
# 编译整机 App 二进制（未打包 .app；打包是 packaging 模块的职责）。
# 用法: build-shell-app.sh <out-dir>；stdout 最后一行是二进制路径。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:?usage: build-shell-app.sh <out-dir>}"
mkdir -p "$OUT_DIR"
xcrun swiftc -O -o "$OUT_DIR/LocalModelDeskShell" "$ROOT"/macos/*.swift 1>&2
echo "$OUT_DIR/LocalModelDeskShell"
```

`chmod +x scripts/build-shell-app.sh`。

### 2. 失败测试 `tests/test_shell_window.py`

```python
"""窗口级行为自动验收（决策 D-0002）：orca computer 驱动真 App。
App 以 LMD_SHELL_PORT 注入随机端口、attach 到假台面服务——绝不触碰真实 8766/8767。
窗口唤回需要菜单栏/Dock 表面（orca capabilities 报 false），留 reality-gate runbook。"""
import functools
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

import pytest

from shell_helpers import ROOT, free_port, start_fake_desk, port_listening

ORCA = "orca"


@functools.lru_cache(maxsize=1)
def app_binary() -> str:
    scratch = tempfile.mkdtemp(prefix="shellapp-")
    proc = subprocess.run([str(ROOT / "scripts" / "build-shell-app.sh"), scratch],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"App 编译失败:\n{proc.stderr}"
    return proc.stdout.strip().splitlines()[-1]


def orca_json(*args, timeout=60):
    r = subprocess.run([ORCA, "computer", *args, "--json"],
                       capture_output=True, text=True, timeout=timeout)
    try:
        return r.returncode, json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return r.returncode, {"raw": r.stdout, "stderr": r.stderr}


def tree_text(pid: int) -> str:
    code, obj = orca_json("get-app-state", "--app", f"pid:{pid}", "--no-screenshot")
    if code != 0:
        return ""
    result = obj.get("result", obj)
    snapshot = result.get("snapshot", {}) if isinstance(result, dict) else {}
    return snapshot.get("treeText", "") or ""


def wait_for_window(pid: int, timeout=45) -> str:
    deadline = time.time() + timeout
    tree = ""
    while time.time() < deadline:
        tree = tree_text(pid)
        if tree.strip():
            return tree
        time.sleep(1.5)
    pytest.fail(f"{timeout}s 内没等到 App 窗口的无障碍树（pid {pid}）")


def hotkey(pid: int, chord: str):
    code, obj = orca_json("hotkey", "--app", f"pid:{pid}", "--key", chord, "--no-screenshot")
    assert code == 0, f"orca hotkey 失败: {obj}"


@pytest.fixture()
def shell_app():
    port = free_port()
    fake = start_fake_desk(port)
    env = dict(os.environ, LMD_SHELL_PORT=str(port))
    proc = subprocess.Popen([app_binary()], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ctx = SimpleNamespace(proc=proc, fake=fake, port=port)
    yield ctx
    for p in (proc, fake):
        if p.poll() is None:
            p.kill()
            p.wait()


def test_cmd_w_keeps_app_and_server_alive(shell_app):
    """R-shell-03：关窗不退——进程仍在、端口仍在监听。"""
    wait_for_window(shell_app.proc.pid)
    hotkey(shell_app.proc.pid, "CmdOrCtrl+W")
    time.sleep(3)
    assert shell_app.proc.poll() is None, "Cmd+W 后 App 进程不应退出"
    assert port_listening(shell_app.port), "Cmd+W 后服务必须继续存活"
    assert shell_app.fake.poll() is None


def test_cmd_q_terminates_app_and_service(shell_app):
    """R-shell-04：Quit 杀服务——App 进程消失且端口无监听（attach 模式也不留监听）。"""
    wait_for_window(shell_app.proc.pid)
    hotkey(shell_app.proc.pid, "CmdOrCtrl+Q")
    deadline = time.time() + 30
    while time.time() < deadline and shell_app.proc.poll() is None:
        time.sleep(0.5)
    assert shell_app.proc.poll() is not None, "Cmd+Q 后 App 进程必须退出"
    assert not port_listening(shell_app.port), "退出后台面端口不得再有监听"


def test_server_death_shows_error_text(shell_app):
    """R-shell-08：外部杀掉服务 ⇒ 无障碍树里读到明确错误文案（非空白 WebView）。"""
    wait_for_window(shell_app.proc.pid)
    shell_app.fake.send_signal(signal.SIGKILL)
    shell_app.fake.wait(timeout=10)
    tree = ""
    deadline = time.time() + 40          # 3s 轮询 × 3 次失败 + 渲染余量
    while time.time() < deadline:
        tree = tree_text(shell_app.proc.pid)
        if "服务未运行" in tree or "意外退出" in tree:
            break
        time.sleep(2)
    else:
        pytest.fail(f"40s 内没读到错误说明文案；最后的树：\n{tree[-2000:]}")
    assert shell_app.proc.poll() is None  # App 本身活着，只是如实说明服务死了
```

### 3. 跑失败（App 未编译过则先红）→ 调通 → 提交 `shell: T-10 orca 窗口级行为自动验收`

调试要点：`orca computer capabilities --json` 确认 windows 表面可用；hotkey 是
synthetic input（unverified），断言全部落在**进程/端口/树文本**这些可独立复查的事实上。

- **acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_shell_window.py`
- **resources** `desktop-ui`（独占真实桌面会话，不与其他桌面自动化并行）

---

## T-shell-11 reality gate：菜单栏 / Dock / NSOpenPanel 外观人工验收

`orca computer capabilities` 报 `menubar/dock/dialogs = false`——这些表面**无法自动读取，
不得伪造证据**（决策 D-0002）。机制面已由 T-01/T-07/T-08/T-09 自动覆盖；本任务只验外观与真实交互。

本任务先把下述步骤固化到
`docs/superpowers/runbooks/2026-08-31-shell-visual-runbook.md`；该文件是 agent 可提交的
运行说明，不是验收证据。人工观察写入
`docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/shell-visual.md`，该路径不在任务
artifact contract 内，agent 无权代写。

### 人工验收 runbook（Phase 2 附证据：照片/录屏 + 命令输出）

前置：用 packaging 产出的真 `.app`（或 `scripts/build-shell-app.sh` 的二进制 + 假服务）启动。

1. **R-shell-05 Dock**：启动后 Dock 出现 LocalModelDesk 图标；⌘Tab 能切换到它；
   点 Dock 图标能激活窗口。
2. **R-shell-02 菜单栏外观**：菜单栏出现状态文本项；初始「启动中…」→ 就绪后「空闲」。
   打开菜单：可见状态详情行、内存行（`内存 已用 x.x / 共 y GiB`）、「打开窗口」、「退出」，
   且只有这四类项。
3. **R-shell-02 实时性**：加载一个 LLM / 起一个视频作业，菜单栏 10s 内变为
   「已加载 …」/「出片中」（此步依赖 llm/media 模块就绪；未就绪时用假服务改 `/api/state`
   payload 复核文案，真模型联动留 e2e/集成阶段）。
4. **R-shell-03 窗口唤回**：关窗后窗口消失、菜单栏项仍在、`lsof -iTCP:8766 -sTCP:LISTEN`
   仍有监听；菜单「打开窗口」与点 Dock 图标都能唤回窗口且内容原状。
5. **R-shell-07 NSOpenPanel**：删除（或改名备份）config 触发首运——弹出三按钮 NSAlert；
   「选择其他目录…」确实弹出原生 NSOpenPanel，只能选目录、能新建目录；
   三条路径（默认 / 自选 / 收编-指向）各走一遍成功；错误路径用只读目录验证：
   NSAlert 原样展示服务端错误文案并可「重选」。
6. **R-shell-04 全景**：菜单「退出」后 App 从 Dock 与菜单栏消失，且
   `lsof -iTCP:8766 -sTCP:LISTEN; lsof -iTCP:8767 -sTCP:LISTEN` 双双为空。

通过标准：六条全部亲眼观察吻合；任何一条不符即 shell 模块不算完成，回修后重跑。
通过后在签核文件中单独写一行 `VERDICT: PASS`。

- **acceptance_cmd** 同时检查独立 runbook、非空人工签核及 `VERDICT: PASS`；签核缺席时
  诚实进入 proof-pending，绝不能以计划文档里的静态文字自动变绿。

---

## Census 义务（shell 归属）在本计划中的落点

- **A10（Swift 硬编码 checkout 路径）**：T-05 静态断言 1（大小写敏感 grep）+ DeskPaths 单点
  + attach-only 开发模式（T-03/T-05）。
- **A13（`media-gui/start.sh` 游离启动脚本）**：其职责（起服务、定端口、日志落盘）由
  T-03/T-04 的 ServerController 取代并被 lifecycle 测试证明；文件本体的 `git rm` 按
  packaging §2.7 在 shell 合入之后执行（不在本模块 touched_paths 内）。

## 任务依赖图

```
T-01 ─ T-02 ─ T-03 ─ T-04 ─ T-05 ─ T-06 ─ T-07 ─ T-08 ─ T-09 ─ T-10 ─ T-11(reality gate)
```

线性链：harness 与静态测试文件逐任务生长（touched_paths 重叠），显式串行最稳。
T-11 是叶子，任何任务都不依赖它（reality-gate 规则）。
