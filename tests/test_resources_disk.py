import os

from desk.resources.catalog import CATALOG
from desk.resources.disk import DiskUsage, dir_bytes, disk_usage, volume_free


def test_dir_bytes_sums_recursively(tmp_path):
    directory = tmp_path / "m"
    (directory / "sub").mkdir(parents=True)
    (directory / "a.bin").write_bytes(b"x" * 100)
    (directory / "sub" / "b.bin").write_bytes(b"y" * 60)
    assert dir_bytes(directory) == 160


def test_dir_bytes_missing_dir_is_zero(tmp_path):
    assert dir_bytes(tmp_path / "nope") == 0


def test_dir_bytes_does_not_follow_symlinked_dirs(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"z" * 10_000)
    directory = tmp_path / "m"
    directory.mkdir()
    (directory / "a.bin").write_bytes(b"x" * 10)
    os.symlink(outside, directory / "link")
    assert dir_bytes(directory) < 10_000


def test_volume_free_positive_and_climbs_missing_parents(tmp_path):
    free, total = volume_free(tmp_path / "does" / "not" / "exist")
    assert free > 0
    assert total >= free


def test_disk_usage_per_model_matches_manual_sums(tmp_path):
    root = tmp_path / "models"
    (root / "minimax-h3").mkdir(parents=True)
    (root / "minimax-h3" / "w.safetensors").write_bytes(b"a" * 50)
    usage = disk_usage(root, CATALOG)
    assert isinstance(usage, DiskUsage)
    assert usage.models_root == str(root)
    assert set(usage.per_model) == {entry.key for entry in CATALOG}
    assert usage.per_model["h3"] == 50
    assert usage.per_model["glm"] == 0
    assert usage.free_bytes > 0 and usage.total_bytes > 0
    assert usage.to_json()["per_model"]["h3"] == 50
