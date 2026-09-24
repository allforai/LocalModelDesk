from types import SimpleNamespace
from pathlib import Path
import json
import threading

import pytest

from desk.library.image_sessions import ImageSessionStore
from desk.media import service as service_mod
from desk.media.service import MediaError
from desk.media.routes import build_routes
from desk.resources.catalog import entry
from desk.resources.manifest import ManifestStore
from desk.resources.verify import verify_tree
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_image_cli import pipeline


def image_service(tmp_path, **kwargs):
    service, deps = make_service(tmp_path, **kwargs)
    model = entry("qwen-image")
    pipeline(tmp_path / "models" / model.relpath)
    roots = SimpleNamespace(models_root=tmp_path / "models", outputs_root=tmp_path / "outputs",
        image_python=Path("/fake/image-python"), image_env={"PYTHONPATH": "/fake/image"},
        media_cli_dir=Path("/fake/media"))
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {"image_runtime": SimpleNamespace(present=True)}
    service._list_catalog = lambda: [model]
    return service, deps


def new_session(deps) -> str:
    return deps.image_sessions.create()["id"]


def session_file(tmp_path, session_id) -> Path:
    return tmp_path / "image-sessions" / f"{session_id}.json"


def attempts(deps, session_id) -> list[dict]:
    return deps.image_sessions.get(session_id)["attempts"]


def start(service, session_id, **kwargs):
    return service.start_image_job(session_id=session_id, **{"prompt": "cat", **kwargs})


def image_route(service):
    return next(handler for method, path, handler in build_routes(service) if path == "/api/media/image")


# ---- parameter validation (unchanged behaviour) ----------------------------

@pytest.mark.parametrize("bad", [dict(width=True), dict(width=255), dict(height=257),
    dict(height=2064), dict(steps=0), dict(steps=True), dict(seed=-1), dict(seed=2**32),
    dict(seed=1.2), dict(force="false"), dict(prompt="")])
def test_invalid_image_params_do_not_spawn(tmp_path, bad):
    service, deps = make_service(tmp_path)
    session_id = new_session(deps)
    before = session_file(tmp_path, session_id).read_bytes()
    with pytest.raises(MediaError):
        service.start_image_job(**{**dict(prompt="cat", session_id=session_id), **bad})
    assert deps.executor.spawned == []
    assert deps.arbiter.acquired == []
    assert session_file(tmp_path, session_id).read_bytes() == before


def test_image_success_records_params_and_unique_png_names(tmp_path):
    service, deps = image_service(tmp_path)
    session_id = new_session(deps)
    first = dict(finished_snapshot(service, lambda: start(service, session_id, seed=123)))
    second = finished_snapshot(service, lambda: start(service, session_id, seed=123))
    assert first["status"] == second["status"] == "done"
    assert first["output"].endswith(".png") and first["output"] != second["output"]
    assert first["params"] == dict(prompt="cat", width=1024, height=1024, steps=40, seed=123)
    assert deps.executor.spawned[0]["cmd"][:3] == ["/fake/image-python", "-s", "/fake/media/image_cli.py"]
    assert deps.history.entries[0]["kind"] == "image"
    assert deps.arbiter.last_precheck["key"] == "qwen-image"
    assert len(deps.arbiter.released) == 2


# ---- session requirement (D-18) --------------------------------------------

@pytest.mark.parametrize("session_id", [None, 7, ["x"]])
def test_missing_session_is_400_session_required_and_nothing_starts(tmp_path, session_id):
    service, deps = image_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        service.start_image_job(session_id=session_id, prompt="cat")
    assert (exc.value.code, exc.value.http_status) == ("session_required", 400)
    assert exc.value.message == "请先选择或新建一个会话"
    assert deps.executor.spawned == [] and deps.arbiter.acquired == []


@pytest.mark.parametrize("session_id", ["0" * 32, "../../etc/passwd", ""])
def test_unknown_session_is_404_session_not_found_and_nothing_starts(tmp_path, session_id):
    service, deps = image_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        start(service, session_id)
    assert (exc.value.code, exc.value.http_status) == ("session_not_found", 404)
    assert exc.value.message == "这个会话已被删除，请选择或新建一个会话"
    assert deps.executor.spawned == [] and deps.arbiter.acquired == []


def test_param_errors_win_over_session_errors(tmp_path):
    service, _ = image_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        service.start_image_job(session_id=None, prompt="cat", steps=0)
    assert exc.value.code == "invalid_params"


# ---- attempt lifecycle: begin + four settle paths (D-20, D-24) --------------

