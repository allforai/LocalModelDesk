import io

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


def test_reports_every_15_seconds_with_reason_and_elapsed():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(8):
        w.pause("图片任务进行中")
    lines = err.getvalue().splitlines()
    assert lines and all(line.startswith("等待中：图片任务进行中（已等 ") for line in lines)
    assert len(lines) == 2


def test_timeout_raises_exit_3_and_never_oversleeps():
    t = T()
    w = Waiter(6, clock=t.clock, sleep=t.sleep, err=io.StringIO())
    with pytest.raises(CliError) as exc:
        for _ in range(10):
            w.pause("x")
    assert exc.value.exit_code == EXIT_TIMEOUT
    assert t.now <= 6.0
