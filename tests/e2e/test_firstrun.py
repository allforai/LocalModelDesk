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


def test_firstrun_uses_the_window_and_inputs_show_full_paths(page, tmp_path):
    """W2/F9: first-run must not sit in a 640px column, and path inputs must show their value."""
    page.set_viewport_size({"width": 1920, "height": 1200})
    with launch_test_harness(tmp_path, configured=False) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".firstrun-wrap")
        measured = page.evaluate(
            "() => { const wrap = document.querySelector('.firstrun-wrap').getBoundingClientRect();"
            " const input = document.querySelector('[data-fr-models-root]').getBoundingClientRect();"
            " return {wrap: wrap.width, input: input.width}; }"
        )
        assert (1920 - measured["wrap"]) / 1920 <= 0.40
        assert measured["input"] >= 400
