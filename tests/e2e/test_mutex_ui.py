"""R-e2e-08：重活互斥在界面上看得见，媒体作业结束后恢复。

台面接上真预算之后（R-budget-16），这里测的是**生产语义**而不是 legacy 排他表。
一个断言随之改变：媒体作业进行中时，聊天的「加载」按钮**不再**连带禁用——
spec `2026-09-17-budget-spec.md:125` 明写「R-arbiter-04 改：拒绝条件由『媒体在跑』
变为『预算装不下』」。视频 27 GiB + 聊天约 1 GiB 在这台面的 100 GiB 能力内装得下，
所以它该是可点的。真加载时仍由带参数的 acquire_heavy 按预算把关，按钮只是 affordance。

「媒体挡媒体」那两条不变——那是与容量无关的归属规则，归属分支保留了它。
"""

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_media_job_disables_other_heavy_controls_shows_reason_and_restores(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        video = page.locator("#pane-video")
        music = page.locator("#pane-music")
        chat = page.locator("#pane-chat")

        page.locator("#tabs [data-tab='video']").click()
        video.locator("[data-video-prompt]").fill("a quiet street in rain")
        video.locator("[data-video-start]").click()

        expect(video.locator("[data-video-start]")).to_be_disabled()
        expect(music.locator("[data-music-start]")).to_be_disabled()
        # 预算装得下，所以聊天的加载按钮不该被连带禁用（spec:125）。
        expect(chat.locator("[data-load]")).to_be_enabled()
        expect(page.locator("#statusbar")).to_contain_text("不可：媒体作业进行中")

        harness.media_script.step()
        harness.media_script.step()

        expect(video.locator("[data-video-start]")).to_be_enabled()
        expect(music.locator("[data-music-start]")).to_be_enabled()
        expect(chat.locator("[data-load]")).to_be_enabled()
        expect(page.locator("#statusbar")).to_contain_text("可开下一件重活")


def test_idle_pane_shows_the_busy_reason_while_sitting_on_that_tab(page, tmp_path):
    """F14 / widewin gap #9: sitting on the music tab (never switching away) while a
    video job starts elsewhere must still update the idle caption on the next 2s
    tick — not leave 'busy reason' and 'idle · fill in the form' contradicting
    each other until the user happens to revisit the tab."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("#tabs [data-tab='music']").click()
        music = page.locator("#pane-music")
        expect(music.locator("[data-job-status]")).to_contain_text("空闲")

        # Start the video job without ever navigating away from the music tab —
        # its own pane is `hidden` in the DOM but its start button still works.
        page.evaluate(
            "() => { document.querySelector('#pane-video [data-video-prompt]').value = 'a quiet street in rain';"
            " document.querySelector('#pane-video [data-video-start]').click(); }"
        )
        expect(music.locator("[data-job-status]")).to_contain_text("媒体作业进行中")
        expect(music.locator("[data-job-status]")).not_to_contain_text("填好左侧参数")


def test_disabled_reason_sits_the_same_distance_in_both_panes(page, tmp_path):
    """S2: the same disabled-reason message must sit the same distance from the
    generate button in both media panes (F7/W7)."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("#tabs [data-tab='video']").click()
        video = page.locator("#pane-video")
        video.locator("[data-video-prompt]").fill("a quiet street in rain")
        video.locator("[data-video-start]").click()
        expect(video.locator("[data-video-start]")).to_be_disabled()

        gaps = {}
        for tab, button_sel, hint_sel in (
            ("video", "[data-video-start]", "[data-video-hint]"),
            ("music", "[data-music-start]", "[data-music-hint]"),
        ):
            page.locator(f"#tabs [data-tab='{tab}']").click()
            expect(page.locator(hint_sel)).not_to_be_empty()
            gaps[tab] = page.evaluate(
                "([b, h]) => { const btn = document.querySelector(b).getBoundingClientRect();"
                " const hint = document.querySelector(h).getBoundingClientRect();"
                " return hint.top - btn.bottom; }", [button_sel, hint_sel])
        assert abs(gaps["video"] - gaps["music"]) <= 1, gaps
        assert round(gaps["video"]) in (8, 12, 16), gaps


def test_a_chat_model_can_be_loaded_while_a_media_job_runs(page, tmp_path):
    """预算模式的共存语义，第一次有浏览器层覆盖。

    在台面接真预算之前（R-budget-16），所有 e2e 跑的都是 legacy 排他表——
    「媒体在跑、预算够，聊天照样装得下」这条 spec 承诺在浏览器层零覆盖，
    只有单测看着。这条补上：视频作业进行中时把模型真的加载起来。
    """
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        video = page.locator("#pane-video")
        chat = page.locator("#pane-chat")

        page.locator("#tabs [data-tab='video']").click()
        video.locator("[data-video-prompt]").fill("a quiet street in rain")
        video.locator("[data-video-start]").click()
        expect(video.locator("[data-video-start]")).to_be_disabled()   # 作业确实在跑

        page.locator("#tabs [data-tab='chat']").click()
        chat.locator("[data-model-select]").select_option("glm")
        chat.get_by_role("button", name="加载").click()

        expect(chat.locator("[data-model-state]")).to_contain_text("已加载")
