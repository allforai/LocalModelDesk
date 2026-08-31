"""R-e2e-07: music parameters progress through the UI into a playable output."""
import time

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_WAV


def test_music_parameters_progress_and_player_src_follow_finished_output(
    page, tmp_path, audit_violations
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        expect(page.get_by_text("空闲", exact=True).first).to_be_visible()
        page.locator("#tabs [data-tab='music']").dispatch_event("click")
        pane = page.locator("#pane-music")
        expect(pane).to_be_visible()
        pane.locator("[data-music-caption]").fill("warm acoustic folk")
        pane.locator("[data-music-lyrics]").fill("under amber skies")
        pane.locator("[data-music-duration]").fill("75")
        pane.locator("[data-music-start]").dispatch_event("click")

        expect(pane.locator("[data-job-log]")).to_contain_text("step 1/10")
        harness.media_script.step()
        expect(pane.locator("[data-job-log]")).to_contain_text("step 5/10")
        harness.media_script.step()

        output_name = "music3-{}.wav".format(
            time.strftime("%Y%m%d-%H%M%S", time.localtime(harness.clock()))
        )
        player = pane.locator("[data-job-player] audio")
        expect(player).to_have_attribute("controls", "")
        expect(player).to_have_attribute("src", f"/api/outputs/{output_name}")
        expect(player).to_have_css("max-width", "100%")
        assert (harness.outputs_root / output_name).read_bytes() == TINY_WAV

        response = page.request.get(f"{harness.base_url}{player.get_attribute('src')}")
        assert response.status in (200, 206)
    assert audit_violations == []
