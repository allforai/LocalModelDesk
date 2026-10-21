"""Backoff between polls, a heartbeat line every 15 s on stderr, and the overall deadline (A-23/A-25)."""
from __future__ import annotations

import contextlib
import signal
import sys
import threading
import time

from .errors import CliError, EXIT_TIMEOUT

DEFAULT_REASON = "等待台面响应"


class Waiter:
    def __init__(self, timeout_s: float, *, clock=time.monotonic, sleep=time.sleep, err=sys.stderr,
                 initial: float = 2.0, factor: float = 1.5, cap: float = 5.0, report_every: float = 15.0):
        self._clock, self._sleep, self._err = clock, sleep, err
        self._initial, self._factor, self._cap, self._report_every = initial, factor, cap, report_every
        self._start = clock()
        self._deadline = self._start + timeout_s
        self._interval = initial
        self._reason = DEFAULT_REASON

    def elapsed(self) -> float:
        return self._clock() - self._start

    def remaining(self) -> float:
        return max(0.0, self._deadline - self._clock())

    def expired(self) -> bool:
        return self._clock() >= self._deadline

    def reset(self) -> None:
        self._interval = self._initial

    def note(self, reason: str) -> None:
        """记下此刻在等什么，心跳行会用它。"""
        self._reason = reason

    def pause(self, reason: str) -> None:
        self._reason = reason
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
        self._sleep(min(self._interval, remaining))
        self._interval = min(self._interval * self._factor, self._cap)
        if self._clock() >= self._deadline:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")

    @contextlib.contextmanager
    def heartbeat(self):
        """命令运行期间每 15s 在 stderr 打一行，不管主线程卡在哪（排队、HTTP 请求、等模型回答）。

        q14：主线程卡在一次慢请求里时，在轮询里打点的写法整整 60s 一行都没有。
        退出时先停线程再返回，保证报错时 stderr 最后一行是原因，不是心跳。
        """
        stop = threading.Event()

        def beat() -> None:
            # 信号只许投给主线程（media._hold_signals 只挡主线程，pthread_sigmask 是按线程的）
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
            while not stop.wait(self._report_every):
                print(f"等待中：{self._reason}（已等 {int(self.elapsed())}s）", file=self._err, flush=True)

        thread = threading.Thread(target=beat, name="lmdesk-heartbeat", daemon=True)
        thread.start()
        try:
            yield self
        finally:
            stop.set()
            thread.join(timeout=1)
