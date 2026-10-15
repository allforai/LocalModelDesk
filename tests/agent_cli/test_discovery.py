from pathlib import Path

import pytest

from desk.agent_cli.client import Unreachable
from desk.agent_cli.discovery import app_bundle_of, connect, port_from_env
from desk.agent_cli.errors import CliError, EXIT_ERROR, EXIT_SANDBOX


@pytest.mark.parametrize("env,port", [({}, 8766), ({"LMD_SHELL_PORT": "9001"}, 9001),
                                      ({"LMD_SHELL_PORT": "0"}, 8766), ({"LMD_SHELL_PORT": "x"}, 8766),
                                      ({"LMD_SHELL_PORT": "70000"}, 8766)])
def test_port_from_env(env, port):
    assert port_from_env(env) == port


def test_app_bundle_of_finds_the_enclosing_app(tmp_path):
    res = tmp_path / "LocalModelDesk.app" / "Contents" / "Resources"
    (res / "desk" / "agent_cli").mkdir(parents=True)
    (res / "bundle.json").write_text("{}")
    assert app_bundle_of(res / "desk" / "agent_cli" / "x.py") == tmp_path / "LocalModelDesk.app"
    assert app_bundle_of(tmp_path / "elsewhere.py") is None


class FakeProbe:
    """Stands in for DeskClient.get('/api/state'): raises the scripted outcomes in order."""
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def __call__(self, base_url):
        outcome = self.outcomes.pop(0) if self.outcomes else {"holder": None}
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _connect(tmp_path, probe, *, in_bundle=True, launch_rc=0):
    calls = []
    here = (tmp_path / "LocalModelDesk.app/Contents/Resources/desk/agent_cli/x.py") if in_bundle else tmp_path / "x.py"
    if in_bundle:
        (tmp_path / "LocalModelDesk.app/Contents/Resources").mkdir(parents=True)
        (tmp_path / "LocalModelDesk.app/Contents/Resources/bundle.json").write_text("{}")
    t = [0.0]
    client = connect({}, here=here, probe=probe,
                     launcher=lambda argv: (calls.append(argv), launch_rc)[1],
                     sleep=lambda s: t.__setitem__(0, t[0] + s), clock=lambda: t[0])
    return client, calls


def test_running_desk_connects_without_launching(tmp_path):
    client, calls = _connect(tmp_path, FakeProbe([{"holder": None}]))
    assert client.base_url == "http://127.0.0.1:8766" and calls == []


def test_refused_in_bundle_launches_hidden_then_connects(tmp_path):
    client, calls = _connect(tmp_path, FakeProbe([Unreachable("refused", "x"), Unreachable("refused", "x"), {"holder": None}]))
    assert calls == [["open", "-gj", str(tmp_path / "LocalModelDesk.app")]]


def test_refused_outside_bundle_does_not_launch(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")]), in_bundle=False)
    assert exc.value.exit_code == EXIT_ERROR


def test_sandbox_is_exit_6_and_never_launches(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("sandbox", "EPERM")]))
    assert exc.value.exit_code == EXIT_SANDBOX


def test_launch_permission_failure_is_exit_6(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")]), launch_rc=-13)
    assert exc.value.exit_code == EXIT_SANDBOX


def test_never_comes_up_is_exit_1_after_60s(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")] * 100))
    assert exc.value.exit_code == EXIT_ERROR
    assert "台面未能启动" in exc.value.message
