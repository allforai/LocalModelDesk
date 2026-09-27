"""Video soundtrack (D2) and music reference (D1) end to end
(docs/superpowers/specs/2026-09-27-video-soundtrack-design.md §5).

One journey through the session-based music, image and video pages in real Chromium against
launch_test_harness — real DeskApp, MediaSessionStore and MediaService, with the scripted media
executor writing a tiny MP4/PNG/WAV instead of running MiniMax H3/Music 3 or Qwen-Image. D2's
「配乐…」job and D1's continuation-style clip are ffmpeg commands the fake executor completes on its
own (any file will do for the join/compose/soundtrack path); D1's own audio clip
(desk/media/service.py `_clip_audio`) runs real ffmpeg synchronously against the song file on disk,
so the song must actually decode as a WAV with a real duration.

The fake music executor always writes `desk.testing.seed.TINY_WAV` (~0.001 s at 8000 Hz) — far
short of the >= 2 s `_clip_audio` requires from the chosen start second (CLIP_MIN_S,
desk/media/service.py). Rather than growing the shared TINY_WAV fixture (other tests assert its
exact bytes/size, e.g. tests/test_e2e_fakes.py, tests/e2e/test_music_flow.py), this test overwrites
the finished song's output file on disk with a longer, equally well-formed silent WAV before using
it as a D1 reference — a test-harness-local workaround, not a production change.
"""
from __future__ import annotations

import struct

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps


def _current_item(prefix):
    return f"[data-{prefix}-session-list] li[aria-current='true']"


def _cards(pane, prefix):
    return pane.locator(f"[data-{prefix}-timeline] .attempt")


def _settled(pane, prefix, count):
    cards = _cards(pane, prefix)
    expect(cards).to_have_count(count)
    expect(cards.nth(count - 1)).to_have_attribute("data-attempt-status", "done", timeout=15_000)
    expect(pane.locator(f"[data-{prefix}-start]")).to_be_enabled(timeout=5_000)


def _session(page, harness, session_id, kind):
    response = page.request.get(f"{harness.base_url}/api/media-sessions/{kind}/{session_id}")
    assert response.status == 200, response.text()
    return response.json()


def _expanded(card):
    if card.get_attribute("aria-expanded") != "true":
        card.locator(".attempt-row").click()
    expect(card).to_have_attribute("aria-expanded", "true")
    return card


def _silent_wav(seconds: float, sample_rate: int = 8000) -> bytes:
    """A well-formed silent PCM WAV, same header shape as desk/testing/seed.py TINY_WAV but long
    enough for D1's clip (>= audio_start + CLIP_MIN_S)."""
    samples = b"\x00\x00" * int(seconds * sample_rate)
    return (
        b"RIFF" + struct.pack("<I", 36 + len(samples)) + b"WAVE"
        + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data" + struct.pack("<I", len(samples)) + samples
    )


