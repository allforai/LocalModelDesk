"""Shared shell-test helpers."""
import functools
import pathlib
import socket
import subprocess
import tempfile

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
