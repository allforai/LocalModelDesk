"""First-run keeps the desk shell hidden until setup persists."""

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_first_run_hides_and_restores_desk_shell_with_selected_models_root(
    page, tmp_path, audit_violations,
):
    selected_root = tmp_path / "external-models"
    with launch_test_harness(tmp_path, configured=False) as harness:
        page.goto(harness.base_url)

        expect(page.locator("#pane-firstrun")).to_be_visible()
        expect(page.locator("#statusbar")).to_be_hidden()
        expect(page.locator("#tabs")).to_be_hidden()
        expect(page.locator("main")).to_be_hidden()

        page.locator("[data-fr-models-root]").fill(str(selected_root))
        page.locator("[data-fr-complete]").click()

        expect(page.locator("#pane-firstrun")).to_be_hidden()
        expect(page.locator("#statusbar")).to_be_visible()
        expect(page.locator("#tabs")).to_be_visible()
        expect(page.locator("main")).to_be_visible()
        config = page.request.get(f"{harness.base_url}/api/config").json()
        assert config["first_run_done"] is True
        assert config["needs_setup"] is False
        assert config["models_root"] == str(selected_root)
    assert audit_violations == []
