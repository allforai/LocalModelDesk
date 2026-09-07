"""MediaService video success path."""
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.media.service import MediaError
from media_fakes import FIXED_TIME, STAMP, FakeExecutor, finished_snapshot, make_service


def start_video(service):
    return service.start_video_job(prompt="rain on a quiet street", width=512,
        height=288, frames=73, steps=10)


@pytest.fixture
def service_factory(tmp_path):
    def factory(*, memory_warning=None, executor=None):
        service, deps = make_service(tmp_path, executor=executor, memory_warning=memory_warning)
        return service, deps.arbiter
    return factory


def wait_until(get_state, predicate, timeout=5.0):
    import time as _time
    deadline = _time.time() + timeout
    state = get_state()
    while not predicate(state):
        if _time.time() > deadline:
            pytest.fail("condition did not become true in time")
        _time.sleep(0.01)
        state = get_state()
    return state


def test_initial_job_state_shape(tmp_path):
    state = make_service(tmp_path)[0].job_status()
    assert state == {"job_id": 0, "status": "idle", "kind": None, "params": None,
        "output": None, "error": None, "started_at": None, "finished_at": None,
        "log": "", "next_log_from": 0, "log_len": 0, "log_truncated": False}


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


def test_start_video_job_success_path(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: start_video(service))
    assert snap["status"] == "done"
    assert snap["output"] == f"h3-{STAMP}.mp4"
    assert snap["params"] == {"prompt": "rain on a quiet street", "width": 512,
        "height": 288, "frames": 73, "steps": 10}
    assert snap["started_at"] == snap["finished_at"] == FIXED_TIME
    assert "line-1" in snap["log"]
    assert deps.arbiter.acquired == [("video", "job-1", "permit-1")]
    assert deps.arbiter.released == ["permit-1"]
    assert deps.history.entries == [{"kind": "video", "status": "done", "params": snap["params"],
        "output": f"h3-{STAMP}.mp4", "duration_s": 0.0, "error": None}]


def test_video_argv_and_running_state(tmp_path):
    from desk.media.commands import build_h3_command

    service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
    completed = threading.Event()
    service.on_job_finished(lambda _: completed.set())
    state = start_video(service)
    assert state["status"] == "running"
    assert deps.executor.spawned == [{"cmd": build_h3_command(
        ("/fake/bin/mlx-h3",), tmp_path / "models" / "minimax-h3",
        prompt="rain on a quiet street", width=512, height=288, frames=73,
        steps=10, output=tmp_path / "outputs" / f"h3-{STAMP}.mp4"),
        "extra_env": {"PYTHONPATH": "/fake/pylibs/h3"}}]
    service.cancel_job()
    assert completed.wait(5)


def test_concurrent_start_allows_one_running_job_and_releases_its_permit_once(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
    start = threading.Barrier(2)
    finished = threading.Event()
    results, errors = [], []
    lock = threading.Lock()
    service.on_job_finished(lambda _: finished.set())

    def attempt_start():
        start.wait(timeout=5)
        try:
            result = start_video(service)
            with lock:
                results.append(result)
        except MediaError as exc:
            with lock:
                errors.append(exc)

    starters = [threading.Thread(target=attempt_start) for _ in range(2)]
    for starter in starters:
        starter.start()
    for starter in starters:
        starter.join(timeout=5)

    assert not any(starter.is_alive() for starter in starters)
    assert len(results) == 1
    assert results[0]["status"] == "running"
    assert len(errors) == 1
    assert errors[0].code == "media_busy"
    assert errors[0].http_status == 409
    assert len(deps.executor.spawned) == 1
    assert len(deps.arbiter.acquired) == 1

    service.cancel_job()

    assert finished.wait(5)
    assert deps.arbiter.released == ["permit-1"]


def test_start_music_job_argv_output_and_runtime_capability(tmp_path):
    """Music jobs use the dedicated runtime, argv, and WAV output convention."""
    from desk.media.commands import build_music_command

    service, deps = make_service(tmp_path)
    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        music_python=Path("/fake/bin/music-python"), media_cli_dir=Path("/fake/media"),
        music_env={"PYTHONPATH": "/fake/pylibs/music"},
    )
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {
        "music_runtime": SimpleNamespace(present=True, detail=""),
    }
    service._list_catalog = lambda: [
        SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0),
    ]

    snap = finished_snapshot(service, lambda: service.start_music_job(
        caption="ambient piano", lyrics="instrumental", duration=30.0))

    output = tmp_path / "outputs" / f"music3-{STAMP}.wav"
    assert snap["status"] == "done"
    assert snap["output"] == output.name
    assert deps.executor.spawned == [{"cmd": build_music_command(
        roots.music_python, roots.media_cli_dir / "music3_cli.py",
        tmp_path / "models" / "minimax-music3", caption="ambient piano",
        lyrics="instrumental", duration=30.0, output=output),
        "extra_env": roots.music_env}]

    service, deps = make_service(tmp_path)
    service._probe_capabilities = lambda: {}
    with pytest.raises(MediaError) as err:
        service.start_music_job(caption="ambient piano", lyrics="instrumental", duration=30.0)
    assert err.value.code == "capability_missing"
    assert err.value.http_status == 503
    assert deps.executor.spawned == []