def test_started_job_appends_running_attempt_with_actual_params(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("block"))
    session_id = new_session(deps)
    snap = start(service, session_id, prompt="一只橘猫", width=512, height=768, steps=20, seed=99)
    try:
        assert snap["session_id"] == session_id and len(snap["attempt_id"]) == 32
        assert service.job_status()["attempt_id"] == snap["attempt_id"]
        [attempt] = attempts(deps, session_id)
        assert attempt["id"] == snap["attempt_id"]
        assert attempt["job_id"] == snap["job_id"]
        assert attempt["status"] == "running"
        assert attempt["finished"] is None and attempt["output"] is None and attempt["error"] is None
        assert attempt["params"] == dict(prompt="一只橘猫", width=512, height=768, steps=20, seed=99)
        assert deps.image_sessions.get(session_id)["title"] == "一只橘猫"
    finally:
        finished_snapshot(service, service.cancel_job)


def test_attempt_begins_only_once_job_is_running(tmp_path):
    service, deps = image_service(tmp_path)
    seen = []
    real_begin = deps.image_sessions.begin_attempt

    def spy(session_id, attempt):
        seen.append((service.job_status()["status"], len(deps.executor.spawned)))
        return real_begin(session_id, attempt)

    deps.image_sessions.begin_attempt = spy
    finished_snapshot(service, lambda: start(service, new_session(deps)))
    assert seen == [("running", 1)]


def test_done_settles_attempt_with_output(tmp_path):
    service, deps = image_service(tmp_path)
    session_id = new_session(deps)
    snap = finished_snapshot(service, lambda: start(service, session_id, seed=5))
    [attempt] = attempts(deps, session_id)
    assert attempt["status"] == "done"
    assert attempt["output"] == snap["output"] and attempt["output_missing"] is False
    assert attempt["error"] is None and attempt["finished"]
    assert (tmp_path / "outputs" / snap["output"]).is_file()
    history = deps.history.entries[-1]
    assert (history["session_id"], history["attempt_id"]) == (session_id, attempt["id"])


def test_failure_settles_attempt_failed_with_worker_error_and_log_tail(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("fail"))
    session_id = new_session(deps)
    snap = finished_snapshot(service, lambda: start(service, session_id))
    assert snap["status"] == "error"
    [attempt] = attempts(deps, session_id)
    assert attempt["status"] == "failed" and attempt["output"] is None and attempt["finished"]
    assert attempt["error"] == snap["error"]
    assert attempt["error"]["code"] == "exit_nonzero" and "line-2" in attempt["error"]["log_tail"]
    assert deps.arbiter.released == ["permit-1"]


def test_user_cancel_settles_attempt_cancelled(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("block"))
    session_id = new_session(deps)
    snap = finished_snapshot(service, lambda: (start(service, session_id), service.cancel_job()))
    assert snap["status"] == "cancelled" and snap["output"] is None
    [attempt] = attempts(deps, session_id)
    assert attempt["status"] == "cancelled" and attempt["output"] is None and attempt["finished"]
    assert attempt["error"] == {"code": "cancelled", "message": "已取消：这次生成被手动停止"}
    assert deps.arbiter.released == ["permit-1"]
    service._executor = FakeExecutor("success")
    assert finished_snapshot(service, lambda: start(service, session_id, prompt="retry"))["status"] == "done"
    assert [a["status"] for a in attempts(deps, session_id)] == ["cancelled", "done"]


def test_close_settles_attempt_cancelled_on_quit_before_returning(tmp_path):
    """Shutdown must not leave a running attempt behind (lost_attempt_on_shutdown)."""
    service, deps = image_service(tmp_path, executor=FakeExecutor("block"))
    service._term_grace_s = 0.01
    session_id = new_session(deps)
    start(service, session_id)
    service.close()  # no waiting after this: settle must already be on disk
    [attempt] = json.loads(session_file(tmp_path, session_id).read_text("utf-8"))["attempts"]
    assert attempt["status"] == "cancelled" and attempt["finished"]
    assert attempt["error"] == {"code": "cancelled_on_quit", "message": "应用退出时停止了这次生成"}
    assert deps.arbiter.released == ["permit-1"]


def test_user_cancel_then_quit_stays_a_user_cancel(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("block", ignore_term=True))
    service._term_grace_s = 0.05
    session_id = new_session(deps)
    start(service, session_id)
    canceller = threading.Thread(target=service.cancel_job)
    canceller.start()
    while not service._cancel_requested:
        threading.Event().wait(0.005)
    service.close()
    canceller.join(5)
    assert attempts(deps, session_id)[0]["error"]["code"] == "cancelled"


