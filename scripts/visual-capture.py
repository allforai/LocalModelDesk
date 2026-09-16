#!/usr/bin/env python3
"""Capture one visual-acceptance case from the running app, with the values it was rendered at.

The app must have been started with LMD_PROBE_PORT set (see macos/VisualProbe.swift). For one case
this sets the window size, reads back what the app actually rendered, photographs the web view as
WebKit painted it — scrollbars included — and writes a capture record in the shape a screenshot
manifest wants. It never judges the picture: that is the reviewer's job.

Usage:
    scripts/visual-capture.py --port 8771 --out <evidence-dir> --case V-abc123 \
        --width 1280 --height 800 [--label chat-default] [--window-shot]

Writes <out>/<case>.png (the web view), optionally <out>/<case>-window.png (the whole window with
its title bar), and <out>/<case>.json (the capture record).
"""
import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import quote
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def probe(port, path, timeout=20, attempts=3):
    """One transient socket error must not cost a case: a lost capture reads as an untested state."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as response:
                return response.read()
        except (OSError, urllib.error.URLError) as exc:
            if attempt == attempts - 1:
                raise
            time.sleep(0.5 * (attempt + 1))


def build_id():
    """commit + a digest of everything uncommitted: two different dirty trees must not share a build."""
    def git(*args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout

    commit = git("rev-parse", "--short", "HEAD").strip() or "unknown"
    digest = hashlib.sha256(git("diff", "HEAD").encode("utf-8"))
    for name in sorted(git("ls-files", "--others", "--exclude-standard").split("\n")):
        if not name:
            continue
        path = REPO / name
        if path.is_file():
            digest.update(name.encode("utf-8"))
            digest.update(path.read_bytes())
    return f"{commit}+{digest.hexdigest()[:12]}"


AXES = ("state", "device", "os", "appearance", "dynamic_type", "locale", "orientation", "pointer")


def capture(port, out_dir, case_id, width, height, label=None, window_shot=False, before=None,
            case=None, bindings=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    window = json.loads(probe(port, f"/window?width={width}&height={height}"))
    setup = None
    if before:
        # The state this case names often sits behind a click; run it after the resize so the page
        # settles at the case's own width, and record what was run beside the picture.
        setup = {"js": before, "result": json.loads(probe(port, "/eval?js=" + quote(before, safe="")))}
        time.sleep(0.3)
    time.sleep(0.2)                                  # let the page settle after the resize
    readback = json.loads(probe(port, "/readback"))

    images, digests = [], {}
    png = probe(port, "/snapshot")
    view_shot = out_dir / f"{case_id}.png"
    view_shot.write_bytes(png)
    images.append(view_shot.name)
    digests[view_shot.name] = hashlib.sha256(png).hexdigest()

    if window_shot:
        # The native shell's own chrome (title bar, traffic lights) is outside the web view.
        shot = out_dir / f"{case_id}-window.png"
        subprocess.run(["screencapture", "-x", "-o", f"-l{window['window_number']}", str(shot)], check=True)
        images.append(shot.name)
        digests[shot.name] = hashlib.sha256(shot.read_bytes()).hexdigest()

    profile = readback.get("scroll_profile") or {}
    record = {
        # The axes come from the frozen matrix row, not from this script's idea of them: a capture that
        # cannot say which case it is cannot be bound to a verdict.
        **{a: case[a] for a in AXES if case and a in case},
        **(bindings or {}),
        "case_id": case_id,
        "label": label or case_id,
        "build": build_id(),
        "captured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "capture_mode": "viewport",
        "headless": False,
        # What the app drew, not what was asked for: a gutter means WebKit reserved space for the bar.
        "scrollbars": "native" if profile.get("gutter_px", 0) > 0 else "overlay",
        "scroll_profile": profile,
        "capture_tool": "LocalModelDesk visual probe (WKWebView takeSnapshot)",
        "setup": setup,
        "window": window,
        "readback": readback,
        "images": images,
        "image_digests": digests,
    }
    (out_dir / f"{case_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, required=True, help="LMD_PROBE_PORT of the running app")
    parser.add_argument("--out", required=True, help="evidence directory for this question")
    parser.add_argument("--case", required=True, help="case id from the frozen matrix")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--label", help="human-readable name for the shot")
    parser.add_argument("--window-shot", action="store_true",
                        help="also capture the whole window (native chrome) with screencapture")
    parser.add_argument("--before", help="JS run in the page after the resize, to reach this case's state")
    args = parser.parse_args()
    record = capture(args.port, args.out, args.case, args.width, args.height,
                     label=args.label, window_shot=args.window_shot, before=args.before)
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
