"""R-e2e-05: model states, download lifecycle, and guarded deletion."""
import os

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import MANIFEST_FILES


def _row(page, key):
    return page.locator(f'[data-model="{key}"]')


def test_resources_panel_renders_states_and_remaining_space(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)

        expect(page.locator("#pane-video")).to_be_hidden()
        page.get_by_text("资源", exact=True).click()
        expect(page.locator("#pane-resources")).to_be_visible()

        states = {state: key for key, state in harness.seeded.items()
                  if key not in ("h3", "music3")}
        expect(_row(page, states["present"])).to_contain_text("齐")
        expect(_row(page, states["partial"])).to_contain_text("一半 60%")
        expect(_row(page, states["missing"])).to_contain_text("没下")
        expect(page.get_by_text("剩余空间", exact=False)).to_be_visible()

        stat = os.statvfs(harness.models_root)
        assert stat.f_bavail * stat.f_frsize > 0


def test_resources_panel_download_cancel_resume_and_finish(page, tmp_path, wait_until):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.get_by_text("资源", exact=True).click()
        key = next(key for key, state in harness.seeded.items() if state == "missing")
        missing = _row(page, key)

        missing.get_by_role("button", name="下载").click()
        wait_until(lambda: len(harness.download_control.spawns) == 1)
        expect(missing.get_by_role("button", name="取消")).to_be_visible()

        destination = harness.download_control.dest_dir(harness.download_control.spawns[0])
        harness.download_control.advance("weights/a.safetensors", 300)
        page.get_by_role("button", name="重新校验").click()
        expect(missing).to_contain_text("30%")

        missing.get_by_role("button", name="取消").click()
        wait_until(lambda: harness.download_control.handle.terminated)
        harness.download_control.exit_terminated()
        assert (destination / "weights" / "a.safetensors").stat().st_size == 300

        expect(missing.get_by_role("button", name="续传")).to_be_visible()
        missing.get_by_role("button", name="续传").click()
        wait_until(lambda: len(harness.download_control.spawns) == 2)
        harness.download_control.finish(list(MANIFEST_FILES))
        page.get_by_role("button", name="重新校验").click()
        expect(missing).to_contain_text("齐")


def test_resources_panel_confirms_deletion(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.get_by_text("资源", exact=True).click()
        key = next(key for key, state in harness.seeded.items()
                   if state == "present" and key not in ("h3", "music3"))
        row = _row(page, key)

        row.get_by_role("button", name="删除").click()
        dialog = page.locator(".overlay .dialog")
        expect(dialog).to_contain_text("删除模型")
        dialog.get_by_role("button", name="取消").click()
        expect(row.get_by_role("button", name="删除")).to_be_visible()

        row.get_by_role("button", name="删除").click()
        dialog.get_by_role("button", name="确认").click()
        expect(row).to_contain_text("没下")
