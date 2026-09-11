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


def test_messages_and_composer_keep_a_16px_gap(page, tmp_path):
    """N6: the scroll list must not be clipped right against the composer."""
    page.set_viewport_size({"width": 1200, "height": 832})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".composer")
        gap = page.evaluate(
            "() => document.querySelector('.composer').getBoundingClientRect().top"
            " - document.querySelector('.messages').getBoundingClientRect().bottom")
        assert gap >= 16, gap
