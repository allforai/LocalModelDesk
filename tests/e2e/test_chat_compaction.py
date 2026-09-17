"""长会话要能被压缩，而且压缩之后一个字都不能少。"""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done


def _long_answer(n_lines: int = 59) -> str:
    block = "第 {} 行，够长够长够长够长够长。"
    return "\n\n".join(block.format(i) for i in range(1, n_lines + 1))


def _compaction_script():
    """两个回合：第一回合是把预算撑爆的长回答，第二回合是两轮之间自动触发的
    压缩摘要请求。不放 Gate——两个回合靠各自的 Done 分界，脚本自己往前走，
    断言只等 DOM 里的确定性标记，不等时间、也不等一个可能本来就成立的条件。"""
    return ChatScript([
        Delta(content=_long_answer()),
        Done(usage={"prompt_tokens": 40_000, "completion_tokens": 100, "total_tokens": 40_100}),
        Delta(content="## 用户要做的事\n打招呼\n\n## 用户说过的每一句\n- 你好"),
        Done(usage={"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550}),
    ])


def _seed_session_with_one_prior_round(harness):
    """压缩要求「至少保留最近一轮完整问答」（R-context-01）：只有一轮对话时，
    那一轮本身就是必须保留的尾部，头部永远是空的，压缩不可能触发。所以要在
    真实的那一轮（会撑爆预算的长回答）之前，先直接种一轮更早的历史——不经过
    假后端，只是把它写进会话文件，就像用户之前问过一句一样。"""
    session = harness.library.create_chat_session("旧会话", "glm")
    harness.library.update_chat_session(session["id"], {"messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好呀，有什么可以帮你的"},
    ]})
    return session["id"]


def test_a_long_conversation_gets_compacted_without_losing_a_word(page, tmp_path, audit_violations):
    # compact_at 设得很小，长回答那一轮的 40000 prompt_tokens 必然越线。
    budget = {"available_bytes": 0, "total_bytes": 0, "pressure": "normal",
              "chat": {"token_limit": 1000, "compact_at": 750, "source": "measured", "window": 4096},
              "media": {}}
    with launch_test_harness(tmp_path, chat_script=_compaction_script(), budget=budget) as harness:
        _seed_session_with_one_prior_round(harness)
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        # 种下的那一轮先渲染出来——确认我们真的是从「已有历史」出发，不是空会话。
        expect(pane.locator(".msg-user")).to_contain_text("你好")

        pane.locator("[data-chat-input]").fill("讲个长的")
        pane.get_by_role("button", name="发送").click()
        # 等回答落地（确定性标记：最后一行进 DOM），不要等时间
        expect(pane.locator(".msg-assistant > .md").last).to_contain_text("第 59 行")

        # 压缩在两轮之间自动发生（R-context-04），过程结束后发送按钮要恢复可用——
        # 这本身就是「没有卡住」的确定性标记，比等一个转瞬即逝的进行中提示条更稳。
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()
        expect(pane.locator(".msg-summary")).to_be_visible()
        expect(pane.locator(".msg-summary summary")).to_contain_text("这里压缩了")

        # R-context-03：原文一条都不少，往上翻还能读到——种下的那一轮和真实问答都在。
        expect(pane.locator(".msg-user").first).to_contain_text("你好")
        expect(pane.locator(".msg-user").last).to_contain_text("讲个长的")
        expect(pane.locator(".msg-assistant > .md").last).to_contain_text("第 59 行")

        # R-context-02：摘要展开后能看到内容（模板小节 + 用户原话已在 Task 3 单测覆盖，
        # 这里只验证端到端确实把摘要内容渲染出来了，不是一个空壳）。
        pane.locator(".msg-summary summary").click()
        expect(pane.locator(".msg-summary .md")).to_contain_text("你好")


def test_nothing_is_compacted_when_the_budget_cannot_be_computed(page, tmp_path, audit_violations):
    """预算说「算不出」时不许替用户裁剪历史——与 budget 的「未经实测不放宽」同一条纪律。

    `compact_at` 显式给 0：真实 `/api/budget` 在「算不出」时压根不带这个键
    （值是 `undefined`），但 `undefined >= promptTokens` 在 JS 里天然是 false，
    这一条本身就不会撞上「算不出就不压」那道守卫——守卫被删掉也测不出来。
    `0` 和 `undefined` 对 needsCompaction 是同一件事（两者都「不能拿来当额度
    用」，Task 1 的单测把它们并列断言），但只有 0 能在这一步真正咬住那道守卫：
    `promptTokens >= 0` 恒真，守卫一旦被删，没有它就会误判「该压」。"""
    # 脚本仍然给出第二回合（摘要）的台词。这不是「预期会被压缩」——是为了让这条
    # 测试真的能咬：守卫若被删掉，maybeCompact 会真的发起第二次请求；脚本里没
    # 台词的话，那次请求会因为「脚本已经用完」直接报错，同样看不到 .msg-summary，
    # 跟「压根没触发」长得一模一样，守卫被删掉也测不出来。台词在，才能把两种
    # 情况分开：真正不触发 vs. 触发了但请求恰好失败。
    budget = {"available_bytes": 0, "total_bytes": 0, "pressure": "normal",
              "chat": {"source": "unavailable", "compact_at": 0}, "media": {}}
    with launch_test_harness(tmp_path, chat_script=_compaction_script(), budget=budget) as harness:
        _seed_session_with_one_prior_round(harness)
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")
        pane.locator("[data-chat-input]").fill("讲个长的")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant > .md").last).to_contain_text("第 59 行")
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()
        assert pane.locator(".msg-summary").count() == 0, "预算算不出，却还是压缩了"
