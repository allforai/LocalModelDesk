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


def test_drawer_close_button_looks_like_a_secondary_button(page, tmp_path):
    """F4: the drawer close button must not render as bare text next to bordered ones."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("[data-open-settings]").click()
        close_button = page.locator("[data-close-settings]")
        expect(close_button).to_be_visible()
        style = close_button.evaluate(
            "el => { const s = getComputedStyle(el); return {border: s.borderColor, bg: s.backgroundColor}; }"
        )
        assert style["border"] not in ("transparent", "rgba(0, 0, 0, 0)"), style
        assert style["bg"] not in ("transparent", "rgba(0, 0, 0, 0)"), style


def test_reconfigure_models_root_asks_before_returning_to_first_run(page, tmp_path):
    """A-Task 7b: a stray click on 'reconfigure' must not silently drop into first-run."""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.locator("[data-open-settings]").click()
        page.locator("[data-settings-models-reset]").click()
        dialog = page.locator(".overlay .dialog")
        expect(dialog).to_contain_text("首次运行")
        dialog.get_by_role("button", name="取消").click()
        expect(page.locator("#pane-firstrun")).to_be_hidden()
        expect(page.locator("#pane-settings")).to_be_visible()

        page.locator("[data-settings-models-reset]").click()
        page.locator(".overlay .dialog").get_by_role("button", name="回到首次运行").click()
        expect(page.locator("#pane-firstrun")).to_be_visible()