class TestStartDiscipline:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    @pytest.mark.parametrize("bad", [
        dict(prompt=""), dict(prompt="   "), dict(prompt=None),
        dict(width=0), dict(width=-1), dict(width="512"), dict(width=True),
        dict(height=0), dict(frames=0), dict(steps=0),
    ])
    def test_invalid_video_params_never_touch_arbiter_or_spawn(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**{**self.VALID, **bad})
        assert err.value.code == "invalid_params"
        assert err.value.http_status == 400
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []
        assert service.job_status()["status"] == "idle"

    @pytest.mark.parametrize("bad", [
        dict(caption=""), dict(caption=None), dict(lyrics=None),
        dict(duration=0), dict(duration=-3.0), dict(duration="30"),
    ])
    def test_invalid_music_params_never_spawns(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        valid = dict(caption="c", lyrics="l", duration=30.0)
        with pytest.raises(MediaError) as err:
            service.start_music_job(**{**valid, **bad})
        assert err.value.code == "invalid_params"
        assert err.value.http_status == 400
        assert deps.executor.spawned == []

    def test_missing_capability_is_503_and_arbiter_untouched(self, tmp_path):
        service, deps = make_service(tmp_path)
        service._probe_capabilities = lambda: {}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "capability_missing"
        assert err.value.http_status == 503
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []

    def test_can_start_refusal_passes_code_and_holder_through(self, tmp_path):
        service, deps = make_service(tmp_path)
        reason = {"code": "transition_in_progress", "message": "evicting now", "holder": {"kind": "llm"}}
        deps.arbiter.can_start_heavy = lambda _kind, estimated_bytes=None: {"ok": False, "reason": reason}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "transition_in_progress"
        assert err.value.http_status == 409
        assert err.value.detail == reason
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []

    def test_acquire_refusal_never_spawns_and_state_unchanged(self, tmp_path):
        service, deps = make_service(tmp_path)
        reason = {"code": "evict_failed", "message": "still listening", "holder": {"kind": "llm"}}
        deps.arbiter.acquire_heavy = lambda *_: {"ok": False, "reason": reason}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "evict_failed"
        assert err.value.detail == reason
        assert deps.executor.spawned == []
        assert deps.arbiter.released == []
        assert service.job_status()["status"] == "idle"


def test_nonzero_exit_records_log_tail(service_factory):
    svc, _arbiter = service_factory(executor=FakeExecutor("block", lines=()))
    svc.start_video_job(prompt="x", width=512, height=288, frames=49, steps=16)
    handle = svc._handle
    handle.emit("step 1/16\n"); handle.emit("Traceback\n"); handle.emit("mlx_h3.memory.BudgetExceeded: SWAPPING\n")
    handle.exit(1)
    final = wait_until(lambda: svc.job_status(), lambda s: s["status"] == "error")
    assert final["error"]["code"] == "exit_nonzero"
    assert final["error"]["log_tail"].splitlines()[-1] == "mlx_h3.memory.BudgetExceeded: SWAPPING"


@pytest.mark.parametrize(("script", "code"), [("no_output", "no_output"), ("fail", "exit_nonzero")])
def test_failed_process_releases_permit_and_records_terminal_failure(tmp_path, script, code):
    service, deps = make_service(tmp_path, executor=FakeExecutor(script))

    snap = finished_snapshot(service, lambda: start_video(service))

    assert snap["status"] == "error"
    assert snap["output"] is None
    assert snap["error"]["code"] == code
    assert deps.arbiter.released == ["permit-1"]
    assert deps.history.entries[0]["status"] == "failed"


def test_spawn_failure_is_terminal_and_releases_permit(tmp_path):
    class SpawnFailure:
        def spawn(self, *_args, **_kwargs):
            raise OSError("executor unavailable")

    service, deps = make_service(tmp_path, executor=SpawnFailure())

    with pytest.raises(MediaError) as err:
        start_video(service)

    assert err.value.code == "spawn_failed"
    assert service.job_status()["status"] == "error"
    assert service.job_status()["error"]["code"] == "spawn_failed"
    assert deps.arbiter.released == ["permit-1"]


def test_history_failure_does_not_change_terminal_status_or_leak_permit(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor("fail"))

    def fail_history(_entry):
        raise OSError("history disk full")

    service._append_history = fail_history
    snap = finished_snapshot(service, lambda: start_video(service))

    assert snap["status"] == "error"
    assert snap["error"]["code"] == "exit_nonzero"
    assert service.job_status()["status"] == "error"
    assert deps.arbiter.released == ["permit-1"]


class TestCancel:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def _start_blocking(self, tmp_path, **executor_kwargs):
        class RecordingExecutor(FakeExecutor):
            def __init__(self):
                super().__init__("block", **executor_kwargs)
                self.handles = []
                self.signals = []

            def spawn(self, *args, **kwargs):
                handle = super().spawn(*args, **kwargs)
                terminate, kill = handle.terminate, handle.kill

                def record_terminate():
                    self.signals.append("terminate")
                    terminate()

                def record_kill():
                    self.signals.append("kill")
                    kill()

                handle.terminate, handle.kill = record_terminate, record_kill
                self.handles.append(handle)
                return handle

        executor = RecordingExecutor()
        service, deps = make_service(tmp_path, executor=executor)
        service._term_grace_s = 0.01
        done = threading.Event()
        service.on_job_finished(lambda _: done.set())
        service.start_video_job(**self.VALID)
        return service, deps, done

    def test_cancel_running_job_exit_zero_stays_cancelled(self, tmp_path):
        service, deps, done = self._start_blocking(tmp_path)

        service.cancel_job()

        assert done.wait(5.0)
        assert deps.executor.handles[0].terminated
        snap = service.job_status()
        assert snap["status"] == "cancelled"
        assert snap["error"] is None
        assert deps.arbiter.released == ["permit-1"]
        assert deps.history.entries[0]["status"] == "cancelled"

    def test_cancel_escalates_to_kill_after_ignored_terminate(self, tmp_path):
        service, deps, done = self._start_blocking(tmp_path, ignore_term=True)

        service.cancel_job()

        assert done.wait(5.0)
        handle = deps.executor.handles[0]
        assert handle.terminated and handle.killed
        assert deps.executor.signals == ["terminate", "kill"]
        assert service.job_status()["status"] == "cancelled"

    @pytest.mark.parametrize("finish_first", [False, True])
    def test_cancel_without_running_job_is_409(self, tmp_path, finish_first):
        service, _ = make_service(tmp_path)
        if finish_first:
            finished_snapshot(service, lambda: service.start_video_job(**self.VALID))

        with pytest.raises(MediaError) as err:
            service.cancel_job()

        assert err.value.code == "no_running_job"
        assert err.value.http_status == 409


class TestLogCursor:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    @staticmethod
    def _blocking_service(tmp_path, *, log_limit=1024 * 1024):
        class RecordingExecutor(FakeExecutor):
            def __init__(self):
                super().__init__("block", lines=())
                self.handles = []

            def spawn(self, *args, **kwargs):
                handle = super().spawn(*args, **kwargs)
                self.handles.append(handle)
                return handle

        executor = RecordingExecutor()
        service, deps = make_service(tmp_path, executor=executor)
        service._log_limit = log_limit
        done = threading.Event()
        service.on_job_finished(lambda _: done.set())
        service.start_video_job(**TestLogCursor.VALID)
        return service, deps, done

    @staticmethod
    def _wait_for(predicate):
        for _ in range(100):
            if predicate():
                return
            threading.Event().wait(0.01)
        pytest.fail("condition did not become true")

    def test_incremental_cursor(self, tmp_path):
        service, deps, done = self._blocking_service(tmp_path)
        handle = deps.executor.handles[0]
        handle._queue.put("alpha")
        self._wait_for(lambda: "alpha" in service.job_status()["log"])

        first = service.job_status()
        assert first["log"] == "alpha\n"
        handle._queue.put("beta")
        self._wait_for(lambda: service.job_status()["next_log_from"] > first["next_log_from"])

        second = service.job_status(log_from=first["next_log_from"], job_id=first["job_id"])
        assert second["log"] == "beta\n"
        assert second["next_log_from"] == first["next_log_from"] + len("beta\n")
        service.cancel_job()
        assert done.wait(5.0)

    def test_stale_job_id_resends_full_log(self, tmp_path):
        service, _ = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        full_log = service.job_status()["log"]

        replay = service.job_status(log_from=len(full_log), job_id=999)
        assert replay["log"] == full_log

    def test_truncation_keeps_absolute_cursor_and_marks_response(self, tmp_path):
        service, deps, done = self._blocking_service(tmp_path, log_limit=32)
        handle = deps.executor.handles[0]
        for index in range(10):
            handle._queue.put(f"line-{index:04d}")
        self._wait_for(lambda: service.job_status()["log_truncated"])

        state = service.job_status()
        assert state["log_truncated"] is True
        assert len(state["log"]) <= 32
        assert state["log_len"] > 32
        assert state["next_log_from"] == state["log_len"]
        assert service.job_status(log_from=state["next_log_from"])["log"] == ""
        service.cancel_job()
        assert done.wait(5.0)


class TestJobFinishedEvent:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def test_payload_is_terminal_snapshot(self, tmp_path):
        service, _ = make_service(tmp_path)
        events: list[dict] = []
        service.on_job_finished(events.append)

        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))

        assert len(events) == 1
        snap = events[0]
        assert snap["status"] == "done"
        assert snap["output"] == f"h3-{STAMP}.mp4"
        assert snap["params"]["prompt"] == "p"

    def test_broken_subscriber_does_not_break_others_or_job(self, tmp_path):
        service, deps = make_service(tmp_path)
        seen: list[dict] = []

        def bad(_snap):
            raise RuntimeError("subscriber bug")

        service.on_job_finished(bad)
        service.on_job_finished(seen.append)
        snap = finished_snapshot(service, lambda: service.start_video_job(**self.VALID))

        assert snap["status"] == "done"
        assert len(seen) == 1
        assert deps.history.entries[0]["status"] == "done"

    def test_unsubscribe_stops_delivery(self, tmp_path):
        service, _ = make_service(tmp_path)
        seen: list[dict] = []
        unsubscribe = service.on_job_finished(seen.append)
        unsubscribe()

        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))

        assert seen == []

    @pytest.mark.parametrize(("script", "status"), [
        ("success", "done"), ("no_output", "error"), ("fail", "error"),
    ])
    def test_event_fires_for_every_terminal_state(self, tmp_path, script, status):
        service, _ = make_service(tmp_path / script, executor=FakeExecutor(script))

        snap = finished_snapshot(service, lambda: service.start_video_job(**self.VALID))

        assert snap["status"] == status
