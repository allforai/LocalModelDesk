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
