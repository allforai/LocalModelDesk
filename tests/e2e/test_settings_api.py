"""R-e2e-11: settings exposes both gateway URLs and the auth warning."""

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_settings_panel_shows_openai_and_anthropic_base_urls_without_authentication(
    page, tmp_path, audit_violations,
):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("[data-open-settings]").dispatch_event("click")

        settings = page.locator("#pane-settings")
        expect(settings).to_be_visible()
        expect(settings.locator("[data-settings-openai-url]")).to_have_text(
            f"http://127.0.0.1:{harness.gateway_port}/v1"
        )
        expect(settings.locator("[data-settings-anthropic-url]")).to_have_text(
            f"http://127.0.0.1:{harness.gateway_port}"
        )
        expect(settings.locator("[data-settings-auth-warning]")).to_contain_text("无鉴权")
    assert audit_violations == []
