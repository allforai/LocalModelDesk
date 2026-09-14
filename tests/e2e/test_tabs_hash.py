"""Restoring a #tab fragment from outside (a link, the native shell) switches the pane."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_hashchange_switches_the_visible_pane(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=library")
        expect(page.locator("#pane-library")).to_be_visible()

        page.evaluate("location.hash = '#tab=chat'")
        expect(page.locator("#pane-chat")).to_be_visible()
        expect(page.locator("#pane-library")).to_be_hidden()

        page.evaluate("location.hash = '#tab=music'")
        expect(page.locator("#pane-music")).to_be_visible()
    assert audit_violations == []
