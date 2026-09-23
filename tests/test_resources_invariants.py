"""R-resources-01 and census A01/A02/A20/A21 repository-wide guards.

`desk/resources/catalog.py` is the single catalog definition. No legacy copy is
tolerated any more (the media-gui prototype was deleted 2026-09-11).
"""
import os
from pathlib import Path

from desk.resources.catalog import CATALOG  # noqa: F401


REPO = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git", ".claude", "__pycache__", ".pytest_cache", "node_modules", "docs",
    "dist", ".venv-desk", ".venv-music3", "llms", "minimax-h3", "minimax-music3",
    "outputs",
    # 仓库里但不是产品代码：`.worktrees/` 是 git 工作区（里面有一整份代码副本），
    # `.superpowers/` 是流程草稿。不跳过的话，「只许有一份」这类全仓库不变式会把
    # 副本当成第二份而误报——2026-09-23 真踩过一次，三条测试同时变红。
    ".worktrees", ".superpowers",
}
TEXT_SUFFIXES = {
    ".py", ".sh", ".js", ".mjs", ".html", ".css", ".swift", ".json",
    ".md", ".txt", ".plist", ".yml", ".yaml", ".toml",
}

ALLOWED = {"desk/resources/catalog.py"}
LEGACY: set[str] = set()
TESTS_PREFIX = "tests/"


def iter_text_files(root_dir: Path = REPO):
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]
        for name in files:
            path = Path(root) / name
            if path.suffix not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 5_000_000:
                    continue
            except OSError:
                continue
            yield path


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def test_no_second_catalog_copy_anywhere():
    needles = [entry.hf_repo for entry in CATALOG]
    offenders = []
    for path in iter_text_files():
        relative_path = rel(path)
        if relative_path in ALLOWED or relative_path in LEGACY or relative_path.startswith(TESTS_PREFIX):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle in text:
                offenders.append((relative_path, needle))
    assert offenders == [], f"second catalog copy found: {offenders}"


def test_no_weak_presence_checks_outside_legacy():
    offenders = []
    for path in iter_text_files():
        relative_path = rel(path)
        if relative_path in LEGACY or relative_path.startswith(TESTS_PREFIX):
            continue
        if "model_present" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(relative_path)
    assert offenders == [], f"weak presence check found outside legacy files: {offenders}"


def test_no_catalog_arrays_outside_legacy():
    offenders = []
    for path in iter_text_files():
        relative_path = rel(path)
        if relative_path in LEGACY or relative_path in ALLOWED or relative_path.startswith(TESTS_PREFIX):
            continue
        if path.suffix not in {".sh", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "CATALOG=(" in text or "MODEL_CATALOG" in text:
            offenders.append(relative_path)
    assert offenders == [], f"catalog array found outside legacy files: {offenders}"


def test_legacy_allowlist_entries_are_files_while_present():
    for relative_path in LEGACY:
        path = REPO / relative_path
        if path.exists():
            assert path.is_file()


# ---- 扫描范围：仓库里的非产品目录必须跳过 ----------------------------

def test_scan_skips_git_worktrees_and_scratch_dirs(tmp_path):
    """`.worktrees/` 与 `.superpowers/` 住在仓库里，但不是产品代码。

    真实踩过：SDD 流程在 `.worktrees/<分支>/` 下开 git 工作区，那里有一份完整的代码副本，
    于是「目录表只许有一份」这类全仓库不变式会把副本当成第二份，三条测试同时误报。
    当时是靠撤掉工作区绕过的——但下一个用工作区的人会再踩一次。
    """
    (tmp_path / "desk").mkdir()
    (tmp_path / "desk" / "real.py").write_text("x = 1", encoding="utf-8")
    for scratch in (".worktrees/branch/desk", ".superpowers/sdd/plan"):
        d = tmp_path / scratch
        d.mkdir(parents=True)
        (d / "copy.py").write_text("x = 1", encoding="utf-8")

    found = sorted(p.relative_to(tmp_path).as_posix() for p in iter_text_files(tmp_path))

    assert found == ["desk/real.py"], f"扫到了非产品目录：{found}"
