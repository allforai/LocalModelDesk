import json

from desk.resources.catalog import entry
from desk.resources.manifest import Manifest, ManifestFile
from desk.resources.verify import FileGap, unknown_status, verify_tree


GLM = entry("glm")

MANIFEST = Manifest(
    repo=GLM.hf_repo,
    files=(
        ManifestFile("model.safetensors", 100),
        ManifestFile("tokenizer.json", 60),
        ManifestFile("sub/weights.bin", 40),
    ),
    fetched_at="2026-08-31T00:00:00+00:00",
    source="fresh",
)


def model_dir(tmp_path):
    directory = tmp_path / GLM.relpath
    (directory / "sub").mkdir(parents=True)
    return directory


def test_full_tree_is_present(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "model.safetensors").write_bytes(b"a" * 100)
    (directory / "tokenizer.json").write_bytes(b"b" * 60)
    (directory / "sub" / "weights.bin").write_bytes(b"c" * 40)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "present"
    assert status.percent == 100.0
    assert status.gaps == ()
    assert status.bytes_expected == 200
    assert status.bytes_local == 200
    assert status.manifest_source == "fresh"
    assert status.manifest_fetched_at == "2026-08-31T00:00:00+00:00"


def test_half_tree_is_partial_with_byte_percent_and_gaps(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "model.safetensors").write_bytes(b"a" * 100)
    (directory / "tokenizer.json").write_bytes(b"b" * 30)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "partial"
    assert status.bytes_local == 130
    assert status.percent == 65.0
    assert status.gaps == (
        FileGap("tokenizer.json", 60, 30),
        FileGap("sub/weights.bin", 40, 0),
    )


def test_empty_tree_is_missing(tmp_path):
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "missing"
    assert status.percent == 0.0
    assert status.bytes_local == 0
    assert len(status.gaps) == 3


def test_junk_files_do_not_change_state_but_count_in_disk_bytes(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "model.safetensors").write_bytes(b"a" * 100)
    (directory / "tokenizer.json").write_bytes(b"b" * 60)
    (directory / "sub" / "weights.bin").write_bytes(b"c" * 40)
    (directory / "junk.tmp").write_bytes(b"j" * 500)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "present"
    assert status.percent == 100.0
    assert status.bytes_local == 200
    assert status.disk_bytes == 700


def test_oversized_local_file_is_truncated_in_percent(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "model.safetensors").write_bytes(b"a" * 120)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.bytes_local == 100
    assert status.state == "partial"
    assert FileGap("model.safetensors", 100, 120) in status.gaps


def test_unknown_status_reports_degradation_honestly():
    status = unknown_status(GLM, disk_bytes_=1234)
    assert status.state == "unknown"
    assert status.reason == "manifest_unavailable"
    assert status.percent == 0.0
    assert status.bytes_expected == 0
    assert status.disk_bytes == 1234
    assert status.manifest_source == "none"
    assert status.manifest_fetched_at is None


def test_to_json_is_plain_data(tmp_path):
    status = verify_tree(GLM, MANIFEST, tmp_path)
    payload = status.to_json()
    assert json.dumps(payload)
    assert payload["gaps"][0]["expected_size"] == 100


def test_incomplete_cache_bytes_count_toward_percent_but_not_bytes_local(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "tokenizer.json").write_bytes(b"b" * 60)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "model.safetensors.abc123.incomplete").write_bytes(b"x" * 70)
    # A download is actively running for this model (active_since predates the
    # blob's mtime), so its .incomplete bytes count as in-flight progress.
    status = verify_tree(GLM, MANIFEST, tmp_path, active_since=0.0)
    assert status.state == "partial"
    assert status.bytes_local == 60
    assert status.bytes_in_flight == 70
    assert status.stale_bytes == 0
    assert status.percent == 65.0          # (60 + 70) / 200


def test_incomplete_bytes_are_capped_at_expected_total(tmp_path):
    directory = model_dir(tmp_path)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "big.incomplete").write_bytes(b"x" * 500)
    status = verify_tree(GLM, MANIFEST, tmp_path, active_since=0.0)
    assert status.state == "partial"
    assert status.percent == 100.0 or status.percent < 100.0 and status.bytes_in_flight == 200


def test_stale_incomplete_is_reported_not_counted(tmp_path):
    """没有下载在跑时，.incomplete 是上次的死数据，不许算成进度（J18）。"""
    directory = model_dir(tmp_path)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "model.safetensors.deadbeef.incomplete").write_bytes(b"x" * 400)

    status = verify_tree(GLM, MANIFEST, tmp_path, active_since=None)
    assert status.bytes_in_flight == 0
    assert status.stale_bytes == 400
    assert status.percent == 0.0


def test_stale_incomplete_from_a_previous_attempt_is_excluded_while_new_attempt_runs(tmp_path):
    """陈旧残片（旧 attempt）与新残片（当前 attempt）并存时，只有新的计入进度（J18）。"""
    import os
    import time

    directory = model_dir(tmp_path)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    dead = cache / "model.safetensors.olddead.incomplete"
    dead.write_bytes(b"x" * 40)
    past = time.time() - 3600
    os.utime(dead, (past, past))
    active_since = time.time()
    fresh = cache / "model.safetensors.newhash.incomplete"
    fresh.write_bytes(b"y" * 15)

    status = verify_tree(GLM, MANIFEST, tmp_path, active_since=active_since)
    assert status.bytes_in_flight == 15
    assert status.stale_bytes == 40
