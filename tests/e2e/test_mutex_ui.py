"""R-e2e-08: mutual exclusion is visible and clears when media work ends.

R-budget-13 (2026-09-18 budget-arithmetic plan, Task 3): the desk_state
`can_start` buttons answer ownership only, not budget arithmetic. Ownership
only forbids a second concurrent media job — it does not forbid loading a
chat model while media runs (that coexistence question needs real params,
which this parameterless poll never has; see the plan's self-review note on
F3, "方向是放宽" — deliberately left unblocked here, F3 is a separate,
un-taken product decision about whether to also gate it elsewhere). So the
chat "load" control must stay enabled throughout a media job; only the two
media controls are mutually exclusive with each other.
"""

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_media_job_disables_other_media_control_shows_reason_and_restores(page, tmp_path):
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
