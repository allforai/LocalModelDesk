"""Manual compose jobs (B §3.5)."""
import threading
from pathlib import Path

import pytest

from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_continue import attempts, fake_ffmpeg, first_segment  # noqa: F401  (autouse fixture)
from test_media_sessions_service import video


def two_segments(service, deps):
    sid, first = first_segment(service, deps)
    second = finished_snapshot(service, lambda: video(service, session_id=sid))["attempt_id"]
    return sid, first, second


class PartialOutputExecutor(FakeExecutor):
    """Like real ffmpeg, writes a (stub) output file as it runs — before the compose
    job's own outcome (cancelled / failed) is known — so a cancel or failure leaves a
    partial ``*-compose-*`` file behind unless the worker cleans it up (B-45–B-47)."""

    def spawn(self, cmd, *, extra_env=None):
        if "--output" not in cmd:  # ffmpeg join/compose commands: target is the last argv
            target = Path(cmd[-1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"partial-ffmpeg-output")
        return super().spawn(cmd, extra_env=extra_env)


def test_compose_appends_a_compose_attempt_without_arbiter_or_memory(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    acquired = len(deps.arbiter.acquired); prechecks = len(deps.arbiter.precheck_calls)
    snap = finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[second, first, second]))
    assert len(deps.arbiter.acquired) == acquired and len(deps.arbiter.precheck_calls) == prechecks
    made = attempts(deps, "video", sid)[-1]
    assert made["op"] == "compose" and made["params"] == {"parts": [second, first, second]}
    assert made["status"] == "done" and made["output"].startswith("h3-compose-") and snap["output"] == made["output"]
    graph = deps.executor.spawned[-1]["cmd"][deps.executor.spawned[-1]["cmd"].index("-filter_complex") + 1]
    assert "trim" not in graph            # 手动乱序：没有续写关系，不丢帧（B-50）
    assert deps.history.entries[-1]["params"]["op"] == "compose"


def test_compose_can_be_continued(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    composed = finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[first, second]))["attempt_id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=composed))
    last = attempts(deps, "video", sid)[-1]
    assert last["joined_output"] and last["continues"] == composed


@pytest.mark.parametrize("kwargs, code, status", [
    ({"kind": "image"}, "invalid_params", 400),
    ({"parts": ["only-one"]}, "invalid_params", 400),
    ({"parts": "nope"}, "invalid_params", 400),
    ({"parts": ["9" * 32, "8" * 32]}, "segment_not_found", 404),
])
def test_bad_compose_requests_write_nothing(tmp_path, kwargs, code, status):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    request = {"kind": "video", "session_id": sid, "parts": [first, second], **kwargs}
    before = len(attempts(deps, "video", sid))
    with pytest.raises(MediaError) as exc:
        service.start_compose_job(**request)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert len(attempts(deps, "video", sid)) == before


def test_compose_is_mutually_exclusive_with_a_running_job(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    deps.executor.script = "block"
    video(service, session_id=sid)
    with pytest.raises(MediaError) as exc:
        service.start_compose_job(kind="video", session_id=sid, parts=[first, second])
    assert exc.value.code == "media_busy"
    service.cancel_job()


def test_compose_failure_settles_failed_join_failed(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    deps.executor.join_script = "fail"
    finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[first, second]))
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "failed" and made["error"]["code"] == "join_failed"


def test_cancelled_compose_removes_its_partial_output(tmp_path):
    service, deps = make_service(tmp_path, executor=PartialOutputExecutor(join_script="block"))
    sid, first, second = two_segments(service, deps)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    service.start_compose_job(kind="video", session_id=sid, parts=[first, second])
    assert service.job_status()["status"] == "running"
    assert list((tmp_path / "outputs").glob("h3-compose-*")), "fixture must write the partial file before blocking"
    service.cancel_job()
    assert finished.wait(5), "compose job never settled after cancel"
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "cancelled"
    assert not list((tmp_path / "outputs").glob("h3-compose-*")), "cancelled compose left its partial file (B-45)"


def test_failed_compose_removes_its_partial_output(tmp_path):
    service, deps = make_service(tmp_path, executor=PartialOutputExecutor(join_script="fail"))
    sid, first, second = two_segments(service, deps)
    finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[first, second]))
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "failed" and made["error"]["code"] == "join_failed"
    assert not list((tmp_path / "outputs").glob("h3-compose-*")), "failed compose left its partial file (B-45)"


def test_compose_route(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    seen = {}
    monkeypatch.setattr(service, "start_compose_job", lambda **kw: seen.update(kw) or {"ok": True})
    handler = next(h for m, p, h in build_routes(service) if (m, p) == ("POST", "/api/media/compose"))
    assert handler({"kind": "music", "session_id": "s", "parts": ["a", "b"]}, {}) == (200, {"ok": True})
    assert seen == {"kind": "music", "session_id": "s", "parts": ["a", "b"], "force": False}
