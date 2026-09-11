"""GatewayService：生命周期、data:gatewayStatus、0.0.0.0 局域网可达（R-gateway-07）。"""
import socket
import subprocess

import pytest

from desk.gateway.service import GatewayService
from gateway_client import json_request
from gateway_fakes import FakeBackend


def _config(enabled=True, host="127.0.0.1", port=0):
    holder = {"gateway": {"enabled": enabled, "host": host, "port": port}}
    return holder, (lambda: holder)


def _connect_refused(host, port):
    with socket.socket() as s:
        s.settimeout(2)
        return s.connect_ex((host, port)) != 0


@pytest.fixture
def service_factory():
    services = []

    def make(read_config, backend=None, server_factory=None):
        kwargs = {} if server_factory is None else {"server_factory": server_factory}
        svc = GatewayService(backend or FakeBackend(), read_config, **kwargs)
        services.append(svc)
        return svc

    yield make
    for svc in services:
        svc.stop()


def test_disabled_does_not_listen(service_factory):
    _, read = _config(enabled=False, port=18999)
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["enabled"] is False
    assert st["listening"] is False
    assert st["last_error"] is None
    assert _connect_refused("127.0.0.1", 18999)


def test_start_serves_models_and_reports_real_port(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["listening"] is True
    assert st["port"] > 0
    status, _, payload = json_request(st["port"], "GET", "/v1/models")
    assert status == 200
    assert payload["object"] == "list"


def test_status_shape(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    port = st["port"]
    assert st == {
        "enabled": True,
        "listening": True,
        "host": "127.0.0.1",
        "port": port,
        "lan_host": "127.0.0.1",
        "lan_candidates": ["127.0.0.1"],
        "openai_base_url": f"http://127.0.0.1:{port}/v1",
        "anthropic_base_url": f"http://127.0.0.1:{port}",
        "auth": "none",
        "last_error": None,
    }


def test_bind_failure_recorded_not_fatal(service_factory):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    try:
        _, read = _config(port=occupied)
        svc = service_factory(read)
        svc.start_from_config()
        st = svc.status()
        assert st["enabled"] is True
        assert st["listening"] is False
        assert st["last_error"] is not None
        assert str(occupied) in st["last_error"]
    finally:
        blocker.close()


def test_stop_closes_listener(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    svc.stop()
    assert svc.status()["listening"] is False
    assert _connect_refused("127.0.0.1", port)


def _lan_ip():
    try:
        proc = subprocess.run(["ipconfig", "getifaddr", "en0"],
                              capture_output=True, text=True, timeout=5)
    except OSError:
        return None
    ip = proc.stdout.strip()
    return ip if proc.returncode == 0 and ip else None


def _spec_port_or_ephemeral():
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", 8770))
        except OSError:
            return 0
    return 8770


def test_lan_reachability_via_en0_ip(service_factory):
    """Decision D-0002: prove wildcard binding through a non-loopback LAN path."""
    ip = _lan_ip()
    if not ip:
        pytest.skip("'ipconfig getifaddr en0' did not return a LAN IP")
    _, read = _config(host="0.0.0.0", port=_spec_port_or_ephemeral())
    svc = service_factory(read)
    svc.start_from_config()
    st = svc.status()
    assert st["listening"] is True
    status, _, payload = json_request(st["port"], "GET", "/v1/models", host=ip)
    assert status == 200
    assert payload["object"] == "list"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_config_request_get_returns_config_and_status(service_factory):
    holder, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    code, payload = svc.handle_config_request("GET")
    assert code == 200
    assert payload["config"] == holder["gateway"]
    assert payload["status"]["listening"] is True


def test_config_request_post_rebinds_to_new_port(service_factory):
    p1, p2 = _free_port(), _free_port()
    holder, read = _config(port=p1)
    svc = service_factory(read)
    svc.start_from_config()
    assert svc.status()["port"] == p1
    holder["gateway"] = {"enabled": True, "host": "127.0.0.1", "port": p2}
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"] == svc.status()
    assert svc.status()["port"] == p2
    status, _, _ = json_request(p2, "GET", "/v1/models")
    assert status == 200
    assert _connect_refused("127.0.0.1", p1)


def test_config_request_post_disable_stops_listening(service_factory):
    holder, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    holder["gateway"] = {"enabled": False, "host": "127.0.0.1", "port": port}
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is False
    assert _connect_refused("127.0.0.1", port)


def test_config_request_post_same_config_is_noop(service_factory):
    _, read = _config()
    svc = service_factory(read)
    svc.start_from_config()
    port = svc.status()["port"]
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is True
    status, _, _ = json_request(port, "GET", "/v1/models")
    assert status == 200


def test_config_request_post_retries_failed_bind(service_factory):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    holder, read = _config(port=occupied)
    svc = service_factory(read)
    svc.start_from_config()
    assert svc.status()["listening"] is False
    blocker.close()
    code, payload = svc.handle_config_request("POST")
    assert code == 200
    assert payload["status"]["listening"] is True
    assert payload["status"]["last_error"] is None


def test_config_request_rejects_other_methods(service_factory):
    _, read = _config()
    svc = service_factory(read)
    code, payload = svc.handle_config_request("DELETE")
    assert code == 405
    assert payload["error"]["code"] == "method_not_allowed"


def test_status_exposes_lan_host_for_wildcard_bind(service_factory):
    _holder, read = _config(enabled=True, host="0.0.0.0", port=0)
    svc = service_factory(read)
    status = svc.status()
    assert status["lan_host"] and status["lan_host"] != "0.0.0.0"
    assert status["openai_base_url"] == f"http://{status['lan_host']}:{status['port']}/v1"


def test_status_keeps_explicit_host(service_factory):
    _holder, read = _config(enabled=True, host="127.0.0.1", port=0)
    svc = service_factory(read)
    assert svc.status()["lan_host"] == "127.0.0.1"


class _FakeServer:
    """Binds only when the requested host is not the poisoned one (F12 rollback test)."""

    _bad_host = "10.255.255.1"

    def __init__(self, address, backend=None):
        if address[0] == self._bad_host:
            raise OSError(49, "Can't assign requested address")
        self.server_address = address

    def serve_forever(self):
        pass

    def shutdown(self):
        pass

    def server_close(self):
        pass


def test_failed_bind_rolls_back_to_the_last_good_config(service_factory):
    """一次误填的主机不许把网关写死成关闭态（F12）。"""
    stored = {"gateway": {"enabled": True, "host": "127.0.0.1", "port": 8770}}
    writes = []

    svc = service_factory(lambda: stored, server_factory=_FakeServer)
    svc.on_rollback = lambda cfg: writes.append(cfg)
    svc.start_from_config()
    assert svc.status()["listening"] is True

    stored["gateway"] = {"enabled": True, "host": "10.255.255.1", "port": 8770}
    status = svc.apply_config()

    assert status["listening"] is True
    assert status["host"] == "127.0.0.1"
    assert writes == [{"enabled": True, "host": "127.0.0.1", "port": 8770}]
    assert status["last_error"] is not None
    assert "无法绑定" in status["last_error"]


def test_bind_errno_49_message_is_plain_chinese(service_factory):
    """OS 原文不能是唯一解释；至少要给出人话提示（视觉基线 C3/F2）。"""
    stored = {"gateway": {"enabled": True, "host": "10.255.255.1", "port": 8770}}
    svc = service_factory(lambda: stored, server_factory=_FakeServer)
    svc.start_from_config()
    status = svc.status()
    assert status["listening"] is False
    assert "无法绑定" in status["last_error"]
    assert "10.255.255.1" in status["last_error"]
    assert "8770" in status["last_error"]
