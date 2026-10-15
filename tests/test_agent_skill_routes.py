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


import pytest
from urllib.request import Request

from desk.agent_skill.service import AgentSkillService


def _post(url, body):
    req = Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def test_service_paths_dev_vs_bundle(tmp_path):
    dev = AgentSkillService(tmp_path, "dev", tmp_path / "home")
    assert dev.cli_path == tmp_path / "scripts" / "lmdesk"
    bundle = AgentSkillService(tmp_path, "bundle", tmp_path / "home")
    assert bundle.cli_path == tmp_path / "bin" / "lmdesk"
    assert dev.skill_dir == tmp_path / "desk" / "agent_skill" / "bundled" / "local-model-desk"


def test_apply_rejects_unknown_target(tmp_path):
    svc = AgentSkillService(tmp_path, "dev", tmp_path / "home")
    with pytest.raises(ValueError):
        svc.apply(["claude", "vim"])


def test_check_reports_cli_outcome(tmp_path):
    class Done:
        def __init__(self, rc, out, err):
            self.returncode, self.stdout, self.stderr = rc, out, err
    ok = AgentSkillService(tmp_path, "dev", tmp_path / "home",
                           run=lambda *a, **k: Done(0, '{"desk": {"reachable": true}}', ""))
    assert ok.check()["ok"] is True
    bad = AgentSkillService(tmp_path, "dev", tmp_path / "home", run=lambda *a, **k: Done(6, "", "被沙箱拦截"))
    result = bad.check()
    assert result["ok"] is False and "沙箱" in result["message"]


def test_routes_status_apply_and_state_flag(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent-skill")
        assert status == 200 and [r["key"] for r in body["targets"]] == ["claude", "codex", "pi", "dsh"]
        status, body = _post(h.base_url + "/api/agent-skill", {"targets": ["claude"]})
        assert status == 200
        assert next(r for r in body["targets"] if r["key"] == "claude")["state"] == "installed"
        assert (home / ".claude/skills/local-model-desk").is_symlink()
        status, body = _post(h.base_url + "/api/agent-skill", {"targets": ["nope"]})
        assert status == 400
        _, state = _get(h.base_url + "/api/state")
        assert state["agent_skill_stale"] is False
        _post(h.base_url + "/api/agent-skill", {"targets": []})
