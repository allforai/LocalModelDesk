"""R-e2e-03: chat renders each SSE delta and saves the completed exchange."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_chat_stream_flushes_each_delta_and_persists_completed_exchange(
    page, tmp_path, audit_violations, wait_until
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        pane.locator("[data-chat-input]").fill("你好")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".reasoning pre").last).to_have_text("让我想想，")

        harness.chat_script.step()
        expect(pane.locator(".reasoning pre").last).to_have_text("让我想想，想好了。")

        harness.chat_script.step()
        expect(pane.locator(".msg-assistant .msg-content").last).to_have_text("你好")

        harness.chat_script.step()
        expect(pane.locator(".msg-assistant .msg-content").last).to_have_text("你好，世界")
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()

        expected_messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，世界", "reasoning": "让我想想，想好了。"},
        ]

        def exchange_is_persisted():
            sessions = harness.library.list_chat_sessions()
            return bool(sessions) and sessions[0]["messages"][-2:] == expected_messages and sessions[0]["model"] == "glm"

        wait_until(exchange_is_persisted)
    assert audit_violations == []
