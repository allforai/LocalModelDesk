"""Acceptance check for image-session-backend, run against the current source.

1. The report claims passed with no gaps, and every evidence file it cites exists with exit 0.
2. The store is really wired: both composition roots hand library.image_sessions to MediaService,
   LibraryService builds the store and recovers on startup, the library routes list /api/image-sessions.
3. The node's own tests pass now (store, HTTP, media settle paths, production + harness wiring).
4. The real HTTP probe against launch_test_harness passes now (create → generate → restart → delete).
Run from the repo root: python3 .allforai/image-sessions/verify_backend.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / ".allforai/image-sessions/backend-report.json"


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        fail(f"report status is {report.get('status')!r}")
    for key in ("code_gaps", "test_gaps", "contract_gaps"):
        if report.get(key):
            fail(f"{key} not empty: {report[key]}")
    for item in report.get("evidence", []):
        record = json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
        if record.get("exit_code") != 0:
            fail(f"evidence {item['path']} exit {record.get('exit_code')}")

    wiring = {
        "desk/runtime.py": "image_sessions=library.image_sessions",
        "desk/testing/harness.py": "image_sessions=library.image_sessions",
        "desk/library/__init__.py": "self.image_sessions.recover_running()",
        "desk/library/http.py": '("GET", "/api/image-sessions", bind(handle_list_image_sessions))',
    }
    for path, needle in wiring.items():
        if needle not in (ROOT / path).read_text(encoding="utf-8"):
            fail(f"{path} lacks {needle}")
    for consumer in report.get("consumers", []):
        text = (ROOT / consumer["file"]).read_text(encoding="utf-8").splitlines()
        line = text[consumer["line"] - 1] if 0 < consumer["line"] <= len(text) else ""
        if consumer["contains"] not in line:
            fail(f"consumer {consumer['file']}:{consumer['line']} does not contain {consumer['contains']!r}")

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_image_sessions.py", "tests/test_image_sessions_wiring.py",
         "tests/test_library_http.py", "tests/test_media_image_service.py", "tests/test_media_service.py",
         "tests/test_foundation_paths.py", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    print(tests.stdout[-400:])
    if tests.returncode != 0:
        fail("node tests failed")

    probe = subprocess.run([sys.executable, ".allforai/image-sessions/probe_real_api.py"],
                           cwd=ROOT, capture_output=True, text=True)
    last = probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else ""
    print(last)
    if probe.returncode != 0 or '"result": "ok"' not in last:
        fail("real HTTP probe failed")
    print("OK")


if __name__ == "__main__":
    main()
