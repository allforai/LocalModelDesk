"""R-e2e-06: video parameters progress through the UI into a playable output."""
import time
import base64
import pytest
import subprocess

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_MP4


@pytest.mark.parametrize("mode,selector,name,mime,content,flag", [
    ("image", "first", "first.png", "image/png", base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9ZkAAAAASUVORK5CYII="), "--first-frame"),
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
        expect(pane.locator(f"[data-video-{selector}-preview] > *")).to_be_visible()
        if mode == "reference":
            pane.locator("[data-video-audio]").uncheck()
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-job-log]")).to_contain_text("step 1/10")
        argv = harness.media_script.spawned_argvs[-1]
        assert flag in argv
        from pathlib import Path
        assert Path(argv[argv.index(flag) + 1]).read_bytes() == content
        harness.media_script.step()
        harness.media_script.step()
        expect(pane.locator("[data-job-player] video")).to_be_visible()


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
        pane.locator("[data-video-size]").select_option("768x448")
        pane.locator("[data-video-frames]").select_option("49")
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


def test_first_frame_picker_is_reachable_by_keyboard(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        page.locator("[data-video-mode]").select_option("image")
        picker = page.locator("[data-video-first]")
        picker.focus()
        assert page.evaluate("document.activeElement.matches('[data-video-first]')")
        with page.expect_file_chooser() as chooser_info:
            page.keyboard.press("Space")
        chooser_info.value.set_files(files=[{"name": "a.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * 64}])
        expect(page.locator("[data-video-first-name]")).to_have_text("a.png")
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
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        _drop_file(page, "#pane-video .file-row:has([data-video-first])", "dropped.png", "image/png", _PNG)
        expect(pane.locator("[data-video-first-name]")).to_have_text("dropped.png")
        expect(pane.locator("[data-video-first-preview] > *")).to_be_visible()
        pane.locator("[data-video-prompt]").fill("gentle waves")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-job-log]")).to_contain_text("step 1/10")
        argv = harness.media_script.spawned_argvs[-1]
        from pathlib import Path
        assert Path(argv[argv.index("--first-frame") + 1]).read_bytes() == _PNG


def test_dropping_a_non_image_on_the_first_frame_row_is_refused(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        _drop_file(page, "#pane-video .file-row:has([data-video-first])", "notes.txt", "text/plain", b"hello")
        expect(pane.locator("[data-video-error]")).to_contain_text("PNG、JPEG、WebP")
        expect(pane.locator("[data-video-first-name]")).to_have_text("未选择文件")


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
