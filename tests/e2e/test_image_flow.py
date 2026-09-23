"""Image shell regression using isolated harness; not real MLX acceptance."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_image_tab_defaults_missing_model_and_keyboard_fields(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=image")
        pane = page.locator("#pane-image")
        expect(pane).to_be_visible()
        for name, value in {"width": "1024", "height": "1024", "steps": "40", "seed": "42"}.items():
            expect(pane.locator(f"[data-image-{name}]")).to_have_value(value)
        expect(pane.locator("[data-image-start]")).to_be_disabled()
        expect(pane.locator("[data-image-model]")).to_contain_text("尚未安装")
        pane.get_by_label("图片提示词", exact=True).fill("一只橘猫")
        expect(pane.locator("[data-image-prompt]")).to_have_value("一只橘猫")
        expect(pane.locator("[data-job-player] video, [data-job-player] audio")).to_have_count(0)
        page.reload()
        expect(pane).to_be_visible()
