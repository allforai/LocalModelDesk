import io
import time

import pytest

from desk.agent_cli.errors import CliError, EXIT_TIMEOUT
from desk.agent_cli.waiter import Waiter


class T:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


def test_backoff_grows_by_1_5_and_caps_at_5():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(5):
        w.pause("x")
    assert t.sleeps == [2.0, 3.0, 4.5, 5.0, 5.0]


def test_reset_restarts_backoff():
    t = T()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=io.StringIO())
    w.pause("x"); w.pause("x"); w.reset(); w.pause("x")
    assert t.sleeps == [2.0, 3.0, 2.0]


def test_pause_only_records_the_reason_and_never_prints():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(8):
        w.pause("图片任务进行中")
    assert err.getvalue() == ""


def test_heartbeat_prints_every_interval_with_the_latest_reason():
    err = io.StringIO()
    w = Waiter(100, err=err, report_every=0.05)
    with w.heartbeat():
        w.note("图片任务进行中")
        time.sleep(0.18)
    lines = err.getvalue().splitlines()
    assert len(lines) >= 2
    assert all(line.startswith("等待中：图片任务进行中（已等 ") for line in lines)


def test_heartbeat_runs_while_the_main_thread_is_blocked_and_stops_on_exit():
    err = io.StringIO()
    w = Waiter(100, err=err, report_every=0.05)
    with w.heartbeat():
        time.sleep(0.12)   # 主线程卡在一次阻塞调用里，从不调 pause（q14 的情形）
    count = len(err.getvalue().splitlines())
    assert count >= 1 and err.getvalue().startswith("等待中：等待台面响应（已等 ")
    time.sleep(0.12)
    assert len(err.getvalue().splitlines()) == count


def test_timeout_raises_exit_3_and_never_oversleeps():
    t = T()
    w = Waiter(6, clock=t.clock, sleep=t.sleep, err=io.StringIO())
    with pytest.raises(CliError) as exc:
        for _ in range(10):
            w.pause("x")
    assert exc.value.exit_code == EXIT_TIMEOUT
    assert t.now <= 6.0