def test_soundtrack_and_music_reference(page, tmp_path):
    # Four model runs, in spawn order: the song, the first video segment, the reference image, and
    # the music_ref video. D2's 「配乐…」 job and the continuation-free joins/compositions are ffmpeg
    # commands the fake executor completes on its own and never consume a scripted job.
    jobs = MediaScript([fast_media_steps() for _ in range(4)])
    with launch_test_harness(
        tmp_path, model_states={"h3": "present", "qwen-image": "present", "music3": "present"},
        image_runtime=True, media_script=jobs,
    ) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})

        # 1. Music page: generate one song.
        page.goto(harness.base_url + "#tab=music")
        music_pane = page.locator("#pane-music")
        expect(music_pane).to_be_visible()
        expect(music_pane.locator(_current_item("music"))).to_have_count(1)
        music_session_id = music_pane.locator(_current_item("music")).get_attribute("data-session-id")
        music_pane.locator("[data-music-caption]").fill("温柔的钢琴曲，安静的夜晚")
        music_pane.locator("[data-music-lyrics]").fill("月光洒落窗台\n心事随风飘散")
        music_pane.locator("[data-music-start]").click()
        _settled(music_pane, "music", 1)
        music_attempts = _session(page, harness, music_session_id, "music")["attempts"]
        assert music_attempts[0]["status"] == "done"
        song_output = music_attempts[0]["output"]

        # D1's clip needs the song to actually be >= audio_start + 2 s; the fake executor always
        # writes the ~0.001 s TINY_WAV, so replace it on disk with a real, longer silent WAV.
        (harness.outputs_root / song_output).write_bytes(_silent_wav(4.0))

        # 2. Video page: generate the first segment (text-to-video).
        page.locator("#tabs [data-tab='video']").click()
        video_pane = page.locator("#pane-video")
        expect(video_pane).to_be_visible()
        expect(video_pane.locator(_current_item("video"))).to_have_count(1)
        video_session_id = video_pane.locator(_current_item("video")).get_attribute("data-session-id")
        video_pane.locator("[data-video-prompt]").fill("篝火旁的露营地，星空下")
        video_pane.locator("[data-video-start]").click()
        _settled(video_pane, "video", 1)

        # 3. D2: expand the card, 「配乐…」→ pick the song → a soundtrack card appears.
        first_card = _expanded(_cards(video_pane, "video").nth(0))
        first_card.get_by_role("button", name="配乐…").click()
        dialog = page.get_by_role("dialog", name="选一首歌配到这段视频")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="选这首").click()
        expect(dialog).to_have_count(0)
        _settled(video_pane, "video", 2)
        soundtrack_card = _expanded(_cards(video_pane, "video").nth(1))
        expect(soundtrack_card.locator(".attempt-label")).to_contain_text("配乐：")
        expect(soundtrack_card.locator(".attempt-label")).to_contain_text("基于第 1 次")
        attempts = _session(page, harness, video_session_id, "video")["attempts"]
        assert attempts[1]["op"] == "soundtrack", attempts[1]
        assert attempts[1]["refs"]["soundtrack"]["kind"] == "music", attempts[1]
        assert attempts[1]["refs"]["soundtrack"]["session_id"] == music_session_id, attempts[1]
        assert attempts[1]["refs"]["soundtrack"]["attempt_id"] == music_attempts[0]["id"], attempts[1]

        # 4. Image page: generate a reference picture for D1.
        page.locator("#tabs [data-tab='image']").click()
        image_pane = page.locator("#pane-image")
        expect(image_pane).to_be_visible()
        image_pane.locator("[data-image-prompt]").fill("篝火映照下的一顶帐篷")
        image_pane.locator("[data-image-start]").click()
        image_cards = image_pane.locator("[data-image-timeline] .attempt")
        expect(image_cards).to_have_count(1)
        expect(image_cards.first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        image_session_id = image_pane.locator(_current_item("image")).get_attribute("data-session-id")

        # 5. Video page again: switch to 「配乐参考（实验性）」, pick the image and the song, generate.
        page.locator("#tabs [data-tab='video']").click()
        video_pane = page.locator("#pane-video")
        expect(video_pane).to_be_visible()
        video_pane.locator("[data-video-mode]").select_option("music_ref")
        music_area = video_pane.locator("[data-video-music-area]")
        expect(music_area).to_be_visible()
        expect(video_pane.get_by_text("从第几秒开始")).to_be_visible()

        video_pane.locator("[data-video-ref-image-pick]").click()
        image_dialog = page.get_by_role("dialog", name="从图片会话选参考图")
        expect(image_dialog).to_be_visible()
        image_dialog.get_by_role("button", name="第 1 次").click()
        expect(image_dialog).to_have_count(0)

        video_pane.locator("[data-video-song-pick]").click()
        song_dialog = page.get_by_role("dialog", name="从音乐会话选一首歌")
        expect(song_dialog).to_be_visible()
        song_dialog.get_by_role("button", name="选这首").click()
        expect(song_dialog).to_have_count(0)

        video_pane.locator("[data-video-prompt]").fill("帐篷在篝火旁轻轻摇曳")
        video_pane.locator("[data-video-start]").click()
        _settled(video_pane, "video", 3)
        attempts = _session(page, harness, video_session_id, "video")["attempts"]
        third = attempts[2]
        assert third["params"]["mode"] == "music_ref", third
        assert third["refs"]["ref_audio"]["kind"] == "music", third
        assert third["refs"]["ref_audio"]["session_id"] == music_session_id, third
        assert third["refs"]["ref_image"]["kind"] == "image", third
        assert third["refs"]["ref_image"]["session_id"] == image_session_id, third

        # 6. Narrow window with the music_ref block visible: no horizontal scroll, 「生成视频」 fully
        # inside the viewport (the video composer is capped at 50vh with a scrollable materials block).
        expect(video_pane.locator("[data-video-mode]")).to_have_value("music_ref")
        expect(music_area).to_be_visible()
        page.set_viewport_size({"width": 900, "height": 700})
        layout = page.evaluate("""() => {
            const b = document.querySelector('#pane-video [data-video-start]');
            const rect = b.getBoundingClientRect();
            return {
                scroll: document.documentElement.scrollWidth, inner: innerWidth, vh: innerHeight,
                btnScroll: b.scrollWidth, btnClient: b.clientWidth,
                btnRight: rect.right, btnBottom: rect.bottom,
            };
        }""")
        assert layout["scroll"] <= layout["inner"], layout
        assert layout["btnScroll"] <= layout["btnClient"], layout
        assert layout["btnRight"] <= layout["inner"], layout
        assert layout["btnBottom"] <= layout["vh"], layout
