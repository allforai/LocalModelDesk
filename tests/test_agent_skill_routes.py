"""A-44/A-45: /api/state carries the version; precheck answers without changing state."""
import json
from urllib.error import HTTPError
from urllib.request import urlopen

from desk.agent_cli.version import read_version, resources_root
from desk.testing import launch_test_harness


def _get(url):
    try:
        with urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def test_read_version_prefers_bundle_json(tmp_path):
    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging" / "VERSION").write_text("1.2.3\n")
    assert read_version(tmp_path) == "1.2.3"
    (tmp_path / "bundle.json").write_text(json.dumps({"bundle_version": "9.9.9"}))
    assert read_version(tmp_path) == "9.9.9"


def test_read_version_unknown_when_nothing_found(tmp_path):
    assert read_version(tmp_path) == "unknown"


def test_resources_root_is_the_parent_of_the_desk_package():
    assert (resources_root() / "desk" / "agent_cli" / "version.py").is_file()


def test_state_reports_version(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, state = _get(h.base_url + "/api/state")
        assert status == 200
        # the harness serves a bundle-mode resources tree, so that is where the version lives
        assert state["version"] == read_version(h.roots.resources_root) == "e2e"
        assert "holder" in state


def test_precheck_chat_for_an_idle_desk_is_ok(tmp_path):
    with launch_test_harness(tmp_path, model_states={"glm": "present"}) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=chat&model=glm")
        assert status == 200
        assert body["ok"] is True
        assert set(body) >= {"ok", "reason", "release", "memory_warning"}
        assert h.llm.status()["state"]["status"] == "idle"


def test_precheck_chat_unknown_model_is_404(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=chat&model=nope")
        assert status == 404
        assert body["error"]["code"] == "model_not_found"


def test_precheck_image_is_ok_when_idle(tmp_path):
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=image&width=512&height=512&steps=4")
        assert status == 200
        assert body["ok"] is True


def test_precheck_bad_op_is_400(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=video")
        assert status == 400
