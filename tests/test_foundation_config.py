import json
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
