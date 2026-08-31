"""Unit tests for deterministic end-to-end test doubles."""
import threading

import pytest

from desk.arbiter.memory import MemorySnapshot
from desk.testing.scripts import (
    ChatScript, Delta, Done, DownloadControl, Gate, MediaScript,
    ScriptExhausted, cancellable_media_steps, fast_media_steps,
)
from desk.testing.fakes import (
    DEFAULT_SNAPSHOT_A, FIXED_CLOCK_AT, FakeDownloadExecutor, FakeLlmBackend,
    FakeMediaExecutor, FakeMemoryReader, FixedClock, fake_reaper,
)
from desk.testing.seed import TINY_MP4, TINY_WAV


def test_fake_llm_backend_spawn_is_alive_and_logs(tmp_path):
    backend = FakeLlmBackend(ChatScript())
    process = backend.spawn(tmp_path / "py", tmp_path / "model", 65001, tmp_path / "logs" / "mlx-lm.log")
    assert process.poll() is None
    assert backend.health(65001) is True
    assert "fake mlx-lm" in (tmp_path / "logs" / "mlx-lm.log").read_text()
    process.terminate()
    assert process.poll() == 0 and backend.health(65001) is False


def test_fake_llm_chat_stream_yields_mlx_shaped_chunks_and_records_payload():
    script = ChatScript(steps=[Delta(reasoning="r1"), Delta(content="c1"), Done(usage={"total_tokens": 2})])
    backend = FakeLlmBackend(script)
    chunks = list(backend.chat_stream(65001, {"messages": [{"role": "user", "content": "hi"}]}))
    assert chunks[0]["choices"][0]["delta"] == {"reasoning_content": "r1"}
    assert chunks[1]["choices"][0]["delta"] == {"content": "c1"}
    assert chunks[2]["usage"] == {"total_tokens": 2}
    assert chunks[2]["choices"][0]["finish_reason"] == "stop"
    assert script.requests == [{"messages": [{"role": "user", "content": "hi"}]}]
    with pytest.raises(ScriptExhausted):
        list(backend.chat_stream(65001, {}))


def test_fake_llm_chat_stream_blocks_on_gate_until_step():
    gate = Gate(timeout_s=2.0)
    script = ChatScript(steps=[Delta(content="a"), gate, Delta(content="b"), Done(usage={})])
    backend = FakeLlmBackend(script)
    received, done = [], threading.Event()

    def consume():
        for chunk in backend.chat_stream(1, {}):
            received.append(chunk)
        done.set()

    threading.Thread(target=consume, daemon=True).start()
    for _ in range(200):
        if len(received) == 1:
            break
        threading.Event().wait(0.01)
    assert len(received) == 1 and not done.is_set()
    script.step()
    assert done.wait(2.0) and len(received) == 3


def test_fake_media_executor_writes_real_tiny_output(tmp_path):
    script = MediaScript(jobs=[fast_media_steps(), fast_media_steps()])
    executor = FakeMediaExecutor(script)
    output_mp4 = tmp_path / "h3-x.mp4"
    handle = executor.spawn(["mlx-h3", "p", "--output", str(output_mp4)])
    assert list(handle.iter_output()) == ["step 1/10", "step 10/10"]
    assert handle.wait() == 0
    assert output_mp4.read_bytes() == TINY_MP4
    output_wav = tmp_path / "music3-x.wav"
    handle_wav = executor.spawn(["python", "cli.py", "--output", str(output_wav)])
    list(handle_wav.iter_output())
    assert output_wav.read_bytes() == TINY_WAV
    assert script.spawned_argvs[0][0] == "mlx-h3"


def test_fake_media_handle_blocks_until_terminate(tmp_path):
    script = MediaScript(jobs=[cancellable_media_steps()])
    script.jobs[0][1].open()
    executor = FakeMediaExecutor(script)
    handle = executor.spawn(["mlx-h3", "p", "--output", str(tmp_path / "o.mp4")])
    lines, finished = [], threading.Event()

    def run():
        for line in handle.iter_output():
            lines.append(line)
        finished.set()

    threading.Thread(target=run, daemon=True).start()
    for _ in range(200):
        if lines:
            break
        threading.Event().wait(0.01)
    assert lines == ["step 1/10"] and not finished.is_set()
    handle.terminate()
    assert finished.wait(2.0)
    assert handle.wait() != 0 and handle.terminated
    assert not (tmp_path / "o.mp4").exists()


def test_fake_download_executor_records_and_is_test_controlled(tmp_path):
    control = DownloadControl()
    executor = FakeDownloadExecutor(control)
    handle = executor.spawn(["hf", "download", "org/r", "--local-dir", str(tmp_path / "d")], cwd=None)
    assert control.spawns[-1][0] == "hf" and control.handle is handle
    assert handle.poll() is None
    handle.terminate()
    assert handle.terminated and handle.poll() is None
    control.exit_terminated()
    assert handle.poll() == -15


def test_fake_memory_reader_returns_snapshots_from_script():
    from desk.testing.scripts import MemoryScript

    reader = FakeMemoryReader(MemoryScript([DEFAULT_SNAPSHOT_A]))
    snapshot = reader.snapshot()
    assert isinstance(snapshot, MemorySnapshot)
    assert snapshot.total_bytes == DEFAULT_SNAPSHOT_A.total_bytes
    assert "128" not in str(snapshot.total_bytes) + str(snapshot.used_bytes) + str(snapshot.available_bytes)


def test_fake_reaper_never_touches_processes():
    result = fake_reaper(64999)
    assert result.ok is True and result.killed_pids == [] and result.port == 64999


def test_fixed_clock_is_fixed_until_advanced():
    clock = FixedClock()
    assert clock() == FIXED_CLOCK_AT == clock()
    clock.advance(3.5)
    assert clock() == FIXED_CLOCK_AT + 3.5
