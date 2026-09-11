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
    # Test fixtures are always adhoc-signed (no Developer ID available in CI/dev);
    # tell verify-app.sh that is expected so its Gatekeeper check doesn't fail these.
    env = dict(os.environ, LMD_ALLOW_ADHOC="1")
    return subprocess.run([str(value) for value in command], capture_output=True, text=True, env=env)


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


LEGACY_PATHS = ("initModels.sh", "run-h3.sh", "run-music3.py", "unload-llm.sh", "media-gui")


def test_no_legacy_scripts_in_repo():
    for relative in LEGACY_PATHS:
        assert not (REPO / relative).exists(), f"遗留原型仍在仓库：{relative}"


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


def test_build_verify_does_not_write_bytecode_after_signing():
    build = (REPO / "scripts" / "build-app.sh").read_text()
    verifier = (REPO / "scripts" / "verify-app.sh").read_text()
    verify = 'PYTHONDONTWRITEBYTECODE=1 "$REPO/scripts/verify-app.sh"'
    assert verify in build
    assert 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$1"' in verifier


def test_build_relocates_and_sanitizes_embedded_cpython_before_signing():
    build = (REPO / "scripts" / "build-app.sh").read_text()
    sign = (REPO / "scripts" / "sign-app.sh").read_text()
    dependencies_at = build.index('echo "==> [4/9] Install dependency libraries"')
    sanitize_at = build.index("sanitize_host_paths")
    sign_at = build.index('echo "==> [8/9] Sign"')

    assert "MEGASTORM_EMBEDDED_PYTHON" in build
    assert "-name '*.pyc' -delete" in build
    assert "-name __pycache__" in build
    assert 'install_name_tool -id "@rpath/libpython3.13.dylib"' in build
    assert '"$SRC_PY" "$REPO" /opt/homebrew' in build
    assert "grep -r -I -l --null -F --" in build
    assert "grep -Z" not in build
    assert dependencies_at < sanitize_at < sign_at
    assert "MEGASTORM_OFFLINE_CODESIGN" in sign
    assert "--timestamp=none" in sign


def test_build_sanitizer_uses_single_perl_quote_meta_escapes():
    build = (REPO / "scripts" / "build-app.sh").read_text()
    assert r"perl -pi -e 's/\Q$ENV{FORBIDDEN}\E//g'" in build
    assert r"perl -pi -e 's/\\Q$ENV{FORBIDDEN}\\E//g'" not in build


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


def test_build_precompiles_desk_bytecode_before_signing():
    build = (REPO / "scripts" / "build-app.sh").read_text()
    precompile_at = build.index("compileall -q -f")
    sign_at = build.index('SIGN=("$REPO/scripts/sign-app.sh"')
    assert "compileall -q -f \"$RES/desk\"" in build
    assert precompile_at < sign_at


def test_verify_flags_a_broken_seal(tmp_path):
    """包内多出 .pyc 就等于封条破了，verify 必须报出来而不是让 codesign 裸奔（V8）。"""
    app = make_fake_bundle(tmp_path)
    intruder = app / "Contents" / "Resources" / "desk" / "__pycache__"
    intruder.mkdir(parents=True)
    (intruder / "app.cpython-313.pyc").write_bytes(b"\x00")

    result = verify(app, tmp_path / "source")
    assert result.returncode != 0
    assert "封条" in result.stdout + result.stderr


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


def test_build_failure_leaves_no_half_product(tmp_path):
    output = tmp_path / "dist"
    output.mkdir()
    existing = output / "LocalModelDesk.app"
    existing.mkdir()
    marker = existing / "marker.txt"
    marker.write_text("intact prior product")

    result = run([
        REPO / "scripts" / "build-app.sh",
        "--output", output,
        "--adhoc",
        "--python-version", "cpython-0.0.0-bogus",
    ])

    assert result.returncode != 0
    assert marker.read_text() == "intact prior product"
    assert [path.name for path in output.iterdir() if path.name.startswith(".staging")] == []


