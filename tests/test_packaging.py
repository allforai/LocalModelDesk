"""Tests for the static packaging assets."""
from __future__ import annotations

import plistlib
import os
import re
import subprocess

from packaging_fixture import BUNDLE_ID, REPO, make_fake_bundle, render_info_plist


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


def test_sign_adhoc_fixture_verifies(tmp_path):
    app = make_fake_bundle(tmp_path)
    result = run(["codesign", "--verify", "--deep", "--strict", app])
    assert result.returncode == 0, result.stderr


def test_sign_no_identity_found_errors(tmp_path):
    app = make_fake_bundle(tmp_path, sign=False)
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    security = stub_bin / "security"
    security.write_text('#!/bin/sh\necho "     0 valid identities found"\n')
    security.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    env.pop("CODESIGN_IDENTITY", None)
    result = subprocess.run([str(REPO / "scripts" / "sign-app.sh"), str(app)],
                            capture_output=True, text=True, env=env)
    assert result.returncode != 0
    assert "找不到 Developer ID Application" in result.stderr
    assert "0 valid identities found" in result.stderr


def verify(app, source_root):
    return run([REPO / "scripts" / "verify-app.sh", app,
                "--source-root", source_root])


def test_verify_passes_clean_fixture(tmp_path):
    app = make_fake_bundle(tmp_path, sign=False)
    resources = app / "Contents" / "Resources"
    (resources / "AppIcon.icns").write_bytes(b"icns-stub")
    desk_init = resources / "desk" / "__init__.py"
    desk_init.parent.mkdir()
    desk_init.write_text("")
    for libdir, package in {
        "desk": "mlx_lm",
        "music": "mlx_minimax_music3",
        "h3": "mlx_h3",
    }.items():
        init = resources / "pylibs" / libdir / package / "__init__.py"
        init.parent.mkdir(parents=True)
        init.write_text("")
    cli = resources / "pylibs" / "h3" / "mlx_h3" / "cli.py"
    cli.write_text("def main():\n    pass\n")
    hf = resources / "pylibs" / "desk" / "huggingface_hub" / "cli" / "hf.py"
    hf.parent.mkdir(parents=True)
    (hf.parent / "__init__.py").write_text("")
    hf.write_text("def main():\n    pass\n")
    result = run([REPO / "scripts" / "sign-app.sh", app, "--adhoc"])
    assert result.returncode == 0, result.stderr

    source_root = tmp_path / "source"
    source_root.mkdir()
    result = verify(app, source_root)
    assert result.returncode == 0, result.stderr
    assert "verify-app: OK" in result.stdout

    (source_root / "run-h3.sh").write_text("#!/bin/sh\n")
    result = verify(app, source_root)
    assert result.returncode != 0
    assert "V7" in result.stderr


def test_verify_flags_homebrew_reference(tmp_path):
    app = make_fake_bundle(tmp_path)
    leak = app / "Contents" / "Resources" / "pylibs" / "desk" / "leak.txt"
    leak.parent.mkdir(parents=True)
    leak.write_text("interpreter = /opt/homebrew/bin/python3\n")
    result = verify(app, tmp_path / "source")
    assert result.returncode != 0
    assert "/opt/homebrew" in result.stderr
    assert "leak.txt" in result.stderr


def test_verify_flags_checkout_reference(tmp_path):
    app = make_fake_bundle(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    leak = app / "Contents" / "Resources" / "desk" / "leak2.txt"
    leak.parent.mkdir(parents=True)
    leak.write_text(f"path = {source_root}/desk\n")
    result = verify(app, source_root)
    assert result.returncode != 0
    assert "leak2.txt" in result.stderr


def test_verify_flags_pyvenv_and_bin(tmp_path):
    app = make_fake_bundle(tmp_path)
    pylibs = app / "Contents" / "Resources" / "pylibs" / "desk"
    pylibs.mkdir(parents=True)
    (pylibs / "pyvenv.cfg").write_text("home = /nowhere\n")
    bindir = pylibs / "bin"
    bindir.mkdir()
    (bindir / "hf").write_text("#!/nowhere/python\n")
    result = verify(app, tmp_path / "source")
    assert result.returncode != 0
    assert "pyvenv.cfg" in result.stderr
    assert "pylibs" in result.stderr
    assert "/bin" in result.stderr


def test_verify_reports_all_failures_at_once(tmp_path):
    app = make_fake_bundle(tmp_path)
    resources = app / "Contents" / "Resources"
    (resources / "desk").mkdir()
    (resources / "desk" / "leak.txt").write_text("/opt/homebrew\n")
    pylibs = resources / "pylibs" / "music"
    pylibs.mkdir(parents=True)
    (pylibs / "pyvenv.cfg").write_text("home = x\n")
    result = verify(app, tmp_path / "source")
    assert result.returncode != 0
    assert "leak.txt" in result.stderr
    assert "pyvenv.cfg" in result.stderr
