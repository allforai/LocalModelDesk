"""Fakes for MediaService tests; no real subprocesses or model weights."""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from desk.library.image_sessions import ImageSessionStore
from desk.media.service import MediaService

FIXED_TIME = 1756600000.0
STAMP = time.strftime("%Y%m%d-%H%M%S", time.localtime(FIXED_TIME))


class FakeHandle:
    def __init__(self, script: str, output: Path, lines, *, ignore_term: bool):
        self.script, self.lines, self.ignore_term = script, list(lines), ignore_term
        self.terminated = self.killed = False
        self._queue: queue.Queue[str] = queue.Queue()
        self._exited = threading.Event()
        self._code: int | None = None
        if script == "success":
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"fake-media-bytes")
        if script != "block":
            self._exit(3 if script == "fail" else 0)

    def _exit(self, code: int) -> None:
        self._code = code
        self._exited.set()

    def iter_output(self):
        yield from self.lines
        while self.script == "block":
            try:
                yield self._queue.get(timeout=0.02)
            except queue.Empty:
                if self._exited.is_set():
                    return

    def wait(self) -> int:
        assert self._exited.wait(10.0)
        return self._code

    def poll(self) -> int | None:
        return self._code if self._exited.is_set() else None

    def terminate(self) -> None:
        self.terminated = True
        if self.script == "block" and not self.ignore_term:
            self._exit(0)

    def kill(self) -> None:
        self.killed = True
        self._exit(-9)

    def emit(self, line: str) -> None:
        self._queue.put(line)

    def exit(self, code: int) -> None:
        self._exit(code)


class FakeExecutor:
    def __init__(self, script="success", lines=("line-1", "line-2"), *, ignore_term=False):
        self.script, self.lines, self.ignore_term = script, lines, ignore_term
        self.spawned: list[dict] = []

    def spawn(self, cmd, *, extra_env=None):
        self.spawned.append({"cmd": list(cmd), "extra_env": dict(extra_env or {})})
        return FakeHandle(self.script, Path(cmd[cmd.index("--output") + 1]), self.lines, ignore_term=self.ignore_term)


class FakeArbiter:
    def __init__(self, memory_warning=None):
        self.acquired: list[tuple] = []
        self.released: list[str] = []
        self.precheck_calls: list[tuple] = []
        self.memory_warning = memory_warning

    def can_start_heavy(self, kind, params=None, key=None, estimated_bytes=None):
        # params/key 单独存：既有断言按位置比对 precheck_calls 的元组，塞进去会
        # 连带炸掉一批与本次改动无关的测试。
        self.last_precheck = {"kind": kind, "params": params, "key": key,
                              "estimated_bytes": estimated_bytes}
        self.precheck_calls.append((kind, estimated_bytes))
        result = {"ok": True, "reason": None}
        if self.memory_warning:
            result["memory_warning"] = self.memory_warning
        return result

    def acquire_heavy(self, kind, label, display=None, *, params=None, key=None):
        self.last_acquire = {"kind": kind, "label": label, "params": params, "key": key}
        token = f"permit-{len(self.acquired) + 1}"
        self.acquired.append((kind, label, token))
        return {"ok": True, "token": token}

    def release_heavy(self, token):
        self.released.append(token)
        return {"ok": True}


class FakeHistory:
    def __init__(self): self.entries: list[dict] = []
    def append(self, entry): self.entries.append(entry); return entry


def make_service(tmp_path: Path, *, executor=None, memory_warning=None, image_sessions=None):
    """The image-session store is the real file store under ``tmp_path`` unless one is given."""
    executor = executor or FakeExecutor()
    image_sessions = image_sessions or ImageSessionStore(tmp_path / "image-sessions", tmp_path / "outputs")
    arbiter, history = FakeArbiter(memory_warning=memory_warning), FakeHistory()
    roots = SimpleNamespace(outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={"PYTHONPATH": "/fake/pylibs/h3"})
    caps = {"mlx_h3": SimpleNamespace(present=True, detail="")}
    service = MediaService(resolve_paths=lambda: roots, probe_capabilities=lambda: caps,
        arbiter=arbiter, list_catalog=lambda: [SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)],
        append_history=history.append, executor=executor, image_sessions=image_sessions,
        clock=lambda: FIXED_TIME)
    return service, SimpleNamespace(executor=executor, arbiter=arbiter, history=history,
                                    image_sessions=image_sessions)


def service_factory(tmp_path: Path):
    """Returns a factory(**kwargs) -> (service, arbiter) for tests that need to vary arbiter behaviour."""
    def factory(*, memory_warning=None, executor=None):
        service, deps = make_service(tmp_path, executor=executor, memory_warning=memory_warning)
        return service, deps.arbiter
    return factory


def finished_snapshot(service, start_fn, timeout=5.0):
    done, box = threading.Event(), {}
    service.on_job_finished(lambda snap: (box.update(snap), done.set()))
    start_fn()
    assert done.wait(timeout), "job never finished"
    return box
