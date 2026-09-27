"""A scripted ffmpeg (join) failure, end to end (#20).

FakeMediaExecutor auto-succeeds every ffmpeg-shaped command (join/compose, no ``--output``);
until this task, e2e had no way to script one to fail, so the join-failed path
(desk/media/service.py `_run_join`, docs/superpowers/specs/2026-09-27-music-sessions-design.md
M-40/M-41) had no real-browser coverage. Fixture shape follows tests/e2e/test_music_sessions.py.
"""
from __future__ import annotations

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


def _expanded(card):
    if card.get_attribute("aria-expanded") != "true":
        card.locator(".attempt-row").click()
    expect(card).to_have_attribute("aria-expanded", "true")
    return card


def test_a_scripted_join_failure_shows_the_problem_and_rejoin_recovers(page, tmp_path, monkeypatch):
    # Joins look ffmpeg up before spawning it; the fake executor never runs it, so any file will do.
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("")
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(ffmpeg))
    # Two model runs (first segment, continuation); the join after the continuation and the
    # rejoin compose both need no scripted job (they're ffmpeg commands the fake executor completes).
    with launch_test_harness(tmp_path, media_script=MediaScript([fast_media_steps() for _ in range(2)])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=music")
        pane = page.locator("#pane-music")
        expect(pane).to_be_visible()
        expect(pane.locator(CURRENT_ITEM)).to_have_count(1)

        # 1. First song.
        pane.locator("[data-music-caption]").fill("温柔的民谣，木吉他伴奏")
        pane.locator("[data-music-lyrics]").fill("第一段歌词\n窗外的雨")
        pane.locator("[data-music-start]").click()
        _settled(pane, 1)
        first = _expanded(_cards(pane).nth(0))

        # 2. Continue after the first, but script the join it triggers to fail.
        harness.media_script.fail_next_ffmpeg()
        first.get_by_role("button", name="接着写下一段").click()
        expect(pane.locator("[data-music-chip]")).to_be_visible()
        pane.locator("[data-music-lyrics]").fill("第二段歌词\n雨停了")
        pane.locator("[data-music-start]").click()
        _settled(pane, 2)   # the segment itself is still "done" even though its join failed
        second = _expanded(_cards(pane).nth(1))
        expect(second.locator(".attempt-join-problem .inline-error")).to_have_text(
            "这一段生成好了，但成片没拼成：拼接成片失败")
        rejoin = second.get_by_role("button", name="重新拼接")
        expect(rejoin).to_be_visible()
        expect(rejoin).to_be_enabled()

        # 3. Rejoin (the flag already cleared, so this one succeeds): a new compose card appears.
        rejoin.click()
        _settled(pane, 3)
        composed = _cards(pane).nth(2)
        expect(composed.locator(".attempt-label")).to_contain_text("合成")
        expect(composed).to_have_attribute("data-attempt-status", "done")
