"""The readback the app hands a visual capture must survive contact with a real page.

The expression lives in `macos/VisualProbe.swift` and runs inside the app's WKWebView, where nothing
here can execute it. What this test can prove is that it is valid JS against the real desk UI and
reports the values a capture is judged against — a typo there would only surface mid-capture, after
the window has already been resized and photographed.
"""
import json
import re
from pathlib import Path

import pytest

from desk.testing import launch_test_harness

PROBE = Path(__file__).resolve().parents[2] / "macos" / "VisualProbe.swift"
REQUIRED = {"appearance", "locale", "direction", "width", "height", "device_pixel_ratio",
            "root_font_px", "pointer", "hover", "scroll_profile", "scroll_source", "pane", "tab",
            "dynamic_type", "orientation"}


def readback_js() -> str:
    source = PROBE.read_text(encoding="utf-8")
    match = re.search(r'let visualReadbackJS = """\n(.*?)\n"""', source, re.S)
    assert match, "macos/VisualProbe.swift no longer defines visualReadbackJS as a multiline string"
    return match.group(1)


def test_the_readback_expression_reports_every_axis_the_matrix_binds(page, tmp_path):
    page.set_viewport_size({"width": 1280, "height": 800})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        raw = page.evaluate(readback_js())
    value = json.loads(raw)
    assert REQUIRED <= set(value), f"readback missing {REQUIRED - set(value)}"
    assert value["width"] == 1280            # the width a capture is checked against
    assert value["appearance"] in ("dark", "light")
    assert value["pointer"] in ("mouse", "touch")
    assert value["locale"], "the locale axis needs a value, not an empty string"
    # These two are axis values the matrix binds by name, so they must read back in the matrix's words.
    assert value["dynamic_type"] == "浏览器缩放 100%"
    assert value["orientation"] == "landscape"


def test_the_readback_measures_the_scroll_gutter(page, tmp_path):
    """`gutter_px` is how a capture proves it was taken with the scrollbars the app really draws."""
    page.set_viewport_size({"width": 1280, "height": 800})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        value = json.loads(page.evaluate(readback_js()))
    profile = value["scroll_profile"]
    assert profile is not None
    # The element it measured must be named, and must be one that is actually on screen: a hidden pane
    # measures 0 everywhere and would claim "no scrollbar" for every tab the chat does not live in.
    assert value["scroll_source"], "readback must say which element it measured"
    assert profile["client_height"] > 0
    assert set(profile) == {"scroll_width", "client_width", "scroll_height", "client_height", "gutter_px"}
    assert profile["gutter_px"] >= 0
