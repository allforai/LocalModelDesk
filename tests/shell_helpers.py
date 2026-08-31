"""Shared shell-test helpers."""
import functools
import pathlib
import socket
import subprocess
import sys
import tempfile
import textwrap
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


@functools.lru_cache(maxsize=1)
def harness_path() -> str:
    """Compile the headless harness once per pytest process."""
    scratch = tempfile.mkdtemp(prefix="shellharness-")
    proc = subprocess.run([str(ROOT / "scripts" / "shell-lifecycle-test.sh"), scratch],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"harness compilation failed:\n{proc.stderr}"
    return proc.stdout.strip().splitlines()[-1]


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


FAKE_DESK_SERVER = textwrap.dedent("""\
    import http.server, json, sys
    PAYLOADS = {
        "/api/state": {"holder": None, "media_busy": False, "can_start": {}},
        "/api/memory": {"total_bytes": 137438953472, "used_bytes": 8589934592,
                        "available_bytes": 128849018880, "pressure": "normal",
                        "page_size": 16384, "captured_at": 0.0},
        "/api/config": {"needs_setup": False},
    }
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = b"<!doctype html><meta charset=utf-8><title>fake desk</title><h1>fake desk shell</h1>"
                ctype = "text/html; charset=utf-8"; code = 200
            elif self.path in PAYLOADS:
                body = json.dumps(PAYLOADS[self.path]).encode(); ctype = "application/json"; code = 200
            else:
                body = b'{"error": {"code": "not_found", "message": "no such route"}}'
                ctype = "application/json"; code = 404
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
""")


def port_listening(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
        return True
    except OSError:
        return False


def wait_port(port: int, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_listening(port):
            return
        time.sleep(0.05)
    raise RuntimeError(f"port {port} never started listening")


def start_script(source: str, port: int) -> subprocess.Popen:
    proc = subprocess.Popen([sys.executable, "-c", source, str(port)])
    try:
        wait_port(port)
    except RuntimeError:
        proc.kill()
        raise
    return proc
