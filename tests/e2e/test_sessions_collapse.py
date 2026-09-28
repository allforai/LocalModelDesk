"""Session sidebar collapse, end to end in real Chromium.

One shared switch for the four session sidebars (chat, image, music, video): collapsing frees the
left column for the main area, the state carries across tabs and survives a reload, and the
collapsed rail keeps working 「展开会话栏」 and 「新会话」 icon buttons.

Screenshots (expanded / collapsed at 1280×800 and 900×700) go to $LMD_SESSIONS_COLLAPSE_SHOTS when
set, otherwise to the test's tmp_path.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def _shots(tmp_path) -> Path:
    target = Path(os.environ.get("LMD_SESSIONS_COLLAPSE_SHOTS") or tmp_path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _width(locator) -> float:
    return locator.evaluate("(n) => n.getBoundingClientRect().width")


def _settle(page):
    # Wait out the 220 ms width transition before measuring.
    page.wait_for_timeout(400)


def test_collapse_frees_the_left_column_and_is_shared_and_remembered(page, tmp_path):
    shots = _shots(tmp_path)
    with launch_test_harness(tmp_path) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=image")
        pane = page.locator("#pane-image")
        expect(pane).to_be_visible()
        aside = pane.locator("aside.sessions")
        toggle = aside.locator("[data-sessions-toggle]")
        main = pane.locator(".image-main")
        expect(toggle).to_have_attribute("aria-label", "收起会话栏")
        expect(toggle).to_have_attribute("aria-expanded", "true")
        expect(aside.locator("[data-image-session-list] li")).to_have_count(1)
        wide_aside, narrow_main = _width(aside), _width(main)
        page.screenshot(path=str(shots / "sessions-expanded-1280.png"))

        # Collapse: a narrow rail, the list gone, the main area wider by the freed width.
        toggle.click()
        _settle(page)
        expect(toggle).to_have_attribute("aria-label", "展开会话栏")
        expect(toggle).to_have_attribute("aria-expanded", "false")
        assert _width(aside) <= 48, _width(aside)
        assert _width(main) >= narrow_main + (wide_aside - 48) - 2, (_width(main), narrow_main, wide_aside)
        expect(aside.locator("[data-image-session-list]")).to_be_hidden()
        new_btn = aside.locator("[data-image-session-new]")
        expect(new_btn).to_be_visible()
        expect(new_btn).to_have_attribute("aria-label", "新会话")
        assert _width(new_btn) <= 40, _width(new_btn)
        # Rail order: the expand control sits above 「新会话」.
        assert toggle.bounding_box()["y"] < new_btn.bounding_box()["y"]
        page.screenshot(path=str(shots / "sessions-collapsed-1280.png"))

        # 「新会话」 still works from the rail.
        new_btn.click()
        expect(aside.locator("[data-image-session-list] li")).to_have_count(2)

        # Shared across tabs.
        for tab in ("chat", "music", "video"):
            page.goto(harness.base_url + f"#tab={tab}")
            other = page.locator(f"#pane-{tab} aside.sessions")
            expect(other).to_be_visible()
            expect(other).to_have_class(re.compile(r"\bis-collapsed\b"))
            expect(other.locator("[data-sessions-toggle]")).to_have_attribute("aria-expanded", "false")

        # Remembered across a reload.
        page.reload()
        page.goto(harness.base_url + "#tab=music")
        music_aside = page.locator("#pane-music aside.sessions")
        expect(music_aside.locator("[data-sessions-toggle]")).to_have_attribute("aria-expanded", "false")

        # Small window: no horizontal scroll, controls not clipped.
        page.set_viewport_size({"width": 900, "height": 700})
        _settle(page)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(shots / "sessions-collapsed-900.png"))

        # Expand again from the rail: list back, labels back.
        music_aside.locator("[data-sessions-toggle]").click()
        _settle(page)
        expect(music_aside.locator("[data-sessions-toggle]")).to_have_attribute("aria-label", "收起会话栏")
        expect(music_aside.locator("[data-music-session-list]")).to_be_visible()
        expect(music_aside.locator(".sessions-new-label")).to_have_text("新会话")
        assert _width(music_aside) >= 240, _width(music_aside)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(shots / "sessions-expanded-900.png"))
