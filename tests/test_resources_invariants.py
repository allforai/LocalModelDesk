"""R-resources-01 and census A01/A02/A20/A21 repository-wide guards.

``initModels.sh`` and ``media-gui/server.py`` are the only legacy catalog
copies tolerated until packaging removes them. Any other catalog copy or weak
presence check is a regression.
"""
import os
from pathlib import Path

from desk.resources.catalog import CATALOG


REPO = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git", ".claude", "__pycache__", ".pytest_cache", "node_modules", "docs",
    "dist", ".venv-desk", ".venv-music3", "llms", "minimax-h3", "minimax-music3",
    "outputs",
}
TEXT_SUFFIXES = {
    ".py", ".sh", ".js", ".mjs", ".html", ".css", ".swift", ".json",
    ".md", ".txt", ".plist", ".yml", ".yaml", ".toml",
}

ALLOWED = {"desk/resources/catalog.py"}
LEGACY = {"initModels.sh", "media-gui/server.py"}
TESTS_PREFIX = "tests/"


def iter_text_files():
    for root, dirs, files in os.walk(REPO):
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
