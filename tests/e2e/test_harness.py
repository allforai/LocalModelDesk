"""R-e2e-01: the browser can reach a deterministic, isolated test desk."""
import re
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness

REPO = Path(__file__).resolve().parents[2]
TABS = ["聊天", "视频", "音乐", "资源", "素材库"]


def test_desk_shell_reachable_with_tabs_and_statusbar(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        for tab in TABS:
            expect(page.get_by_text(tab, exact=True).first).to_be_visible()
        expect(page.get_by_text("空闲").first).to_be_visible()
        expect(page.get_by_text("设置").first).to_be_visible()
    assert audit_violations == []


def test_same_params_twice_yield_identical_seeding(page, tmp_path):
    with launch_test_harness(tmp_path / "a") as first:
        page.goto(first.base_url)
        expect(page.get_by_text("聊天", exact=True).first).to_be_visible()
        seeded = dict(first.seeded)
    with launch_test_harness(tmp_path / "b") as second:
        page.goto(second.base_url)
        expect(page.get_by_text("聊天", exact=True).first).to_be_visible()
        assert dict(second.seeded) == seeded


def test_route_coverage_guards_against_assembly_drift(tmp_path):
    source = (REPO / "desk/static/js/api.js").read_text(encoding="utf-8")
    paths = sorted(set(re.findall(r"[\"'`](/api/[A-Za-z0-9_/\\-]+)", source)))
    assert len(paths) >= 10, f"api.js extraction failed: {paths}"
    with launch_test_harness(tmp_path) as harness:
        prefixes = [path for _method, path in harness.routes]
        unmounted = [path for path in paths if not any(
            path.startswith(prefix) or prefix.startswith(path) for prefix in prefixes)]
    assert unmounted == [], f"frontend paths not mounted by harness: {unmounted}"
