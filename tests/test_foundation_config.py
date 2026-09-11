import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.foundation import config as config_mod
from desk.foundation.errors import ConfigCorruptError, ConfigInvalidError


def make_roots(tmp_path):
    """config.py only needs .data_root and .config_path (duck-typed roots)."""
    return SimpleNamespace(data_root=tmp_path, config_path=tmp_path / "config.json")


def test_missing_file_gives_pure_defaults_and_creates_nothing(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.read_config(roots)
    assert cfg.needs_setup is True
    assert cfg.first_run_done is False
    assert cfg.config_version == 1
    assert cfg.models_root == tmp_path / "models"
    assert cfg.outputs_root == tmp_path / "outputs"
    assert (cfg.gateway.enabled, cfg.gateway.host, cfg.gateway.port) == (True, "0.0.0.0", 8770)
    assert not roots.config_path.exists()


def test_partial_file_merges_key_by_key(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({
        "models_root": "/somewhere/models",
        "gateway": {"port": 9000},
    }), encoding="utf-8")
    cfg = config_mod.read_config(roots)
    assert cfg.models_root == Path("/somewhere/models")
    assert cfg.outputs_root == tmp_path / "outputs"
    assert cfg.gateway.port == 9000
    assert cfg.gateway.host == "0.0.0.0"
    assert cfg.gateway.enabled is True
    assert cfg.needs_setup is True


def test_first_run_done_true_clears_needs_setup(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"first_run_done": True}), encoding="utf-8")
    assert config_mod.read_config(roots).needs_setup is False


def test_unknown_keys_land_in_extra(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"future_knob": 42}), encoding="utf-8")
    cfg = config_mod.read_config(roots)
    assert cfg.extra == {"future_knob": 42}
    assert cfg.to_json()["future_knob"] == 42


def test_corrupt_json_raises_typed_error(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text("{definitely not json", encoding="utf-8")
    with pytest.raises(ConfigCorruptError) as exc:
        config_mod.read_config(roots)
    assert exc.value.code == "config_corrupt"
    assert exc.value.payload["path"] == str(roots.config_path)
    assert exc.value.payload["parse_error"]


def test_non_object_top_level_is_corrupt(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConfigCorruptError):
        config_mod.read_config(roots)


def test_default_config_helper_matches_missing_file(tmp_path):
    roots = make_roots(tmp_path)
    assert config_mod.default_config(tmp_path) == config_mod.read_config(roots)


def test_write_read_round_trip(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.default_config(tmp_path)
    config_mod.write_config(roots, cfg)
    again = config_mod.read_config(roots)
    assert again.to_json() == cfg.to_json()
    assert json.loads(roots.config_path.read_text())["config_version"] == 1


def test_update_config_changes_only_named_fields(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.update_config(roots, first_run_done=True,
                                   models_root=tmp_path / "elsewhere")
    assert cfg.first_run_done is True
    assert cfg.needs_setup is False
    assert cfg.models_root == tmp_path / "elsewhere"
    assert cfg.gateway.port == 8770
    cfg2 = config_mod.update_config(roots, gateway={"port": 9001})
    assert cfg2.gateway.port == 9001
    assert cfg2.gateway.host == "0.0.0.0"
    assert cfg2.models_root == tmp_path / "elsewhere"


def test_unknown_keys_round_trip_through_update(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"future_knob": 42}), encoding="utf-8")
    config_mod.update_config(roots, first_run_done=True)
    on_disk = json.loads(roots.config_path.read_text())
    assert on_disk["future_knob"] == 42


def test_atomic_write_replace_failure_keeps_old_file(tmp_path, monkeypatch):
    roots = make_roots(tmp_path)
    config_mod.update_config(roots, first_run_done=True)
    before = roots.config_path.read_bytes()

    def boom(src, dst):
        raise OSError("injected replace failure")

    monkeypatch.setattr(config_mod.os, "replace", boom)
    with pytest.raises(OSError, match="injected replace failure"):
        config_mod.update_config(roots, first_run_done=False)
    assert roots.config_path.read_bytes() == before
    assert [p for p in tmp_path.iterdir() if "tmp" in p.name] == []


def test_reset_backs_up_the_broken_file_and_starts_over(tmp_path):
    """坏配置必须可一键重设，且坏文件留一份备份（J25）。"""
    roots = make_roots(tmp_path)
    roots.config_path.write_text("{not json", encoding="utf-8")

    result = config_mod.reset_config(roots)

    assert Path(result["backup"]).read_text(encoding="utf-8") == "{not json"
    assert result["needs_setup"] is True
    assert config_mod.read_config(roots).first_run_done is False


def test_atomic_write_serialization_failure_keeps_old_file(tmp_path, monkeypatch):
    roots = make_roots(tmp_path)
    config_mod.update_config(roots, first_run_done=True)
    before = roots.config_path.read_bytes()

    def boom(*args, **kwargs):
        raise ValueError("injected dump failure")

    monkeypatch.setattr(config_mod.json, "dump", boom)
    with pytest.raises(ValueError, match="injected dump failure"):
        config_mod.update_config(roots, first_run_done=False)
    assert roots.config_path.read_bytes() == before
    assert [p for p in tmp_path.iterdir() if "tmp" in p.name] == []


def test_concurrent_updates_lose_no_fields(tmp_path):
    roots = make_roots(tmp_path)
    n = 40

    def bump(key):
        for i in range(n):
            config_mod.update_config(roots, **{key: i})

    threads = [threading.Thread(target=bump, args=(key,)) for key in ("knob_a", "knob_b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    on_disk = json.loads(roots.config_path.read_text())
    assert on_disk["knob_a"] == n - 1
    assert on_disk["knob_b"] == n - 1


def test_update_config_rejects_bad_port_type_and_keeps_file_untouched(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"first_run_done": True, "gateway": {"port": 8770}}), encoding="utf-8")
    before = roots.config_path.read_bytes()
    with pytest.raises(ConfigInvalidError) as exc:
        config_mod.update_config(roots, gateway={"port": "not-a-number"})
    assert exc.value.code == "config_invalid"
    assert exc.value.payload["field"] == "gateway.port"
    assert roots.config_path.read_bytes() == before


@pytest.mark.parametrize("fields,field", [
    ({"gateway": {"port": 0}}, "gateway.port"),
    ({"gateway": {"port": 70000}}, "gateway.port"),
    ({"gateway": {"host": ""}}, "gateway.host"),
    ({"gateway": {"enabled": "yes"}}, "gateway.enabled"),
    ({"first_run_done": "false"}, "first_run_done"),
    ({"models_root": 12}, "models_root"),
])
def test_update_config_rejects_each_bad_field(tmp_path, fields, field):
    roots = make_roots(tmp_path)
    with pytest.raises(ConfigInvalidError) as exc:
        config_mod.update_config(roots, **fields)
    assert exc.value.payload["field"] == field
    assert not roots.config_path.exists()


def test_read_config_reports_wrong_type_on_disk_as_corrupt(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"gateway": {"port": "abc"}}), encoding="utf-8")
    with pytest.raises(ConfigCorruptError) as exc:
        config_mod.read_config(roots)
    assert "gateway.port" in exc.value.payload["parse_error"]
