"""Image sessions are wired into both composition roots and survive a restart over real HTTP."""
import json
import time
import urllib.error
import urllib.request

from desk.runtime import build_runtime
from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, cancellable_media_steps, fast_media_steps

from http_helpers import http_call
from test_production_runtime import _configured_data_root


def request(base_url, method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read()
            kind = response.headers.get_content_type()
            return response.status, json.loads(raw) if kind == "application/json" else raw
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_job_settled(base_url, session_id, attempt_id, timeout=10.0):
    """Poll the session like the pane does (D-27) until the attempt leaves running."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _, session = request(base_url, "GET", f"/api/image-sessions/{session_id}")
        attempt = next(a for a in session["attempts"] if a["id"] == attempt_id)
        if attempt["status"] != "running":
            return attempt
        time.sleep(0.02)
    raise AssertionError(f"attempt {attempt_id} never settled")


def image_harness(tmp_path, jobs):
    return launch_test_harness(
        tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
        media_script=MediaScript(jobs))


# ---- production composition root (cross-phase closure: no unwired store) -------------

def test_production_runtime_mounts_image_sessions_and_hands_the_store_to_media(tmp_path, monkeypatch):
    data_root = _configured_data_root(tmp_path, monkeypatch)
    stale_id = "a" * 32
    (data_root / "image-sessions").mkdir()
    (data_root / "image-sessions" / f"{stale_id}.json").write_text(json.dumps({
        "id": stale_id, "title": "上次的", "title_auto": True, "created": "2026-09-24T10:00:00",
        "updated": "2026-09-24T10:00:00", "attempts": [{
            "id": "b" * 32, "job_id": 3, "ts": "2026-09-24T10:00:00", "finished": None,
            "status": "running", "params": {"prompt": "p", "width": 1024, "height": 1024,
                                            "steps": 40, "seed": 1}, "output": None, "error": None}],
    }), encoding="utf-8")
    runtime = build_runtime(port=0)
    runtime.start_background()
    try:
        assert runtime.media._image_sessions is not None
        status, created = http_call(runtime, "POST", "/api/image-sessions", {})
        assert status == 200 and (data_root / "image-sessions" / f"{created['id']}.json").is_file()
        assert runtime.media._image_sessions.exists(created["id"])

        status, body = http_call(runtime, "POST", "/api/media/image", {"prompt": "cat"})
        assert status == 400 and body["error"]["code"] == "session_required"
        status, body = http_call(runtime, "POST", "/api/media/image",
                                 {"prompt": "cat", "session_id": "f" * 32})
        assert status == 404 and body["error"]["code"] == "session_not_found"
        status, body = http_call(runtime, "POST", "/api/media/image",
                                 {"prompt": "cat", "session_id": created["id"]})
        assert body.get("error", {}).get("code") not in ("session_required", "session_not_found")

        status, recovered = http_call(runtime, "GET", f"/api/image-sessions/{stale_id}")
        assert status == 200
        assert recovered["attempts"][0]["status"] == "failed"
        assert recovered["attempts"][0]["error"]["code"] == "interrupted"
    finally:
        runtime.shutdown()


# ---- test harness: real HTTP, fake executor ---------------------------------------------

def test_harness_session_attempts_survive_restart_and_delete_keeps_images(tmp_path):
    with image_harness(tmp_path, [fast_media_steps(), fast_media_steps()]) as harness:
        base = harness.base_url
        status, session = request(base, "POST", "/api/image-sessions", {})
        assert status == 200
        status, started = request(base, "POST", "/api/media/image",
                                  {"session_id": session["id"], "prompt": "一只橘猫", "seed": 77})
        assert status == 200, started
        assert started["session_id"] == session["id"] and started["attempt_id"]
        wait_job_settled(base, session["id"], started["attempt_id"])
        status, again = request(base, "POST", "/api/media/image",
                                {"session_id": session["id"], "prompt": "一只橘猫"})
        assert status == 200, again
        wait_job_settled(base, session["id"], again["attempt_id"])

        _, got = request(base, "GET", f"/api/image-sessions/{session['id']}")
        assert [a["status"] for a in got["attempts"]] == ["done", "done"]
        assert got["attempts"][0]["params"]["seed"] == 77
        assert got["attempts"][1]["params"]["seed"] != 42
        assert got["title"] == "一只橘猫"
        outputs = [a["output"] for a in got["attempts"]]
        for name in outputs:
            status, png = request(base, "GET", f"/api/outputs/{name}")
            assert status == 200 and png.startswith(b"\x89PNG")

    with image_harness(tmp_path, []) as restarted:
        base = restarted.base_url
        _, listed = request(base, "GET", "/api/image-sessions")
        assert [(s["id"], s["attempt_count"], s["cover"]) for s in listed] == [
            (session["id"], 2, outputs[-1])]
        _, after_restart = request(base, "GET", f"/api/image-sessions/{session['id']}")
        assert [a["id"] for a in after_restart["attempts"]] == [a["id"] for a in got["attempts"]]
        _, history_before = request(base, "GET", "/api/history")
        _, outputs_before = request(base, "GET", "/api/outputs")

        assert request(base, "DELETE", f"/api/image-sessions/{session['id']}") == (
            200, {"deleted": session["id"]})
        assert request(base, "GET", "/api/image-sessions") == (200, [])
        assert request(base, "GET", "/api/history") == (200, history_before)
        assert request(base, "GET", "/api/outputs") == (200, outputs_before)
        for name in outputs:
            assert request(base, "GET", f"/api/outputs/{name}")[0] == 200
        image_entries = [e for e in history_before if e["kind"] == "image"]
        assert {e["session_id"] for e in image_entries} == {session["id"]}


def test_harness_cancel_is_recorded_in_the_session(tmp_path):
    with image_harness(tmp_path, [cancellable_media_steps()]) as harness:
        base = harness.base_url
        _, session = request(base, "POST", "/api/image-sessions", {})
        status, started = request(base, "POST", "/api/media/image",
                                  {"session_id": session["id"], "prompt": "p"})
        assert status == 200
        _, listed = request(base, "GET", "/api/image-sessions")
        assert listed[0]["running"] is True
        harness.media_script.step()  # past the first gate, into BLOCK_UNTIL_CANCEL
        assert request(base, "POST", "/api/media/cancel", {})[0] == 200
        wait_job_settled(base, session["id"], started["attempt_id"])
        _, got = request(base, "GET", f"/api/image-sessions/{session['id']}")
        assert got["attempts"][0]["status"] == "cancelled"
        assert got["attempts"][0]["error"]["code"] == "cancelled"
