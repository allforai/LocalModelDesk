"""Deterministic fakes for the end-to-end composition root."""
from __future__ import annotations

import threading
from pathlib import Path

from desk.arbiter.memory import MemorySnapshot
from desk.arbiter.reaper import ReapResult

from .scripts import (
    BLOCK_UNTIL_CANCEL,
    ChatScript,
    Delta,
    Done,
    DownloadControl,
    Exit,
    Gate,
    Line,
    MediaScript,
    MemoryScript,
    ScriptExhausted,
    ScriptStall,
    WRITE_OUTPUT,
)
from .seed import TINY_MP4, TINY_WAV


FIXED_CLOCK_AT = 1_756_600_000.0
DEFAULT_SNAPSHOT_A = MemorySnapshot(
    total_bytes=200_000_000_000,
    used_bytes=75_000_000_000,
    available_bytes=125_000_000_000,
    pressure="normal",
    page_size=16384,
    captured_at=FIXED_CLOCK_AT,
)
SNAPSHOT_B = MemorySnapshot(
    total_bytes=300_000_000_000,
    used_bytes=90_000_000_000,
    available_bytes=210_000_000_000,
    pressure="warn",
    page_size=16384,
    captured_at=FIXED_CLOCK_AT + 1,
)


class _FakeBackendProcess:
    def __init__(self):
        self._code: int | None = None

    def poll(self) -> int | None:
        return self._code

    def terminate(self) -> None:
        self._code = 0

    def kill(self) -> None:
        self._code = -9

    def wait(self, timeout: float) -> None:
        return None


class FakeLlmBackend:
    """A live-on-spawn LLM backend driven by a one-shot chat script."""

    def __init__(self, script: ChatScript):
        self.script = script
        self.proc: _FakeBackendProcess | None = None

    def spawn(self, python, model_path, port, log_path):
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write("[fake mlx-lm] serving for e2e\n")
        self.proc = _FakeBackendProcess()
        return self.proc

    def health(self, port: int) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _iter_steps(self, payload: dict, *, wait_gates: bool):
        script = self.script
        if script.consumed:
            raise ScriptExhausted("chat script already consumed")
        script.consumed = True
        script.requests.append(payload)
        for step in script.steps:
            if isinstance(step, Gate):
                if wait_gates:
                    step.wait()
            elif isinstance(step, (Delta, Done)):
                yield step
            else:
                raise ScriptExhausted(f"unexpected chat step: {step!r}")

    def chat_stream(self, port: int, payload: dict):
        for step in self._iter_steps(payload, wait_gates=True):
            if isinstance(step, Delta):
                delta = {}
                if step.content is not None:
                    delta["content"] = step.content
                if step.reasoning is not None:
                    delta["reasoning_content"] = step.reasoning
                yield {"choices": [{"delta": delta, "finish_reason": None}]}
            else:
                yield {
                    "choices": [{"delta": {}, "finish_reason": step.finish_reason}],
                    "usage": step.usage,
                }

    def chat(self, port: int, payload: dict) -> dict:
        content, reasoning, done = [], [], None
        for step in self._iter_steps(payload, wait_gates=False):
            if isinstance(step, Delta):
                if step.content:
                    content.append(step.content)
                if step.reasoning:
                    reasoning.append(step.reasoning)
            else:
                done = step
        if done is None:
            raise ScriptExhausted("chat script has no Done step")
        message = {"role": "assistant", "content": "".join(content)}
        if reasoning:
            message["reasoning_content"] = "".join(reasoning)
        return {
            "choices": [{"message": message, "finish_reason": done.finish_reason}],
            "usage": done.usage,
        }

    def log_tail(self, log_path: Path, max_lines: int = 40) -> str:
        log_path = Path(log_path)
        if not log_path.exists():
            return f"日志文件不存在: {log_path}"
        return "".join(log_path.read_text(encoding="utf-8").splitlines(keepends=True)[-max_lines:])


class FakeMediaHandle:
    def __init__(self, steps: list, output_path: Path):
        self._steps = steps
        self._output_path = output_path
        self._code: int | None = None
        self._cancel = threading.Event()
        self.terminated = False

    def iter_output(self):
        for step in self._steps:
            if isinstance(step, Gate):
                step.wait()
            elif isinstance(step, Line):
                yield step.text
            elif step is WRITE_OUTPUT:
                self._output_path.parent.mkdir(parents=True, exist_ok=True)
                output = TINY_MP4 if self._output_path.suffix == ".mp4" else TINY_WAV
                self._output_path.write_bytes(output)
            elif isinstance(step, Exit):
                self._code = step.code
                return
            elif step is BLOCK_UNTIL_CANCEL:
                if not self._cancel.wait(30.0):
                    raise ScriptStall("BLOCK_UNTIL_CANCEL: terminate never arrived")
                self._code = -15
                return
            else:
                raise ScriptExhausted(f"unexpected media step: {step!r}")
        self._code = 0

    def wait(self) -> int:
        if self._code is None:
            raise ScriptStall("wait() called before iter_output() finished")
        return self._code

    def poll(self) -> int | None:
        return self._code

    def terminate(self) -> None:
        self.terminated = True
        self._cancel.set()

    def kill(self) -> None:
        self.terminated = True
        self._cancel.set()
        if self._code is None:
            self._code = -9


class FakeMediaExecutor:
    """Media executor that records argv and produces scripted tiny artifacts."""

    def __init__(self, script: MediaScript):
        self.script = script

    def spawn(self, cmd: list[str], *, log_path=None, extra_env=None) -> FakeMediaHandle:
        argv = list(cmd)
        self.script.spawned_argvs.append(argv)
        output_path = Path(argv[argv.index("--output") + 1])
        return FakeMediaHandle(self.script.next_job(), output_path)


class FakeDownloadHandle:
    def __init__(self):
        self._code: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self._code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self._code = -9

    def exit(self, code: int) -> None:
        self._code = code


class FakeDownloadExecutor:
    """Download executor whose process lifetime remains under test control."""

    def __init__(self, control: DownloadControl):
        self.ctl = control

    def spawn(self, cmd: list[str], cwd=None, extra_env=None) -> FakeDownloadHandle:
        handle = FakeDownloadHandle()
        self.ctl.spawns.append(list(cmd))
        self.ctl.envs.append(dict(extra_env or {}))
        self.ctl.handles.append(handle)
        return handle


class FakeMemoryReader:
    """Memory reader that supplies snapshots from a deterministic script."""

    def __init__(self, script: MemoryScript):
        self.script = script

    def snapshot(self) -> MemorySnapshot:
        return self.script.current()


def fake_reaper(port: int, **_kwargs) -> ReapResult:
    """Never inspect or signal real processes in tests."""
    return ReapResult(ok=True, port=port, killed_pids=[], error=None)


class FixedClock:
    """A manually advanced clock for deterministic timestamps."""

    def __init__(self, at: float = FIXED_CLOCK_AT):
        self.at = at

    def __call__(self) -> float:
        return self.at

    def advance(self, seconds: float) -> None:
        self.at += seconds
