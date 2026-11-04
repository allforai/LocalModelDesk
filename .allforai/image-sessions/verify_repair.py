"""Acceptance check for image-session-repair (round 2), run against the current source.

1. repair-report.json is well-formed: every fixed gap names files that exist, tests that exist
   (the test function or node test title is present in the named file), red evidence files that
   exist, an evidence record with exit 0 and screenshots whose DOM checks are clean; every unfixed
   gap and follow-up carries a reason/owner; the blocking B-01 is among the fixed gaps.
2. The fixes are really in the product source: round 1 (the pane refits and re-pins the expanded
   card, the cancelled card carries its explanation, the harness writes PNGs at the declared size)
   and round 2 (B-01: no header thumbnail on the expanded card, image floor, header-scrolls-first
   reveal; N-02/N-03 list CSS).
3. node --test tests/js/*.test.js passes now.
4. The image-page e2e (tests/e2e/test_image_sessions.py + tests/e2e/test_image_flow.py, real
   Chromium via launch_test_harness with the scripted media executor) passes now.
Run from the repo root: python3 .allforai/image-sessions/verify_repair.py
"""
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / ".allforai/image-sessions/repair-report.json"


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def test_exists(ref):
    path, _, name = ref.partition("::")
    name = re.split(r" \(", name, maxsplit=1)[0].strip()
    text = (ROOT / path).read_text(encoding="utf-8")
    if path.endswith(".py"):
        return f"def {name}(" in text
    return f'test("{name}' in text


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("node_id") != "image-session-repair":
        fail("report node_id")
    if report.get("code_gaps") or report.get("test_gaps"):
        fail("report still lists open code_gaps/test_gaps")
    open_contract = {g["id"] for g in report.get("contract_gaps", [])}
    if report.get("status") == "passed" and open_contract:
        fail("status passed while contract gaps are open")
    if report.get("status") == "blocked" and not open_contract:
        fail("status blocked without an open contract gap")
    for gap in report.get("contract_gaps", []):
        if gap.get("kind") != "unspecified_user_visible_decision" or not gap.get("repair_owner"):
            fail(f"contract gap {gap.get('id')} lacks kind/repair_owner")
    for item in report.get("follow_ups", []):
        if item.get("blocking") or not item.get("repair_owner") or not item.get("detail"):
            fail(f"follow-up {item.get('id')} must be non-blocking with an owner and detail")
    # The fix log lives in fixes_applied (renamed from gaps, 2026-09-24); gaps must stay empty.
    fixes = report.get("fixes_applied", [])
    if report.get("gaps"):
        fail("report still lists open gaps")
    if "B-01" not in {g["gap"] for g in fixes}:
        fail("blocking gap B-01 is not among the fixed gaps")
    for gap in fixes:
        for f in gap.get("files", []):
            if not (ROOT / f).is_file():
                fail(f"{gap['gap']}: file {f} missing")
        if not gap.get("test"):
            fail(f"{gap['gap']}: no test")
        for ref in gap["test"]:
            if not test_exists(ref):
                fail(f"{gap['gap']}: test {ref} not found")
        for red in gap.get("red_evidence", []):
            if not (ROOT / red).is_file():
                fail(f"{gap['gap']}: red evidence {red} missing")
        record = json.loads((ROOT / gap["evidence_path"]).read_text(encoding="utf-8"))
        if record.get("exit_code") != 0:
            fail(f"{gap['gap']}: evidence {gap['evidence_path']} exit {record.get('exit_code')}")
        for shot in gap.get("screenshots", []):
            png = ROOT / shot
            checks = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))["dom_checks"]
            if not png.is_file() or checks["blank_images"] or checks["horizontal_scroll"] or checks["clipped_buttons"] \
                    or checks["overlaps"] or checks["seed_word_in_main_flow"]:
                fail(f"{gap['gap']}: screenshot {shot} missing or fails its DOM checks")
    for item in report.get("not_fixed", []):
        if not item.get("reason"):
            fail(f"unfixed {item.get('gap')} has no reason")

    pane = (ROOT / "desk/static/js/panes/image.js").read_text(encoding="utf-8")
    for needle in ("function fitExpandedImage()", "function revealExpanded()", "ResizeObserver(settleSoon)",
                   "onImageLoad: settleView", 'scrollIntent = "selected"', "keep-together"):
        if needle not in pane:
            fail(f"panes/image.js lacks {needle!r}")
    pure = (ROOT / "desk/static/js/pure/image_session.js").read_text(encoding="utf-8")
    if "sub: said" not in pure:
        fail("cancelled attempt explanation not wired in attemptView")
    for needle in ("const IMAGE_FLOOR = 192;", "Math.max(IMAGE_FLOOR, Math.floor(room))",
                   "card.height <= timelineInner() || !image ? card.top : image.top"):
        if needle not in pane:
            fail(f"panes/image.js lacks {needle!r} (B-01)")
    card = (ROOT / "desk/static/js/widgets/image_session_card.js").read_text(encoding="utf-8")
    if 'view.kind === "done" && !expanded' not in card:
        fail("expanded card still renders the header thumbnail (B-01)")
    css = (ROOT / "desk/static/app.css").read_text(encoding="utf-8")
    for needle in (".attempt-done[aria-expanded=true] .attempt-prompt{display:none}", ".attempt-action-hint:empty{display:none}",
                   "#pane-image .sessions ul{margin-top:12px}", ".image-session .session-actions{display:none}"):
        if needle not in css:
            fail(f"app.css lacks {needle!r}")
    fakes = (ROOT / "desk/testing/fakes.py").read_text(encoding="utf-8")
    if "_declared_png(argv)" not in fakes:
        fail("scripted executor does not write PNGs at the declared size")

    tests = sorted(glob.glob(str(ROOT / "tests/js/*.test.js")))
    node = subprocess.run(["node", "--test", *tests], cwd=ROOT, capture_output=True, text=True)
    print(node.stdout[-200:])
    if node.returncode != 0:
        fail("node --test failed")
    e2e = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "tests/e2e/test_image_sessions.py", "tests/e2e/test_image_flow.py",
         "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    print(e2e.stdout[-300:])
    if e2e.returncode != 0:
        fail("image page e2e failed")
    print("OK")


if __name__ == "__main__":
    main()