def test_install_to_tmp_dest(tmp_path):
    app = make_fake_bundle(tmp_path, sign=False)
    resources = app / "Contents" / "Resources"
    (resources / "AppIcon.icns").write_bytes(b"icns-stub")
    (resources / "desk").mkdir()
    for libdir, package in {
        "desk": "mlx_lm",
        "music": "mlx_minimax_music3",
        "h3": "mlx_h3",
    }.items():
        init = resources / "pylibs" / libdir / package / "__init__.py"
        init.parent.mkdir(parents=True)
        init.write_text("")
    (resources / "pylibs" / "h3" / "mlx_h3" / "cli.py").write_text("")
    hf = resources / "pylibs" / "desk" / "huggingface_hub" / "cli" / "hf.py"
    hf.parent.mkdir(parents=True)
    (hf.parent / "__init__.py").write_text("")
    hf.write_text("def main():\n    pass\n")
    assert run([REPO / "scripts" / "sign-app.sh", app, "--adhoc"]).returncode == 0

    source_root = tmp_path / "source"
    source_root.mkdir()
    dest = tmp_path / "FakeApplications"
    dest.mkdir()
    result = run([REPO / "scripts" / "install-app.sh", "--app", app,
                  "--dest", dest, "--source-root", source_root])
    assert result.returncode == 0, result.stderr
    installed = dest / "LocalModelDesk.app"
    assert (installed / "Contents" / "MacOS" / "LocalModelDesk").exists()
    assert (installed / "Contents" / "Resources" / "bundle.json").exists()

    other_dest = tmp_path / "OtherApplications"
    other = other_dest / "LocalModelDesk.app" / "Contents"
    other.mkdir(parents=True)
    other_plist = other / "Info.plist"
    other_plist.write_bytes((app / "Contents" / "Info.plist").read_bytes().replace(
        BUNDLE_ID.encode(), b"com.other.thing"))
    refused = run([REPO / "scripts" / "install-app.sh", "--app", app,
                   "--dest", other_dest, "--source-root", source_root])
    assert refused.returncode != 0
    assert other_plist.exists()

    repeated = run([REPO / "scripts" / "install-app.sh", "--app", app,
                    "--dest", dest, "--source-root", source_root])
    assert repeated.returncode == 0, repeated.stderr


def test_install_help_exits_zero():
    out = run([REPO / "scripts" / "install-app.sh", "--help"])
    assert out.returncode == 0
    assert "--dest" in out.stdout


def test_install_names_the_missing_dest(tmp_path):
    missing = tmp_path / "nope"
    out = run([REPO / "scripts" / "install-app.sh", "--dest", missing])
    assert out.returncode == 2
    assert "目标目录不存在" in out.stderr
    assert str(missing) in out.stderr


def uninstall(app, launch_agents, data_root, env, *extra):
    return subprocess.run([
        str(REPO / "scripts" / "uninstall-app.sh"),
        "--app-path", app,
        "--launch-agents-dir", launch_agents,
        "--data-root", data_root,
        *extra,
    ], capture_output=True, text=True, env=env)


def uninstall_layout(tmp_path, bundle_id=BUNDLE_ID):
    apps = tmp_path / "Applications"
    apps.mkdir()
    app = make_fake_bundle(apps, sign=False)
    plist = app / "Contents" / "Info.plist"
    plist.write_bytes(plist.read_bytes().replace(BUNDLE_ID.encode(), bundle_id.encode()))
    launch_agents = tmp_path / "LaunchAgents"
    launch_agents.mkdir()
    (launch_agents / f"{BUNDLE_ID}.plist").write_text("<plist/>")
    data = tmp_path / "data"
    (data / "models").mkdir(parents=True)
    (data / "models" / "weights.bin").write_bytes(b"weights")
    (data / "sessions").mkdir()
    (data / "sessions" / "session.json").write_text("{}")
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = stub_bin / "launchctl"
    launchctl.write_text(f'#!/bin/sh\necho "$@" >> "{launchctl_log}"\n')
    launchctl.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    return app, launch_agents, data, env, launchctl_log


