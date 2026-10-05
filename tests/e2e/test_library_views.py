"""素材库预览（设计 L-10–L-51）：三视图、预览弹层、键盘、切页停声；截图写到 $LMD_LIBRARY_SHOTS。"""
import os
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_PNG


def _seed(harness, count=6):
    harness.outputs_root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (harness.outputs_root / f"seed {i}.png").write_bytes(TINY_PNG)


def _open_library(page, harness):
    page.goto(harness.base_url + "#tab=library")
    expect(page.locator("[data-lib-item]").first).to_be_visible()
    return page.locator("#pane-library")


def _shot(page, name):
    shots = os.environ.get("LMD_LIBRARY_SHOTS")
    if shots:
        page.evaluate("() => Promise.all(document.getAnimations().map((a) => a.finished))")  # 弹层淡入完再截
        Path(shots).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(shots) / f"{name}.png"))


def _no_horizontal_scroll(page):
    return page.evaluate("() => document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth")


def test_three_views_render_and_are_remembered(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        _seed(harness)
        for width in (1280, 900):
            page.set_viewport_size({"width": width, "height": 800})
            library = _open_library(page, harness)
            for view in ("grid", "list", "table"):
                library.locator(f"[data-lib-view-btn='{view}']").click()
                expect(library.locator("[data-lib-view]")).to_have_attribute("data-lib-mode", view)
                expect(library.locator("[data-lib-item]")).to_have_count(6)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#pane-library .lib-thumb img')].every((i) => i.complete && i.naturalWidth > 0)")
                assert _no_horizontal_scroll(page), (view, width)
                _shot(page, f"{view}-{width}")
        page.reload()
        expect(page.locator("[data-lib-view]")).to_have_attribute("data-lib-mode", "table")


def test_preview_opens_pages_and_closes_with_keyboard(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        _seed(harness, 3)
        page.set_viewport_size({"width": 1280, "height": 800})
        library = _open_library(page, harness)
        first = library.locator("[data-lib-item]").first
        first.click()
        expect(first).to_have_attribute("aria-current", "true")
        page.keyboard.press("ArrowRight")
        second = library.locator("[data-lib-item]").nth(1)
        expect(second).to_have_attribute("aria-current", "true")
        expect(second).to_be_focused()
        page.keyboard.press("Enter")
        dialog = page.locator(".lib-preview[role=dialog]")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-lib-preview-stage] img")).to_be_visible()
        _shot(page, "preview-1280")
        page.keyboard.press("ArrowRight")
        expect(dialog.locator("[data-lib-next]")).to_be_disabled()
        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        third = library.locator("[data-lib-item]").nth(2)
        expect(third).to_have_attribute("aria-current", "true")
        expect(third).to_be_focused()
        page.set_viewport_size({"width": 900, "height": 700})
        third.dblclick()
        expect(dialog).to_be_visible()
        _shot(page, "preview-900")
        dialog.get_by_role("button", name="关闭").click()
        expect(dialog).to_have_count(0)


def test_leaving_the_library_stops_audition(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        harness.outputs_root.mkdir(parents=True, exist_ok=True)
        (harness.outputs_root / "music3-seed.wav").write_bytes(_silent_wav())
        library = _open_library(page, harness)
        audition = library.locator("[data-lib-audition-btn]")
        audition.click()
        expect(audition).to_have_attribute("aria-pressed", "true")
        page.locator("#tabs [data-tab='chat']").click()
        assert page.evaluate("() => !document.querySelector('[data-lib-audition]').getAttribute('src')")
        page.locator("#tabs [data-tab='library']").click()
        expect(library.locator("[data-lib-audition-btn]")).to_have_attribute("aria-pressed", "false")


def _silent_wav(seconds=1, rate=8000):
    import struct
    frames = seconds * rate
    data = b"\x00\x00" * frames
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def test_long_prompt_keeps_preview_buttons_in_view(page, tmp_path):
    """F1：很长的提示词只让信息栏在弹层里滚动，关闭等按钮不能被推出视口。"""
    from desk.testing.scripts import MediaScript, fast_media_steps

    long_prompt = "一只橘猫坐在窗台上看着外面下雨，" * 50  # ~800 字
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
                             media_script=MediaScript([fast_media_steps()])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=image")
        image = page.locator("#pane-image")
        image.locator("[data-image-prompt]").fill(long_prompt)
        start = image.locator("[data-image-start]")
        expect(start).to_be_enabled()
        start.click()
        expect(image.locator(".attempt").first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        page.locator("#tabs [data-tab='library']").click()
        library = page.locator("#pane-library")
        expect(library.locator("[data-lib-item]").first).to_be_visible()
        library.locator("[data-lib-item]").first.dblclick()
        dialog = page.locator(".lib-preview[role=dialog]")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-lib-preview-stage] img")).to_be_visible()
        _shot(page, "preview-long-prompt-1280")
        for width, height in ((1280, 800), (900, 700)):
            page.set_viewport_size({"width": width, "height": height})
            close = dialog.get_by_role("button", name="关闭")
            if width <= 900:
                close.scroll_into_view_if_needed()
                _shot(page, "preview-long-prompt-900")
            box = close.bounding_box()
            assert box and box["y"] >= 0 and box["y"] + box["height"] <= height, (width, box)
            assert box["x"] >= 0 and box["x"] + box["width"] <= width, (width, box)
        page.set_viewport_size({"width": 1280, "height": 800})
        dialog.get_by_role("button", name="关闭").click()
        expect(dialog).to_have_count(0)
