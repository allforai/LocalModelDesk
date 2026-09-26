"""R-e2e-06: video parameters progress through the UI into a playable output."""
import time
import base64
import pytest
import subprocess

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_MP4


# 视频页改成会话式后（设计 V-20），作业进度与日志在时间线里正在生成的那张卡片上，成品是卡片里的 <video>。
def _job_log(pane):
    return pane.locator(".attempt-log pre")


def _card_video(pane):
    return pane.locator(".attempt video.attempt-video")


def _open_advanced(pane):
    advanced = pane.locator("[data-video-advanced]")
    if advanced.get_attribute("open") is None:
        advanced.locator("summary").click()


@pytest.mark.parametrize("mode,selector,name,mime,content,flag", [
    ("image", "first-upload", "first.png", "image/png", base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9ZkAAAAASUVORK5CYII="), "--first-frame"),
    ("reference", "source", "clip.mp4", "video/mp4", TINY_MP4, "--ref-video-silent"),
])
def test_conditioning_file_upload_preview_and_generation(page, tmp_path, mode, selector, name, mime, content, flag):
    if mode == "reference":
        clip = tmp_path / "sample.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:d=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True)
        content = clip.read_bytes()
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("#tabs [data-tab='video']").click()
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option(mode)
        pane.locator("[data-video-prompt]").fill("gentle waves")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-video-error]")).to_contain_text("请先选择")
        pane.locator(f"[data-video-{selector}]").set_input_files({"name": name, "mimeType": mime, "buffer": content})
        preview = "first" if mode == "image" else "source"
        expect(pane.locator(f"[data-video-{preview}-preview] > *")).to_be_visible()
        if mode == "reference":
            _open_advanced(pane)
            pane.locator("[data-video-audio]").uncheck()
        pane.locator("[data-video-start]").click()
        expect(_job_log(pane)).to_contain_text("step 1/10")
        argv = harness.media_script.spawned_argvs[-1]
        assert flag in argv
        from pathlib import Path
        assert Path(argv[argv.index(flag) + 1]).read_bytes() == content
        harness.media_script.step()
        harness.media_script.step()
        expect(_card_video(pane)).to_be_visible()


def test_video_parameters_progress_and_player_src_follow_finished_output(
    page, tmp_path, audit_violations
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        expect(page.get_by_text("内存里：无", exact=True).first).to_be_visible()
        page.locator("#tabs [data-tab='video']").dispatch_event("click")
        pane = page.locator("#pane-video")
        expect(pane).to_be_visible()
        pane.locator("[data-video-prompt]").fill("rain on a quiet street")
        _open_advanced(pane)
        pane.locator("[data-video-size]").select_option("768x448")
        pane.locator("[data-video-frames]").select_option("49")
        pane.locator("[data-video-steps]").fill("16")
        pane.locator("[data-video-start]").dispatch_event("click")

        expect(_job_log(pane)).to_contain_text("step 1/10")
        harness.media_script.step()
        expect(_job_log(pane)).to_contain_text("step 5/10")
        harness.media_script.step()

        output_name = "h3-{}.mp4".format(
            time.strftime("%Y%m%d-%H%M%S", time.localtime(harness.clock()))
        )
        player = _card_video(pane)
        expect(player).to_have_attribute("controls", "")
        expect(player).to_have_attribute("src", f"/api/outputs/{output_name}")
        assert (harness.outputs_root / output_name).read_bytes() == TINY_MP4

        response = page.request.get(f"{harness.base_url}{player.get_attribute('src')}")
        assert response.status in (200, 206)
    assert audit_violations == []


def test_first_frame_picker_is_reachable_by_keyboard(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        page.locator("[data-video-mode]").select_option("image")
        picker = page.locator("[data-video-first-upload]")
        picker.focus()
        assert page.evaluate("document.activeElement.matches('[data-video-first-upload]')")
        with page.expect_file_chooser() as chooser_info:
            page.keyboard.press("Space")
        chooser_info.value.set_files(files=[{"name": "a.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * 64}])
        expect(page.locator("[data-video-first-label]")).to_have_text("已选择：a.png")
    assert audit_violations == []


_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9ZkAAAAASUVORK5CYII=")


def _drop_file(page, row_selector, name, mime, content):
    """Dispatch the drag events a real drop produces, carrying one File (issue #15)."""
    page.evaluate(
        """([selector, name, mime, bytes]) => {
            const row = document.querySelector(selector);
            const data = new DataTransfer();
            data.items.add(new File([new Uint8Array(bytes)], name, {type: mime}));
            for (const type of ["dragenter", "dragover", "drop"]) {
              row.dispatchEvent(new DragEvent(type, {bubbles: true, cancelable: true, dataTransfer: data}));
            }
        }""",
        [row_selector, name, mime, list(content)],
    )


def test_dropping_an_image_on_the_first_frame_row_uses_it(page, tmp_path):
    """issue #15: the file inputs are visually hidden and the page had no drop handling,
    so a dragged image never reached them."""
    page.set_viewport_size({"width": 900, "height": 700})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        _drop_file(page, "#pane-video .file-row:has([data-video-first-upload])", "dropped.png", "image/png", _PNG)
        expect(pane.locator("[data-video-first-label]")).to_have_text("已选择：dropped.png")
        expect(pane.locator("[data-video-first-preview] > *")).to_be_visible()
        # 首帧、尾帧都选了时，输入区里的预览只是与按钮同一行的 64px 小图：900×700 下时间线仍放得下一整张
        # 折叠卡片（实测 118px；小图各占一行时只剩 28px），也没有横向滚动。
        pane.locator("[data-video-last]").set_input_files({"name": "last.png", "mimeType": "image/png", "buffer": _PNG})
        expect(pane.locator("[data-video-last-preview] > *")).to_be_visible()
        expect(pane.locator("[data-video-start]")).to_be_enabled()  # 服务状态查完，状态提示行不占高度
        timeline = pane.locator("[data-video-timeline]").evaluate("el => el.clientHeight")
        assert timeline >= 100, timeline
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        pane.locator("[data-video-prompt]").fill("gentle waves")
        pane.locator("[data-video-start]").click()
        expect(_job_log(pane)).to_contain_text("step 1/10")
        argv = harness.media_script.spawned_argvs[-1]
        from pathlib import Path
        assert Path(argv[argv.index("--first-frame") + 1]).read_bytes() == _PNG


def test_dropping_a_non_image_on_the_first_frame_row_is_refused(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        _drop_file(page, "#pane-video .file-row:has([data-video-first-upload])", "notes.txt", "text/plain", b"hello")
        expect(pane.locator("[data-video-error]")).to_contain_text("PNG、JPEG、WebP")
        expect(pane.locator("[data-video-first-label]")).to_have_text("未选择")


def test_a_file_dropped_outside_any_upload_row_does_not_replace_the_desk(page, tmp_path):
    """issue #15: with no drop handling, WebKit's default for a dropped file is to open it,
    replacing the desk UI. A stray drop must be swallowed, not followed."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        prevented = page.evaluate(
            """() => {
                const data = new DataTransfer();
                data.items.add(new File(["x"], "stray.png", {type: "image/png"}));
                const results = [];
                for (const type of ["dragover", "drop"]) {
                  const event = new DragEvent(type, {bubbles: true, cancelable: true, dataTransfer: data});
                  document.body.dispatchEvent(event);
                  results.push(event.defaultPrevented);
                }
                return results;
            }"""
        )
        assert prevented == [True, True]