def test_uninstall_removes_app_and_plist(tmp_path):
    app, launch_agents, data, env, launchctl_log = uninstall_layout(tmp_path)
    result = uninstall(app, launch_agents, data, env)
    assert result.returncode == 0, result.stderr
    assert not app.exists()
    assert not (launch_agents / f"{BUNDLE_ID}.plist").exists()
    assert "bootout" in launchctl_log.read_text()


def test_uninstall_keeps_data_by_default(tmp_path):
    app, launch_agents, data, env, _ = uninstall_layout(tmp_path)
    result = uninstall(app, launch_agents, data, env)
    assert result.returncode == 0, result.stderr
    assert (data / "models" / "weights.bin").read_bytes() == b"weights"
    assert (data / "sessions" / "session.json").read_text() == "{}"


def test_uninstall_dry_run_touches_nothing(tmp_path):
    app, launch_agents, data, env, launchctl_log = uninstall_layout(tmp_path)
    result = uninstall(app, launch_agents, data, env, "--purge-data", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "[dry-run]" in result.stdout
    assert app.exists()
    assert (launch_agents / f"{BUNDLE_ID}.plist").exists()
    assert (data / "models" / "weights.bin").exists()
    assert not launchctl_log.exists()


def test_uninstall_wrong_bundle_id_refuses(tmp_path):
    app, launch_agents, data, env, _ = uninstall_layout(tmp_path, "com.other.app")
    result = uninstall(app, launch_agents, data, env)
    assert result.returncode != 0
    assert app.exists()


def test_uninstall_purge_never_touches_models(tmp_path):
    app, launch_agents, data, env, _ = uninstall_layout(tmp_path)
    nested_models = data / "sessions" / "configured-models"
    nested_models.mkdir()
    (nested_models / "weights.bin").write_bytes(b"configured weights")
    (data / "config.json").write_text(
        '{"models_root": ' + repr(str(nested_models)).replace("'", '"') + "}"
    )
    result = uninstall(app, launch_agents, data, env, "--purge-data")
    assert result.returncode == 0, result.stderr
    assert (data / "models" / "weights.bin").read_bytes() == b"weights"
    assert (nested_models / "weights.bin").read_bytes() == b"configured weights"


def test_uninstall_purge_refuses_on_corrupt_config(tmp_path):
    app, launch_agents, data, env, _ = uninstall_layout(tmp_path)
    (data / "config.json").write_text("{not valid json")
    result = uninstall(app, launch_agents, data, env, "--purge-data")
    assert result.returncode != 0
    assert (data / "models" / "weights.bin").exists()
    assert (data / "sessions" / "session.json").exists()

    # A dangling config symlink is unreadable config, rather than absent config.
    (data / "config.json").unlink()
    (data / "config.json").symlink_to(data / "missing-config.json")
    result = uninstall(app, launch_agents, data, env, "--purge-data")
    assert result.returncode != 0
    assert (data / "models" / "weights.bin").exists()
    assert (data / "sessions" / "session.json").exists()


def test_build_refuses_silent_adhoc_and_verify_checks_gatekeeper():
    build = (REPO / "scripts" / "build-app.sh").read_text(encoding="utf-8")
    verify = (REPO / "scripts" / "verify-app.sh").read_text(encoding="utf-8")
    assert "LMD_ALLOW_ADHOC" in build and "--adhoc" in build
    assert "spctl --assess --type execute" in verify and "LMD_ALLOW_ADHOC" in verify


def test_readme_states_real_behavior():
    text = (REPO / "README.md").read_text()
    for statement in (
        "安装后不会自动启动",
        "菜单栏",
        "选择模型目录",
        "收编已有模型目录",
        "0.0.0.0:8770",
        "无鉴权",
    ):
        assert statement in text
