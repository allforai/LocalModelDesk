import json

import pytest

from desk.media.image_cli import validate_model
from desk.media.image_model import PROVENANCE, files, prepare_destination


def pipeline(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    meta = {**PROVENANCE, "complete": True}
    (tmp_path / "localmodeldesk-image.json").write_text(json.dumps(meta))
    for item in files():
        path = tmp_path / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.truncate(item["size"])
    return meta


def test_complete_marker_does_not_hide_missing_encoder_shard(tmp_path):
    pipeline(tmp_path)
    (tmp_path / "text_encoder/model-00001-of-00004.safetensors").unlink()
    with pytest.raises(ValueError, match="分片缺失"):
        validate_model(tmp_path)


def test_incomplete_download_rejected_before_loading_gpu(tmp_path):
    meta = pipeline(tmp_path)
    meta["complete"] = False
    (tmp_path / "localmodeldesk-image.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="未下载完成"):
        validate_model(tmp_path)


def test_encoder_cannot_silently_fall_back_to_original(tmp_path):
    meta = pipeline(tmp_path)
    assert validate_model(tmp_path) == meta
    meta["text_encoder"] = "Qwen/Qwen3-VL-8B-Instruct"
    (tmp_path / "localmodeldesk-image.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="来源不匹配"):
        validate_model(tmp_path)


def test_truncated_file_rejected(tmp_path):
    pipeline(tmp_path)
    (tmp_path / "processor/tokenizer.json").write_bytes(b"broken")
    with pytest.raises(ValueError, match="不完整"):
        validate_model(tmp_path)


def test_unknown_directory_preserved_and_known_partial_resumable(tmp_path):
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    (unknown / "user-file").write_text("keep")
    with pytest.raises(ValueError):
        prepare_destination(unknown)
    assert (unknown / "user-file").read_text() == "keep"
    managed = tmp_path / "managed"
    prepare_destination(managed)
    (managed / "partial.part").write_text("resume")
    prepare_destination(managed)
    assert (managed / "partial.part").read_text() == "resume"


def test_marker_symlink_cannot_modify_external_file(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({**PROVENANCE, "complete": True}))
    original = outside.read_text()
    root = tmp_path / "model"
    root.mkdir()
    (root / "localmodeldesk-image.json").symlink_to(outside)
    with pytest.raises(ValueError, match="符号链接"):
        prepare_destination(root)
    assert outside.read_text() == original
