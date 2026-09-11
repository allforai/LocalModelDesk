"""R-e2e-09: historical parameters refill field by field; outputs play."""

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import fast_media_steps


VIDEO_PARAMS = {
    "prompt": "回填用视频",
    "size": "512x288",
    "frames": "73",
    "steps": "10",
}
MUSIC_PARAMS = {
    "caption": "回填用音乐",
    "lyrics": "一句歌词",
    "duration": "75",
}


def _run_video(page):
    page.locator("#tabs [data-tab='video']").click()
    pane = page.locator("#pane-video")
    pane.locator("[data-video-prompt]").fill(VIDEO_PARAMS["prompt"])
    pane.locator("[data-video-size]").select_option(VIDEO_PARAMS["size"])
    pane.locator("[data-video-frames]").select_option(VIDEO_PARAMS["frames"])
    pane.locator("[data-video-steps]").fill(VIDEO_PARAMS["steps"])
    pane.locator("[data-video-start]").click()
    expect(pane.locator("video[controls]")).to_be_visible()


def _run_music(page):
    page.locator("#tabs [data-tab='music']").click()
    pane = page.locator("#pane-music")
    pane.locator("[data-music-caption]").fill(MUSIC_PARAMS["caption"])
    pane.locator("[data-music-lyrics]").fill(MUSIC_PARAMS["lyrics"])
    pane.locator("[data-music-duration]").fill(MUSIC_PARAMS["duration"])
    pane.locator("[data-music-start]").click()
    expect(pane.locator("audio[controls]")).to_be_visible()


def test_audio_player_matches_the_dark_palette(page, tmp_path):
    """C1: the player must not be the single lightest rectangle on screen (F10/W3)."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("#tabs [data-tab='music']").dispatch_event("click")
        pane = page.locator("#pane-music")
        pane.locator("[data-music-caption]").fill("warm acoustic folk")
        pane.locator("[data-music-lyrics]").fill("under amber skies")
        pane.locator("[data-music-start]").dispatch_event("click")
        expect(pane.locator("[data-job-log]")).to_contain_text("step 1/10")
        harness.media_script.step()
        expect(pane.locator("[data-job-log]")).to_contain_text("step 5/10")
        harness.media_script.step()
        audio = pane.locator("[data-job-player] audio")
        expect(audio).to_be_visible()
        style = audio.evaluate(
            "el => { const s = getComputedStyle(el);"
            " return {scheme: s.colorScheme, bg: s.backgroundColor}; }"
        )
        assert "dark" in style["scheme"], style
        assert style["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), style


def test_history_refill_and_playback(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        harness.media_script.jobs.clear()
        harness.media_script.jobs.extend([fast_media_steps(), fast_media_steps()])
        page.goto(harness.base_url)

        _run_video(page)
        _run_music(page)

        page.locator("#tabs [data-tab='library']").click()
        library = page.locator("#pane-library")
        video_entry = library.locator("li").filter(has_text=VIDEO_PARAMS["prompt"])
        music_entry = library.locator("li").filter(has_text=MUSIC_PARAMS["caption"])
        expect(video_entry).to_be_visible()
        expect(music_entry).to_be_visible()

        video_entry.get_by_role("button", name="回填参数").click()
        video = page.locator("#pane-video")
        expect(video).to_be_visible()
        assert video.locator("[data-video-prompt]").input_value() == VIDEO_PARAMS["prompt"]
        assert video.locator("[data-video-size]").input_value() == VIDEO_PARAMS["size"]
        assert video.locator("[data-video-frames]").input_value() == VIDEO_PARAMS["frames"]
        assert video.locator("[data-video-steps]").input_value() == VIDEO_PARAMS["steps"]

        page.locator("#tabs [data-tab='library']").click()
        music_entry.get_by_role("button", name="回填参数").click()
        music = page.locator("#pane-music")
        expect(music).to_be_visible()
        assert music.locator("[data-music-caption]").input_value() == MUSIC_PARAMS["caption"]
        assert music.locator("[data-music-lyrics]").input_value() == MUSIC_PARAMS["lyrics"]
        assert music.locator("[data-music-duration]").input_value() == MUSIC_PARAMS["duration"]

        page.locator("#tabs [data-tab='library']").click()
        video_entry.click()
        player = library.locator("video[controls]")
        expect(player).to_be_visible()
        src = player.get_attribute("src")
        assert src and src.startswith("/api/outputs/") and src.endswith(".mp4")
        assert page.request.get(f"{harness.base_url}{src}").status in (200, 206)

    assert audit_violations == []
