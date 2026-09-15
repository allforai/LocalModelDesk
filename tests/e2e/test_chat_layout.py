"""L6: a fixed-pixel centered main column must not waste more than the cap on wide windows."""
import pytest

from desk.testing import launch_test_harness

CASES = [(800, 832, 0.40), (1024, 768, 0.40), (1280, 800, 0.40), (1440, 1000, 0.40),
         (1920, 1200, 0.40), (2240, 1260, 0.40), (2560, 1440, 0.40)]


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


@pytest.mark.parametrize("width,height", [(1024, 768), (1440, 1000), (1920, 1080), (2560, 1440)])
def test_message_column_fills_the_chat_area_up_to_1400px(page, tmp_path, width, height):
    """用户 2026-09-15 选择：消息列宽 = 聊天区宽 − 48px（两侧各留 24px），最宽 1400px；超过后两侧留白继续变宽。"""
    page.set_viewport_size({"width": width, "height": height})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        box = page.evaluate(
            "() => { const m = document.querySelector('.messages').getBoundingClientRect();"
            " const c = document.querySelector('.composer').getBoundingClientRect();"
            " const host = document.querySelector('.chat-main').getBoundingClientRect();"
            " return {col: m.width, composer: c.width, host: host.width}; }"
        )
        expected = min(box["host"] - 48, 1400)
        assert abs(box["col"] - expected) <= 2, f"{width} 宽：消息列 {box['col']:.0f}px，应为 {expected:.0f}px"
        assert abs(box["composer"] - expected) <= 2, f"{width} 宽：输入区 {box['composer']:.0f}px，应为 {expected:.0f}px"


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


@pytest.mark.parametrize("width", [800, 2560])
def test_no_horizontal_overflow_at_the_extremes(page, tmp_path, width):
    page.set_viewport_size({"width": width, "height": 900})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_scrollbars_are_thin_in_the_session_list_and_messages(page, tmp_path):
    """用户 2026-09-16 截图：会话列和消息列的系统滚动条又宽又亮，和深色界面格格不入。"""
    page.set_viewport_size({"width": 1440, "height": 600})
    with launch_test_harness(tmp_path) as harness:
        for n in range(12):
            page.request.post(f"{harness.base_url}/api/sessions", data={"title": f"会话 {n}"})
        page.goto(harness.base_url)
        page.wait_for_selector("#pane-chat li.session")
        widths = page.evaluate(
            "() => { const box = (sel) => { const el = document.querySelector(sel);"
            " const cs = getComputedStyle(el);"
            " const borders = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);"
            " return {overflows: el.scrollHeight > el.clientHeight, bar: el.offsetWidth - el.clientWidth - borders}; };"
            " const m = document.querySelector('#pane-chat .messages');"
            " for (let i = 0; i < 60; i++) { const p = document.createElement('p'); p.textContent = '填充'; m.append(p); }"
            " return {sessions: box('#pane-chat .sessions'), messages: box('#pane-chat .messages')}; }"
        )
        assert widths["sessions"]["overflows"] and widths["messages"]["overflows"], widths
        assert widths["sessions"]["bar"] <= 8, widths
        assert widths["messages"]["bar"] <= 8, widths
