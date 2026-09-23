"""ui module server surface: static delivery and traversal protection."""
from pathlib import Path

import pytest

from desk.ui import CONTENT_TYPES, StaticAssets


@pytest.fixture
def static_root(tmp_path):
    root = tmp_path / "static"
    (root / "js" / "pure").mkdir(parents=True)
    (root / "index.html").write_text("<p>desk</p>", encoding="utf-8")
    (root / "app.css").write_text("body{}", encoding="utf-8")
    (root / "js" / "main.js").write_text("export {};", encoding="utf-8")
    (root / "js" / "pure" / "format.js").write_text("export {};", encoding="utf-8")
    (root / "notes.txt").write_text("nope", encoding="utf-8")
    (tmp_path / "secret.js").write_text("export {};", encoding="utf-8")
    return root


@pytest.fixture
def assets(static_root):
    return StaticAssets(static_root)


def test_root_and_index_serve_index(assets, static_root):
    for url in ("", "/", "/index.html"):
        hit = assets.resolve(url)
        assert hit is not None, url
        path, ctype = hit
        assert path == (static_root / "index.html").resolve()
        assert ctype == "text/html; charset=utf-8"


def test_css_and_js_content_types(assets):
    assert assets.resolve("/static/app.css")[1] == "text/css; charset=utf-8"
    assert assets.resolve("/static/js/main.js")[1] == "text/javascript; charset=utf-8"
    assert assets.resolve("/static/js/pure/format.js")[1] == "text/javascript; charset=utf-8"
    assert CONTENT_TYPES[".html"] == "text/html; charset=utf-8"


def test_query_string_stripped(assets):
    assert assets.resolve("/static/app.css?v=3") is not None


def test_unlisted_suffix_not_served(assets):
    assert assets.resolve("/static/notes.txt") is None


def test_missing_file_404(assets):
    assert assets.resolve("/static/js/nope.js") is None


def test_directory_paths_not_served(assets):
    assert assets.resolve("/static/js/") is None
    assert assets.resolve("/static/js") is None


def test_non_static_prefixes_not_served(assets):
    assert assets.resolve("/api/config") is None
    assert assets.resolve("/favicon.ico") is None


def test_escape_dotdot(assets):
    assert assets.resolve("/static/../secret.js") is None


def test_escape_urlencoded_dotdot(assets):
    assert assets.resolve("/static/%2e%2e/secret.js") is None


def test_escape_absolute_path(assets):
    assert assets.resolve("/static//etc/passwd") is None


# ---------- 仓库级断言（T-ui-19 起生效） ----------

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = REPO_ROOT / "desk" / "static"

REQUIRED_STATIC = [
    "index.html", "app.css",
    "js/main.js", "js/api.js", "js/store.js", "js/stream.js",
    "js/panes/chat.js", "js/panes/video.js", "js/panes/music.js",
    "js/panes/resources.js", "js/panes/library.js", "js/panes/firstrun.js", "js/panes/settings.js",
    "js/widgets/statusbar.js", "js/widgets/confirm.js", "js/widgets/jobview.js",
    "js/pure/chat_stream.js", "js/pure/model_status.js", "js/pure/desk_state.js",
    "js/pure/mem_warn.js", "js/pure/history_fill.js", "js/pure/base_url.js",
    "js/pure/sessions.js", "js/pure/format.js",
]


def test_required_static_files_exist():
    missing = [rel for rel in REQUIRED_STATIC if not (STATIC_ROOT / rel).is_file()]
    assert missing == []


def test_real_static_tree_fully_served():
    assets = StaticAssets(STATIC_ROOT)
    served = 0
    for f in STATIC_ROOT.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(STATIC_ROOT).as_posix()
        hit = assets.resolve(f"/static/{rel}")
        assert hit is not None, rel
        assert hit[1] == CONTENT_TYPES[f.suffix], rel
        served += 1
    assert served >= len(REQUIRED_STATIC)
    assert assets.resolve("/")[0].name == "index.html"


