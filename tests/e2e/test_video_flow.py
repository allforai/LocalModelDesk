"""R-e2e-06: video parameters progress through the UI into a playable output."""
import time

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_MP4


def test_video_parameters_progress_and_player_src_follow_finished_output(
    page, tmp_path, audit_violations
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        expect(page.get_by_text("空闲", exact=True).first).to_be_visible()
        page.locator("#tabs [data-tab='video']").dispatch_event("click")
        pane = page.locator("#pane-video")
        expect(pane).to_be_visible()
        pane.locator("[data-video-prompt]").fill("rain on a quiet street")
        pane.locator("[data-video-size]").select_option("768x448")
        pane.locator("[data-video-frames]").fill("49")
        pane.locator("[data-video-steps]").fill("16")
        pane.locator("[data-video-start]").dispatch_event("click")

        expect(pane.locator("[data-job-log]")).to_contain_text("step 1/10")
        harness.media_script.step()
        expect(pane.locator("[data-job-log]")).to_contain_text("step 5/10")
        harness.media_script.step()

        output_name = "h3-{}.mp4".format(
            time.strftime("%Y%m%d-%H%M%S", time.localtime(harness.clock()))
        )
        player = pane.locator("[data-job-player] video")
        expect(player).to_have_attribute("controls", "")
        expect(player).to_have_attribute("src", f"/api/outputs/{output_name}")
        assert (harness.outputs_root / output_name).read_bytes() == TINY_MP4

        response = page.request.get(f"{harness.base_url}{player.get_attribute('src')}")
        assert response.status in (200, 206)
    assert audit_violations == []
