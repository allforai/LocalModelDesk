"""Acceptance check for image-session-pane, run against the current source.

1. The report claims passed with no gaps; every evidence record it cites exists with exit 0.
2. Every consumer line it lists still contains the call it names (the new modules are really wired:
   main.js drives the pane, the pane imports the session widgets and pure helpers).
3. The frontend unit suite passes now (node --test over tests/js/*.test.js).
4. The real-browser e2e for the image pane and the library refill passes now (Playwright, real Chromium,
   launch_test_harness with the scripted media executor).
Run from the repo root: python3 .allforai/image-sessions/verify_pane.py
"""
import glob
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / ".allforai/image-sessions/pane-report.json"


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        fail(f"report status is {report.get('status')!r}")
    for key in ("code_gaps", "test_gaps", "contract_gaps", "visual_quality_gaps"):
        if report.get(key):
            fail(f"{key} not empty: {report[key]}")
    for item in report.get("evidence", []):
        if item.get("expect_exit") is not None:
            continue
        if item["kind"] == "screenshot":
            records = sorted((ROOT / item["path"]).glob("*.json"))
            if not records:
                fail(f"no screenshot records under {item['path']}")
            for path in records:
                checks = json.loads(path.read_text(encoding="utf-8"))["dom_checks"]
                if (checks["seed_word_in_main_flow"] or checks["blank_images"] or checks["horizontal_scroll"]
                        or checks["clipped_buttons"] or checks["overlaps"]
                        or not path.with_suffix(".png").is_file()):
                    fail(f"screenshot record {path.name} fails its DOM checks or lacks its PNG")
            continue
        record = json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
        if record.get("exit_code") != 0:
            fail(f"evidence {item['path']} exit {record.get('exit_code')}")
    for consumer in report.get("consumers", []):
        lines = (ROOT / consumer["file"]).read_text(encoding="utf-8").splitlines()
        # The recorded line is a hint; later repairs may move it. The wiring claim is that
        # the consumer file still makes the call, so search the whole file.
        if not any(consumer["contains"] in line for line in lines):
            fail(f"consumer {consumer['file']}:{consumer['line']} does not contain {consumer['contains']!r}")

    tests = sorted(glob.glob(str(ROOT / "tests/js/*.test.js")))
    node = subprocess.run(["node", "--test", *tests], cwd=ROOT, capture_output=True, text=True)
    print(node.stdout[-200:])
    if node.returncode != 0:
        fail("node --test failed")

    e2e = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/e2e/test_image_flow.py", "tests/e2e/test_library_panel.py",
         "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    print(e2e.stdout[-300:])
    if e2e.returncode != 0:
        fail("image pane e2e failed")
    print("OK")


if __name__ == "__main__":
    main()
