"""A-T5: settings → 本机 agent: multi-select apply, stale row, check, copy, narrow window."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def _open(page, h):
    page.goto(h.base_url)
    page.locator("[data-open-settings]").dispatch_event("click")
    section = page.locator("[data-agent-skill]")
    expect(section).to_be_visible()
    return section


def test_multi_select_apply_installs_only_checked(page, tmp_path, monkeypatch, audit_violations):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        rows = section.locator(".agent-skill-row")
        expect(rows).to_have_count(4)
        apply = section.locator("[data-agent-skill-apply]")
        expect(apply).to_be_disabled()
        section.locator(".agent-skill-row[data-key=pi] input").check()
        expect(apply).to_be_enabled()
        apply.click()
        expect(section.locator(".agent-skill-row[data-key=pi] [data-agent-skill-status]")).to_have_text("已安装")
        expect(section.locator(".agent-skill-row[data-key=claude] [data-agent-skill-status]")).to_have_text("未安装")
        assert (home / ".pi/agent/skills/local-model-desk").is_symlink()
        assert not (home / ".claude/skills/local-model-desk").exists()
        expect(apply).to_be_disabled()
    assert audit_violations == []


def test_stale_row_is_checked_and_apply_is_enabled(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    link = home / ".claude/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to("/gone/Old.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk")
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        row = section.locator(".agent-skill-row[data-key=claude]")
        expect(row.locator("input")).to_be_checked()
        expect(row.locator("[data-agent-skill-status]")).to_have_text("指向旧位置，点应用更新")
        expect(section.locator("[data-agent-skill-apply]")).to_be_enabled()


def test_occupied_row_shows_reason(page, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".dsh/skills/local-model-desk").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        expect(section.locator(".agent-skill-row[data-key=dsh] [data-agent-skill-status]")).to_contain_text("台面不会改动")


def test_check_and_copy(page, tmp_path, monkeypatch, context):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        section.locator("[data-agent-skill-check]").click()
        expect(section.locator("[data-agent-skill-check-result]")).not_to_have_text("检查中…")
        section.locator("[data-agent-skill-copy]").click()
        assert page.evaluate("navigator.clipboard.readText()") == "用本地模型把这句话翻成英文：今天天气很好"


def test_narrow_and_short_window_no_horizontal_scroll(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        page.set_viewport_size({"width": 720, "height": 520})
        section = _open(page, h)
        expect(section.locator(".agent-skill-row")).to_have_count(4)
        page.wait_for_timeout(500)  # let the drawer finish sliding in
        overflow = page.locator("#pane-settings").evaluate("el => el.scrollWidth - el.clientWidth")
        assert overflow <= 0
