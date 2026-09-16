"""R-e2e-03: chat renders each SSE delta and saves the completed exchange."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done, Gate


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
        expect(pane.locator(".msg-assistant .thinking p").last).to_have_text("让我想想，")

        harness.chat_script.step()
        expect(pane.locator(".msg-assistant .thinking p").last).to_have_text("让我想想，想好了。")

        harness.chat_script.step()
        expect(pane.locator(".msg-assistant .md").last).to_have_text("你好")

        harness.chat_script.step()
        expect(pane.locator(".msg-assistant .md").last).to_have_text("你好，世界")
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()

        expected_messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，世界", "reasoning": "让我想想，想好了。"},
        ]

        def exchange_is_persisted():
            sessions = harness.library.list_chat_sessions()
            if not sessions or sessions[0]["model"] != "glm":
                return False
            last_two = sessions[0]["messages"][-2:]
            trimmed = [{k: v for k, v in message.items() if k != "thinking_s"} for message in last_two]
            return trimmed == expected_messages

        wait_until(exchange_is_persisted)
    assert audit_violations == []


def test_stop_button_ends_a_streaming_reply_and_saves_it_as_stopped(page, tmp_path, audit_violations, wait_until):
    """真机 2026-09-15：模型复读到上限，界面没有办法停下来。"""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        pane.locator("[data-chat-input]").fill("你是谁")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant .thinking p").last).to_have_text("让我想想，")

        pane.get_by_role("button", name="停止").click()

        expect(pane.locator(".msg-assistant .inline-error").last).to_have_text("已停止生成")
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()
        harness.chat_script.run_to_end()

        def saved_as_stopped():
            sessions = harness.library.list_chat_sessions()
            messages = sessions[0]["messages"] if sessions else []
            return (len(messages) == 2 and messages[1].get("interrupted", {}).get("code") == "stopped"
                    and messages[1].get("reasoning") == "让我想想，")

        wait_until(saved_as_stopped)
    assert audit_violations == []


def _long_answer_script():
    """用户报的是「长回答在生成时画面不动」——要复现就得让内容真的撑出滚动条。
    每块 40 行，一块就足够超过 420px 高视口里的消息区。每块最后一行带块号，
    测试靠它判断「这一块真的渲染完了」，不靠等时间。"""
    block = lambda n: "\n\n".join(f"第 {n} 段第 {i} 行，够长够长够长够长够长够长够长。" for i in range(1, 41))
    return ChatScript([
        Delta(content=block(1)), Gate(),
        Delta(content=block(2)), Gate(),
        Delta(content=block(3)), Gate(),
        Delta(content=block(4)),
        Done(usage={"prompt_tokens": 5, "completion_tokens": 400, "total_tokens": 405}),
    ])


def test_streaming_keeps_the_view_at_the_bottom_unless_the_user_scrolled_up(
    page, tmp_path, audit_violations
):
    """生成时视口要跟着内容走——用户报的就是这个：回答在长，画面不动。

    反过来也要成立：用户往上翻看历史时，流式内容不许把他拽回底部。"""
    page.set_viewport_size({"width": 900, "height": 420})
    with launch_test_harness(tmp_path, chat_script=_long_answer_script()) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")
        pane.locator("[data-chat-input]").fill("讲个长的")
        pane.get_by_role("button", name="发送").click()

        # 正文是 .msg-assistant 的直接子节点；思考过程那块同样是 .md，但包在 <details> 里。
        answer = pane.locator(".msg-assistant > .md")
        metrics = lambda: page.evaluate(
            "() => { const m = document.querySelector('.messages');"
            " return {top: m.scrollTop, client: m.clientHeight, total: m.scrollHeight}; }")
        # 每块都等它的最后一行落进 DOM 再量：等时间会在流还在路上时就量到旧画面，
        # 那样量出来的「贴底」是上一块的贴底，测不到东西。
        def after_block(n):
            expect(answer).to_contain_text(f"第 {n} 段第 40 行")
            return metrics()

        first = after_block(1)
        assert first["total"] > first["client"] * 3, f"内容没撑出滚动，这条测不到东西：{first}"
        assert first["total"] - (first["top"] + first["client"]) <= 48, f"正文在长，视口没跟上：{first}"

        harness.chat_script.step()
        second = after_block(2)
        assert second["total"] > first["total"], f"第二块没长出来：{second}"
        assert second["total"] - (second["top"] + second["client"]) <= 48, f"继续长，视口仍要跟上：{second}"

        # 用户翻上去之后，后续增量不许把他拽回底部
        page.evaluate("() => { document.querySelector('.messages').scrollTop = 0; }")
        scrolled = metrics()
        assert scrolled["top"] == 0 and scrolled["total"] - scrolled["client"] > 200, \
            f"没真的翻上去，后面那条断言就是空的：{scrolled}"

        harness.chat_script.step()
        after_block(3)
        harness.chat_script.step()
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()
        end = metrics()
        assert end["total"] > scrolled["total"], f"翻上去之后内容没再长，测不到拽回：{end}"
        assert end["top"] < 48, f"用户翻上去了却被拽回底部：{end}"
