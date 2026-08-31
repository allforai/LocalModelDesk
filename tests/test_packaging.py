"""Tests for the static packaging assets."""
from __future__ import annotations

import plistlib
import re
import subprocess

from packaging_fixture import BUNDLE_ID, REPO, render_info_plist


PLIST_KEYS = [
    "CFBundleIdentifier", "CFBundleName", "CFBundleExecutable",
    "CFBundleShortVersionString", "CFBundleVersion", "CFBundleIconFile",
    "LSMinimumSystemVersion", "CFBundlePackageType", "NSHighResolutionCapable",
]


def run(command: list[object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(value) for value in command], capture_output=True, text=True)


def test_plist_template_renders_all_keys(tmp_path):
    plist_path = tmp_path / "Info.plist"
    render_info_plist(plist_path, version="9.9.9")
    result = run(["plutil", "-lint", plist_path])
    assert result.returncode == 0, result.stdout + result.stderr
    data = plistlib.loads(plist_path.read_bytes())
    for key in PLIST_KEYS:
        assert key in data and data[key] not in ("", None), f"missing or empty key: {key}"
    assert data["CFBundleShortVersionString"] == "9.9.9"
    assert data["CFBundleVersion"] == "9.9.9"
    assert data["CFBundleIdentifier"] == BUNDLE_ID
    assert data["LSMinimumSystemVersion"] == "15.0"
    assert "@VERSION@" not in plist_path.read_text()


def test_entitlements_is_empty_dict():
    data = plistlib.loads((REPO / "packaging" / "entitlements.plist").read_bytes())
    assert data == {}


def test_icon_source_is_1024_png():
    result = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", REPO / "packaging" / "icon" / "icon-1024.png"])
    assert result.returncode == 0, result.stderr
    assert "pixelWidth: 1024" in result.stdout
    assert "pixelHeight: 1024" in result.stdout


def test_requirements_locks_are_pinned():
    tops = {
        "desk": "mlx-lm==0.31.3",
        "music": "mlx-minimax-music3==0.0.1a0",
        "h3": "mlx-h3==0.0.1a3",
    }
    for name, top in tops.items():
        lock = REPO / "packaging" / f"requirements-{name}.txt"
        text = lock.read_text()
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        assert lines, f"{lock} is empty"
        for line in lines:
            assert re.fullmatch(r"[A-Za-z0-9._\[\],-]+==[A-Za-z0-9.!+-]+", line), (
                f"{lock}: unpinned line {line!r}"
            )
        assert top in text, f"{lock} is missing top-level pin {top}"
        for banned in ("file://", "/Users/", "/opt/"):
            assert banned not in text, f"{lock} contains {banned!r}"
