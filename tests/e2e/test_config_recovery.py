"""J25: a half-written config.json can be recovered from the window alone."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_corrupt_config_offers_reset_and_lands_in_first_run(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        config_path = harness.data_root / "config.json"
        config_path.write_text('{"config_version": 1, "first_run', encoding="utf-8")

        page.goto(harness.base_url)
        expect(page.locator("#fatal [data-fatal-text]")).to_contain_text("无法读取配置")
        page.get_by_role("button", name="重新设置").click()

        expect(page.locator("#pane-firstrun")).to_be_visible()
        backups = list(harness.data_root.glob("config.broken-*.json"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == '{"config_version": 1, "first_run'
    assert audit_violations == []
