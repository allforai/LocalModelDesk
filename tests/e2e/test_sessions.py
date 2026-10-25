"""R-e2e-04: chat sessions can be managed and survive a browser refresh.

2026-10-25：会话卡的动作（改名/删除）从「右侧常驻、悬停才露出的按钮列」改成右键菜单。
那条列一直扣着标题宽度，卡片里也不再留按钮。
"""
import re

import pytest
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_chat_sessions_can_be_created_switched_renamed_deleted_and_reloaded(
    page, tmp_path, audit_violations
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")

        pane.get_by_role("button", name="新会话").click()
        expect(pane.locator("[data-session-list] li")).to_have_count(2)

        original = pane.locator("[data-session-list] li").filter(has_text="新会话").first
        original.click(button="right")
        page.get_by_role("menuitem", name="改名").click()
        rename_input = pane.locator("[data-session-list] input")
        rename_input.fill("保留会话")
        rename_input.press("Enter")
        expect(pane.get_by_text("保留会话", exact=True)).to_be_visible()

        retained = pane.locator("[data-session-list] li").filter(has_text="保留会话")
        disposable = pane.locator("[data-session-list] li").filter(has_text="新会话")
        disposable.locator(".session-title").click()
        expect(disposable).to_have_class(re.compile(r"\bactive\b"))
        retained.locator(".session-title").click()
        expect(retained).to_have_class(re.compile(r"\bactive\b"))
        disposable.click(button="right")
        page.get_by_role("menuitem", name="删除").click()
        dialog = page.locator(".overlay .dialog")
        expect(dialog).to_contain_text("删除会话")
        dialog.get_by_role("button", name="删除").click()
        expect(pane.locator("[data-session-list] li")).to_have_count(1)

        page.reload()
        expect(pane.locator("[data-session-list] li")).to_have_count(1)
        expect(pane.get_by_text("保留会话", exact=True)).to_be_visible()
        assert [session["title"] for session in harness.library.list_chat_sessions()] == ["保留会话"]
    assert audit_violations == []


def test_clicking_a_card_switches_instead_of_renaming(page, tmp_path):
    """F7: hover-revealed action buttons must not sit on top of the card's own
    click target — a hover+click at the card's center must switch, not rename.
    2026-10-25 之后卡里连按钮都没有了（动作在右键菜单里），这条继续守着「点卡片＝切会话」。"""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.get_by_role("button", name="新会话").click()
        pane.get_by_role("button", name="新会话").click()
        cards = pane.locator("[data-session-list] li")
        expect(cards).to_have_count(3)

        target = cards.nth(1)
        target.hover()
        target.click()
        expect(target.locator("input")).to_have_count(0)
        expect(target).to_have_class(re.compile(r"\bactive\b"))
        expect(target.locator("button, .session-actions")).to_have_count(0)


def test_sessions_are_reachable_by_keyboard(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.get_by_role("button", name="新会话").click()
        cards = pane.locator("li.session")
        expect(cards).to_have_count(2)

        target_id = cards.nth(1).get_attribute("data-session-id")
        cards.nth(1).focus()
        page.keyboard.press("Enter")
        expect(pane.locator(f'li.session.active[data-session-id="{target_id}"]')).to_have_count(1)

        # 卡片里没有可 Tab 到的「改名/删除」按钮了，动作全部走 Shift+F10 打开的同一个菜单。
        menu = page.get_by_role("menu")
        page.keyboard.press("Shift+F10")
        expect(menu).to_be_visible()
        expect(page.get_by_role("menuitem", name="改名")).to_be_focused()
        page.keyboard.press("ArrowDown")
        expect(page.get_by_role("menuitem", name="删除")).to_be_focused()
        page.keyboard.press("ArrowUp")
        expect(page.get_by_role("menuitem", name="改名")).to_be_focused()
        page.keyboard.press("Escape")
        expect(menu).to_have_count(0)
        expect(cards.nth(1)).to_be_focused()

        # 菜单键打开、回车选中的那条路也能进改名，跟鼠标右键同一套动作。
        page.keyboard.press("Shift+F10")
        page.keyboard.press("Enter")
        rename = pane.locator("[data-session-list] input")
        expect(rename).to_be_focused()
        rename.press("Enter")  # 名称没改，不该发请求，输入框收起
        expect(pane.locator("[data-session-list] input")).to_have_count(0)
        assert pane.get_by_role("button", name=re.compile("^删除会话")).count() == 0
    assert audit_violations == []


def test_session_actions_live_in_a_right_click_menu_and_titles_use_the_whole_card(page, tmp_path):
    """右键菜单取代右侧动作列：① 卡里不再有按钮列；② 标题吃满整张卡的可用宽度
    （用户要的「可视区域变大」）；③ 右键吃掉浏览器自己的菜单；④ 菜单贴着指针但不出视口。"""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.get_by_role("button", name="新会话").click()
        card = pane.locator("[data-session-list] li").first

        expect(pane.locator("[data-session-list] .session-actions")).to_have_count(0)
        widths = page.evaluate(
            """() => {
                 const card = document.querySelector('#pane-chat [data-session-list] li.session');
                 const box = card.getBoundingClientRect();
                 const style = getComputedStyle(card);
                 const title = card.querySelector('.session-title').getBoundingClientRect();
                 return { title: title.width,
                          inner: box.width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
                                 - parseFloat(style.borderLeftWidth) - parseFloat(style.borderRightWidth) };
               }"""
        )
        assert widths["title"] == pytest.approx(widths["inner"], abs=0.5), widths

        # 浏览器/外壳默认的右键菜单（英文「重新载入」）必须被我们的菜单顶掉。
        prevented = page.evaluate(
            """() => new Promise((resolve) => {
                 const card = document.querySelector('#pane-chat [data-session-list] li.session');
                 card.addEventListener('contextmenu', (event) => resolve(event.defaultPrevented), { once: true });
                 card.dispatchEvent(new MouseEvent('contextmenu',
                   { bubbles: true, cancelable: true, clientX: 40, clientY: 40 }));
               })"""
        )
        assert prevented is True, "右键要吃掉浏览器自己的菜单"
        title = card.locator(".session-title").inner_text()
        menu = page.get_by_role("menu", name=re.compile(f"^会话操作：{re.escape(title)}"))
        expect(menu).to_be_visible()
        expect(page.get_by_role("menuitem", name="改名")).to_be_visible()
        expect(page.get_by_role("menuitem", name="删除")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("menu")).to_have_count(0)

        # 矮窗口 + 列表底部：菜单要收在视口里（放不下就翻到锚点上方）。
        page.set_viewport_size({"width": 900, "height": 620})
        for _ in range(8):
            pane.get_by_role("button", name="新会话").click()
        # 每次「新会话」回来都会重绘整个列表（旧的 li 被换掉），先等它落地再抓最后一个。
        expect(pane.locator("[data-session-list] li")).to_have_count(9)
        page.wait_for_timeout(150)
        last = pane.locator("[data-session-list] li").last
        last.scroll_into_view_if_needed()
        page.wait_for_timeout(200)  # 这一步的自动滚动自己会发 scroll 事件（见下一条），先让它落地
        last.click(button="right")
        expect(page.get_by_role("menu")).to_be_visible()
        box = page.get_by_role("menu").bounding_box()
        assert box["y"] >= 0, box
        assert box["y"] + box["height"] <= 620, box
        assert box["x"] >= 0, box
        assert box["x"] + box["width"] <= 900, box

        # 列表自己滚起来时菜单要收掉：它指着的是一个屏幕位置，底下的会话已经换人了。
        page.evaluate("() => { document.querySelector('#pane-chat .sessions').scrollTop = 0; }")
        expect(page.get_by_role("menu")).to_have_count(0)


def test_sidebar_does_not_clip_the_focus_ring_of_its_edge_controls(page, tmp_path, audit_violations):
    """真机 2026-09-15：会话栏的滚动裁切把「新会话」焦点框的上边和左边切掉了。
    焦点框（卡片为 2px 线 + 2px 间距）需要控件与会话栏边缘至少留 4px。"""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector("#pane-chat li.session")
        gaps = page.evaluate(
            "() => { const s = document.querySelector('#pane-chat .sessions').getBoundingClientRect();"
            " const b = document.querySelector('#pane-chat [data-session-new]').getBoundingClientRect();"
            " const c = document.querySelector('#pane-chat li.session').getBoundingClientRect();"
            " return {newTop: b.top - s.top, newLeft: b.left - s.left,"
            " cardLeft: c.left - s.left, cardRight: s.right - c.right}; }"
        )
        assert min(gaps.values()) >= 4, gaps
    assert audit_violations == []
