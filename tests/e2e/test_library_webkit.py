"""L-53：外壳是 WKWebView，视频首帧缩略图（#t=0.1 + preload=metadata）要在 WebKit 上确认能出画面。"""
import shutil
import subprocess
import threading

import pytest
from playwright.sync_api import expect, sync_playwright

from desk.testing import launch_test_harness


def test_video_thumbnail_shows_a_frame_in_webkit(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("没有 ffmpeg，造不出测试视频")
    clip = tmp_path / "clip.mp4"
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=24", "-t", "1",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)], check=True)
    # The session-wide Chromium fixture keeps a sync Playwright loop alive on this thread, so WebKit runs on its own thread.
    outcome: list[BaseException] = []

    def run():
        try:
            _check_webkit(clip, tmp_path)
        except BaseException as error:  # noqa: BLE001 - re-raised on the test thread (skips included)
            outcome.append(error)

    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    if outcome:
        raise outcome[0]


def _check_webkit(clip, tmp_path):
    with sync_playwright() as playwright:
        try:
            browser = playwright.webkit.launch()
        except Exception as error:  # 没装 WebKit 时不算失败，但要在报告里看得到
            pytest.skip(f"WebKit 不可用：{error}")
        try:
            with launch_test_harness(tmp_path / "harness") as harness:
                harness.outputs_root.mkdir(parents=True, exist_ok=True)
                (harness.outputs_root / "h3-webkit.mp4").write_bytes(clip.read_bytes())
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(harness.base_url + "#tab=library")
                expect(page.locator("[data-lib-view] .lib-thumb video")).to_have_count(1)
                page.wait_for_function(
                    "() => { const v = document.querySelector('[data-lib-view] .lib-thumb video');"
                    " return v && v.readyState >= 2 && v.videoWidth > 0; }", timeout=15_000)
        finally:
            browser.close()
