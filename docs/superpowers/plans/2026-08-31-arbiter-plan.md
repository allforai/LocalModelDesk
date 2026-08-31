# arbiter 实施计划（TDD）

**日期** 2026-08-31
**模块** `arbiter` —— 「同一时刻只干一件重活」的唯一权威
**spec** `docs/superpowers/specs/2026-08-31-arbiter-spec.md`
**design** `docs/superpowers/specs/2026-08-31-arbiter-design.md`
**覆盖需求** R-arbiter-01 … R-arbiter-07
**消灭的 census 项** A06、A07（按端口收割合并单点）、A09（写死 `ram_gb: 128`）

## 总则

- 每个任务：先写失败测试 → 跑一次确认红 → 实现 → 跑一次确认绿 → commit。
- 包位于 `desk/arbiter/`，纯进程内 Python，不开端口、不 import 兄弟模块。
- 测试位于 `tests/`，全部 `python3 -m pytest` 快速确定性。
- **绝不**触碰 8767 端口、真实权重目录（`llms/`、`minimax-h3/`、`minimax-music3/`）、真实 `outputs/`。
  收割测试用 OS 分配的临时端口 + 测试自起的 `python -c` 子进程。
- 包内**不出现任何内存常量**（A09）、**不出现 8767 字面量**（design Assumption 1：
  `llm_port` 由组装层注入 `desk.llm.DEFAULT_LLM_PORT`）。
- 错误就是错误：内存读不到抛 `MemoryProbeError`；收割未确认端口释放不算成功；无任何假数据回退。

## Reality gate 审查结论

**本计划零 reality-gate 任务。** 依据：

- 互斥/状态机/事件 → 注入假 memory / 假 reaper / 假 clock 的毫秒级单元测试（环境实测 pytest 可用）。
- `api:reapLlmPort` → 测试自起绑定临时端口的真 `python -c` 子进程（不是被测代码 spawn 的），
  收割后以 lsof 复查为准 —— 完全在本机自动可证，不需要真 mlx-lm。
- `api:memorySnapshot` → 真机用例直接对 `sysctl -n hw.memsize` 输出断言（darwin 上必跑）。

不涉及真实推理、真实权重扫描、/Applications 安装或菜单栏外观，故无需人工 runbook。

## 任务 DAG

```
T-arbiter-01 (state.py + 测试引导)
   ├── T-arbiter-02 (memory.py)              ─┐
   ├── T-arbiter-03 (reaper.py)              ─┼─ T-arbiter-04 (core 门面) ─ T-05 (快速拒绝)
   └──────────────────────────────────────────┘        ─ T-06 (竞态) ─ T-07 (canStart) ─ T-08 (导出+全套)
```

（04→05→06→07→08 线性：它们都改 `desk/arbiter/core.py` / `tests/test_arbiter_core.py`。）

---

## T-arbiter-01 纯状态机 `state.py` + 测试引导

**需求** R-arbiter-01/04 的判定表。
**创建** `desk/__init__.py`（空）、`desk/arbiter/__init__.py`、`desk/arbiter/state.py`、
`tests/conftest.py`、`tests/test_arbiter_state.py`

### 1. 测试引导（一次性，供全部 arbiter 测试导入 `desk.*`）

`tests/conftest.py`：

```python
"""Make the repo root importable so tests can `import desk.*` without an install."""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
```

（幂等追加式：若其他模块任务已建同文件，保留其内容，仅确保上述 sys.path 逻辑存在。）

### 2. 失败测试 `tests/test_arbiter_state.py`

```python
"""Transition-table tests for the pure arbiter state machine (R-arbiter-01/04)."""
import pytest

from desk.arbiter.state import (
    Decision, Holder, PHASE_ACQUIRING, PHASE_HELD, plan_acquire,
)


def holder(kind, phase=PHASE_HELD):
    return Holder(kind=kind, label="x", token="tok", since=0.0, phase=phase)


def test_idle_llm_grants():
    assert plan_acquire(None, "llm") == Decision("grant")


@pytest.mark.parametrize("kind", ["video", "music"])
def test_idle_media_grants(kind):
    assert plan_acquire(None, kind) == Decision("grant")


@pytest.mark.parametrize("kind", ["video", "music"])
def test_llm_held_media_evicts_then_grants(kind):
    assert plan_acquire(holder("llm"), kind).action == "evict_then_grant"


def test_llm_held_llm_refused():
    d = plan_acquire(holder("llm"), "llm")
    assert (d.action, d.reason_code) == ("refuse", "llm_already_held")


@pytest.mark.parametrize("held", ["video", "music"])
@pytest.mark.parametrize("kind", ["llm", "video", "music"])
def test_media_held_refuses_everything(held, kind):
    d = plan_acquire(holder(held), kind)
    assert (d.action, d.reason_code) == ("refuse", "media_busy")


@pytest.mark.parametrize("kind", ["llm", "video", "music"])
def test_acquiring_phase_refuses(kind):
    d = plan_acquire(holder("video", phase=PHASE_ACQUIRING), kind)
    assert (d.action, d.reason_code) == ("refuse", "transition_in_progress")


def test_unknown_kind_refused():
    d = plan_acquire(None, "quantum")
    assert (d.action, d.reason_code) == ("refuse", "unknown_kind")


def test_refusals_carry_messages():
    assert plan_acquire(holder("music"), "llm").reason_message
```

红：`python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_state.py`
（`ModuleNotFoundError: desk.arbiter.state`）

### 3. 实现 `desk/arbiter/state.py`

```python
"""Pure state machine for heavy-work mutual exclusion (R-arbiter-01/04).

Zero I/O, zero locks: `plan_acquire` maps (current holder, requested kind)
to a Decision. All concurrency and side effects live in core.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

KINDS = ("llm", "video", "music")
MEDIA_KINDS = ("video", "music")

PHASE_HELD = "held"
PHASE_ACQUIRING = "acquiring"


@dataclass(frozen=True)
class Holder:
    kind: str            # "llm" | "video" | "music"
    label: str           # model key or job id, supplied by the caller
    token: str           # uuid4 hex; only ever returned to the acquirer
    since: float         # epoch seconds
    phase: str           # PHASE_HELD | PHASE_ACQUIRING


@dataclass(frozen=True)
class Decision:
    action: Literal["grant", "evict_then_grant", "refuse"]
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None


def plan_acquire(holder: Optional[Holder], kind: str) -> Decision:
    """Full transition table from the spec. Anything not granted is refused
    with a machine-readable reason_code."""
    if kind not in KINDS:
        return Decision("refuse", "unknown_kind", f"unknown heavy kind: {kind!r}")
    if holder is None:
        return Decision("grant")
    if holder.phase == PHASE_ACQUIRING:
        return Decision("refuse", "transition_in_progress",
                        "a heavy-work transition is in progress; retry shortly")
    if holder.kind in MEDIA_KINDS:
        return Decision("refuse", "media_busy",
                        f"{holder.kind} job {holder.label!r} is running")
    # holder.kind == "llm"
    if kind == "llm":
        return Decision("refuse", "llm_already_held",
                        f"llm {holder.label!r} already holds memory; release it first")
    return Decision("evict_then_grant")
```

