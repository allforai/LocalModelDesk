"""Bounded, explicit-click Homebrew install job; never uses a shell or sudo."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading


def which_brew():
    found = shutil.which("brew")
    if found:
        return found
    return next((str(p) for p in (Path("/opt") / "homebrew/bin/brew", Path("/usr/local/bin/brew"))
                 if p.is_file() and os.access(p, os.X_OK)), None)


class BrewInstall:
    def __init__(self, *, which=which_brew, popen=subprocess.Popen, timeout=900):
        self._which, self._popen, self._timeout = which, popen, timeout
        self._lock = threading.RLock()
        self._state = {"state": "idle", "message": "", "output": ""}
        self._process = None
        self._thread = None
        self._closed = False

    def status(self):
        with self._lock:
            return dict(self._state)

    def reset(self):
        with self._lock:
            if self._state["state"] != "running":
                self._state = {"state": "idle", "message": "", "output": ""}

    def start(self, complete):
        with self._lock:
            if self._closed:
                raise RuntimeError("台面正在退出，请重新打开后再安装")
            if self._state["state"] == "running":
                return
            brew = self._which()
            if not brew:
                raise RuntimeError("未检测到 Homebrew；请先从 brew.sh 安装 Homebrew，再重试（不会自动执行安装脚本或 sudo）")
            self._state = {"state": "running", "message": "正在通过 Homebrew 安装 pi-coding-agent（最多 15 分钟）…", "output": ""}
            self._thread = threading.Thread(target=self._work, args=(brew, complete), name="install-pi", daemon=True)
            self._thread.start()

    def _work(self, brew, complete):
        output = ""
        try:
            with tempfile.TemporaryFile() as log:
                with self._lock:
                    if self._closed:
                        return
                    self._process = self._popen(
                        [brew, "install", "--formula", "pi-coding-agent"],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                        env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_ENV_HINTS": "1"},
                    )
                    process = self._process
                try:
                    code = process.wait(timeout=self._timeout)
                except subprocess.TimeoutExpired:
                    self._signal(process, signal.SIGKILL)
                    process.wait()
                    raise RuntimeError("Homebrew 安装 pi 超时，请检查网络后重试") from None
                finally:
                    log.seek(0, os.SEEK_END)
                    log.seek(max(0, log.tell() - 4000))
                    output = log.read().decode("utf-8", errors="replace")
                if code:
                    raise RuntimeError(f"Homebrew 安装失败（退出码 {code}），请查看下方日志；不会安装台面扩展")
            with self._lock:
                if self._closed:
                    return
            # The callback acquires the service lock; never call it holding ours.
            complete()
            with self._lock:
                self._state = {"state": "done", "message": "pi 与台面接入扩展已安装；在 pi 执行 /reload，再用 /model 选择 lmdesk", "output": output}
        except Exception as error:
            with self._lock:
                self._state = {"state": "error", "message": str(error), "output": output}
        finally:
            with self._lock:
                self._process = None

    @staticmethod
    def _signal(process, sig):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    def close(self):
        with self._lock:
            self._closed = True
            process = self._process
        if process is not None and process.poll() is None:
            self._signal(process, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._signal(process, signal.SIGKILL)
                process.wait(timeout=2)
