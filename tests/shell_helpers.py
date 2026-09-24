"""Shared shell-test helpers."""
import os
import re
import signal
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
                # A file input filling the rest of the window: a click anywhere below the heading
                # lands on it, so the open-panel test (issue #15) needs no element lookup.
                body = ("<!doctype html><meta charset=utf-8><title>fake desk</title><h1>fake desk shell</h1>"
                        "<input type=file aria-label=pick-file style='position:fixed;left:0;top:80px;"
                        "width:100%;height:calc(100% - 80px);opacity:0.01'>").encode()
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

FAKE_BAD_LISTENER = "import socket, sys; s = socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.listen(); __import__('time').sleep(300)"


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


def start_fake_desk(port: int) -> subprocess.Popen:
    return start_script(FAKE_DESK_SERVER, port)


# 临时目录里的外壳二进制长这样：.../T/shellapp-<随机>/LocalModelDeskShell
# 必须同时要求「在 shellapp- 目录下」和「叫 LocalModelDeskShell」：只匹配后者会
# 连用户装着的那个 app 一起杀掉（dist/LocalModelDesk.app/Contents/MacOS/...），
# 那是毁用户的东西，不是清理。
_STALE_SHELL = re.compile(r"^\s*(\d+)\s+(\S*/shellapp-[^/\s]+/LocalModelDeskShell)\s*$")


def stale_shell_app_pids(listing: str) -> list[int]:
    """从 `ps -o pid,comm` 形状的文本里挑出遗留的临时外壳进程号。

    纯解析，不杀任何东西——所以「该不该杀这一行」可以穷举着测，而不必真的
    起一个 GUI 进程来验。

    只认「整行就是 pid + 可执行文件路径」的形状：扫除命令自己的命令行里会出现
    同样的模式（`ps ... | grep shellapp-...`），按整行匹配就不会匹配到自己。
    今天真踩过同形的坑——一个等待循环 `until ! ps aux | grep -q "[p]ytest"`
    因为 ps 列出了它自己而在等自己结束，跑了 7 小时 37 分。
    """
    pids = []
    for line in (listing or "").splitlines():
        found = _STALE_SHELL.match(line)
        if found:
            pids.append(int(found.group(1)))
    return pids


def sweep_stale_shell_apps() -> list[int]:
    """杀掉上次遗留的外壳进程；返回杀掉的那些。

    放在「跑之前」而不是「跑完清」：fixture 的 teardown 在 pytest 被 SIGKILL 时
    一行都不执行，而那正是漏进程的场合。清理不能保证，清理前的自查可以。
    """
    try:
        listing = subprocess.run(["ps", "-eo", "pid,comm"], capture_output=True,
                                 text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    killed = []
    for pid in stale_shell_app_pids(listing):
        try:
            os.kill(pid, signal.SIGKILL)      # GUI 程序会忽略 SIGTERM，今天实测过
            killed.append(pid)
        except OSError:
            pass
    return killed