def test_worker_failure_releases(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("fail"))
    snap = finished_snapshot(service, lambda: start(service, new_session(deps)))
    assert snap["status"] == "error"
    assert deps.arbiter.released == ["permit-1"]


# ---- refusals before the job runs never write the session (D-21) ------------

def _refusal_cases():
    def busy(service, deps, tmp_path):
        other = new_session(deps)
        service._executor = FakeExecutor("block")
        start(service, other)
        return lambda: finished_snapshot(service, service.cancel_job)

    def capability(service, deps, tmp_path):
        service._probe_capabilities = lambda: {"image_runtime": SimpleNamespace(present=False, detail="x")}

    def model(service, deps, tmp_path):
        (tmp_path / "models" / entry("qwen-image").relpath / "processor/tokenizer.json").unlink()

    def arbiter(service, deps, tmp_path):
        deps.arbiter.can_start_heavy = lambda *a, **k: {"ok": False, "reason": {"code": "chat_busy", "message": "m"}}

    def acquire(service, deps, tmp_path):
        deps.arbiter.acquire_heavy = lambda *a, **k: {"ok": False, "reason": {"code": "held", "message": "m"}}

    def memory(service, deps, tmp_path):
        deps.arbiter.memory_warning = {"required_bytes": 52 * 1024**3, "available_bytes": 1}

    def spawn(service, deps, tmp_path):
        class SpawnFailure:
            def spawn(self, *_a, **_k):
                raise OSError("executor unavailable")
        service._executor = SpawnFailure()

    return [("media_busy", 409, busy), ("capability_missing", 503, capability),
            ("model_incomplete", 409, model), ("chat_busy", 409, arbiter), ("held", 409, acquire),
            ("insufficient_memory", 409, memory), ("spawn_failed", 500, spawn)]


@pytest.mark.parametrize("code,status,arrange", _refusal_cases(), ids=[c[0] for c in _refusal_cases()])
def test_start_refusals_leave_session_file_untouched(tmp_path, code, status, arrange):
    service, deps = image_service(tmp_path)
    session_id = new_session(deps)
    cleanup = arrange(service, deps, tmp_path)
    before = session_file(tmp_path, session_id).read_bytes()
    try:
        with pytest.raises(MediaError) as exc:
            start(service, session_id)
        assert (exc.value.code, exc.value.http_status) == (code, status)
        assert session_file(tmp_path, session_id).read_bytes() == before
    finally:
        if cleanup:
            cleanup()


def test_missing_model_is_rejected_before_arbiter(tmp_path):
    service, deps = image_service(tmp_path)
    (tmp_path / "models" / entry("qwen-image").relpath / "processor/tokenizer.json").unlink()
    with pytest.raises(MediaError, match="缺失") as exc:
        start(service, new_session(deps))
    assert exc.value.code == "model_incomplete"
    assert not deps.arbiter.acquired


def test_image_memory_warning_requires_explicit_force(tmp_path):
    service, deps = image_service(tmp_path, memory_warning={"required_bytes": 52*1024**3, "available_bytes": 1})
    session_id = new_session(deps)
    with pytest.raises(MediaError) as exc:
        start(service, session_id)
    assert exc.value.code == "insufficient_memory"
    assert not deps.arbiter.acquired
    assert attempts(deps, session_id) == []
    assert finished_snapshot(service, lambda: start(service, session_id, force=True))["status"] == "done"
    assert [a["status"] for a in attempts(deps, session_id)] == ["done"]


# ---- the session disappears (D-23, D-31) ------------------------------------

def test_session_deleted_before_begin_runs_job_unattached(tmp_path):
    class VanishingStore(ImageSessionStore):
        def exists(self, session_id):
            found = super().exists(session_id)
            self.delete(session_id)  # deleted between the check and the job start
            return found

    store = VanishingStore(tmp_path / "image-sessions", tmp_path / "outputs")
    service, deps = image_service(tmp_path, image_sessions=store)
    session_id = store.create()["id"]
    snap = finished_snapshot(service, lambda: start(service, session_id))
    assert snap["status"] == "done" and (tmp_path / "outputs" / snap["output"]).is_file()
    assert snap["session_id"] is None and snap["attempt_id"] is None
    assert not session_file(tmp_path, session_id).exists()
    assert deps.history.entries[-1]["output"] == snap["output"]
    assert deps.history.entries[-1]["session_id"] is None


