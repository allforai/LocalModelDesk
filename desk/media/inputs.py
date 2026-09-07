"""Local conditioning assets, addressed by opaque IDs rather than client paths."""
import base64
import binascii
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

MAX_INPUT_BYTES = 32 * 1024 * 1024
EXTENSIONS = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
              ".mp4": "video", ".mov": "video", ".webm": "video"}


def _tool(name, default=None):
    """Locate an ffmpeg-suite binary: LOCALMODELDESK_FF* override, then PATH.

    Absolute build-machine prefixes must not appear here: a shipped bundle that
    names one fails the self-containment check in scripts/verify-app.sh (V3).
    """
    return os.environ.get("LOCALMODELDESK_" + name.upper()) or shutil.which(name) or default or name


def resolve_input(root, asset_id, kind):
    if not isinstance(asset_id, str) or not re.fullmatch(r"[0-9a-f]{32}\.[a-z0-9]+", asset_id):
        raise ValueError("素材编号无效，请重新选择文件")
    path = Path(root) / ".inputs" / asset_id
    if EXTENSIONS.get(path.suffix) != kind or not path.is_file() or path.is_symlink():
        raise ValueError("素材不存在或类型不匹配，请重新选择文件")
    return path


def save_input(root, name, data):
    suffix = Path(name).suffix.lower() if isinstance(name, str) else ""
    if suffix not in EXTENSIONS:
        raise ValueError("请选择 PNG、JPEG、WebP 图片或 MP4、MOV、WebM 视频")
    if not isinstance(data, str) or len(data) > ((MAX_INPUT_BYTES + 2) // 3) * 4:
        raise ValueError("素材不能超过 32 MB")
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("素材内容无效") from None
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("素材为空或超过 32 MB")
    directory = Path(root) / ".inputs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (uuid.uuid4().hex + suffix)
    try:
        path.write_bytes(raw)
        probe = _tool("ffprobe")
        result = subprocess.run([probe, "-v", "error", "-show_streams", "-show_format",
                                 "-of", "json", str(path)], capture_output=True, timeout=15, check=True)
        info = json.loads(result.stdout)
        if EXTENSIONS[suffix] == "image":
            ffmpeg = _tool("ffmpeg", probe.replace("ffprobe", "ffmpeg"))
            decode = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"],
                                    capture_output=True, timeout=30)
            if decode.returncode != 0:
                raise ValueError("图片文件已损坏，无法解码")
        visual = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if not visual or not visual.get("width") or not visual.get("height"):
            raise ValueError("文件没有可读取的画面")
        if EXTENSIONS[suffix] == "image" and visual.get("codec_name") not in ("png", "mjpeg", "webp"):
            raise ValueError("图片内容与文件格式不符")
        if EXTENSIONS[suffix] == "video" and not 0 < float(info.get("format", {}).get("duration", 0)) <= 15:
            raise ValueError("参考视频须在 15 秒以内，请先裁剪")
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError("无法读取素材，请检查文件格式及 ffprobe 是否可用") from exc
    return {"id": path.name, "kind": EXTENSIONS[suffix], "name": name}
