import sys

import pytest

from desk.foundation import capabilities as caps_mod
from desk.foundation import paths as paths_mod


KEYS = {"mlx_h3", "venv", "models_root", "music_runtime", "image_runtime", "config"}


@pytest.fixture()
def dev_roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


@pytest.fixture()
def bundle_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    resources = tmp_path / "Resources"
    (resources / "desk").mkdir(parents=True)
    (resources / "bundle.json").write_text("{}", encoding="utf-8")
    return resources


def test_all_five_keys_always_present_and_probe_never_raises(dev_roots, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", "/definitely/not/there")
    roots = paths_mod.resolve_paths(resources_root=dev_roots.resources_root)
    caps = caps_mod.probe_capabilities(roots)

    assert set(caps) == KEYS
    assert caps["mlx_h3"].present is False
    assert caps["mlx_h3"].detail
    assert caps["models_root"].present is False
    assert caps["venv"].present is True
    assert caps["venv"].path == sys.executable
    assert caps["config"].present is True


def test_dev_mlx_h3_present_when_executable(dev_roots, tmp_path, monkeypatch):
    fake = tmp_path / "mlx-h3"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", str(fake))

    roots = paths_mod.resolve_paths(resources_root=dev_roots.resources_root)
    caps = caps_mod.probe_capabilities(roots)

    assert caps["mlx_h3"].present is True
    assert caps["mlx_h3"].detail == ""


def test_bundle_probes_are_directory_stats(bundle_tree):
    roots = paths_mod.resolve_paths(resources_root=bundle_tree)
    caps = caps_mod.probe_capabilities(roots)

    assert caps["mlx_h3"].present is False
    assert caps["music_runtime"].present is False
    assert caps["venv"].present is False

    (bundle_tree / "pylibs" / "h3" / "mlx_h3").mkdir(parents=True)
    (bundle_tree / "pylibs" / "music" / "mlx_minimax_music3").mkdir(parents=True)
    python = bundle_tree / "python" / "bin" / "python3.13"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)

    caps = caps_mod.probe_capabilities(roots)
    assert caps["mlx_h3"].present is True
    assert caps["music_runtime"].present is True
    assert caps["venv"].present is True


def test_models_root_present_after_first_run(dev_roots):
    from desk.foundation import firstrun

    firstrun.complete_first_run(dev_roots)
    roots = paths_mod.resolve_paths(resources_root=dev_roots.resources_root)

    assert caps_mod.probe_capabilities(roots)["models_root"].present is True


def test_corrupt_config_reported_not_raised(dev_roots):
    dev_roots.config_path.write_text("{nope", encoding="utf-8")
    caps = caps_mod.probe_capabilities(dev_roots)

    assert caps["config"].present is False
    assert caps["config"].detail
