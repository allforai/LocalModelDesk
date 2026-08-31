"""Adoption tests using tiny fake model files."""
import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import LegacyRootError


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


def make_legacy(tmp_path, name="legacy"):
    legacy = tmp_path / name
    files = {
        "llms/org/repo-a/model-00001.safetensors": b"A" * 40,
        "llms/org/repo-a/config.json": b"{}",
        "minimax-h3/dit.safetensors": b"H" * 64,
        "minimax-music3/music.safetensors": b"M" * 32,
    }
    for rel, content in files.items():
        path = legacy / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return legacy


def snapshot(root):
    return sorted(
        (str(path.relative_to(root)), path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    )


def test_point_mode_repoints_without_touching_source(roots, tmp_path):
    legacy = make_legacy(tmp_path)
    before = snapshot(legacy)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")

    assert result.mode == "point"
    assert result.models_root == legacy.resolve()
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert result.moved_bytes == 0
    assert result.source_retained is False
    assert snapshot(legacy) == before
    cfg = config_mod.read_config(roots)
    assert cfg.models_root == legacy.resolve()
    assert cfg.first_run_done is True


def test_partial_legacy_tree_is_accepted(roots, tmp_path):
    legacy = tmp_path / "only-llms"
    (legacy / "llms" / "o" / "r").mkdir(parents=True)
    (legacy / "llms" / "o" / "r" / "w.safetensors").write_bytes(b"x" * 10)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")

    assert result.adopted == ["llms"]


def test_no_known_subtree_raises(roots, tmp_path):
    empty = tmp_path / "nothing"
    (empty / "unrelated").mkdir(parents=True)

    with pytest.raises(LegacyRootError) as exc:
        firstrun.adopt_legacy_models(roots, empty, mode="point")

    assert exc.value.code == "legacy_root_invalid"
    assert not roots.config_path.exists()


def test_unknown_mode_raises(roots, tmp_path):
    legacy = make_legacy(tmp_path)

    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="copy")
