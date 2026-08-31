import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.foundation import config as config_mod
from desk.foundation.errors import ConfigCorruptError


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
