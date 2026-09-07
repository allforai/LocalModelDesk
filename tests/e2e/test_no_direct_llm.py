"""R-e2e-12：组合聊天旅程不会让浏览器直连本地 LLM 端口。"""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_full_journey_makes_zero_requests_to_8767(page, context, tmp_path):
    requests: list[str] = []
    context.on("request", lambda request: requests.append(request.url))

    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        key = next(key for key, state in harness.seeded.items() if state == "present")
        pane.locator("[data-model-select]").select_option(key)
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        harness.chat_script.run_to_end()
        pane.locator("[data-chat-input]").fill("零直连旅程")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant .md").last).to_have_text("你好，世界")

        pane.get_by_role("button", name="卸载").click()
        expect(pane.get_by_role("button", name="加载")).to_be_visible()

    assert len(requests) > 10, requests
    direct = [url for url in requests if ":8767" in url]
    assert direct == [], direct
