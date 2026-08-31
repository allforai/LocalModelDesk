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
