"""Repo-level static guards for foundation path, exit, and logging invariants."""
import re
from pathlib import Path


DESK = Path(__file__).resolve().parent.parent / "desk"
PATHS_PY = DESK / "foundation" / "paths.py"


def _py_files():
    files = sorted(DESK.rglob("*.py"))
    assert files, "desk/ package missing"
    return files


def test_home_expansion_only_in_paths_py():
    offenders = []
    for source in _py_files():
        if source == PATHS_PY:
            continue
        text = source.read_text(encoding="utf-8")
        if "Path.home(" in text or "expanduser" in text:
            offenders.append(str(source))
    assert offenders == [], f"home-dir path building outside paths.py: {offenders}"


def test_no_system_exit_anywhere_in_desk():
    offenders = []
    for source in _py_files():
        text = source.read_text(encoding="utf-8")
        if "raise SystemExit" in text or "sys.exit(" in text:
            offenders.append(str(source))
    assert offenders == [], f"SystemExit/sys.exit found: {offenders}"


def test_file_logging_configured_in_exactly_one_place():
    offenders = []
    for source in _py_files():
        if source == PATHS_PY:
            continue
        text = source.read_text(encoding="utf-8")
        for needle in ("logging.FileHandler", "RotatingFileHandler", "logging.basicConfig"):
            if needle in text:
                offenders.append(f"{source}: {needle}")
    assert offenders == [], f"file logging outside setup_logging: {offenders}"
    assert "logging.FileHandler" in PATHS_PY.read_text(encoding="utf-8")


def test_foundation_imports_no_sibling_packages():
    pattern = re.compile(r"^\s*(?:from|import)\s+desk\.(\w+)", re.MULTILINE)
    for source in (DESK / "foundation").rglob("*.py"):
        for match in pattern.finditer(source.read_text(encoding="utf-8")):
            assert match.group(1) == "foundation", f"{source} imports desk.{match.group(1)}"
