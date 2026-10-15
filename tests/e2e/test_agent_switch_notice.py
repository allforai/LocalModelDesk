"""A-66: the chat page says so when an agent swapped the resident model."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness

CHAT, OTHER = "glm", "qwen27"   # 同 Task 8


def test_notice_appears_after_agent_swap_and_closes(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        page.goto(h.base_url)
        expect(page.locator("[data-model-state]")).to_contain_text("已加载")
        notice = page.locator("[data-agent-switch]")
        expect(notice).to_be_hidden()
        h.llm.load(OTHER, origin="agent"); h.llm.wait_settled()
        expect(notice).to_be_visible(timeout=10_000)
        expect(notice).to_contain_text("模型已被 agent 切换为")
        page.locator("[data-agent-switch-close]").click()
        expect(notice).to_be_hidden()


def test_no_notice_when_the_user_switches(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        page.goto(h.base_url)
        expect(page.locator("[data-model-state]")).to_contain_text("已加载")
        h.llm.load(OTHER); h.llm.wait_settled()
        page.wait_for_timeout(4000)
        expect(page.locator("[data-agent-switch]")).to_be_hidden()
