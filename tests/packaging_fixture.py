"""Small helpers for packaging tests."""
from __future__ import annotations

import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
BUNDLE_ID = "com.aa.localmodeldesk"
PY_WRAPPER = '#!/bin/sh\nexec /usr/bin/python3 "$@"\n'


def render_info_plist(dest: Path, version: str = "0.0.1") -> None:
    """Render the packaging plist template with the requested version."""
    template = (REPO / "packaging" / "Info.plist.template").read_text()
    dest.write_text(template.replace("@VERSION@", version))


def make_fake_bundle(root: Path, *, sign: bool = True) -> Path:
    """Create a minimal signable application bundle below ``root``."""
    app = root / "LocalModelDesk.app"
    resources = app / "Contents" / "Resources"
    executable = app / "Contents" / "MacOS" / "LocalModelDesk"
    executable.parent.mkdir(parents=True)
    resources.mkdir(parents=True)
    render_info_plist(app / "Contents" / "Info.plist")

    source = root / "stub.c"
    source.write_text("int main(void){return 0;}\n")
    subprocess.run(["cc", "-x", "c", str(source), "-o", str(executable)], check=True)
    source.unlink()

    (resources / "bundle.json").write_text('{"app": "LocalModelDesk"}\n')
    python_bin = resources / "python" / "bin"
    python_bin.mkdir(parents=True)
    python = python_bin / "python3.13"
    python.write_text(PY_WRAPPER)
    python.chmod(0o755)

    if sign:
        subprocess.run([str(REPO / "scripts" / "sign-app.sh"), str(app), "--adhoc"], check=True)
    return app
