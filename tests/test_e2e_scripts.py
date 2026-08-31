"""Deterministic behavior of the E2E script and gate primitives."""
import pytest

from desk.testing.scripts import (
    Done, DownloadControl, Exit, Gate, Line, ChatScript, MediaScript,
    MemoryScript, ScriptExhausted, ScriptStall, WRITE_OUTPUT,
    default_chat_steps, default_media_steps, fast_media_steps,
)


def test_gate_open_then_wait_passes_immediately():
    gate = Gate(timeout_s=0.05)
    gate.open()
    gate.wait()


def test_gate_starves_into_script_stall_not_hang():
    with pytest.raises(ScriptStall):
        Gate(timeout_s=0.05).wait()


def test_chat_script_default_has_three_gates_and_steps_open_in_order():
    script = ChatScript()
    gates = [step for step in script.steps if isinstance(step, Gate)]
    assert len(gates) == 3
    script.step(); script.step(); script.step()
    for gate in gates:
        gate.wait()
    with pytest.raises(ScriptExhausted):
        script.step()


def test_chat_script_run_to_end_opens_all_remaining_gates():
    script = ChatScript()
    script.step()
    script.run_to_end()
    for gate in [step for step in script.steps if isinstance(step, Gate)]:
        gate.wait()


def test_chat_default_steps_shape_matches_design():
    steps = default_chat_steps()
    deltas = [step for step in steps if hasattr(step, "reasoning")]
    assert [delta.reasoning for delta in deltas[:2]] == ["让我想想，", "想好了。"]
    assert [delta.content for delta in deltas[2:]] == ["你好", "，世界"]
    assert isinstance(steps[-1], Done) and steps[-1].finish_reason == "stop" and steps[-1].usage


def test_media_script_pops_jobs_and_exhausts():
    script = MediaScript(jobs=[fast_media_steps()])
    assert any(isinstance(step, Exit) for step in script.next_job())
    with pytest.raises(ScriptExhausted):
        script.next_job()


def test_media_script_step_opens_active_job_gates():
    script = MediaScript()
    job = script.next_job()
    gates = [step for step in job if isinstance(step, Gate)]
    assert len(gates) == 2
    script.step(); script.step()
    for gate in gates:
        gate.wait()
    with pytest.raises(ScriptExhausted):
        script.step()


def test_default_media_steps_write_output_then_exit_zero():
    steps = default_media_steps()
    assert steps[-2] is WRITE_OUTPUT and isinstance(steps[-1], Exit) and steps[-1].code == 0
    assert [step.text for step in steps if isinstance(step, Line)] == ["step 1/10", "step 5/10"]


def test_memory_script_repeats_last_and_advances_on_push():
    script = MemoryScript(["A"])
    assert script.current() == "A"
    assert script.current() == "A"
    script.push("B")
    assert script.current() == "A"
    assert script.current() == "B"
    assert script.current() == "B"


def test_memory_script_empty_is_error():
    with pytest.raises(ScriptExhausted):
        MemoryScript([]).current()


def test_download_control_parses_local_dir_and_writes_bytes(tmp_path):
    control = DownloadControl()
    dest = tmp_path / "models" / "llms" / "x"
    control.spawns.append(["hf", "download", "org/repo", "--local-dir", str(dest)])

    class Handle:
        exit_code = None
        terminated = False
        def exit(self, code): self.exit_code = code
    control.handles.append(Handle())

    control.advance("weights/a.safetensors", 300)
    assert (dest / "weights" / "a.safetensors").stat().st_size == 300
    control.finish([("weights/a.safetensors", 600), ("weights/b.safetensors", 400)])
    assert (dest / "weights" / "a.safetensors").stat().st_size == 600
    assert (dest / "weights" / "b.safetensors").stat().st_size == 400
    assert control.handle.exit_code == 0


def test_download_control_exit_terminated_requires_terminate_first(tmp_path):
    control = DownloadControl()
    control.spawns.append(["hf", "download", "r", "--local-dir", str(tmp_path)])

    class Handle:
        exit_code = None
        terminated = False
        def exit(self, code): self.exit_code = code
    control.handles.append(Handle())
    with pytest.raises(AssertionError):
        control.exit_terminated()
    control.handle.terminated = True
    control.exit_terminated()
    assert control.handle.exit_code == -15
