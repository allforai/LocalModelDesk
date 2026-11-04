#!/usr/bin/env python3
"""Real-model acceptance journey for image sessions (image-session-verify).

Drives an isolated copy of the packaged app (built with scripts/build-app.sh into a scratch
directory, its own data root and ports) with the real Qwen-Image model through its visual probe:
UI actions run as DOM clicks inside the app's own WKWebView (/eval), outcomes are read from the
app's HTTP API, screenshots come from scripts/visual-capture.py. Only the pids this script started
are ever signalled; the user's dist/ instance is never addressed.

Usage: real_journey.py --app <LocalModelDesk.app> --data <data-root> --out <evidence-dir>
Writes <out>/journey.json (every step with timestamps, pids, API readbacks) and screenshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("visual_capture", REPO / "scripts" / "visual-capture.py")
visual_capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(visual_capture)

DESK_PORT = 8791
PROBE_PORT = 8792
GATEWAY_PORT = 8793
MODELS_ROOT = REPO  # image-models/qwen-image-2.1-heretic lives here
SIZES = {"wide": (1280, 800), "narrow": (900, 700)}
LOG: list[dict] = []


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def note(step, **data):
    entry = {"at": now(), "step": step, **data}
    LOG.append(entry)
    print(json.dumps(entry, ensure_ascii=False)[:400], flush=True)
    return entry


def http(method, path, body=None, *, port=DESK_PORT, timeout=30):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        kind = response.headers.get("Content-Type", "")
        return response.status, (json.loads(raw) if "json" in kind else raw)


def api(path):
    return http("GET", path)[1]


def js(expr):
    """Run JS inside the app's WKWebView. The expression must evaluate to something JSON-able."""
    raw = visual_capture.probe(PROBE_PORT, "/eval?js=" + quote(expr, safe=""), timeout=20)
    return json.loads(raw)["value"]  # the probe answers {"value": <result>}


def wait(predicate, timeout, interval=1.0, what=""):
    deadline, last = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        try:
            last = predicate()
        except (OSError, urllib.error.URLError, ValueError) as exc:
            last = f"error: {exc}"
        if last and not (isinstance(last, str) and last.startswith("error:")):
            return last
        time.sleep(interval)
    raise TimeoutError(f"{what} not met within {timeout}s (last={last!r})")


