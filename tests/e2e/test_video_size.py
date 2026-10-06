# tests/e2e/test_video_size.py
"""视频画幅（视频画幅设计 Z-52）：竖屏档位与自定义尺寸真的按选的宽高生成；上传方图做首帧时方向切到方形；
续写时画幅控件锁住。截图写到 $LMD_VIDEO_SIZE_SHOTS（未设置时写 tmp_path）。"""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps


def _png(width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _shot(page, tmp_path, name):
    folder = Path(os.environ.get("LMD_VIDEO_SIZE_SHOTS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f"{name}.png"))


def _orientation(pane):
    return pane.locator("[data-video-orientation] [role=radio][aria-checked=true]")


def _attempts(page, harness):
    session_id = page.locator("#pane-video [data-video-session-list] li[aria-current='true']").get_attribute("data-session-id")
    response = page.request.get(f"{harness.base_url}/api/media-sessions/video/{session_id}")
    assert response.status == 200, response.text()
    return response.json()["attempts"]


def test_portrait_and_custom_sizes_generate_with_those_dimensions(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={"h3": "present"},
                             media_script=MediaScript([fast_media_steps(), fast_media_steps()])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-orientation] [role=radio]", has_text="竖屏").click()
        expect(_orientation(pane)).to_have_text("竖屏")
        pane.locator("[data-video-advanced] summary").click()
        pane.locator("[data-video-size]").select_option("448x768")
        pane.locator("[data-video-prompt]").fill("竖屏的雨夜街道")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-video-timeline] .attempt").first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        _shot(page, tmp_path, "portrait-1280")

        pane.locator("[data-video-size]").select_option("custom")
        pane.locator("[data-video-height]").fill("810")
        pane.locator("[data-video-height]").blur()
        expect(pane.locator("[data-video-height]")).to_have_value("800")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-video-timeline] .attempt")).to_have_count(2)
        expect(pane.locator("[data-video-timeline] .attempt").nth(1)).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        page.set_viewport_size({"width": 900, "height": 700})
        _shot(page, tmp_path, "custom-900")

        sizes = [(a["params"]["width"], a["params"]["height"]) for a in _attempts(page, harness)]
        assert sizes == [(448, 768), (448, 800)]


def test_square_first_frame_switches_orientation_and_continuation_locks_size(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={"h3": "present"},
                             media_script=MediaScript([fast_media_steps()])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        square = tmp_path / "square.png"
        square.write_bytes(_png(600, 600))
        pane.locator("[data-video-first-upload]").set_input_files(str(square))
        expect(_orientation(pane)).to_have_text("方形")
        expect(pane.locator("[data-video-shape-note]")).to_have_text("已按首帧切到方形")
        _shot(page, tmp_path, "square-first-frame-1280")

        pane.locator("[data-video-prompt]").fill("方形的猫")
        pane.locator("[data-video-start]").click()
        card = pane.locator("[data-video-timeline] .attempt").first
        expect(card).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        assert [(a["params"]["width"], a["params"]["height"]) for a in _attempts(page, harness)] == [(384, 384)]

        if card.get_attribute("aria-expanded") != "true":
            card.locator(".attempt-row").click()
        card.get_by_role("button", name="接着往下生").click()
        expect(pane.locator("[data-video-size]")).to_be_disabled()
        for radio in pane.locator("[data-video-orientation] [role=radio]").all():
            expect(radio).to_be_disabled()
        expect(pane.locator("[data-video-size]")).to_have_attribute("title", "接着往下生沿用上一段的画幅")
        pane.locator("[data-video-chip-clear]").click()
        expect(pane.locator("[data-video-size]")).to_be_enabled()
