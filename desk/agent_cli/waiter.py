"""Backoff between polls, a progress line every 15 s on stderr, and the overall deadline (A-23/A-25)."""
from __future__ import annotations

import sys
import time

from .errors import CliError, EXIT_TIMEOUT


class Waiter:
    def __init__(self, timeout_s: float, *, clock=time.monotonic, sleep=time.sleep, err=sys.stderr,
                 initial: float = 2.0, factor: float = 1.5, cap: float = 5.0, report_every: float = 15.0):
        self._clock, self._sleep, self._err = clock, sleep, err
        self._initial, self._factor, self._cap, self._report_every = initial, factor, cap, report_every
        self._start = clock()
        self._deadline = self._start + timeout_s
        self._interval = initial
        self._last_report = self._start

    def elapsed(self) -> float:
        return self._clock() - self._start

    def remaining(self) -> float:
        return max(0.0, self._deadline - self._clock())

    def expired(self) -> bool:
        return self._clock() >= self._deadline

    def reset(self) -> None:
        self._interval = self._initial

    def pause(self, reason: str) -> None:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
        self._sleep(min(self._interval, remaining))
        self._interval = min(self._interval * self._factor, self._cap)
        now = self._clock()
        if now - self._last_report >= self._report_every:
            self._last_report = now
            print(f"等待中：{reason}（已等 {int(now - self._start)}s）", file=self._err, flush=True)
        if now >= self._deadline:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
