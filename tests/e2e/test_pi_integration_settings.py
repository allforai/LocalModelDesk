"""Real settings UI + real installer in temporary HOME; no inference."""
from playwright.sync_api import expect
from desk.testing import launch_test_harness


def open_section(page, h):
    page.goto(h.base_url)
    page.locator("[data-open-settings]").click()
    section = page.locator("[data-pi-integration]")
    section.scroll_into_view_if_needed()
    expect(section.locator("[data-pi-status]")).to_have_text("未安装")
    return section


def test_install_versions_copy_check_remove(page, context, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    with launch_test_harness(tmp_path) as h:
        h.pi_integration._which = lambda _: "/fake/pi"
        section = open_section(page, h)
        expect(section.locator("[data-pi-model]")).to_have_count(6)
        for key, version in (("glm", "GLM 4.7"), ("superqwen", "SuperQwen3.8"), ("gemma", "Gemma 4 31B"), ("arete", "Arete-27B")):
            expect(section.locator(f'[data-pi-model="{key}"] strong')).to_contain_text(version)
        expect(section.locator('[data-pi-model="qwen35"] strong')).to_contain_text("最推荐编程")
        expect(section.locator('[data-pi-model="gemma"] strong')).to_contain_text("看图")
        section.locator('[data-pi-model="glm"] button').click()
        assert page.evaluate("navigator.clipboard.readText()") == "pi --model lmdesk/glm"
        section.locator("[data-pi-install]").click()
        expect(section.locator("[data-pi-status]")).to_have_text("已安装")
        assert (home / ".pi/agent/extensions/lmdesk.ts").is_file()
        expect(section.locator("[data-pi-install]")).to_be_disabled()
        section.locator("[data-pi-check]").click()
        expect(section.locator("[data-pi-result]")).not_to_have_text("处理中…")
        # User modifications after installation must survive a later refresh/removal.
        target = home / ".pi/agent/extensions/lmdesk.ts"
        original = target.read_bytes()
        target.write_text("// user edit")
        section.locator("[data-pi-refresh]").click()
        expect(section.locator("[data-pi-status]")).to_have_text("文件冲突")
        expect(section.locator("[data-pi-remove]")).to_be_disabled()
        target.write_bytes(original)
        section.locator("[data-pi-refresh]").click()
        expect(section.locator("[data-pi-status]")).to_have_text("已安装")
        section.locator("[data-pi-remove]").click()
        page.get_by_role("button", name="移除接入", exact=True).click()
        expect(section.locator("[data-pi-status]")).to_have_text("未安装")
        assert not target.exists()


def test_missing_pi_brew_progress_and_failure_are_visible(page, tmp_path, monkeypatch):
    import threading
    from desk.pi_integration.brew import BrewInstall
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    release = threading.Event()
    calls = []
    class Failed:
        def wait(self, timeout=None):
            assert release.wait(10)
            return 1
        def poll(self): return 1 if release.is_set() else None
    def spawn(args, **kwargs):
        calls.append(args)
        kwargs["stdout"].write(b"brew fixture download failed")
        return Failed()
    with launch_test_harness(tmp_path) as h:
        h.pi_integration._which = lambda _: None
        h.pi_integration._brew = BrewInstall(which=lambda: "/fake/brew", popen=spawn)
        try:
            section = open_section(page, h)
            assert calls == []
            expect(section.locator("[data-pi-detected]")).to_contain_text("brew install")
            section.locator("[data-pi-install]").click()
            expect(section.locator("[data-pi-status]")).to_have_text("正在安装 pi")
            expect(section.locator("[data-pi-install]")).to_be_disabled()
            assert len(calls) == 1
            release.set()
            expect(section.locator("[data-pi-brew-message]")).to_contain_text("安装失败")
            expect(section.locator("[data-pi-log]")).to_contain_text("brew fixture download failed")
            expect(section.locator("[data-pi-install]")).to_be_enabled()
            assert not (home / ".pi/agent/extensions/lmdesk.ts").exists()
        finally:
            release.set()
            h.pi_integration._brew._thread.join(3)


def test_narrow_settings_models_do_not_overflow(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        page.set_viewport_size({"width": 720, "height": 520})
        section = open_section(page, h)
        expect(section.locator("[data-pi-model]")).to_have_count(6)
        assert page.locator("#pane-settings").evaluate("el => el.scrollWidth <= el.clientWidth")
