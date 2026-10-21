"""Run lmdesk as a real subprocess against a launched test harness."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def harness_port(harness) -> str:
    return harness.base_url.rsplit(":", 1)[1]


def run_cli(harness, *args, stdin: str = "", timeout: float = 60, extra_env: dict | None = None):
    env = {**os.environ, "LMD_SHELL_PORT": harness_port(harness), "PYTHONPATH": str(ROOT),
           "LMDESK_FAKE_VERSION": "e2e"}  # the fake bundle reports version "e2e"
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "-m", "desk.agent_cli", *args], input=stdin,
                          capture_output=True, text=True, timeout=timeout, env=env, cwd=str(ROOT))


def popen_cli(harness, *args, stdin=subprocess.DEVNULL):
    env = {**os.environ, "LMD_SHELL_PORT": harness_port(harness), "PYTHONPATH": str(ROOT),
           "LMDESK_FAKE_VERSION": "e2e"}  # the fake bundle reports version "e2e"
    return subprocess.Popen([sys.executable, "-m", "desk.agent_cli", *args], stdin=stdin,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=str(ROOT))
