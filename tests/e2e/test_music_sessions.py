"""Music sessions end to end (docs/superpowers/specs/2026-09-27-music-sessions-design.md §3).

One journey through the session-based music page in real Chromium against launch_test_harness —
real DeskApp, MediaSessionStore and MediaService, with the scripted media executor writing a tiny
WAV instead of running MiniMax Music 3 (joins and compositions are ffmpeg commands the fake
executor completes on its own). Every step asserts both what the page shows and what the backend
settled in GET /api/media-sessions/music/{id}.

The 900×700 screenshot is written to $LMD_MUSIC_SESSIONS_SHOTS when set (the image-sessions
convention), otherwise to the test's tmp_path.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps

CURRENT_ITEM = "[data-music-session-list] li[aria-current='true']"


def _cards(pane):
    return pane.locator("[data-music-timeline] .attempt")


def _settled(pane, count):
    expect(_cards(pane)).to_have_count(count)
    expect(_cards(pane).nth(count - 1)).to_have_attribute("data-attempt-status", "done", timeout=15_000)
    expect(pane.locator("[data-music-start]")).to_be_enabled(timeout=5_000)


def _session(page, harness, session_id):
    response = page.request.get(f"{harness.base_url}/api/media-sessions/music/{session_id}")
    assert response.status == 200, response.text()
    return response.json()


def _expanded(card):
    if card.get_attribute("aria-expanded") != "true":
        card.locator(".attempt-row").click()
    expect(card).to_have_attribute("aria-expanded", "true")
    return card


def test_continue_version_and_compose_a_song_in_one_session(page, tmp_path, monkeypatch):
    # Joins look ffmpeg up before spawning it; the fake executor never runs it, so any file will do.
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("")
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(ffmpeg))
    # Three model runs (first, continuation, new version); joins and the composition need no script.
    with launch_test_harness(tmp_path, media_script=MediaScript([fast_media_steps() for _ in range(3)])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=music")
        pane = page.locator("#pane-music")
        expect(pane).to_be_visible()
        expect(pane.locator(CURRENT_ITEM)).to_have_count(1)
        session_id = pane.locator(CURRENT_ITEM).get_attribute("data-session-id")

        # The lyrics box: at least four lines tall, grows to at most half the viewport.
        lyrics = pane.locator("[data-music-lyrics]")
        sizes = lyrics.evaluate("""(box) => { const s = getComputedStyle(box);
            return {min: parseFloat(s.minHeight), max: s.maxHeight, line: parseFloat(s.lineHeight) || parseFloat(s.fontSize) * 1.5,
                    vh: innerHeight}; }""")
        assert sizes["min"] >= 4 * sizes["line"], sizes
        assert abs(float(sizes["max"].removesuffix("px")) - sizes["vh"] * 0.5) <= 1, sizes

        # 1. First song.
        pane.locator("[data-music-caption]").fill("温柔的民谣，木吉他伴奏")
        lyrics.fill("第一段歌词\n窗外的雨")
        pane.locator("[data-music-start]").click()
        _settled(pane, 1)
        first = _expanded(_cards(pane).nth(0))
        expect(first.locator(".attempt-label")).to_contain_text("第 1 次")
        expect(first.locator("audio.attempt-audio")).to_have_count(1)
        attempts = _session(page, harness, session_id)["attempts"]
        assert [a["status"] for a in attempts] == ["done"]
        first_id = attempts[0]["id"]

        # 2. Continue after the first: the chip names it, the lyrics box starts empty.
        first.get_by_role("button", name="接着写下一段").click()
        expect(pane.locator("[data-music-chip]")).to_be_visible()
        expect(pane.locator("[data-music-chip-text]")).to_have_text("接在第 1 次后面")
        expect(lyrics).to_have_value("")
        lyrics.fill("第二段歌词\n雨停了")
        pane.locator("[data-music-start]").click()
        _settled(pane, 2)
        second = _expanded(_cards(pane).nth(1))
        expect(second.locator(".attempt-label")).to_contain_text("接第 1 次")
        expect(second.get_by_role("radio", name="成片")).to_be_visible()
        expect(second.get_by_role("radio", name="只听这一段")).to_be_visible()
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[1]["continues"] == first_id
        assert attempts[1]["joined_output"], attempts[1]
        assert attempts[1]["joined_error"] is None, attempts[1]
        expect(second.locator("audio.attempt-audio")).to_have_attribute(
            "src", f"/api/outputs/{attempts[1]['joined_output']}")

        # 3. A new version of the second: still continues the first.
        second.get_by_role("button", name="换个版本").click()
        _settled(pane, 3)
        expect(_cards(pane).nth(2).locator(".attempt-label")).to_contain_text("接第 1 次")
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[2]["continues"] == first_id
        third_id = attempts[2]["id"]

        # 4. Pick the third, then the first, move the first up, compose.
        pane.get_by_role("button", name="挑几段合成…").click()
        bar = pane.locator("[data-music-compose-bar]")
        expect(bar).to_be_visible()
        pane.get_by_role("checkbox", name="选中第 3 次").check()
        pane.get_by_role("checkbox", name="选中第 1 次").check()
        bar.get_by_role("button", name="上移第 1 次").click()
        submit = bar.get_by_role("button", name="合成（2 段）")
        expect(submit).to_be_enabled()
        submit.click()
        _settled(pane, 4)
        expect(_cards(pane).nth(3).locator(".attempt-label")).to_contain_text("合成：第 1、3 次")
        attempts = _session(page, harness, session_id)["attempts"]
        assert attempts[3]["params"]["parts"] == [first_id, third_id]
        assert attempts[3]["status"] == "done" and attempts[3]["output"]

        # 5. Narrow window: no horizontal scroll, the primary button is not clipped.
        page.set_viewport_size({"width": 900, "height": 700})
        shots = Path(os.environ.get("LMD_MUSIC_SESSIONS_SHOTS") or tmp_path)
        shots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shots / "music-sessions-900x700.png"))
        layout = page.evaluate("""() => { const b = document.querySelector('#pane-music [data-music-start]');
            return {scroll: document.documentElement.scrollWidth, inner: innerWidth,
                    btnScroll: b.scrollWidth, btnClient: b.clientWidth}; }""")
        assert layout["scroll"] <= layout["inner"], layout
        assert layout["btnScroll"] <= layout["btnClient"], layout

        # 6. The seed stays inside the advanced blocks.
        visible = pane.evaluate("""(root) => {
            const hidden = (n) => n.closest('details.music-advanced, details.attempt-advanced');
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
            const out = [];
            for (let n = walker.nextNode(); n; n = walker.nextNode()) {
                if (hidden(n.parentElement) || !n.parentElement.checkVisibility()) continue;
                out.push(n.textContent);
            }
            return out.join(' '); }""")
        assert "种子" not in visible, visible
