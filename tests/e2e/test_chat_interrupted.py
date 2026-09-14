"""P3: an answer cut off mid-stream keeps the question and partial text in the session."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import Break, ChatScript, Delta, Gate


def test_interrupted_answer_is_persisted_and_labelled(page, tmp_path, audit_violations, wait_until):
    script = ChatScript([Delta(content="半句话"), Gate(), Break("上游断开")])
    with launch_test_harness(tmp_path, chat_script=script) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        pane.locator("[data-chat-input]").fill("你好")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant .md").last).to_have_text("半句话")
        harness.chat_script.step()

        expect(pane.locator(".msg-assistant .inline-error").last).to_contain_text("回答没有生成完")
        expect(pane.get_by_role("button", name="重试")).to_be_visible()

        def persisted():
            sessions = harness.library.list_chat_sessions()
            messages = sessions[0]["messages"] if sessions else []
            return (len(messages) == 2 and messages[0]["content"] == "你好"
                    and messages[1]["content"] == "半句话"
                    and messages[1].get("interrupted", {}).get("message"))

        wait_until(persisted)
        page.reload()
        expect(page.locator("#pane-chat .msg-assistant .inline-error").last).to_contain_text("回答没有生成完")
    assert audit_violations == []