def write_config(data_root: Path):
    data_root.mkdir(parents=True, exist_ok=True)
    config = {
        "config_version": 1, "first_run_done": True, "models_root": str(MODELS_ROOT),
        "outputs_root": str(data_root / "outputs"),
        "gateway": {"enabled": False, "host": "127.0.0.1", "port": GATEWAY_PORT},
    }
    path = data_root / "config.json"
    if not path.exists():
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def server_pids(app: Path):
    """The bundle's own server processes; macOS may report /private/tmp paths as /tmp."""
    python = str(app.resolve() / "Contents" / "Resources" / "python" / "bin" / "python3.13")
    forms = {python, python.replace("/private/tmp/", "/tmp/", 1)}
    out = subprocess.run(["ps", "-ww", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout
    return [int(line.split()[0]) for line in out.splitlines()
            if any(form in line for form in forms) and "-m desk" in line]


def image_cli_pids(app: Path):
    """image_cli.py children started by this bundle's server (never the user's dist/ instance)."""
    bundle = str(app.resolve())
    forms = {bundle, bundle.replace("/private/tmp/", "/tmp/", 1)}
    out = subprocess.run(["ps", "-ww", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout
    return [int(line.split()[0]) for line in out.splitlines()
            if "image_cli.py" in line and any(form in line for form in forms)]


def activate(pid):
    script = ("ObjC.import('AppKit');"
              f"var a=$.NSRunningApplication.runningApplicationWithProcessIdentifier({pid});"
              "a.activateWithOptions($.NSApplicationActivateIgnoringOtherApps); a.isActive;")
    subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True, text=True)


RUNNING: list = []  # shells this script started, so a failed launch is still stopped


def launch(app: Path, data_root: Path, log_dir: Path):
    env = {**os.environ, "LOCALMODELDESK_DATA_ROOT": str(data_root), "LMD_SHELL_PORT": str(DESK_PORT),
           "LMD_PROBE_PORT": str(PROBE_PORT)}
    log = open(log_dir / f"shell-{int(time.time())}.log", "w")
    shell = subprocess.Popen([str(app / "Contents" / "MacOS" / "LocalModelDesk")], env=env,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    RUNNING.append(shell)
    wait(lambda: api("/api/state"), 120, what="desk /api/state")
    servers = wait(lambda: server_pids(app), 30, what="server pid")
    for _ in range(20):
        activate(shell.pid)
        try:
            visual_capture.probe(PROBE_PORT, "/readback", timeout=5, attempts=1)
            break
        except Exception:
            time.sleep(1)
    note("launched", shell_pid=shell.pid, server_pids=servers, data_root=str(data_root),
         desk_port=DESK_PORT, probe_port=PROBE_PORT)
    return shell, servers


def stop(shell, app: Path):
    servers = server_pids(app)
    shell.send_signal(signal.SIGTERM)
    try:
        shell.wait(timeout=60)
    except subprocess.TimeoutExpired:
        shell.kill()
        shell.wait(timeout=10)
    wait(lambda: not server_pids(app) or None, 60, what="server exit")
    note("stopped", shell_pid=shell.pid, shell_returncode=shell.returncode, server_pids_before=servers,
         server_pids_after=server_pids(app))


def open_image_tab():
    js("(location.hash='#tab=image', true)")
    wait(lambda: js("!!document.querySelector(\"#pane-image [data-image-session-list] li[aria-current='true']\")"),
         60, 0.5, "current session")
    wait(lambda: js("!document.querySelector('#pane-image [data-image-start]').disabled || "
                    "document.querySelector('#pane-image [data-image-hint-text]').textContent"), 60, 0.5, "start ready")


def current_session_id():
    return js("document.querySelector(\"#pane-image li[aria-current='true']\").dataset.sessionId")


def set_field(selector, value):
    return js(f"""(() => {{ const el = document.querySelector('#pane-image {selector}');
        el.value = {json.dumps(str(value))}; el.dispatchEvent(new Event('input', {{bubbles: true}}));
        el.dispatchEvent(new Event('change', {{bubbles: true}})); return el.value; }})()""")


def click(selector):
    return js(f"""(() => {{ const el = document.querySelector({json.dumps(selector)});
        if (!el) return 'missing'; el.click(); return 'clicked'; }})()""")


def start_generation():
    ok = wait(lambda: js("!document.querySelector('#pane-image [data-image-start]').disabled"), 120, 1, "start enabled")
    assert ok
    return click("#pane-image [data-image-start]")


def wait_settled(session_id, count, timeout=1800):
    def settled():
        session = api(f"/api/image-sessions/{session_id}")
        attempts = session["attempts"]
        if len(attempts) >= count and attempts[count - 1]["status"] != "running":
            return session
        return None
    return wait(settled, timeout, 3, f"attempt {count} settled")


def click_card(index, inner=None):
    """Click the index-th (1-based) attempt card, or a control inside it."""
    return js(f"""(() => {{ const c = document.querySelectorAll('#pane-image [data-image-timeline] .attempt')[{index - 1}];
        if (!c) return 'missing'; const t = {json.dumps(inner)} ? c.querySelector({json.dumps(inner or '')}) : c;
        if (!t) return 'missing-inner'; t.click(); return 'clicked'; }})()""")


def card_js(index):
    return f"document.querySelectorAll('#pane-image [data-image-timeline] .attempt')[{index - 1}]"


def ui_timeline():
    return js("""[...document.querySelectorAll('#pane-image [data-image-timeline] .attempt')].map((c) => ({
        id: c.dataset.attemptId, status: c.dataset.attemptStatus, expanded: c.getAttribute('aria-expanded'),
        label: c.querySelector('.attempt-label')?.textContent, prompt: c.querySelector('.attempt-prompt')?.textContent,
        spec: c.querySelector('.attempt-spec')?.textContent, reason: c.querySelector('.attempt-reason')?.textContent ?? null,
        reason_sub: c.querySelector('.attempt-reason-sub')?.textContent ?? null,
        header_thumb: !!c.querySelector('.attempt-thumb img'),
        big_img_h: c.querySelector('img.attempt-image') ? Math.round(c.querySelector('img.attempt-image').getBoundingClientRect().height) : null,
        badge: c.querySelector('.attempt-badge')?.textContent ?? null, imgs: c.querySelectorAll('img').length,
        thumb_ok: [...c.querySelectorAll('img')].every((i) => i.complete && i.naturalWidth > 0)}))""")


def shoot(out: Path, state: str, before: str | None = None, build=None):
    records = []
    for name, (width, height) in SIZES.items():
        record = visual_capture.capture(PROBE_PORT, out, f"real-{state}-{name}", width, height,
                                        label=f"{state} ({name}, real app + real model)", before=before,
                                        build=build)
        records.append({"state": state, "viewport": name, "png": str(out / f"real-{state}-{name}.png"),
                        "readback_width": record["readback"].get("width") or record["readback"].get("innerWidth")})
    note("screenshot", state=state, files=[r["png"] for r in records])
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()
    app, data_root, out = Path(args.app), Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_config(data_root)
    build = visual_capture.build_id()
    result = {"app": str(app), "data_root": str(data_root), "build": build,
              "model": str(MODELS_ROOT / "image-models" / "qwen-image-2.1-heretic"),
              "params": {"width": args.size, "height": args.size, "steps": args.steps}}
    shots = []
    shell = None
    try:
        shell, _ = launch(app, data_root, out)
        result["capabilities"] = api("/api/capabilities")
        open_image_tab()
        session_a = current_session_id()
        note("session", session_a=session_a)

        # Small size and few steps keep a real Qwen-Image run short; the refine must carry them.
        js("document.querySelector('#pane-image details[data-image-advanced]').open = true")
        for key, value in (("width", args.size), ("height", args.size), ("steps", args.steps)):
            set_field(f"[data-image-{key}]", value)
        js("document.querySelector('#pane-image details[data-image-advanced]').open = false")

        prompts = ["一座海边灯塔，黄昏，水彩画风", "一座海边灯塔，黄昏，水彩画风，天空有飞鸟",
                   "一座海边灯塔，黄昏，水彩画风，天空有飞鸟，远处有帆船"]
        set_field("[data-image-prompt]", prompts[0])
        start_generation()
        wait(lambda: js("!!document.querySelector(\"#pane-image .attempt[data-attempt-status='running']\")"), 60, 0.5,
             "running card")
        time.sleep(4)
        shots += shoot(out, "running", build=build)
        session = wait_settled(session_a, 1)
        note("round-1", attempt=session["attempts"][0])

        for round_index in (1, 2):
            # The API settles before the pane's 2 s poll re-renders the card; wait for the UI too.
            wait(lambda: js(f"(() => {{ const c = {card_js(round_index)}; return !!c && c.dataset.attemptStatus !== 'running'; }})()"),
                 30, 0.5, f"card {round_index} settled in the UI")
            click_card(round_index)
            wait(lambda: js(f"!!{card_js(round_index)}?.querySelector('[data-attempt-refine]')"), 15, 0.3,
                 f"card {round_index} actions")
            assert click_card(round_index, "[data-attempt-refine]") == "clicked"
            prefilled = wait(lambda: js("document.querySelector('#pane-image [data-image-prompt]').value"), 10, 0.3)
            chip = js("document.querySelector('#pane-image [data-image-refine-text]')?.textContent")
            seed_box = js("document.querySelector('#pane-image [data-image-seed]').value")
            note(f"refine-from-{round_index}", prefilled_prompt=prefilled, chip=chip, seed_box=seed_box)
            if round_index == 2:
                shots += shoot(out, "refine-prefill", build=build)
            set_field("[data-image-prompt]", prompts[round_index])
            start_generation()
            session = wait_settled(session_a, round_index + 1)
            note(f"round-{round_index + 1}", attempt=session["attempts"][round_index])

        attempts = session["attempts"]
        wait(lambda: js(f"(() => {{ const c = {card_js(3)}; return !!c && c.dataset.attemptStatus !== 'running'"
                        " && [...document.querySelectorAll('#pane-image img')].every((i) => i.complete); })()"),
             30, 0.5, "round 3 rendered")
        time.sleep(1)
        result["three_rounds"] = attempts
        result["ui_after_three_rounds"] = ui_timeline()
        shots += shoot(out, "timeline-three-rounds", build=build)
        # The same timeline scrolled to the top by the user: 第 1 次 → 第 3 次 in one frame (U-03).
        top_js = ("(() => { const t = document.querySelector('#pane-image [data-image-timeline]');"
                  " t.scrollTop = 0; t.dispatchEvent(new Event('scroll')); return true; })()")
        shots += shoot(out, "timeline-three-rounds-top", before=top_js, build=build)
        shots += shoot(out, "attempt-selected-actions",
                       before=f"({card_js(1)}.click(), true)", build=build)

        # 换个构图 on attempt 2.
        wait(lambda: js(f"(() => {{ const c = {card_js(3)}; return !!c && c.dataset.attemptStatus !== 'running'; }})()"),
             30, 0.5, "card 3 settled in the UI")
        click_card(2)
        wait(lambda: js(f"!!{card_js(2)}?.querySelector('[data-attempt-recompose]')"), 15, 0.3, "card 2 actions")
        assert click_card(2, "[data-attempt-recompose]") == "clicked"
        session = wait_settled(session_a, 4)
        result["recompose"] = session["attempts"][3]
        note("recompose", attempt=session["attempts"][3])

        # A real cancel: start, let the model start running, press 取消 on the running card.
        set_field("[data-image-prompt]", "会被取消的一张：雪山日出")
        start_generation()
        wait(lambda: js("!!document.querySelector(\"#pane-image .attempt[data-attempt-status='running'] [data-attempt-cancel]\")"),
             60, 0.5, "cancel button")
        time.sleep(8)
        click("#pane-image .attempt[data-attempt-status='running'] [data-attempt-cancel]")
        session = wait_settled(session_a, 5, timeout=300)
        result["cancelled"] = session["attempts"][4]
        note("cancelled", attempt=session["attempts"][4])
        time.sleep(3)
        shots += shoot(out, "attempt-cancelled", build=build)

        # A real failure: the real image_cli process dies mid-run (SIGKILL, as an OOM kill would).
        # Only the child of this script's own bundle is signalled; the product code is untouched.
        set_field("[data-image-prompt]", "会失败的一张：进程中途被杀掉")
        start_generation()
        wait(lambda: js("!!document.querySelector(\"#pane-image .attempt[data-attempt-status='running']\")"), 60, 0.5,
             "running card (failure)")
        victims = wait(lambda: image_cli_pids(app), 60, 0.5, "image_cli pid")
        time.sleep(6)
        for pid in victims:
            os.kill(pid, signal.SIGKILL)
        note("killed-image-cli", pids=victims)
        session = wait_settled(session_a, 6, timeout=300)
        result["failed"] = session["attempts"][5]
        result["failed_killed_pids"] = victims
        note("failed", attempt=session["attempts"][5])
        time.sleep(3)
        result["ui_after_failed"] = ui_timeline()
        shots += shoot(out, "attempt-failed", build=build)

        # AC-4: a new session receives only its own image; switching back changes nothing.
        before_a_ui = ui_timeline()
        before_a_file = api(f"/api/image-sessions/{session_a}")
        click("#pane-image [data-image-session-new]")
        wait(lambda: current_session_id() != session_a, 20, 0.5, "new session current")
        session_b = current_session_id()
        set_field("[data-image-prompt]", "另一个想法：竹林小径，晨雾")
        start_generation()
        session_b_doc = wait_settled(session_b, 1)
        note("session-b", session_b=session_b, attempt=session_b_doc["attempts"][0])
        click(f"#pane-image [data-image-session-list] [data-session-id='{session_a}']")
        wait(lambda: current_session_id() == session_a, 20, 0.5, "back to A")
        time.sleep(2)
        after_a_ui = ui_timeline()
        after_a_file = api(f"/api/image-sessions/{session_a}")
        result["switch_back"] = {
            "session_b": session_b, "session_b_attempts": session_b_doc["attempts"],
            "ui_before": before_a_ui, "ui_after": after_a_ui,
            "file_equal": before_a_file == after_a_file,
            "ui_equal_ignoring_selection": [{k: v for k, v in c.items() if k != "expanded"} for c in before_a_ui]
            == [{k: v for k, v in c.items() if k != "expanded"} for c in after_a_ui],
        }

        # AC-3: stop the app's processes (only the ones started here) and start again on the same data root.
        listing_before = api("/api/image-sessions")
        full_before = {s["id"]: api(f"/api/image-sessions/{s['id']}") for s in listing_before}
        pids_before = {"shell": shell.pid, "server": server_pids(app)}
        stop(shell, app)
        shell, _ = launch(app, data_root, out)
        pids_after = {"shell": shell.pid, "server": server_pids(app)}
        open_image_tab()
        listing_after = api("/api/image-sessions")
        full_after = {s["id"]: api(f"/api/image-sessions/{s['id']}") for s in listing_after}
        images = {}
        for doc in full_after.values():
            for attempt in doc["attempts"]:
                if attempt.get("output"):
                    status, body = http("GET", f"/api/outputs/{attempt['output']}")
                    images[attempt["output"]] = {"status": status, "bytes": len(body),
                                                 "sha256": hashlib.sha256(body).hexdigest(),
                                                 "png_magic": body[:8] == b"\x89PNG\r\n\x1a\n"}
        result["restart"] = {"pids_before": pids_before, "pids_after": pids_after,
                             "listing_equal": listing_before == listing_after,
                             "sessions_equal": full_before == full_after,
                             "listing_after": listing_after, "images_after": images}
        click(f"#pane-image [data-image-session-list] [data-session-id='{session_a}']")
        time.sleep(2)
        result["ui_after_restart"] = ui_timeline()
        shots += shoot(out, "after-restart", build=build)

        # AC-5: delete session B through the UI; its image stays in the library and still opens.
        outputs_before = api("/api/outputs")
        click(f"#pane-image [data-image-session-list] [data-session-id='{session_b}']")
        wait(lambda: current_session_id() == session_b, 20, 0.5, "B current")
        js(f"""(() => {{ const li = document.querySelector("#pane-image [data-session-id='{session_b}']");
            const btn = [...li.querySelectorAll('button')].find((b) => (b.getAttribute('aria-label') || '').startsWith('删除会话'));
            btn.click(); return true; }})()""")
        wait(lambda: js("!!document.querySelector('.overlay .dialog')"), 10, 0.3, "confirm dialog")
        time.sleep(0.5)
        result["delete_dialog_focus"] = js(
            "(() => { const a = document.activeElement; return a ? {tag: a.tagName, text: (a.textContent || '').trim(),"
            " in_dialog: !!a.closest('.overlay .dialog'), focus_visible: a.matches(':focus-visible')} : null; })()")
        note("delete-dialog-focus", focus=result["delete_dialog_focus"])
        shots += shoot(out, "delete-confirm", build=build)
        js("""(() => { const b = [...document.querySelectorAll('.overlay .dialog button')].find((x) => x.textContent.trim() === '删除');
            b.click(); return true; })()""")
        wait(lambda: js(f"!document.querySelector(\"#pane-image [data-session-id='{session_b}']\")"), 20, 0.5, "B gone")
        time.sleep(2)
        result["after_delete_current"] = current_session_id()
        result["after_delete_sessions_ui"] = js(
            "[...document.querySelectorAll('#pane-image [data-image-session-list] li')].map((li) => li.dataset.sessionId)")
        shots += shoot(out, "after-delete", build=build)
        b_output = session_b_doc["attempts"][0]["output"]
        try:
            http("GET", f"/api/image-sessions/{session_b}")
            b_status = 200
        except urllib.error.HTTPError as exc:
            b_status = exc.code
        js("(location.hash='#tab=library', true)")
        time.sleep(2)
        js(f"""(() => {{ const li = [...document.querySelectorAll('#pane-library li')].find((x) => x.textContent.includes('竹林小径'));
            [...li.querySelectorAll('button')].find((b) => b.textContent.includes('预览')).click(); return true; }})()""")
        preview = wait(lambda: js("(() => { const i = document.querySelector('#pane-library [data-lib-player] img');"
                                  " return i && i.complete && i.naturalWidth > 0 ? {src: i.getAttribute('src'), w: i.naturalWidth, h: i.naturalHeight} : null; })()"),
                       20, 0.5, "library preview")
        shots += shoot(out, "library-after-delete", build=build)
        result["delete"] = {"session_b": session_b, "session_get_status": b_status,
                            "listing_after": api("/api/image-sessions"),
                            "outputs_equal": outputs_before == api("/api/outputs"),
                            "b_output": b_output, "library_preview": preview}
        result["history_tail"] = api("/api/history")[:8]
        result["shots"] = shots
        result["ok"] = True
    except Exception as exc:  # record what happened, then stop our own instance
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        note("error", error=result["error"])
    finally:
        for started in RUNNING:
            if started.poll() is None:
                stop(started, app)
        result["log"] = LOG
        (out / "journey.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
