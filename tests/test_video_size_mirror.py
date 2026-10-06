"""视频画幅规则与内存公式以 Python 为准，desk/static/js/pure/video_size.js 镜像一份给页面即时反馈（视频画幅设计 Z-04）。
两边一旦不一致，页面就会放行后端拒绝的尺寸，或报错误的 GiB 数——所以把 JS 常量钉在 Python 的值上。"""
import re
from pathlib import Path

from desk.media import memory_estimate, service
from desk.media.commands import H3_BUDGET_GB

JS = (Path(__file__).resolve().parents[1] / "desk/static/js/pure/video_size.js").read_text(encoding="utf-8")


def _js_number(name: str) -> float:
    match = re.search(rf"\b{name}\s*=\s*([0-9.]+)\s*;", JS)
    assert match, f"{name} not found in video_size.js"
    return float(match.group(1))


def test_canvas_rules_match_the_backend():
    assert _js_number("MULTIPLE") == service.VIDEO_CANVAS_MULTIPLE
    assert _js_number("SIDE_MIN") == service.VIDEO_SIDE_MIN
    assert _js_number("SIDE_MAX") == service.VIDEO_SIDE_MAX
    assert "MAX_PIXELS = 768 * 1344;" in JS and service.VIDEO_MAX_PIXELS == 768 * 1344


def test_memory_formula_and_budget_match_the_backend():
    fixed, per_unit = memory_estimate._VIDEO
    assert _js_number("FIXED_GIB") * memory_estimate.GIB == fixed
    assert _js_number("PER_VOLUME_GIB") * memory_estimate.GIB == per_unit
    assert "DRAFT_VOLUME = 512 * 288 * 49;" in JS and memory_estimate._DRAFT_VOLUME == 512 * 288 * 49
    assert _js_number("H3_BUDGET_GIB") == H3_BUDGET_GB
