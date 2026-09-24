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


# ---- main(): img2img arguments reach mflux (image-to-image, 2026-09-24) ----

import sys
import types
from pathlib import Path

import pytest


def _fake_runtime(monkeypatch, calls):
    """mlx + mflux stand-ins: record generate_image kwargs, save a byte to the output path."""
    core = types.SimpleNamespace(metal=types.SimpleNamespace(is_available=lambda: True),
                                 get_peak_memory=lambda: 0, eval=lambda *_: None)
    mlx = types.ModuleType("mlx"); mlx.core = core
    monkeypatch.setitem(sys.modules, "mlx", mlx)
    monkeypatch.setitem(sys.modules, "mlx.core", core)

    class Result:
        def save(self, path):
            Path(path).write_bytes(b"png")

    class QwenImage21:
        def __init__(self, model_path):
            self.callbacks = types.SimpleNamespace(register=lambda _cb: None)

        def generate_image(self, **kwargs):
            calls.append(kwargs)
            return Result()

    name = "mflux.models.qwen21.variants.txt2img.qwen_image_21"
    module = types.ModuleType(name); module.QwenImage21 = QwenImage21
    monkeypatch.setitem(sys.modules, name, module)
    from desk.media import image_cli
    monkeypatch.setattr(image_cli, "version", lambda _pkg: "0")
    return image_cli


def _run(monkeypatch, image_cli, argv):
    monkeypatch.setattr(sys, "argv", ["image_cli", *argv])
    image_cli.main()


def test_init_image_and_strength_are_passed_to_mflux(tmp_path, monkeypatch):
    calls = []
    image_cli = _fake_runtime(monkeypatch, calls)
    root = tmp_path / "model"; pipeline(root)
    base = tmp_path / "base.png"; base.write_bytes(b"png")
    out = tmp_path / "out.png"
    _run(monkeypatch, image_cli, ["--root", str(root), "--prompt", "猫", "--width", "512", "--height", "512",
                                  "--steps", "8", "--seed", "3", "--output", str(out),
                                  "--init-image", str(base), "--image-strength", "0.6"])
    assert calls[-1]["image_path"] == str(base) and calls[-1]["image_strength"] == 0.6
    meta = json.loads(out.with_suffix(".json").read_text())
    assert meta["init_image"] == str(base) and meta["image_strength"] == 0.6


def test_plain_generation_passes_no_init_image(tmp_path, monkeypatch):
    calls = []
    image_cli = _fake_runtime(monkeypatch, calls)
    root = tmp_path / "model"; pipeline(root)
    _run(monkeypatch, image_cli, ["--root", str(root), "--prompt", "猫", "--output", str(tmp_path / "o.png")])
    assert "image_path" not in calls[-1] and "image_strength" not in calls[-1]


@pytest.mark.parametrize("extra", [["--image-strength", "0.6"], ["--init-image", "MISSING", "--image-strength", "0.6"],
                                   ["--init-image", "BASE", "--image-strength", "1.5"], ["--init-image", "BASE"]])
def test_bad_img2img_arguments_are_rejected(tmp_path, monkeypatch, extra):
    calls = []
    image_cli = _fake_runtime(monkeypatch, calls)
    root = tmp_path / "model"; pipeline(root)
    base = tmp_path / "base.png"; base.write_bytes(b"png")
    extra = [str(base) if a == "BASE" else str(tmp_path / "nope.png") if a == "MISSING" else a for a in extra]
    with pytest.raises(SystemExit):
        _run(monkeypatch, image_cli, ["--root", str(root), "--prompt", "猫", "--output", str(tmp_path / "o.png"), *extra])
    assert calls == []