def test_no_inline_html_in_python():
    offenders = []
    for p in (REPO_ROOT / "desk").rglob("*.py"):
        if "testing" in p.relative_to(REPO_ROOT / "desk").parts:
            continue
        src = p.read_text(encoding="utf-8", errors="replace").lower()
        if "<!doctype" in src or "<html" in src:
            offenders.append(str(p))
    assert offenders == []


def test_no_direct_llm_port_in_frontend():
    offenders = []
    for f in STATIC_ROOT.rglob("*"):
        if f.is_file() and "8767" in f.read_text(encoding="utf-8", errors="replace"):
            offenders.append(str(f))
    assert offenders == []


def test_shell_tick_refreshes_resource_download_progress():
    source = (STATIC_ROOT / "js" / "main.js").read_text(encoding="utf-8")
    assert "await panes.resources.refresh()" in source

    api_source = (STATIC_ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "request(ROUTES.download)" in api_source


CSS = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")       # STATIC_ROOT already defined in this file
HTML = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")


def test_css_defines_three_button_levels_and_disabled_state():
    assert ".btn-primary{" in CSS.replace(" ", "") and "background:var(--accent)" in CSS
    assert ".btn-danger{" in CSS.replace(" ", "") and "background:var(--danger)" in CSS
    assert "button:disabled" in CSS and "cursor:not-allowed" in CSS and "opacity:.5" in CSS
    assert "button,input,select,textarea{font:inherit" in CSS.replace(" ", "")


def test_primary_actions_carry_the_primary_class():
    for hook in ("data-session-new", "data-send", "data-video-start", "data-music-start", "data-settings-save", "data-fr-complete"):
        assert f"{hook} " in HTML and "btn-primary" in HTML.split(hook, 1)[1].split(">", 1)[0], hook


def test_layout_is_full_width_with_24px_margins_and_cards():
    assert "main>section{" in CSS.replace(" ", "") and "padding:var(--margin)" in CSS.replace(" ", "")
    assert ".badge-ok{" in CSS.replace(" ", "") and ".badge-busy{" in CSS.replace(" ", "") and ".badge-none{" in CSS.replace(" ", "")

def test_reason_hints_are_not_error_red_and_motion_is_limited():
    assert ".hint-busy{" in CSS.replace(" ", "") and "color:var(--busy)" in CSS
    assert "prefers-reduced-motion" in CSS


def test_drawer_and_firstrun_markup_use_shared_form_language():
    assert 'class="check-row"' in HTML and "data-settings-enabled" in HTML.split('class="check-row"', 1)[1].split("</label>", 1)[0]
    assert '<fieldset' not in HTML          # first-run uses cards, not browser fieldsets
    assert 'class="drawer-head"' in HTML and 'data-close-settings' in HTML.split('class="drawer-head"', 1)[1].split("</div>", 1)[0]


def test_music_duration_field_explains_the_real_length():
    assert "成品时长由模型按歌词决定" in HTML


def test_file_inputs_stay_in_the_tab_order():
    """hidden 的 input 不可聚焦，键盘用户选不了首帧/参考视频（P2）。"""
    import re

    inputs = re.findall(r'<input type="file"[^>]*>', HTML)
    assert len(inputs) == 3
    for tag in inputs:
        assert " hidden" not in tag
        assert 'class="visually-hidden"' in tag


def test_skill_bar_states_editing_skill_md_takes_effect_next_turn():
    """R-skill-05：skill 是「当前的指令」，不是「当时说过的话」——改了 SKILL.md，
    老会话的下一轮就用新版本。这个后果 spec 要求「必须在界面上说明」，但一直
    只活在 spec 文字里，desk/static/ 下找不到这句话（2026-09-23 finding 4）。
    放在 skill-bar（重新扫描按钮）旁边，是用户唯一会去看这一块的地方。
    """
    assert "data-skill-effect-hint" in HTML
    bar_and_after = HTML.split("data-skill-bar", 1)[1]
    hint = bar_and_after.split("data-skill-effect-hint", 1)[1].split("</span>", 1)[0]
    assert "SKILL.md" in hint
    assert "下一轮" in hint and "新版本" in hint
