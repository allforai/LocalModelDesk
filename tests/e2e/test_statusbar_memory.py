"""R-e2e-10: status-bar memory values come from the injected snapshots."""

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.fakes import DEFAULT_SNAPSHOT_A, SNAPSHOT_B
from desk.testing.scripts import MemoryScript


def _rendered_numbers(snapshot):
    """Accept either documented GB convention while proving the input is rendered."""
    divisors = (10**9, 1024**3)
    return {
        f"{value / divisor:.1f}"
        for divisor in divisors
        for value in (
            snapshot.used_bytes,
            snapshot.total_bytes,
            snapshot.available_bytes,
        )
    }


def _statusbar_contains_snapshot(statusbar, snapshot):
    text = statusbar.inner_text()
    return any(number in text for number in _rendered_numbers(snapshot))


def test_statusbar_memory_follows_injected_snapshot(page, tmp_path, wait_until):
    memory = MemoryScript([DEFAULT_SNAPSHOT_A])
    with launch_test_harness(tmp_path, memory_script=memory) as harness:
        page.goto(harness.base_url)
        statusbar = page.locator("#statusbar")

        expect(statusbar).to_contain_text("已用")
        assert _statusbar_contains_snapshot(statusbar, DEFAULT_SNAPSHOT_A)

        memory.push(SNAPSHOT_B)
        wait_until(lambda: _statusbar_contains_snapshot(statusbar, SNAPSHOT_B), timeout=6)
        assert _statusbar_contains_snapshot(statusbar, SNAPSHOT_B)
        assert "128" not in statusbar.inner_text()
