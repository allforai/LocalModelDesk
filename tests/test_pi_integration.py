"""Pi settings installer: temporary HOME only, no model inference or Pi execution."""
import hashlib
import json
from pathlib import Path
import re

import pytest

from desk.pi_integration.service import EXTENSION, RECEIPT, IntegrationError, PiIntegrationService
from desk.resources.catalog import list_catalog
from desk.testing import launch_test_harness
from http_helpers import http_call

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    source = tmp_path / "res/integrations/pi/lmdesk.ts"
    source.parent.mkdir(parents=True)
    source.write_text("// trusted provider v1\n")
    gateway = {"enabled": True, "listening": True, "host": "0.0.0.0", "port": 8770}
    calls = []

    def probe(url):
        calls.append(url)
        return {"state": {"status": "idle"}} if url.endswith("/api/llm/status") else {"object": "list", "data": []}

    service = PiIntegrationService(tmp_path / "res", "dev", home,
        gateway_status=lambda: gateway, control_url=lambda: "http://127.0.0.1:8766",
        which=lambda _: "/fake/pi", probe=probe)
    return service, home, source, gateway, calls


def test_fresh_install_idempotent_and_remove_preserves_pi_settings(setup):
    svc, home, source, _, _ = setup
    settings = home / ".pi/agent/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"defaultModel":"cloud"}')
    before = settings.read_bytes()
    assert svc.status()["state"] == "absent"
    assert svc.apply("install")["state"] == "installed"
    assert (home / EXTENSION).read_bytes() == source.read_bytes()
    assert json.loads((home / RECEIPT).read_text())["installed_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert svc.apply("install")["state"] == "installed"
    assert svc.apply("remove")["state"] == "absent"
    assert not (home / EXTENSION).exists() and not (home / RECEIPT).exists()
    assert svc.apply("remove")["state"] == "absent"
    assert settings.read_bytes() == before


def test_update_source_and_connection_defaults(setup):
    svc, home, source, gateway, _ = setup
    svc.apply("install")
    source.write_text("// trusted provider v2\n")
    assert svc.status()["state"] == "stale"
    assert svc.apply("install")["state"] == "installed"
    gateway["port"] = 18870
    assert svc.status()["state"] == "stale"
    svc.apply("install")
    assert json.loads((home / RECEIPT).read_text())["gateway_url"] == "http://127.0.0.1:18870/v1"


def test_manual_exact_copy_can_be_adopted_but_not_deleted_before_adoption(setup):
    svc, home, source, _, _ = setup
    target = home / EXTENSION
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    assert svc.status()["state"] == "manual"
    with pytest.raises(IntegrationError):
        svc.apply("remove")
    assert svc.apply("install")["state"] == "installed"
    assert svc.apply("remove")["state"] == "absent"


@pytest.mark.parametrize("foreign", ["file", "dir", "link", "dangling-link", "parent-link", "receipt-link", "receipt-dir", "receipt-json", "receipt-owner"])
def test_foreign_files_directories_and_links_are_untouched(setup, tmp_path, foreign):
    svc, home, _, _, _ = setup
    target = home / EXTENSION
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "mine"
    sentinel.write_text("user data")
    if foreign == "file": target.write_text("// user extension")
    elif foreign == "dir": target.mkdir()
    elif foreign == "link": target.symlink_to(sentinel)
    elif foreign == "dangling-link": target.symlink_to(outside / "missing")
    elif foreign == "parent-link":
        target.parent.rmdir()
        target.parent.symlink_to(outside)
    elif foreign == "receipt-link": (home / RECEIPT).symlink_to(sentinel)
    elif foreign == "receipt-dir": (home / RECEIPT).mkdir()
    elif foreign == "receipt-json": (home / RECEIPT).write_text("{broken")
    else: (home / RECEIPT).write_text('{"owner":"foreign"}')
    state = svc.status()
    assert not state["can_install"] and not state["can_remove"]
    with pytest.raises(IntegrationError): svc.apply("install")
    with pytest.raises(IntegrationError): svc.apply("remove")
    assert sentinel.read_text() == "user data"
    if foreign == "file": assert target.read_text() == "// user extension"


def test_modified_managed_extension_is_not_overwritten_or_removed(setup):
    svc, home, _, _, _ = setup
    svc.apply("install")
    (home / EXTENSION).write_text("// modified by user")
    assert svc.status()["state"] == "conflict"
    for action in ("install", "remove"):
        with pytest.raises(IntegrationError): svc.apply(action)
    assert (home / EXTENSION).read_text() == "// modified by user"


def test_orphan_receipt_can_reinstall_or_be_removed(setup):
    svc, home, _, _, _ = setup
    svc.apply("install")
    (home / EXTENSION).unlink()
    assert svc.status()["can_remove"]
    assert svc.apply("install")["state"] == "installed"
    (home / EXTENSION).unlink()
    svc.apply("remove")
    assert not (home / RECEIPT).exists()


@pytest.mark.parametrize("empty", [True, False])
def test_missing_or_empty_bundle_cannot_be_installed(setup, empty):
    svc, _, source, _, _ = setup
    if empty: source.write_bytes(b"")
    else: source.unlink()
    assert svc.status()["state"] == "error"
    with pytest.raises(IntegrationError): svc.apply("install")


@pytest.mark.parametrize("action", [None, [], {}, "update", 1])
def test_invalid_actions_are_rejected(setup, action):
    svc, *_ = setup
    with pytest.raises(ValueError): svc.apply(action)


def test_check_only_reads_control_and_gateway_never_loads(setup):
    svc, _, _, gateway, calls = setup
    assert not svc.check()["ok"] and calls == []
    svc.apply("install")
    assert svc.check()["ok"]
    assert calls == ["http://127.0.0.1:8766/api/llm/status", "http://127.0.0.1:8770/v1/models"]
    gateway["listening"] = False
    calls.clear()
    assert not svc.check()["ok"] and calls == []


def test_check_reports_missing_pi_bad_protocol_and_network_error(setup):
    svc, *_ = setup
    svc.apply("install")
    svc._which = lambda _: None
    assert "未检测到" in svc.check()["message"]
    svc._which = lambda _: "/fake/pi"
    svc._probe = lambda _: []
    assert not svc.check()["ok"]
    svc._probe = lambda _: {"state": {"status": "idle"}}
    assert not svc.check()["ok"]
    def fail(_): raise OSError("offline")
    svc._probe = fail
    assert "offline" in svc.check()["message"]


def test_exact_legacy_release_is_adoptable_not_just_a_marker(setup, monkeypatch):
    import desk.pi_integration.service as module
    svc, home, _, _, _ = setup
    legacy = b"// an exact previous release"
    monkeypatch.setattr(module, "LEGACY_HASHES", frozenset({hashlib.sha256(legacy).hexdigest()}))
    target = home / EXTENSION
    target.parent.mkdir(parents=True)
    target.write_bytes(legacy)
    assert svc.status()["state"] == "manual"
    assert svc.apply("install")["state"] == "installed"


def test_partial_receipt_write_failure_is_visible_and_recoverable(setup, monkeypatch):
    import desk.pi_integration.service as module
    svc, home, _, _, _ = setup
    real_write = module._atomic_write
    def fail_receipt(path, data, **kwargs):
        if path == home / RECEIPT: raise OSError("receipt permission denied")
        return real_write(path, data, **kwargs)
    monkeypatch.setattr(module, "_atomic_write", fail_receipt)
    with pytest.raises(IntegrationError, match="写入 pi 接入失败"):
        svc.apply("install")
    assert svc.status()["state"] == "manual"
    monkeypatch.setattr(module, "_atomic_write", real_write)
    assert svc.apply("install")["state"] == "installed"


def test_invalid_gateway_yields_error_not_uncaught_exception(setup):
    svc, _, _, gateway, _ = setup
    gateway["port"] = 0
    assert svc.status()["state"] == "error"


def test_bundle_mode_is_checkout_independent(setup, tmp_path):
    svc, home, source, _, _ = setup
    bundled = tmp_path / "App/Contents/Resources/desk/pi_integration/bundled/lmdesk.ts"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(source.read_bytes())
    source.unlink()
    bundle = PiIntegrationService(bundled.parents[3], "bundle", home,
        gateway_status=svc._gateway_status, control_url=svc._control_url, which=lambda _: "/fake/pi")
    assert bundle.apply("install")["state"] == "installed"


def test_metadata_matches_catalog_and_provider_ids_and_names():
    rows = json.loads((REPO / "desk/pi_integration/models.json").read_text())
    assert {m["key"] for m in rows} == {e.key for e in list_catalog() if e.group == "chat"}
    assert [m["key"] for m in rows if m["recommended"]] == ["qwen35"]
    source = (REPO / "integrations/pi/lmdesk.ts").read_text()
    block = source.split("const MODELS = [", 1)[1].split("\n];", 1)[0]
    actual = dict(re.findall(r'\["([^"\n]+)", "([^"\n]+)"\]', block))
    assert actual == {m["key"]: f'{m["version"]} · {m["use_case"]}' for m in rows}
    assert "glm" in actual and "30B-A3B" in actual["glm"]
    assert "看图" in actual["gemma"]
    assert next(m for m in rows if m["key"] == "gemma")["input"] == ["text", "image"]


def test_routes_apply_status_origin_and_connection(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        h.pi_integration._which = lambda _: "/fake/pi"
        status, body = http_call(h.app, "GET", "/api/pi-integration")
        assert status == 200 and len(body["models"]) == len([e for e in list_catalog() if e.group == "chat"])
        for action in (None, "bad", []):
            status, _ = http_call(h.app, "POST", "/api/pi-integration", {"action": action})
            assert status == 400
        status, body = http_call(h.app, "POST", "/api/pi-integration", {"action": "install"})
        assert status == 200 and body["state"] == "installed"
        status, check = http_call(h.app, "POST", "/api/pi-integration/check", {})
        assert status == 200 and isinstance(check["ok"], bool)
        status, body = http_call(h.app, "POST", "/api/pi-integration", {"action": "remove"})
        assert status == 200 and body["state"] == "absent"
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        for origin in ("https://evil.example", "null", "http://[bad"):
            req = Request(h.base_url + "/api/pi-integration", data=b'{"action":"install"}',
                headers={"Content-Type": "application/json", "Origin": origin}, method="POST")
            with pytest.raises(HTTPError) as error: urlopen(req)
            assert error.value.code == 403
        req = Request(h.base_url + "/api/pi-integration", data=b'{"action":"install"}', method="POST")
        with pytest.raises(HTTPError) as error: urlopen(req)
        assert error.value.code == 415
        assert not (home / EXTENSION).exists()
