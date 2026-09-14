"""R-e2e-10: status-bar memory values come from the injected snapshots."""

import pytest
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.fakes import DEFAULT_SNAPSHOT_A, SNAPSHOT_B
from desk.testing.scripts import MemoryScript


def _rendered_numbers(snapshot):
    """Accept either documented GB convention while proving the input is rendered.

    The bar rounds to whole GiB so the window and the menu bar can never disagree on
    the same reading (N3), so accept the rounded form as well as the old one-decimal one.
    """
    divisors = (10**9, 1024**3)
    return {
        text
        for divisor in divisors
        for value in (
            snapshot.used_bytes,
            snapshot.total_bytes,
            snapshot.available_bytes,
        )
        for text in (f"{value / divisor:.1f}", str(round(value / divisor)))
    }


def _statusbar_contains_snapshot(statusbar, snapshot):
    text = statusbar.inner_text()
    return any(number in text for number in _rendered_numbers(snapshot))


def test_statusbar_memory_follows_injected_snapshot(page, tmp_path, wait_until):
    memory = MemoryScript([DEFAULT_SNAPSHOT_A])
    with launch_test_harness(tmp_path, memory_script=memory) as harness:
        page.goto(harness.base_url)
        statusbar = page.locator("#statusbar")

        expect(statusbar).to_contain_text("已用")
        assert _statusbar_contains_snapshot(statusbar, DEFAULT_SNAPSHOT_A)

        memory.push(SNAPSHOT_B)
        wait_until(lambda: _statusbar_contains_snapshot(statusbar, SNAPSHOT_B), timeout=6)
        assert _statusbar_contains_snapshot(statusbar, SNAPSHOT_B)
        assert "128" not in statusbar.inner_text()


@pytest.mark.parametrize("width", [900, 1440, 1920])
def test_four_states_are_never_truncated(page, tmp_path, width):
    """D3: the four states must read in full at every declared width, including the
    longer busy-state wording that F1 caught at 900px (media busy + a mutex reason)."""
    page.set_viewport_size({"width": width, "height": 800})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("#tabs [data-tab='video']").click()
        page.locator("[data-video-prompt]").fill("a quiet street in rain")
        page.locator("[data-video-start]").click()
        expect_visible = page.locator("#statusbar")
        expect_visible.wait_for()
        clipped = page.evaluate(
            "() => [...document.querySelectorAll('#statusbar .status-part span')]"
            ".filter(el => el.offsetParent !== null && el.scrollWidth > el.clientWidth + 1)"
            ".map(el => el.textContent)"
        )
        assert clipped == [], f"{width} 宽下被截断：{clipped}"
