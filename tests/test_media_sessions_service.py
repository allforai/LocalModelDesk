"""MediaService × media sessions for video and music (design B §3.2, §5)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service


def music_ready(service, tmp_path):
    roots = SimpleNamespace(outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
                            music_python=Path("/fake/py"), media_cli_dir=Path("/fake/media"), music_env={},
                            mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={})
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {"music_runtime": SimpleNamespace(present=True, detail=""),
                                           "mlx_h3": SimpleNamespace(present=True, detail="")}
    service._list_catalog = lambda: [SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0),
                                     SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)]


def video(service, **kw):
    return service.start_video_job(**{"prompt": "雨夜", "width": 512, "height": 288, "frames": 49, "steps": 12, **kw})


def music(service, **kw):
    return service.start_music_job(**{"caption": "独立流行", "lyrics": "[verse]\n早晨", "duration": 20.0, **kw})


def test_video_in_a_session_appends_and_settles_an_attempt(tmp_path):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, seed=7))
    attempt = deps.media_sessions["video"].get(sid)["attempts"][0]
    assert attempt["status"] == "done" and attempt["output"] == snap["output"]
    assert attempt["params"]["seed"] == 7 and attempt["op"] == "generate"
    assert snap["session_id"] == sid and snap["attempt_id"] == attempt["id"]
    assert deps.history.entries[-1]["session_id"] == sid and deps.history.entries[-1]["attempt_id"] == attempt["id"]


def test_music_in_a_session_takes_its_title_from_the_caption(tmp_path):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    sid = deps.media_sessions["music"].create()["id"]
    finished_snapshot(service, lambda: music(service, session_id=sid))
    assert deps.media_sessions["music"].get(sid)["title"] == "独立流行"


def test_video_without_session_still_runs_unattached(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: video(service))
    assert snap["status"] == "done" and snap["session_id"] is None and snap["attempt_id"] is None
    assert deps.history.entries[-1]["session_id"] is None


@pytest.mark.parametrize("session_id, code, status", [(None, "session_required", 400), (7, "session_required", 400),
                                                      ("f" * 32, "session_not_found", 404)])
def test_music_requires_a_session(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    with pytest.raises(MediaError) as exc:
        music(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == []


@pytest.mark.parametrize("session_id, code, status", [(123, "session_required", 400), ("f" * 32, "session_not_found", 404)])
def test_bad_session_is_refused_before_anything_starts(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == [] and deps.arbiter.acquired == []


def test_refs_without_a_session_is_session_required(tmp_path):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, refs={"x": {}})
    assert exc.value.code == "session_required"


def test_unregistered_ref_name_is_400(tmp_path):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, refs={"soundtrack": {"kind": "music", "session_id": "a" * 32, "attempt_id": "b" * 32}})
    assert exc.value.code == "invalid_params"
    assert deps.media_sessions["video"].get(sid)["attempts"] == []


def done_image(deps, tmp_path):
    images = deps.media_sessions["image"]
    sid = images.create()["id"]
    images.begin_attempt(sid, {"id": "a" * 32, "job_id": 1, "params": {"prompt": "猫", "width": 1024, "height": 1024, "steps": 40, "seed": 1}})
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / "cat.png").write_bytes(b"png")
    images.settle_attempt(sid, "a" * 32, "done", "cat.png")
    return sid


def test_registered_ref_resolves_to_a_file_and_is_stored_as_a_pointer(tmp_path):
    service, deps = make_service(tmp_path)
    service._ref_slots = {"video": {"probe": "image"}}
    image_sid = done_image(deps, tmp_path)
    ref = {"kind": "image", "session_id": image_sid, "attempt_id": "a" * 32}
    stored, paths = service._resolve_refs("video", {"probe": ref})
    assert stored == {"probe": ref} and paths == {"probe": tmp_path / "outputs" / "cat.png"}
    sid = deps.media_sessions["video"].create()["id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, refs={"probe": ref}))
    assert deps.media_sessions["video"].get(sid)["attempts"][0]["refs"] == {"probe": ref}


@pytest.mark.parametrize("mutate", ["wrong_kind", "gone_session", "gone_file"])
def test_broken_ref_is_404_ref_missing(tmp_path, mutate):
    service, deps = make_service(tmp_path)
    service._ref_slots = {"video": {"probe": "image"}}
    image_sid = done_image(deps, tmp_path)
    ref = {"kind": "image", "session_id": image_sid, "attempt_id": "a" * 32}
    if mutate == "wrong_kind":
        ref = {**ref, "kind": "music"}
    elif mutate == "gone_session":
        deps.media_sessions["image"].delete(image_sid)
    else:
        (tmp_path / "outputs" / "cat.png").unlink()
    code = "invalid_params" if mutate == "wrong_kind" else "ref_missing"
    with pytest.raises(MediaError) as exc:
        service._resolve_refs("video", {"probe": ref})
    assert exc.value.code == code
    if code == "ref_missing":
        assert exc.value.http_status == 404 and exc.value.message == "引用的图片已不在"


@pytest.mark.parametrize("extra", [{"continues": "a" * 32}, {"refs": {}}])
def test_image_refuses_continues_and_refs(tmp_path, extra):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["image"].create()["id"]
    with pytest.raises(MediaError) as exc:
        service.start_image_job(session_id=sid, prompt="猫", **extra)
    assert exc.value.code == "invalid_params"                       # B-00b
    assert deps.media_sessions["image"].get(sid)["attempts"] == []


def test_routes_pass_session_and_refs_through(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    seen = {}
    monkeypatch.setattr(service, "start_video_job", lambda **kw: seen.update(kw) or {"ok": True})
    handler = next(h for m, p, h in build_routes(service) if p == "/api/media/video")
    handler({"prompt": "p", "width": 512, "height": 288, "frames": 49, "steps": 12,
             "session_id": "s", "refs": {"a": 1}, "continues": "c", "seed": 3}, {})
    assert (seen["session_id"], seen["refs"], seen["continues"], seen["seed"]) == ("s", {"a": 1}, "c", 3)
