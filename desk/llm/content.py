"""Validate multimodal messages without fetching remote URLs or local files."""
from __future__ import annotations

import base64
import binascii
import re

MAX_IMAGE_BYTES = 5 * 1024 * 1024
_IMAGE = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")


def normalize_content(content, role="user"):
    if not isinstance(content, list):
        return content
    result = []
    for block in content:
        if not isinstance(block, dict):
            raise ValueError("content blocks must be objects")
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            result.append({"type": "text", "text": block["text"]})
        elif block.get("type") == "image_url" and role == "user":
            image = block.get("image_url")
            url = image.get("url") if isinstance(image, dict) else None
            match = _IMAGE.fullmatch(url) if isinstance(url, str) else None
            if not match or len(match[2]) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
                raise ValueError("images require a base64 PNG, JPEG or WebP data URL (at most 5 MiB)")
            try:
                raw = base64.b64decode(match[2], validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("invalid image base64") from exc
            if not raw or len(raw) > MAX_IMAGE_BYTES:
                raise ValueError("invalid image size")
            # Decode validation happens in the vision processor; do not accept paths/URLs.
            result.append({"type": "image_url", "image_url": {"url": url}})
        else:
            raise ValueError("only text and user image_url blocks are supported")
    if all(b["type"] == "text" for b in result):
        return "".join(b["text"] for b in result)
    return result


def has_images(messages):
    return any(isinstance(m.get("content"), list) and
               any(b.get("type") == "image_url" for b in m["content"]) for m in messages)


def uses_vision(model_dir):
    import json
    try:
        config = json.loads((model_dir / "config.json").read_text())
        return bool(config.get("vision_config"))
    except (OSError, ValueError):
        return False