`desk/arbiter/__init__.py`（本任务的最小导出；T-arbiter-08 定稿）：

```python
from .state import (
    KINDS, MEDIA_KINDS, PHASE_ACQUIRING, PHASE_HELD, Decision, Holder, plan_acquire,
)
```

绿 → commit `arbiter: pure acquire state machine (R-arbiter-01/04)`

**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_state.py`

---

## T-arbiter-02 真实内存 `memory.py`（R-arbiter-02，消灭 A09）

**创建** `desk/arbiter/memory.py`、`tests/test_arbiter_memory.py`

### 1. 失败测试 `tests/test_arbiter_memory.py`

```python
"""MemoryReader: real numbers from sysctl/vm_stat, no hard-coded constants (A09)."""
import subprocess
import sys

import pytest

from desk.arbiter.memory import (
    AVAILABLE_COUNTERS, MemoryProbeError, MemoryReader, parse_vm_stat,
)

VM_STAT_CANNED = """\
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                              105595.
Pages active:                           3646394.
Pages inactive:                         2755967.
Pages speculative:                        66177.
Pages throttled:                              0.
Pages wired down:                        538077.
Pages purgeable:                          92765.
"Translation faults":                 926814395.
Pages copy-on-write:                   34567890.
Pages purged:                          12345678.
"""


class FakeRun:
    """Injectable subprocess.run replacement: argv-tuple -> (rc, stdout)."""

    def __init__(self, outputs):
        self.outputs = outputs

    def __call__(self, argv, **kwargs):
        rc, out = self.outputs[tuple(argv)]
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")


def reader(memsize="137438953472\n", pressure="1\n", vm=VM_STAT_CANNED):
    return MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (0, memsize),
        ("vm_stat",): (0, vm),
        ("sysctl", "-n", "kern.memorystatus_vm_pressure_level"): (0, pressure),
    }), clock=lambda: 123.0)


def test_parse_vm_stat_page_size_and_counters():
    page_size, counters = parse_vm_stat(VM_STAT_CANNED)
    assert page_size == 16384
    assert counters["Pages free"] == 105595
    assert counters["Pages inactive"] == 2755967
    assert counters["Pages purgeable"] == 92765
    assert counters["Pages speculative"] == 66177


def test_parse_vm_stat_garbage_raises():
    with pytest.raises(MemoryProbeError):
        parse_vm_stat("this is not vm_stat output")


def test_snapshot_arithmetic():
    snap = reader().snapshot()
    pages = 105595 + 2755967 + 92765 + 66177   # exactly AVAILABLE_COUNTERS
    assert len(AVAILABLE_COUNTERS) == 4
    assert snap.page_size == 16384
    assert snap.available_bytes == pages * 16384
    assert snap.total_bytes == 137438953472
    assert snap.used_bytes + snap.available_bytes == snap.total_bytes
    assert snap.captured_at == 123.0


@pytest.mark.parametrize("level,expected", [
    ("1\n", "normal"), ("2\n", "warn"), ("4\n", "critical"), ("7\n", "unknown"),
])
def test_pressure_mapping(level, expected):
    assert reader(pressure=level).snapshot().pressure == expected


def test_pressure_probe_failure_is_unknown_not_fatal():
    r = MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (0, "137438953472\n"),
        ("vm_stat",): (0, VM_STAT_CANNED),
        ("sysctl", "-n", "kern.memorystatus_vm_pressure_level"): (1, ""),
    }), clock=lambda: 1.0)
    assert r.snapshot().pressure == "unknown"


@pytest.mark.parametrize("injected", [271_437_611_008, 96_636_764_160])
def test_total_comes_from_probe_not_a_constant(injected):
    """A09 anti-hardcode: total tracks the injected probe output exactly.
    Any baked-in 128GB-style constant fails this for at least one value."""
    assert reader(memsize=f"{injected}\n").snapshot().total_bytes == injected


def test_memsize_probe_failure_raises():
    r = MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (1, ""),
    }), clock=lambda: 1.0)
    with pytest.raises(MemoryProbeError):
        r.snapshot()


def test_to_dict_shape():
    d = reader().snapshot().to_dict()
    assert set(d) == {"total_bytes", "used_bytes", "available_bytes",
                      "pressure", "page_size", "captured_at"}


@pytest.mark.skipif(sys.platform != "darwin", reason="real macOS probes")
def test_real_snapshot_matches_sysctl():
    """Spec acceptance verbatim: total equals `sysctl -n hw.memsize`."""
    snap = MemoryReader().snapshot()
    expected = int(subprocess.run(
        ["sysctl", "-n", "hw.memsize"],
        capture_output=True, text=True, check=True).stdout.strip())
    assert snap.total_bytes == expected
    assert snap.total_bytes > 0
    assert snap.available_bytes > 0
    assert snap.used_bytes > 0
    assert snap.page_size > 0
    assert snap.captured_at > 0
    assert snap.pressure in {"normal", "warn", "critical", "unknown"}
```

红 → 实现：

### 2. 实现 `desk/arbiter/memory.py`

```python
"""Real memory snapshot from macOS sysctl/vm_stat (R-arbiter-02).

No hard-coded memory constants anywhere: every number comes from probe
output (census A09). Probe failure for total/available raises
MemoryProbeError — errors stay errors, no invented numbers.
"""
from __future__ import annotations

import re
import subprocess
import time
from dataclasses import asdict, dataclass


class MemoryProbeError(RuntimeError):
    """Total/available memory could not be read."""


PRESSURE_LEVELS = {1: "normal", 2: "warn", 4: "critical"}

