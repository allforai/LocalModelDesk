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
