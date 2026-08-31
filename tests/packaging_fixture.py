"""Small helpers for packaging tests."""
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
BUNDLE_ID = "com.aa.localmodeldesk"
PY_WRAPPER = '#!/bin/sh\nexec /usr/bin/python3 "$@"\n'


def render_info_plist(dest: Path, version: str = "0.0.1") -> None:
    """Render the packaging plist template with the requested version."""
    template = (REPO / "packaging" / "Info.plist.template").read_text()
    dest.write_text(template.replace("@VERSION@", version))
