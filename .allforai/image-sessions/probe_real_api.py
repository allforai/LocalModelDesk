"""Real HTTP round trip for image sessions against launch_test_harness (fake media executor).

Prints one JSON line per request/response so the capture is a transcript, then a final
summary line. Exits non-zero on the first broken expectation.
Run from the repo root: python3 .allforai/image-sessions/probe_real_api.py
"""
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk.testing import launch_test_harness  # noqa: E402
from desk.testing.scripts import MediaScript, cancellable_media_steps, fast_media_steps  # noqa: E402


def call(base, method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status, raw, kind = response.status, response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        status, raw, kind = exc.code, exc.read(), "application/json"
    payload = json.loads(raw) if kind == "application/json" else {
        "content_type": kind, "bytes": len(raw), "magic": raw[:8].hex()}
    shown = payload
    if isinstance(payload, dict) and "log" in payload:
        shown = {k: v for k, v in payload.items() if k != "log"}
    print(json.dumps({"request": [method, path, body], "status": status, "response": shown},
                     ensure_ascii=False))
    return status, payload


def expect(condition, message):
    if not condition:
        print(json.dumps({"FAILED": message}, ensure_ascii=False))
        sys.exit(1)


def settle(base, session_id, attempt_id):
    for _ in range(500):
        _, session = call(base, "GET", f"/api/image-sessions/{session_id}")
        attempt = next(a for a in session["attempts"] if a["id"] == attempt_id)
        if attempt["status"] != "running":
            return attempt
        time.sleep(0.02)
    expect(False, f"attempt {attempt_id} never settled")


def harness(tmp, jobs):
    return launch_test_harness(tmp, model_states={"qwen-image": "present"}, image_runtime=True,
                               media_script=MediaScript(jobs))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="image-sessions-probe-"))
    print(json.dumps({"harness_tmp": str(tmp)}))
    with harness(tmp, [fast_media_steps(), fast_media_steps(), cancellable_media_steps()]) as h:
        base = h.base_url
        print(json.dumps({"phase": "first launch", "base_url": base, "data_root": str(h.data_root)}))
        status, body = call(base, "POST", "/api/media/image", {"prompt": "一只橘猫"})
        expect(status == 400 and body["error"]["code"] == "session_required", "session_required")
        _, session = call(base, "POST", "/api/image-sessions", {})
        sid = session["id"]
        status, first = call(base, "POST", "/api/media/image",
                             {"session_id": sid, "prompt": "一只橘猫坐在窗边，午后阳光，细腻的水彩插画", "seed": 3021987455})
        expect(status == 200 and first["attempt_id"], "first start")
        a1 = settle(base, sid, first["attempt_id"])
        expect(a1["status"] == "done", "first done")
        # 「在这张基础上改」: same seed, edited prompt
        status, second = call(base, "POST", "/api/media/image",
                              {"session_id": sid, "prompt": "一只橘猫坐在窗边，黄昏", "seed": a1["params"]["seed"]})
        a2 = settle(base, sid, second["attempt_id"])
        expect(a2["params"]["seed"] == a1["params"]["seed"], "same seed kept")
        # a cancelled attempt
        status, third = call(base, "POST", "/api/media/image", {"session_id": sid, "prompt": "会被取消"})
        h.media_script.step()
        call(base, "POST", "/api/media/cancel", {})
        a3 = settle(base, sid, third["attempt_id"])
        expect(a3["status"] == "cancelled" and a3["error"]["code"] == "cancelled", "cancelled recorded")
        _, full = call(base, "GET", f"/api/image-sessions/{sid}")
        expect([a["status"] for a in full["attempts"]] == ["done", "done", "cancelled"], "order")
        outputs = [a["output"] for a in full["attempts"] if a["output"]]
        for name in outputs:
            status, png = call(base, "GET", f"/api/outputs/{name}")
            expect(status == 200 and png["magic"].startswith("89504e47"), "png served")

    with harness(tmp, []) as h:
        base = h.base_url
        print(json.dumps({"phase": "relaunch on same data root", "base_url": base}))
        _, listed = call(base, "GET", "/api/image-sessions")
        expect([s["id"] for s in listed] == [sid] and listed[0]["attempt_count"] == 3, "list after restart")
        _, again = call(base, "GET", f"/api/image-sessions/{sid}")
        expect([a["id"] for a in again["attempts"]] == [a["id"] for a in full["attempts"]], "attempts after restart")
        _, history_before = call(base, "GET", "/api/history")
        _, outputs_before = call(base, "GET", "/api/outputs")
        status, deleted = call(base, "DELETE", f"/api/image-sessions/{sid}")
        expect(status == 200 and deleted == {"deleted": sid}, "delete")
        _, listed = call(base, "GET", "/api/image-sessions")
        expect(listed == [], "gone from list")
        expect(call(base, "GET", "/api/history")[1] == history_before, "history untouched")
        expect(call(base, "GET", "/api/outputs")[1] == outputs_before, "outputs untouched")
        for name in outputs:
            expect(call(base, "GET", f"/api/outputs/{name}")[0] == 200, "image still opens")
    print(json.dumps({"result": "ok", "session_id": sid, "outputs": outputs,
                      "attempt_statuses": ["done", "done", "cancelled"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