AVAILABLE_COUNTERS = (
    "Pages free",
    "Pages inactive",
    "Pages purgeable",
    "Pages speculative",
)

_PAGE_SIZE_RE = re.compile(r"page size of (\d+) bytes")
_COUNTER_RE = re.compile(r"^(.+?):\s+([\d.]+)\.?$")


@dataclass(frozen=True)
class MemorySnapshot:
    total_bytes: int
    used_bytes: int
    available_bytes: int
    pressure: str        # "normal" | "warn" | "critical" | "unknown"
    page_size: int
    captured_at: float

    def to_dict(self) -> dict:
        return asdict(self)


def parse_vm_stat(text: str) -> tuple[int, dict[str, int]]:
    """Pure parser: vm_stat output -> (page_size, {counter: pages})."""
    m = _PAGE_SIZE_RE.search(text)
    if not m:
        raise MemoryProbeError("vm_stat output missing page size")
    page_size = int(m.group(1))
    counters: dict[str, int] = {}
    for line in text.splitlines():
        cm = _COUNTER_RE.match(line.strip())
        if cm:
            counters[cm.group(1).strip('"')] = int(float(cm.group(2)))
    return page_size, counters


class MemoryReader:
    def __init__(self, run=subprocess.run, clock=time.time):
        self._run = run
        self._clock = clock

    def _out(self, argv: list[str]) -> str:
        proc = self._run(argv, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            raise MemoryProbeError(
                f"{' '.join(argv)} failed: rc={proc.returncode} stderr={proc.stderr!r}")
        return proc.stdout

    def snapshot(self) -> MemorySnapshot:
        try:
            total_bytes = int(self._out(["sysctl", "-n", "hw.memsize"]).strip())
            page_size, counters = parse_vm_stat(self._out(["vm_stat"]))
        except MemoryProbeError:
            raise
        except Exception as exc:                      # noqa: BLE001 — rewrap, no fallback
            raise MemoryProbeError(f"memory probe failed: {exc}") from exc
        available_bytes = sum(counters.get(n, 0) for n in AVAILABLE_COUNTERS) * page_size
        used_bytes = total_bytes - available_bytes
        try:
            level = int(self._out(
                ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip())
            pressure = PRESSURE_LEVELS.get(level, "unknown")
        except Exception:                             # pressure is additive info only
            pressure = "unknown"
        return MemorySnapshot(
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            available_bytes=available_bytes,
            pressure=pressure,
            page_size=page_size,
            captured_at=self._clock(),
        )
```

绿 → commit `arbiter: real memory snapshot via sysctl/vm_stat, kills ram_gb:128 (R-arbiter-02, A09)`

**implements** `data:memorySnapshot`
**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_memory.py`

---

## T-arbiter-03 按端口收割 `reaper.py`（R-arbiter-03，吸收 A06/A07）

**创建** `desk/arbiter/reaper.py`、`tests/test_arbiter_reaper.py`

### 1. 失败测试 `tests/test_arbiter_reaper.py`

```python
"""reap_port against real child processes on OS-assigned ephemeral ports.

Never touches 8767. The children are spawned by the TEST, not by the code
under test — exactly the orphan scenario of R-arbiter-03 / census A06.
"""
import contextlib
import socket
import subprocess
import sys

from desk.arbiter.reaper import ReapResult, _listening_pids, reap_port

CHILD = r"""
import signal, socket, sys, time
if "ignore-term" in sys.argv:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.listen(1)
print(s.getsockname()[1], flush=True)
time.sleep(120)
"""


def spawn_listener(*extra):
    proc = subprocess.Popen([sys.executable, "-c", CHILD, *extra],
                            stdout=subprocess.PIPE, text=True)
    port = int(proc.stdout.readline())   # printed only after listen() succeeded
    return proc, port


@contextlib.contextmanager
def listener(*extra):
    proc, port = spawn_listener(*extra)
    try:
        yield proc, port
    finally:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        proc.wait(timeout=10)


def test_reap_kills_foreign_listener():
    with listener() as (proc, port):
        result = reap_port(port, term_timeout=3.0, kill_timeout=3.0)
        assert result.ok is True
        assert proc.pid in result.killed_pids
        assert result.error is None
        assert _listening_pids(port) == []          # port truly released
        assert proc.wait(timeout=5) is not None     # process truly gone


def test_empty_port_is_success_with_no_kills():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    assert reap_port(port) == ReapResult(ok=True, port=port, killed_pids=[])


def test_sigterm_immune_listener_falls_through_to_sigkill():
    with listener("ignore-term") as (proc, port):
        result = reap_port(port, term_timeout=0.5, kill_timeout=3.0)
        assert result.ok is True
        assert proc.pid in result.killed_pids
        assert _listening_pids(port) == []


def test_result_to_dict_shape():
    d = ReapResult(ok=True, port=1, killed_pids=[2]).to_dict()
    assert set(d) == {"ok", "port", "killed_pids", "error"}
```

红 → 实现：

### 2. 实现 `desk/arbiter/reaper.py`

```python
"""Kill ANYTHING listening on a TCP port: TERM, then KILL, then verify.

R-arbiter-03. Absorbs unload-llm.sh's by-port semantics (census A06) and
replaces the own-child-only terminate() (census A07). Success is decided
ONLY by a final lsof re-check showing the port free — a sent signal is
never reported as success by itself.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ReapResult:
    ok: bool
    port: int
    killed_pids: list[int]
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _listening_pids(port: int) -> list[int]:
    """All PIDs with a LISTEN socket on the port (orphans included), minus self."""
    proc = subprocess.run(
        ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True, text=True)
    pids = []
    for tok in proc.stdout.split():
        try:
            pid = int(tok)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return pids


def _signal_and_wait(pids, sig, timeout, port, errors):
    """Send sig to pids, poll lsof up to timeout; return PIDs still listening."""
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass                                   # already dead: fine
        except PermissionError:
            errors.append(f"EPERM sending signal {int(sig)} to pid {pid}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _listening_pids(port):
            return []
        time.sleep(0.1)
    return _listening_pids(port)


def reap_port(port: int, *, term_timeout: float = 5.0,
              kill_timeout: float = 3.0) -> ReapResult:
    errors: list[str] = []
    initial = _listening_pids(port)
    if not initial:
        return ReapResult(ok=True, port=port, killed_pids=[])
    remaining = _signal_and_wait(initial, signal.SIGTERM, term_timeout, port, errors)
    if remaining:
        remaining = _signal_and_wait(remaining, signal.SIGKILL, kill_timeout, port, errors)
    still = _listening_pids(port)                  # the ONLY success criterion
    if still:
        msg = f"pids {still} still listening after SIGKILL"
        if errors:
            msg += "; " + "; ".join(errors)
        return ReapResult(ok=False, port=port,
                          killed_pids=[p for p in initial if p not in still],
                          error=msg)
    return ReapResult(ok=True, port=port, killed_pids=initial,
                      error="; ".join(errors) or None)
```

绿 → commit `arbiter: by-port reaper TERM->KILL->verify, orphan-proof (R-arbiter-03, A06/A07)`

**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_reaper.py`

---

## T-arbiter-04 `Arbiter` 门面：令牌化持有权、驱逐编排、deskState、事件

**需求** R-arbiter-01/05/06 主体。
**创建** `desk/arbiter/core.py`、`tests/test_arbiter_core.py`

### 1. 失败测试 `tests/test_arbiter_core.py`

```python
"""Arbiter facade: tokens, transitions, eviction, deskState, events.

All side effects injected (fake memory / fake reaper / fake clock):
millisecond-fast, deterministic, never touches port 8767 or real weights.
"""
import threading
import time

import pytest

from desk.arbiter.core import Arbiter
from desk.arbiter.memory import MemorySnapshot
from desk.arbiter.reaper import ReapResult

GB = 2 ** 30            # test-local unit; production code has no memory constants
LLM_PORT = 59999        # never 8767


class FakeMemory:
    def __init__(self, available=52 * GB, total=128 * GB):
        self.available = available
        self.total = total
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        return MemorySnapshot(
            total_bytes=self.total,
            used_bytes=self.total - self.available,
            available_bytes=self.available,
            pressure="normal",
            page_size=16384,
            captured_at=1.0,
        )


class FakeReaper:
    def __init__(self, ok=True, error=None):
        self.ok = ok
        self.error = error
        self.calls = []

    def __call__(self, port):
        self.calls.append(port)
        return ReapResult(ok=self.ok, port=port, killed_pids=[], error=self.error)


def make_arbiter(reaper=None, memory=None):
    return Arbiter(
        llm_port=LLM_PORT,
        memory=memory if memory is not None else FakeMemory(),
        reaper=reaper if reaper is not None else FakeReaper(),
        clock=lambda: 42.0,
    )


# ---- grant / release / token (R-arbiter-01) ----

def test_idle_llm_acquire_grants_token_and_state():
    arb = make_arbiter()
    r = arb.acquire_heavy("llm", "qwen3-30b")
    assert r["ok"] is True
    assert isinstance(r["token"], str) and len(r["token"]) == 32
    assert r["state"]["holder"]["kind"] == "llm"
    assert r["state"]["holder"]["label"] == "qwen3-30b"
    assert r["state"]["holder"]["phase"] == "held"
    assert r["state"]["holder"]["since"] == 42.0
    assert r["state"]["media_busy"] is False


def test_release_with_token_returns_to_idle():
    arb = make_arbiter()
    tok = arb.acquire_heavy("llm", "qwen3-30b")["token"]
    assert arb.release_heavy(tok) == {"ok": True}
    assert arb.desk_state()["holder"] is None
    assert arb.current_holder() is None


def test_release_wrong_token_is_not_holder_and_harmless():
    arb = make_arbiter()
    arb.acquire_heavy("llm", "qwen3-30b")
    r = arb.release_heavy("deadbeef")
    assert r["ok"] is False
    assert r["reason"]["code"] == "not_holder"
    assert arb.desk_state()["holder"]["kind"] == "llm"   # unchanged


def test_release_when_idle_is_not_holder():
    r = make_arbiter().release_heavy("anything")
    assert (r["ok"], r["reason"]["code"]) == (False, "not_holder")


# ---- refusals (R-arbiter-04) ----

def test_llm_then_llm_refused():
    arb = make_arbiter()
    arb.acquire_heavy("llm", "a")
    r = arb.acquire_heavy("llm", "b")
    assert (r["ok"], r["reason"]["code"]) == (False, "llm_already_held")


@pytest.mark.parametrize("second", ["llm", "video", "music"])
def test_media_busy_refuses_everything(second):
    arb = make_arbiter()
    assert arb.acquire_heavy("video", "job1")["ok"] is True
    r = arb.acquire_heavy(second, "next")
    assert (r["ok"], r["reason"]["code"]) == (False, "media_busy")


def test_unknown_kind_refused():
    r = make_arbiter().acquire_heavy("quantum", "x")
    assert (r["ok"], r["reason"]["code"]) == (False, "unknown_kind")


def test_refusal_calls_no_reaper_and_dispatches_no_event():
    reaper = FakeReaper()
    arb = make_arbiter(reaper=reaper)
    arb.acquire_heavy("music", "job1")
    reaper.calls.clear()
    events = []
    arb.subscribe(events.append)
    r = arb.acquire_heavy("llm", "x")
    assert r["ok"] is False
    assert reaper.calls == []      # refuse path must never reap
    assert events == []            # no state change, no event


# ---- eviction (R-arbiter-05) ----

def test_media_acquire_evicts_llm_then_grants():
    reaper = FakeReaper(ok=True)
    arb = make_arbiter(reaper=reaper)
    llm_tok = arb.acquire_heavy("llm", "qwen3-30b")["token"]
    r = arb.acquire_heavy("video", "job-1")
    assert r["ok"] is True
    assert reaper.calls == [LLM_PORT]              # evicted via injected llm_port
    state = arb.desk_state()
    assert state["holder"]["kind"] == "video"
    assert state["holder"]["phase"] == "held"
    assert state["media_busy"] is True
    late = arb.release_heavy(llm_tok)              # evicted llm's late release
    assert (late["ok"], late["reason"]["code"]) == (False, "not_holder")
    assert arb.desk_state()["holder"]["kind"] == "video"


def test_evict_failure_rolls_back_and_refuses():
    reaper = FakeReaper(ok=False, error="pids [4242] still listening after SIGKILL")
    arb = make_arbiter(reaper=reaper)
    llm_tok = arb.acquire_heavy("llm", "qwen3-30b")["token"]
    r = arb.acquire_heavy("music", "job-1")
    assert r["ok"] is False
    assert r["reason"]["code"] == "evict_failed"
    assert "4242" in r["reason"]["message"]
    state = arb.desk_state()                        # never runs media over a live LLM
    assert state["holder"]["kind"] == "llm"
    assert state["holder"]["phase"] == "held"
    assert arb.release_heavy(llm_tok) == {"ok": True}   # original token still valid


# ---- deskState shape (R-arbiter-06) ----

def test_desk_state_idle_shape():
    state = make_arbiter().desk_state()
    assert state == {
        "holder": None,
        "media_busy": False,
        "can_start": {
            "llm": {"ok": True, "reason": None},
            "media": {"ok": True, "reason": None},
        },
    }


def test_desk_state_llm_held_shape_and_no_token_leak():
    arb = make_arbiter()
    arb.acquire_heavy("llm", "qwen3-30b")
    state = arb.desk_state()
    assert "token" not in state["holder"]
    assert state["can_start"]["llm"]["ok"] is False
    assert state["can_start"]["llm"]["reason"]["code"] == "llm_already_held"
    assert state["can_start"]["media"]["ok"] is True   # eviction is allowed


def test_desk_state_media_held():
    arb = make_arbiter()
    arb.acquire_heavy("music", "job-9")
    state = arb.desk_state()
    assert state["media_busy"] is True
    assert state["can_start"]["llm"]["reason"]["code"] == "media_busy"
    assert state["can_start"]["media"]["reason"]["code"] == "media_busy"


def test_current_holder_mirrors_desk_state_holder():
    arb = make_arbiter()
    arb.acquire_heavy("video", "job-2")
    assert arb.current_holder() == arb.desk_state()["holder"]


# ---- events (R-arbiter-06) ----

def test_grant_and_release_dispatch_desk_state_payloads():
    arb = make_arbiter()
    events = []
    arb.subscribe(events.append)
    tok = arb.acquire_heavy("llm", "qwen3-30b")["token"]
    arb.release_heavy(tok)
    assert [e["holder"] and e["holder"]["kind"] for e in events] == ["llm", None]
    assert set(events[0]) == {"holder", "media_busy", "can_start"}


def test_eviction_event_sequence_acquiring_then_held():
    arb = make_arbiter(reaper=FakeReaper(ok=True))
    arb.acquire_heavy("llm", "qwen3-30b")
    events = []
    arb.subscribe(events.append)
    arb.acquire_heavy("video", "job-1")
    assert [(e["holder"]["kind"], e["holder"]["phase"]) for e in events] == [
        ("video", "acquiring"), ("video", "held"),
    ]


def test_evict_failure_event_sequence_rolls_back():
    arb = make_arbiter(reaper=FakeReaper(ok=False, error="stuck"))
    arb.acquire_heavy("llm", "qwen3-30b")
    events = []
    arb.subscribe(events.append)
    arb.acquire_heavy("video", "job-1")
    assert [(e["holder"]["kind"], e["holder"]["phase"]) for e in events] == [
        ("video", "acquiring"), ("llm", "held"),
    ]


def test_unsubscribe_stops_delivery():
    arb = make_arbiter()
    events = []
    unsubscribe = arb.subscribe(events.append)
    unsubscribe()
    arb.acquire_heavy("llm", "a")
    assert events == []


def test_raising_subscriber_does_not_break_others_or_state():
    arb = make_arbiter()
    def bad(_payload):
        raise RuntimeError("boom")
    good = []
    arb.subscribe(bad)
    arb.subscribe(good.append)
    r = arb.acquire_heavy("llm", "a")
    assert r["ok"] is True
    assert len(good) == 1
```

红 → 实现：

### 2. 实现 `desk/arbiter/core.py`

```python
"""Arbiter facade: locks, tokens, eviction, events.

R-arbiter-01/04/05/06. Decisions come from state.plan_acquire (pure);
this file owns concurrency and side effects only.

Locking model (see design):
- _transition_lock serialises acquire/release including eviction subprocess time.
- _state_lock guards only the holder/subscriber fields and is never held
  across a subprocess call, so desk_state() stays instant during eviction.
- Events are buffered per call and dispatched with NO lock held
  (threading.Lock is not reentrant; dispatching under a lock would deadlock
  any subscriber that calls back into the arbiter).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable, Optional

from .memory import MemoryReader
from .reaper import ReapResult, reap_port
from .state import MEDIA_KINDS, PHASE_ACQUIRING, PHASE_HELD, Holder, plan_acquire


def _refusal(code: str, message: str) -> dict:
    return {"ok": False, "reason": {"code": code, "message": message}}


class Arbiter:
    """Single authority for "one heavy job at a time"."""

    def __init__(self, llm_port: int, *,
                 memory: MemoryReader | None = None,
                 reaper: Callable[[int], ReapResult] = reap_port,
                 clock: Callable[[], float] = time.time,
                 logger: logging.Logger | None = None) -> None:
        # llm_port is injected by the assembly layer (desk.llm.DEFAULT_LLM_PORT);
        # this package contains no 8767 literal.
        self._llm_port = llm_port
        self._memory = memory if memory is not None else MemoryReader()
        self._reaper = reaper
        self._clock = clock
        self._log = logger if logger is not None else logging.getLogger(__name__)
        self._transition_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._holder: Optional[Holder] = None
        self._subscribers: list[Callable[[dict], None]] = []

    # ---- internal helpers ----

    def _read_holder(self) -> Optional[Holder]:
        with self._state_lock:
            return self._holder

    def _set_holder(self, holder: Optional[Holder], events: list[dict]) -> None:
        with self._state_lock:
            self._holder = holder
        events.append(self.desk_state())

    def _dispatch(self, events: list[dict]) -> None:
        if not events:
            return
        with self._state_lock:
            subscribers = list(self._subscribers)
        for payload in events:
            for cb in subscribers:
                try:
                    cb(payload)
                except Exception:                      # noqa: BLE001
                    self._log.exception("heavyStateChanged subscriber failed")

    # ---- api:acquireHeavy ----

    def acquire_heavy(self, kind: str, label: str) -> dict:
        events: list[dict] = []
        try:
            with self._transition_lock:
                holder = self._read_holder()
                decision = plan_acquire(holder, kind)
                if decision.action == "refuse":
                    return _refusal(decision.reason_code, decision.reason_message)
                if decision.action == "evict_then_grant":
                    previous = holder
                    # Transition holder carries a throwaway token: the evicted
                    # llm's late release can never match it (not_holder).
                    self._set_holder(
                        Holder(kind=kind, label=label, token=uuid.uuid4().hex,
                               since=self._clock(), phase=PHASE_ACQUIRING),
                        events)
                    result = self._reaper(self._llm_port)
                    if not result.ok:
                        self._set_holder(previous, events)   # roll back, original token intact
                        self._log.error("evict failed: %s", result.error)
                        return _refusal("evict_failed",
                                        result.error or "eviction failed")
                token = uuid.uuid4().hex
                self._set_holder(
                    Holder(kind=kind, label=label, token=token,
                           since=self._clock(), phase=PHASE_HELD),
                    events)
                return {"ok": True, "token": token, "state": self.desk_state()}
        finally:
            self._dispatch(events)

    # ---- api:releaseHeavy ----

    def release_heavy(self, token: str) -> dict:
        events: list[dict] = []
        try:
            with self._transition_lock:
                holder = self._read_holder()
                if (holder is None or holder.token != token
                        or holder.phase != PHASE_HELD):
                    return _refusal("not_holder",
                                    "token does not match the current holder")
                self._set_holder(None, events)
                return {"ok": True}
        finally:
            self._dispatch(events)

    # ---- api:currentHolder ----

    def current_holder(self) -> Optional[dict]:
        holder = self._read_holder()
        if holder is None:
            return None
        return {"kind": holder.kind, "label": holder.label,
                "since": holder.since, "phase": holder.phase}

    # ---- data:deskState ----

    def desk_state(self) -> dict:
        holder = self._read_holder()

        def verdict(kind: str) -> dict:
            d = plan_acquire(holder, kind)
            if d.action == "refuse":
                return {"ok": False,
                        "reason": {"code": d.reason_code, "message": d.reason_message}}
            return {"ok": True, "reason": None}

        return {
            "holder": None if holder is None else {
                "kind": holder.kind, "label": holder.label,
                "since": holder.since, "phase": holder.phase,
            },
            "media_busy": holder is not None and holder.kind in MEDIA_KINDS,
            # video/music are isomorphic in the state machine: one "media" answer.
            "can_start": {"llm": verdict("llm"), "media": verdict("video")},
        }

    # ---- event:heavyStateChanged ----

    def subscribe(self, cb: Callable[[dict], None]) -> Callable[[], None]:
        with self._state_lock:
            self._subscribers.append(cb)

        def unsubscribe() -> None:
            with self._state_lock:
                if cb in self._subscribers:
                    self._subscribers.remove(cb)

        return unsubscribe
```

绿 → commit `arbiter: tokened facade with eviction orchestration and events (R-arbiter-01/05/06)`

**implements** `api:acquireHeavy`、`api:releaseHeavy`、`api:currentHolder`、`data:deskState`、`event:heavyStateChanged`
**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_core.py`

---

## T-arbiter-05 驱逐进行中的快速拒绝路径

**需求** design「transition_in_progress 快速拒绝」：慢收割（可达 ~8s）期间新请求不得阻塞在
`_transition_lock` 上排队，必须立即拒绝；deskState 读取全程即时并如实显示过渡态。
**修改** `desk/arbiter/core.py`、`tests/test_arbiter_core.py`

### 1. 失败测试（追加到 `tests/test_arbiter_core.py`）

```python
# ---- fast reject during slow eviction (design: transition_in_progress) ----

def test_fast_reject_and_live_desk_state_during_slow_eviction():
    gate = threading.Event()
    entered = threading.Event()

    def slow_reaper(port):
        entered.set()
        assert gate.wait(10.0)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arb = make_arbiter(reaper=slow_reaper)
    arb.acquire_heavy("llm", "qwen3-30b")
    events = []
    arb.subscribe(events.append)
    outcome = {}
    t = threading.Thread(
        target=lambda: outcome.update(r=arb.acquire_heavy("video", "job-1")))
    t.start()
    try:
        assert entered.wait(10.0)          # eviction is now mid-flight
        # deskState is instantaneous and shows the transition truthfully
        state = arb.desk_state()
        assert (state["holder"]["kind"], state["holder"]["phase"]) == ("video", "acquiring")
        # a competing acquire returns immediately, without queueing on the lock
        t0 = time.monotonic()
        r2 = arb.acquire_heavy("music", "job-2")
        assert time.monotonic() - t0 < 1.0
        assert (r2["ok"], r2["reason"]["code"]) == (False, "transition_in_progress")
    finally:
        gate.set()
        t.join(10.0)
    assert outcome["r"]["ok"] is True      # original eviction finished normally
    final = arb.desk_state()
    assert (final["holder"]["kind"], final["holder"]["phase"]) == ("video", "held")
    assert [(e["holder"]["kind"], e["holder"]["phase"]) for e in events] == [
        ("video", "acquiring"), ("video", "held"),   # event order undisturbed
    ]
```

红（当前实现会阻塞在 `_transition_lock` 直到 `gate.set()`，断言 `< 1.0` 失败）→ 实现：

### 2. 实现：`acquire_heavy` 开头加入锁前快速检查

```python
    def acquire_heavy(self, kind: str, label: str) -> dict:
        # Fast-reject path (design): peek under _state_lock BEFORE competing for
        # _transition_lock. During a slow eviction (up to term+kill timeouts)
        # new requests must fail immediately instead of queueing. A request
        # already blocked on the lock in the tiny pre-transition window simply
        # re-plans once inside and is refused by the table — mutex unaffected.
        pre = self._read_holder()
        if pre is not None and pre.phase == PHASE_ACQUIRING:
            return _refusal("transition_in_progress",
                            "a heavy-work transition is in progress; retry shortly")
        events: list[dict] = []
        ...  # rest unchanged from T-arbiter-04
```

绿 → commit `arbiter: non-queueing fast reject while an eviction is in flight`

**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_core.py`

---

## T-arbiter-06 并发竞态证明（R-arbiter-01）

**修改** `tests/test_arbiter_core.py`（纯测试任务：锁已在 T-04 落位，本任务是互斥的独立证明；
若竞态暴露缺陷，修复落回 `desk/arbiter/core.py`）

### 1. 测试（追加）

```python
# ---- concurrency races (R-arbiter-01) ----

def _race(arb, kinds):
    barrier = threading.Barrier(len(kinds))
    results = [None] * len(kinds)

    def worker(i, kind):
        barrier.wait()
        results[i] = arb.acquire_heavy(kind, f"contender-{i}")

    threads = [threading.Thread(target=worker, args=(i, k))
               for i, k in enumerate(kinds)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30.0)
    assert all(r is not None for r in results)
    return results


def test_sixteen_simultaneous_llm_acquires_grant_exactly_one():
    arb = make_arbiter()
    results = _race(arb, ["llm"] * 16)
    winners = [r for r in results if r["ok"]]
    assert len(winners) == 1
    for r in results:
        if not r["ok"]:
            assert r["reason"]["code"] == "llm_already_held"
    assert arb.desk_state()["holder"]["kind"] == "llm"


def test_mixed_media_race_grants_exactly_one():
    arb = make_arbiter()
    results = _race(arb, ["video", "music"] * 8)
    winners = [r for r in results if r["ok"]]
    assert len(winners) == 1
    for r in results:
        if not r["ok"]:
            assert r["reason"]["code"] == "media_busy"
    assert arb.desk_state()["holder"]["kind"] in ("video", "music")
    assert arb.desk_state()["media_busy"] is True


def test_late_release_of_loser_token_cannot_unseat_winner():
    arb = make_arbiter()
    tok1 = arb.acquire_heavy("video", "job-1")["token"]
    assert arb.release_heavy(tok1) == {"ok": True}
    arb.acquire_heavy("music", "job-2")
    stale = arb.release_heavy(tok1)                 # replay of an old token
    assert (stale["ok"], stale["reason"]["code"]) == (False, "not_holder")
    assert arb.desk_state()["holder"]["kind"] == "music"
```

运行必须一次全绿（多跑几次确认稳定：`python3 -m pytest tests/test_arbiter_core.py -q` ×3）。
若出现多于一个 winner，即为 `_transition_lock` 缺陷，修复后重跑。

commit `arbiter: race proof — concurrent acquires grant exactly one (R-arbiter-01)`

**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_core.py`

---

## T-arbiter-07 `can_start_heavy`：只读预检 + 加载前内存警告（R-arbiter-04/07）

**修改** `desk/arbiter/core.py`、`tests/test_arbiter_core.py`

### 1. 失败测试（追加）

```python
# ---- can_start_heavy (R-arbiter-04 + R-arbiter-07) ----

def test_can_start_idle_no_estimate():
    r = make_arbiter().can_start_heavy("llm")
    assert r == {"ok": True, "reason": None, "memory_warning": None}


def test_can_start_matches_acquire_table():
    arb = make_arbiter()
    arb.acquire_heavy("llm", "qwen3-30b")
    r = arb.can_start_heavy("llm")
    assert (r["ok"], r["reason"]["code"]) == (False, "llm_already_held")
    assert arb.can_start_heavy("video")["ok"] is True     # eviction allowed
    arb2 = make_arbiter()
    arb2.acquire_heavy("music", "job-1")
    assert arb2.can_start_heavy("video")["reason"]["code"] == "media_busy"


def test_can_start_is_read_only():
    arb = make_arbiter()
    arb.can_start_heavy("llm")
    arb.can_start_heavy("video", estimated_bytes=999 * GB)
    assert arb.desk_state()["holder"] is None             # nothing changed


def test_oversized_model_warns_but_ok_stays_true():
    arb = make_arbiter(memory=FakeMemory(available=52 * GB))
    r = arb.can_start_heavy("llm", estimated_bytes=74 * GB)
    assert r["ok"] is True                                # warning, not refusal
    w = r["memory_warning"]
    assert w["code"] == "insufficient_memory"
    assert w["required_bytes"] == 74 * GB
    assert w["available_bytes"] == 52 * GB
    assert w["message"]


def test_fitting_model_has_no_warning():
    arb = make_arbiter(memory=FakeMemory(available=52 * GB))
    r = arb.can_start_heavy("llm", estimated_bytes=30 * GB)
    assert r == {"ok": True, "reason": None, "memory_warning": None}


def test_no_estimate_never_probes_memory():
    mem = FakeMemory()
    arb = make_arbiter(memory=mem)
    arb.can_start_heavy("llm")
    assert mem.calls == 0          # no subprocess cost on plain status checks


def test_can_start_during_eviction_is_transition_in_progress():
    gate = threading.Event()
    entered = threading.Event()

    def slow_reaper(port):
        entered.set()
        assert gate.wait(10.0)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arb = make_arbiter(reaper=slow_reaper)
    arb.acquire_heavy("llm", "qwen3-30b")
    t = threading.Thread(target=arb.acquire_heavy, args=("video", "job-1"))
    t.start()
    try:
        assert entered.wait(10.0)
        r = arb.can_start_heavy("llm")
        assert (r["ok"], r["reason"]["code"]) == (False, "transition_in_progress")
    finally:
        gate.set()
        t.join(10.0)
```

红 → 实现：

### 2. 实现：`Arbiter` 追加方法

```python
    # ---- api:canStartHeavy ----

    def can_start_heavy(self, kind: str, estimated_bytes: int | None = None) -> dict:
        """Read-only pre-check. ok/reason come from the SAME transition table as
        acquire (necessarily consistent); an oversized estimate adds a warning
        BEFORE load time (R-arbiter-07) but never flips ok to False."""
        decision = plan_acquire(self._read_holder(), kind)
        if decision.action == "refuse":
            return {"ok": False,
                    "reason": {"code": decision.reason_code,
                               "message": decision.reason_message},
                    "memory_warning": None}
        warning = None
        if estimated_bytes is not None:
            snap = self._memory.snapshot()
            if estimated_bytes > snap.available_bytes:
                warning = {
                    "code": "insufficient_memory",
                    "required_bytes": estimated_bytes,
                    "available_bytes": snap.available_bytes,
                    "message": (f"该模型约需 {estimated_bytes / 1e9:.1f} GB，"
                                f"当前可用 {snap.available_bytes / 1e9:.1f} GB"),
                }
        return {"ok": True, "reason": None, "memory_warning": warning}
```

（只读、不取 `_transition_lock` —— 快速拒绝天然满足：过渡态由 `plan_acquire` 的
`transition_in_progress` 行回答。）

绿 → commit `arbiter: read-only can_start pre-check with pre-load memory warning (R-arbiter-04/07)`

**implements** `api:canStartHeavy`
**acceptance_cmd** `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_core.py`

---

## T-arbiter-08 门面收尾：`memory_snapshot` / `reap_llm_port` 包装 + 包导出 + 全套回归

**修改** `desk/arbiter/core.py`、`desk/arbiter/__init__.py`、`tests/test_arbiter_core.py`
**消费** `api:resolvePaths`（间接：组装层用 foundation 的 `setup_logging(roots)` 配好文件日志后，
本包只 `logging.getLogger(__name__)`；包内零路径拼接 —— design Assumption 1。本任务在
`__init__` 文档串中写明该组装合同。）

### 1. 失败测试（追加）

```python
# ---- facade wrappers + package exports ----

def test_memory_snapshot_is_reader_dict():
    mem = FakeMemory(available=52 * GB, total=128 * GB)
    d = make_arbiter(memory=mem).memory_snapshot()
    assert d == {
        "total_bytes": 128 * GB,
        "used_bytes": 76 * GB,
        "available_bytes": 52 * GB,
        "pressure": "normal",
        "page_size": 16384,
        "captured_at": 1.0,
    }


def test_reap_llm_port_uses_argument_port_not_llm_port():
    reaper = FakeReaper(ok=True)
    arb = make_arbiter(reaper=reaper)
    d = arb.reap_llm_port(61234)
    assert reaper.calls == [61234]          # by-argument, NOT self._llm_port
    assert d == {"ok": True, "port": 61234, "killed_pids": [], "error": None}


def test_package_exports():
    import desk.arbiter as pkg
    for name in ("Arbiter", "MemoryReader", "MemorySnapshot", "MemoryProbeError",
                 "parse_vm_stat", "ReapResult", "reap_port",
                 "Decision", "Holder", "plan_acquire",
                 "KINDS", "MEDIA_KINDS", "PHASE_ACQUIRING", "PHASE_HELD"):
        assert hasattr(pkg, name), name
```

红 → 实现：

### 2. 实现：`Arbiter` 追加两个一行包装

```python
    # ---- api:memorySnapshot ----

    def memory_snapshot(self) -> dict:
        return self._memory.snapshot().to_dict()

    # ---- api:reapLlmPort ----

    def reap_llm_port(self, port: int) -> dict:
        """Reap by the ARGUMENT port (llm passes its DEFAULT_LLM_PORT constant).
        self._llm_port is used only by eviction inside acquire_heavy."""
        return self._reaper(port).to_dict()
```

### 3. 定稿 `desk/arbiter/__init__.py`

```python
"""arbiter — single authority for "one heavy job at a time".

Pure in-process package: no HTTP server, no sibling-module imports.
Assembly contract (design Assumptions 1-2):
- llm_port: pass desk.llm.DEFAULT_LLM_PORT into Arbiter(); no 8767 literal here.
- logging: foundation's setup_logging(roots) (api:resolvePaths) configures the
  file handler; this package only calls logging.getLogger and joins no paths.
- routes: mount Arbiter methods (desk_state / memory_snapshot / ...) one-line each.
"""
from .core import Arbiter
from .memory import MemoryProbeError, MemoryReader, MemorySnapshot, parse_vm_stat
from .reaper import ReapResult, reap_port
from .state import (
    KINDS, MEDIA_KINDS, PHASE_ACQUIRING, PHASE_HELD, Decision, Holder, plan_acquire,
)

__all__ = [
    "Arbiter",
    "MemoryProbeError", "MemoryReader", "MemorySnapshot", "parse_vm_stat",
    "ReapResult", "reap_port",
    "KINDS", "MEDIA_KINDS", "PHASE_ACQUIRING", "PHASE_HELD",
    "Decision", "Holder", "plan_acquire",
]
```

### 4. 全套回归 + 单点自查

```bash
python3 -m pytest /Users/aa/LocalModelDesk/tests/test_arbiter_state.py \
                  /Users/aa/LocalModelDesk/tests/test_arbiter_core.py \
                  /Users/aa/LocalModelDesk/tests/test_arbiter_reaper.py \
                  /Users/aa/LocalModelDesk/tests/test_arbiter_memory.py
grep -rn '8767' /Users/aa/LocalModelDesk/desk/arbiter/          # 必须无输出
grep -rn 'ram_gb\|137438953472\|128' /Users/aa/LocalModelDesk/desk/arbiter/  # 128 只许出现在注释外？→ 必须无输出
```

绿 → commit `arbiter: memory_snapshot/reap_llm_port wrappers + package exports (R-arbiter-02/03 api)`

**implements** `api:memorySnapshot`、`api:reapLlmPort`　**requires** `api:resolvePaths`
**acceptance_cmd** 上述四文件 pytest（见任务 JSON）

---

## 需求覆盖矩阵

| 需求 | 任务 | 测试 |
|---|---|---|
| R-arbiter-01 互斥、并发唯一 | T-01, T-04, T-06 | 转移表全格；16 线程 barrier 竞态恰一 winner；混合 media 竞态 |
| R-arbiter-02 真实内存 | T-02 | 算术、压力映射、防写死双注入值、真机对 `sysctl hw.memsize` |
| R-arbiter-03 按端口收割 | T-03 | 真子进程（孤儿）、空端口、SIGTERM 免疫走 KILL、lsof 复查为准 |
| R-arbiter-04 机器可读拒绝 | T-01, T-04, T-07 | `media_busy`/`llm_already_held`/`transition_in_progress` 各码 |
| R-arbiter-05 先让内存、失败即拒 | T-04 | 驱逐成功换持有者；驱逐失败回滚 + `evict_failed` |
| R-arbiter-06 单一台面状态 + 事件 | T-04, T-05 | deskState 形状、无 token 泄漏、事件序列、异常订阅者隔离 |
| R-arbiter-07 加载前内存警告 | T-07 | 超量→警告且 `ok:true`；装得下→无警告；不传体积→不探测 |

## 接口落点

| 注册表接口 | 任务 | 落点 |
|---|---|---|
| `data:memorySnapshot` | T-02 | `MemorySnapshot.to_dict()` |
| `api:acquireHeavy` / `api:releaseHeavy` / `api:currentHolder` / `data:deskState` / `event:heavyStateChanged` | T-04 | `Arbiter` 门面 |
| `api:canStartHeavy` | T-07 | `Arbiter.can_start_heavy` |
| `api:memorySnapshot` / `api:reapLlmPort` | T-08 | 门面一行包装 |
| 消费 `api:resolvePaths` | T-08 | 组装合同（日志落点），包内零路径 |
