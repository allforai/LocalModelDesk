"""R-e2e-04: chat sessions can be managed and survive a browser refresh."""
import re

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
        original.hover()
        original.get_by_role("button", name="改名").click()
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
        disposable.hover()
        disposable.get_by_role("button", name="删").click()
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
    click target — a hover+click at the card's center must switch, not rename."""
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
