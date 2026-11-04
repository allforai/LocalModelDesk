#!/usr/bin/env python3
"""Mutation check for tests/e2e/test_image_sessions.py (image-session-verify, round 2).

Each mutation breaks one accepted behaviour in a working-tree file, runs the image-sessions e2e file
through capture_evidence, then restores the file byte-for-byte (verified). A mutation "is caught"
when the run exits non-zero. Product code is left exactly as found.
"""
import json, shutil, subprocess, sys, hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CE = "/Users/aa/.claude/plugins/marketplaces/myskills/claude/meta-skill/scripts/capture_evidence.py"
OUT = REPO / ".allforai/verify/evidence/mutation"
MUTATIONS = [
    ("m1-refine-drops-seed", "desk/static/js/panes/image.js",
     'els.seed.value = fields.seed == null ? "" : String(fields.seed);', 'els.seed.value = "";',
     "「在这张基础上改」 no longer carries the attempt's seed (AC-2 first half)"),
    ("m2-recompose-reuses-seed", "desk/static/js/pure/image_session.js",
     "let seed = draw();\n  while (seed === fields.seed) seed = draw();", "const seed = fields.seed ?? draw();",
     "「换个构图」 reuses the original seed (AC-2 second half)"),
    ("m3-delete-keeps-session", "desk/library/image_sessions.py",
     "            path.unlink()\n\n    def begin_attempt", "            pass\n\n    def begin_attempt",
     "deleting a session leaves it in the list (AC-5)"),
    ("m4-failure-reason-hidden", "desk/static/js/pure/image_session.js",
     'return { kind: "failed", badge: "失败", title, sub: "", icon: "x", tone: "danger" };',
     'return { kind: "failed", badge: "失败", title: "", sub: "", icon: "x", tone: "danger" };',
     "a failed attempt no longer shows its reason (AC-6)"),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


results = []
for name, rel, old, new, what in MUTATIONS:
    path = REPO / rel
    original = path.read_bytes()
    before = digest(path)
    text = original.decode()
    assert text.count(old) == 1, (name, "anchor not unique")
    try:
        path.write_text(text.replace(old, new), encoding="utf-8")
        evidence = OUT / f"{name}.json"
        subprocess.run([sys.executable, CE, str(evidence), "--", sys.executable, "-m", "pytest",
                        "tests/e2e/test_image_sessions.py", "-q", "-x", "--no-header"], cwd=REPO,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        record = json.loads(evidence.read_text())
    finally:
        path.write_bytes(original)
    restored = digest(path) == before
    failed = [line for line in record["stdout"].splitlines() if line.startswith("FAILED")]
    results.append({"mutation": name, "file": rel, "breaks": what, "exit_code": record["exit_code"],
                    "caught": record["exit_code"] != 0, "failed_tests": failed,
                    "evidence": str(evidence.relative_to(REPO)), "restored_byte_identical": restored})
    print(json.dumps(results[-1], ensure_ascii=False))
(OUT / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
sys.exit(0 if all(r["caught"] and r["restored_byte_identical"] for r in results) else 1)
