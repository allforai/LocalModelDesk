"""Run the Desk HTTP service."""
from __future__ import annotations
import os

from .app import DeskApp
from .runtime import build_runtime


def runtime_port() -> int:
    """Use the same overridable shell port contract as the native host."""
    try:
        port = int(os.environ.get("LMD_SHELL_PORT", "8766"))
    except ValueError:
        return 8766
    return port if 1 <= port <= 65535 else 8766


def build_app(host: str = "127.0.0.1", port: int = 8766) -> DeskApp:
    """Compatibility helper returning the fully assembled production app."""
    runtime = build_runtime(host, port)
    runtime.app.runtime = runtime
    return runtime.app


def main() -> None:
    runtime = build_runtime(port=runtime_port())
    try:
        runtime.serve_forever()
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
