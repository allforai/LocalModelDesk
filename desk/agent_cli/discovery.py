"""Find the desk: port from env, the enclosing app bundle, and a hidden launch when it is down (A-30/A-31/A-33)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable, Mapping

from .client import DeskClient, Unreachable
from .errors import CliError, EXIT_ERROR, EXIT_SANDBOX

DEFAULT_PORT = 8766
SANDBOX_MESSAGE = "被沙箱拦截，需要允许访问本机网络（127.0.0.1）"
# 与 macos/ShellStatus.swift 的 backgroundLaunchArgument 一致：带它启动的台面不显示主窗口（A-31）。
BACKGROUND_ARG = "--lmdesk-background"


def port_from_env(env: Mapping[str, str]) -> int:
    try:
        port = int(env.get("LMD_SHELL_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


def app_bundle_of(path: Path) -> Path | None:
    for parent in Path(path).resolve().parents:
        if parent.suffix == ".app" and (parent / "Contents" / "Resources" / "bundle.json").is_file():
            return parent
    return None


def _default_probe(base_url: str):
    return DeskClient(base_url, timeout=3.0).get("/api/state")


def _default_launcher(argv: list[str]) -> int:
    try:
        return subprocess.run(argv, capture_output=True).returncode
    except PermissionError:
        return -13


def _sandbox() -> CliError:
    return CliError(EXIT_SANDBOX, "sandboxed", SANDBOX_MESSAGE)


def connect(env: Mapping[str, str], *, here: Path, probe: Callable = _default_probe,
            launcher: Callable[[list[str]], int] = _default_launcher,
            sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
            start_timeout_s: float = 60.0) -> DeskClient:
    base_url = f"http://127.0.0.1:{port_from_env(env)}"
    try:
        probe(base_url)
        return DeskClient(base_url)
    except Unreachable as exc:
        if exc.kind == "sandbox":
            raise _sandbox() from None
        if exc.kind != "refused":
            raise CliError(EXIT_ERROR, "unreachable", f"连不上台面：{exc.detail}") from None
    app = app_bundle_of(here)
    if app is None:
        raise CliError(EXIT_ERROR, "desk_not_running", "台面没有运行。请先打开 LocalModelDesk。（这个 lmdesk 不在 app 包里，不会自动启动台面）")
    rc = launcher(["open", "-gj", str(app), "--args", BACKGROUND_ARG])
    if rc in (-13, 13, 126):
        raise _sandbox()
    if rc != 0:
        raise CliError(EXIT_ERROR, "launch_failed", f"台面未能启动（open 退出码 {rc}）")
    deadline = clock() + start_timeout_s
    while clock() < deadline:
        sleep(1.0)
        try:
            probe(base_url)
            return DeskClient(base_url)
        except Unreachable as exc:
            if exc.kind == "sandbox":
                raise _sandbox() from None
    raise CliError(EXIT_ERROR, "launch_timeout", f"台面未能启动（{int(start_timeout_s)}s 内无响应）")
