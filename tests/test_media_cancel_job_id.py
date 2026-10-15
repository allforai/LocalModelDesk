"""A-42: cancel names its job, so an agent never cancels someone else's."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, cancellable_media_steps


def _post(url, body):
    req = Request(url, data=json.dumps(body).encode(), method="POST",
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def _start_image(h):
    _, session = _post(h.base_url + "/api/media-sessions/image", {})
    status, job = _post(h.base_url + "/api/media/image",
                        {"session_id": session["id"], "prompt": "猫", "width": 512, "height": 512, "steps": 4})
    assert status == 200, job
    return job


def test_cancel_with_a_stale_job_id_is_refused_and_leaves_the_running_job(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
                             media_script=script) as h:
        job = _start_image(h)
        status, body = _post(h.base_url + "/api/media/cancel", {"job_id": job["job_id"] - 1})
        assert status == 409
        assert body["error"]["code"] == "job_not_running"
        assert h.media.job_status()["status"] == "running"
        status, body = _post(h.base_url + "/api/media/cancel", {"job_id": job["job_id"]})
        assert status == 200


def test_cancel_with_a_non_integer_job_id_is_400(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, body = _post(h.base_url + "/api/media/cancel", {"job_id": "3"})
        assert status == 400
        assert body["error"]["code"] == "invalid_params"


def test_cancel_without_job_id_keeps_todays_behavior(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
                             media_script=script) as h:
        _start_image(h)
        status, _ = _post(h.base_url + "/api/media/cancel", {})
        assert status == 200
