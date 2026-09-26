"""Video sessions end to end (docs/superpowers/specs/2026-09-27-video-sessions-design.md §4).

One journey through the session-based video page in real Chromium against launch_test_harness —
real DeskApp, MediaSessionStore and MediaService, with the scripted media executor writing a tiny
MP4/PNG instead of running MiniMax H3/Qwen-Image (joins and compositions are ffmpeg commands the
fake executor completes on its own). Every step asserts both what the page shows and what the
backend settled in GET /api/media-sessions/video/{id}.

The 900×700 screenshot is written to $LMD_VIDEO_SESSIONS_SHOTS when set (the image/music-sessions
convention), otherwise to the test's tmp_path.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps

CURRENT_ITEM = "[data-video-session-list] li[aria-current='true']"


def _cards(pane):
    return pane.locator("[data-video-timeline] .attempt")


def _settled(pane, count):
    expect(_cards(pane)).to_have_count(count)
    expect(_cards(pane).nth(count - 1)).to_have_attribute("data-attempt-status", "done", timeout=15_000)
    expect(pane.locator("[data-video-start]")).to_be_enabled(timeout=5_000)


def _session(page, harness, session_id, kind="video"):
    response = page.request.get(f"{harness.base_url}/api/media-sessions/{kind}/{session_id}")
    assert response.status == 200, response.text()
    return response.json()


def _expanded(card):
    if card.get_attribute("aria-expanded") != "true":
        card.locator(".attempt-row").click()
    expect(card).to_have_attribute("aria-expanded", "true")
    return card


def test_continue_use_image_first_frame_and_compose_a_video_in_one_session(page, tmp_path):
    # Unlike a music join, extracting a continuation's first frame runs real ffmpeg synchronously
    # (desk/media/service.py _extract_last_frame) against the seeded TINY_MP4 — a decodable
    # one-frame VP9 — so this test needs the system's real ffmpeg, not the join/compose ffmpeg
    # commands the fake executor completes on its own (any path would do for those).
    # Four model runs: first video (text), continuation, one image, and a video using that image as
    # first frame; the join after the continuation and the final composition are ffmpeg and need no
    # scripted job.
    jobs = MediaScript([fast_media_steps() for _ in range(4)])
    with launch_test_harness(
        tmp_path, model_states={"h3": "present", "qwen-image": "present"}, image_runtime=True,
        media_script=jobs,
    ) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        expect(pane).to_be_visible()
        expect(pane.locator(CURRENT_ITEM)).to_have_count(1)
        session_id = pane.locator(CURRENT_ITEM).get_attribute("data-session-id")

        # 1. First video, text-to-video.
        pane.locator("[data-video-prompt]").fill("湖面上的落日，微风吹起涟漪")
        pane.locator("[data-video-start]").click()
        _settled(pane, 1)
        first = _expanded(_cards(pane).nth(0))
        expect(first.locator(".attempt-label")).to_contain_text("第 1 次")
        expect(first.locator("video.attempt-video")).to_have_count(1)
        attempts = _session(page, harness, session_id)["attempts"]
        assert [a["status"] for a in attempts] == ["done"]
        first_id = attempts[0]["id"]

        # 2. 接着往下生: chip names it, first-frame explanation, mode select locked.
        first.get_by_role("button", name="接着往下生").click()
        expect(pane.locator("[data-video-chip]")).to_be_visible()
        expect(pane.locator("[data-video-chip-text]")).to_have_text("接在第 1 次后面")
        expect(pane.locator("[data-video-first-label]")).to_have_text("接在第 1 次后面（用它的最后一帧）")
        expect(pane.locator("[data-video-mode]")).to_be_disabled()
        pane.locator("[data-video-prompt]").fill("镜头拉远，天色渐暗")
        pane.locator("[data-video-start]").click()
        _settled(pane, 2)
        second = _expanded(_cards(pane).nth(1))
        expect(second.locator(".attempt-label")).to_contain_text("接第 1 次")
        expect(second.get_by_role("radio", name="成片")).to_be_visible()
        expect(second.get_by_role("radio", name="只看这一段")).to_be_visible()
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[1]["continues"] == first_id
        assert attempts[1]["joined_output"], attempts[1]
        assert attempts[1]["joined_error"] is None, attempts[1]
        second_id = attempts[1]["id"]

        # 3. Switch to the image tab, generate a picture, use it as the video's first frame.
        page.locator("#tabs [data-tab='image']").click()
        image_pane = page.locator("#pane-image")
        expect(image_pane).to_be_visible()
        image_pane.locator("[data-image-prompt]").fill("一只在湖边散步的白鹭")
        image_pane.locator("[data-image-start]").click()
        image_cards = image_pane.locator("[data-image-timeline] .attempt")
        expect(image_cards).to_have_count(1)
        expect(image_cards.first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        image_id = image_pane.locator(CURRENT_ITEM.replace("video", "image")).get_attribute("data-session-id")
        image_card = _expanded(image_cards.first)
        image_card.get_by_role("button", name="用这张生成视频").click()

        pane = page.locator("#pane-video")
        expect(pane).to_be_visible()
        expect(pane.locator("[data-video-mode]")).to_have_value("image")
        expect(pane.locator("[data-video-first-label]")).to_have_text("首帧：图片会话「一只在湖边散步的白鹭」第 1 次")
        pane.locator("[data-video-prompt]").fill("白鹭展开翅膀飞走")
        pane.locator("[data-video-start]").click()
        _settled(pane, 3)
        third = _expanded(_cards(pane).nth(2))
        expect(third.locator("p.hint.attempt-first-frame")).to_have_text("首帧：图片会话「一只在湖边散步的白鹭」第 1 次")
        attempts = _session(page, harness, session_id)["attempts"]
        third_attempt = attempts[2]
        image_attempts = _session(page, harness, image_id, kind="image")["attempts"]
        assert third_attempt["refs"]["first_frame"] == {
            "kind": "image", "session_id": image_id, "attempt_id": image_attempts[0]["id"],
        }
        third_id = third_attempt["id"]

        # 4. Pick two segments, compose.
        pane.get_by_role("button", name="挑几段合成…").click()
        bar = pane.locator("[data-video-compose-bar]")
        expect(bar).to_be_visible()
        pane.get_by_role("checkbox", name="选中第 1 次").check()
        pane.get_by_role("checkbox", name="选中第 3 次").check()
        submit = bar.get_by_role("button", name="合成（2 段）")
        expect(submit).to_be_enabled()
        submit.click()
        _settled(pane, 4)
        expect(_cards(pane).nth(3).locator(".attempt-label")).to_contain_text("合成：第 1、3 次")
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[3]["params"]["parts"] == [first_id, third_id]
        assert attempts[3]["status"] == "done" and attempts[3]["output"]

        # 5. Narrow window: no horizontal scroll; main-flow text (excluding the advanced-params
        # <details>) has no 「种子」.
        page.set_viewport_size({"width": 900, "height": 700})
        shots = Path(os.environ.get("LMD_VIDEO_SESSIONS_SHOTS") or tmp_path)
        shots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shots / "video-sessions-900x700.png"))
        layout = page.evaluate("""() => ({
            scroll: document.documentElement.scrollWidth, inner: innerWidth,
        })""")
        assert layout["scroll"] <= layout["inner"], layout

        visible = pane.evaluate("""(root) => {
            const hidden = (n) => n.closest('details.video-advanced, details.attempt-advanced');
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            const out = [];
            for (let n = walker.nextNode(); n; n = walker.nextNode()) {
                if (hidden(n.parentElement) || !n.parentElement.checkVisibility()) continue;
                out.push(n.textContent);
            }
            return out.join(' '); }""")
        assert "种子" not in visible, visible
