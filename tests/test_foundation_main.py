from http_helpers import http_call

from desk import __main__ as main_mod


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
