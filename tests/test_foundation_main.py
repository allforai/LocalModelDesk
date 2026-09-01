from http_helpers import http_call

from desk import __main__ as main_mod


def test_runtime_port_reads_shell_contract(monkeypatch):
    monkeypatch.setenv("LMD_SHELL_PORT", "18766")
    assert main_mod.runtime_port() == 18766


def test_runtime_port_rejects_values_swift_host_cannot_bind(monkeypatch):
    for value in ("0", "-1", "65536", "not-a-port"):
        monkeypatch.setenv("LMD_SHELL_PORT", value)
        assert main_mod.runtime_port() == 8766


def test_build_app_binds_with_corrupt_config(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(data_root))
    data_root.mkdir()
    (data_root / "config.json").write_text("{not valid json", encoding="utf-8")

    app = main_mod.build_app(host="127.0.0.1", port=0)
    app.start_background()
    try:
        assert app.port > 0
        assert app.capabilities["config"].present is False

        status, payload = http_call(app, "GET", "/api/config")
        assert status == 500
        assert payload["error"]["code"] == "config_corrupt"
    finally:
        app.shutdown()
