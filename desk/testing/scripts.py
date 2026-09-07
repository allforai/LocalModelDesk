"""Deterministic scripts and gates for end-to-end test doubles."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GATE_TIMEOUT_S = 5.0


class ScriptStall(RuntimeError):
    """A gate was not opened before its timeout."""


class ScriptExhausted(RuntimeError):
    """A script has no remaining requested steps."""


class Gate:
    def __init__(self, timeout_s: float = DEFAULT_GATE_TIMEOUT_S):
        self._event = threading.Event()
        self._timeout_s = timeout_s

    def open(self) -> None:
        self._event.set()

    def wait(self) -> None:
        if not self._event.wait(self._timeout_s):
            raise ScriptStall(f"gate not opened within {self._timeout_s}s")


@dataclass(frozen=True)
class Delta:
    content: str | None = None
    reasoning: str | None = None


@dataclass(frozen=True)
class Done:
    usage: dict
    finish_reason: str = "stop"


@dataclass(frozen=True)
class Line:
    text: str


class _WriteOutput:
    pass


WRITE_OUTPUT = _WriteOutput()


@dataclass(frozen=True)
class Exit:
    code: int = 0


class _BlockUntilCancel:
    pass


BLOCK_UNTIL_CANCEL = _BlockUntilCancel()


def _gates(steps: list) -> list[Gate]:
    return [step for step in steps if isinstance(step, Gate)]


def default_chat_steps() -> list:
    return [
        Delta(reasoning="让我想想，"), Gate(),
        Delta(reasoning="想好了。"), Gate(),
        Delta(content="你好"), Gate(),
        Delta(content="，世界"),
        Done(usage={"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9}),
    ]


class ChatScript:
    def __init__(self, steps: list | None = None):
        self.steps = steps if steps is not None else default_chat_steps()
        self._opened = 0
        self.consumed = False
        self.requests: list[dict] = []

    def step(self) -> None:
        gates = _gates(self.steps)
        if self._opened >= len(gates):
            raise ScriptExhausted("no more gates in chat script")
        gates[self._opened].open()
        self._opened += 1

    def run_to_end(self) -> None:
        gates = _gates(self.steps)
        for gate in gates[self._opened:]:
            gate.open()
        self._opened = len(gates)


def default_media_steps() -> list:
    return [Line("step 1/10"), Gate(), Line("step 5/10"), Gate(), WRITE_OUTPUT, Exit(0)]


def fast_media_steps() -> list:
    return [Line("step 1/10"), Line("step 10/10"), WRITE_OUTPUT, Exit(0)]


def cancellable_media_steps() -> list:
    return [Line("step 1/10"), Gate(), BLOCK_UNTIL_CANCEL]


class MediaScript:
    def __init__(self, jobs: list[list] | None = None):
        self.jobs: deque[list] = deque(jobs if jobs is not None else [default_media_steps()])
        self.active: list | None = None
        self._opened = 0
        self.spawned_argvs: list[list[str]] = []

    def next_job(self) -> list:
        if not self.jobs:
            raise ScriptExhausted("no more media jobs scripted")
        self.active = self.jobs.popleft()
        self._opened = 0
        return self.active

    def step(self) -> None:
        gates = _gates(self.active or [])
        if self._opened >= len(gates):
            raise ScriptExhausted("no more gates in active media job")
        gates[self._opened].open()
        self._opened += 1


class MemoryScript:
    def __init__(self, snapshots: list | None = None):
        self._snaps = deque(snapshots or [])
        self._lock = threading.Lock()

    def push(self, snapshot) -> None:
        with self._lock:
            self._snaps.append(snapshot)

    def current(self):
        with self._lock:
            if not self._snaps:
                raise ScriptExhausted("memory script is empty")
            if len(self._snaps) > 1:
                return self._snaps.popleft()
            return self._snaps[0]


class DownloadControl:
    def __init__(self):
        self.spawns: list[list[str]] = []
        self.envs: list[dict] = []
        self.handles: list = []

    @property
    def handle(self):
        if not self.handles:
            raise ScriptExhausted("no download spawned yet")
        return self.handles[-1]

    @staticmethod
    def dest_dir(argv: list[str]) -> Path:
        return Path(argv[argv.index("--local-dir") + 1])

    def advance(self, rel_path: str, n_bytes: int) -> None:
        destination = self.dest_dir(self.spawns[-1]) / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"x" * n_bytes)

    def finish(self, manifest_files: list[tuple[str, int]]) -> None:
        for rel_path, size in manifest_files:
            self.advance(rel_path, size)
        self.handle.exit(0)

    def exit_terminated(self) -> None:
        handle = self.handle
        assert handle.terminated, "handle has not received terminate yet"
        handle.exit(-15)
