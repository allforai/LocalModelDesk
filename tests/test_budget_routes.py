"""R-budget-01：每个数字的来源必须出现在 API 里。

`client` 沿用 tests/test_production_runtime.py 的既有写法——build_runtime(port=0) +
http_helpers.http_call——这个仓库没有名为 client 的共享 pytest 夹具，所以在本文件
里按同样的模式搭一个，而不是凭空造一套新的假后端。
"""
import json

import pytest

from desk.runtime import build_runtime

from http_helpers import http_call


def _configured_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "config.json").write_text(json.dumps({
        "config_version": 1,
        "first_run_done": False,
        "models_root": str(data_root / "models"),
        "outputs_root": str(data_root / "outputs"),
        # port 0 是校验器明确拒绝的值（tests/test_foundation_config.py:184）——用一个
        # 合法端口，这个 fixture 本来就不是在测「端口 0」这件事。
        "gateway": {"enabled": False, "host": "127.0.0.1", "port": 8770},
    }), encoding="utf-8")
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(data_root))
    return data_root


class _Response:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def json(self):
        return self._body


class _Client:
    def __init__(self, runtime):
        self._runtime = runtime

    def get(self, path):
        status, body = http_call(self._runtime, "GET", path)
        return _Response(status, body)


@pytest.fixture
def client(tmp_path, monkeypatch):
    _configured_data_root(tmp_path, monkeypatch)
    runtime = build_runtime(port=0)
    runtime.start_background()
    try:
        yield _Client(runtime)
    finally:
        runtime.shutdown()


def test_budget_route_reports_source_for_every_number(client):
    body = client.get("/api/budget").json()
    assert body["chat"]["source"] in ("measured", "predicted", "unavailable")
    assert body["media"]["video"]["source"] in ("measured", "predicted", "unavailable")
    assert isinstance(body["available_bytes"], int)


def test_budget_route_reports_unavailable_chat_when_nothing_is_loaded(client):
    """没有驻留模型时 chat 不该猜一个数，而是照实说算不出。"""
    body = client.get("/api/budget").json()
    assert body["chat"] == {"source": "unavailable"}
