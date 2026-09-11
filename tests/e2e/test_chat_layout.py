"""L6: a fixed-pixel centered main column must not waste more than the cap on wide windows."""
import pytest

from desk.testing import launch_test_harness

CASES = [(1440, 1000, 0.40), (1920, 1200, 0.40)]


@pytest.mark.parametrize("width,height,max_ratio", CASES)
def test_message_column_keeps_whitespace_under_the_cap(page, tmp_path, width, height, max_ratio):
    page.set_viewport_size({"width": width, "height": height})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        box = page.evaluate(
            "() => { const m = document.querySelector('.messages').getBoundingClientRect();"
            " const host = document.querySelector('.chat-main').getBoundingClientRect();"
            " return {col: m.width, host: host.width}; }"
        )
        whitespace = box["host"] - box["col"]
        assert whitespace / width <= max_ratio, (
            f"{width} 宽下消息列两侧留白 {whitespace:.0f}px = {whitespace / width:.1%}")


def test_composer_tracks_the_message_column(page, tmp_path):
    page.set_viewport_size({"width": 1920, "height": 1200})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".composer")
        widths = page.evaluate(
            "() => [document.querySelector('.messages').getBoundingClientRect().width,"
            " document.querySelector('.composer').getBoundingClientRect().width]"
        )
        assert abs(widths[0] - widths[1]) < 2