def test_session_deleted_while_running_drops_settle_and_keeps_image(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("block"))
    session_id = new_session(deps)
    started = start(service, session_id)
    deps.image_sessions.delete(session_id)
    handle_output = Path(deps.executor.spawned[0]["cmd"][deps.executor.spawned[0]["cmd"].index("--output") + 1])
    handle_output.write_bytes(b"png")

    done = threading.Event()
    service.on_job_finished(lambda _snap: done.set())
    service._handle.exit(0)
    assert done.wait(5)
    assert service.job_status()["status"] == "done"
    assert not session_file(tmp_path, session_id).exists()
    assert (tmp_path / "outputs" / handle_output.name).is_file()
    entry_ = deps.history.entries[-1]
    assert (entry_["session_id"], entry_["attempt_id"], entry_["output"]) == (
        session_id, started["attempt_id"], handle_output.name)


def test_store_failures_never_break_the_job(tmp_path):
    class BrokenStore(ImageSessionStore):
        def settle_attempt(self, *args, **kwargs):
            raise OSError("disk full")

    store = BrokenStore(tmp_path / "image-sessions", tmp_path / "outputs")
    service, deps = image_service(tmp_path, image_sessions=store)
    fired = []
    service.on_job_finished(fired.append)
    snap = finished_snapshot(service, lambda: start(service, store.create()["id"]))
    assert snap["status"] == "done"
    assert deps.arbiter.released == ["permit-1"]
    assert deps.history.entries and fired


# ---- seed (D-19) --------------------------------------------------------------

def test_omitted_seed_is_random_and_recorded_as_used(tmp_path, monkeypatch):
    service, deps = image_service(tmp_path)
    monkeypatch.setattr(service_mod.secrets, "randbelow", lambda bound: bound - 1)
    session_id = new_session(deps)
    snap = finished_snapshot(service, lambda: start(service, session_id))
    assert snap["params"]["seed"] == 2**32 - 1
    assert attempts(deps, session_id)[0]["params"]["seed"] == 2**32 - 1
    cmd = deps.executor.spawned[0]["cmd"]
    assert cmd[cmd.index("--seed") + 1] == str(2**32 - 1)


def test_omitted_seed_differs_between_jobs(tmp_path):
    service, deps = image_service(tmp_path)
    session_id = new_session(deps)
    for _ in range(3):
        finished_snapshot(service, lambda: start(service, session_id))
    seeds = [a["params"]["seed"] for a in attempts(deps, session_id)]
    assert all(isinstance(s, int) and 0 <= s < 2**32 for s in seeds)
    assert len(set(seeds)) > 1


# ---- route (§3.6) ---------------------------------------------------------------

def test_image_route_requires_session_and_rejects_truthy_string_force(tmp_path, monkeypatch):
    service, deps = image_service(tmp_path)
    route = image_route(service)
    session_id = new_session(deps)
    assert route({"prompt": "cat", "session_id": session_id, "force": "false"}, {})[0] == 400
    status, body = route({"prompt": "cat"}, {})
    assert status == 400 and body["error"]["code"] == "session_required"
    assert body["error"]["message"] == "请先选择或新建一个会话"
    status, body = route({"prompt": "cat", "session_id": "f" * 32}, {})
    assert status == 404 and body["error"]["code"] == "session_not_found"
    monkeypatch.setattr(service_mod.secrets, "randbelow", lambda bound: 7)
    done = threading.Event()
    service.on_job_finished(lambda _snap: done.set())
    status, body = route({"prompt": "cat", "session_id": session_id}, {})
    assert status == 200 and done.wait(5)
    assert body["session_id"] == session_id and body["attempt_id"] == attempts(deps, session_id)[0]["id"]
    assert body["params"]["seed"] == 7  # no fixed default of 42 any more


def test_non_image_jobs_carry_null_session_fields(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: service.start_video_job(
        prompt="rain", width=512, height=288, frames=73, steps=10))
    assert snap["session_id"] is None and snap["attempt_id"] is None
    assert "session_id" not in deps.history.entries[-1]


def test_image_manifest_is_pinned_offline_and_describes_two_sources(tmp_path):
    model = entry("qwen-image")
    store = ManifestStore(lambda: tmp_path, fetcher=lambda _: pytest.fail("must not fetch main"))
    manifest = store.get(model, refresh=True)
    assert manifest.source == "pinned"
    assert len({f.repo for f in manifest.files}) == 2
    assert all(len(f.revision) == 40 for f in manifest.files)
    pipeline(tmp_path / model.relpath)
    assert verify_tree(model, manifest, tmp_path).state == "present"
    (tmp_path / model.relpath / "localmodeldesk-image.json").unlink()
    assert verify_tree(model, manifest, tmp_path).state == "partial"
