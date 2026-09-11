"""R-e2e-08: mutual exclusion is visible and clears when media work ends."""

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
        expect(chat.locator("[data-load]")).to_be_disabled()
        expect(page.locator("#statusbar")).to_contain_text("不可：媒体作业进行中")

        harness.media_script.step()
        harness.media_script.step()

        expect(video.locator("[data-video-start]")).to_be_enabled()
        expect(music.locator("[data-music-start]")).to_be_enabled()
        expect(chat.locator("[data-load]")).to_be_enabled()
        expect(page.locator("#statusbar")).to_contain_text("可开下一件重活")


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
