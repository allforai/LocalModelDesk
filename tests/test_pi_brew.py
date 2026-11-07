"""Homebrew job tests use only controlled subprocess doubles, never install software."""
import subprocess
import threading

import pytest

from desk.pi_integration.brew import BrewInstall
from desk.pi_integration.service import EXTENSION, IntegrationError, PiIntegrationService


class FakeProcess:
    def __init__(self, release, code=0):
        self.release, self.code = release, code
    def wait(self, timeout=None):
        assert self.release.wait(3)
        return self.code


def make_job(code=0):
    release = threading.Event()
    started = threading.Event()
    calls = []
    def popen(args, **kwargs):
        calls.append((args, kwargs))
        kwargs["stdout"].write(b"brew test output\n")
        started.set()
        return FakeProcess(release, code)
    return BrewInstall(which=lambda: "/fake/brew", popen=popen), release, started, calls


def test_exact_formula_no_shell_deduplicated_and_bounded():
    job, release, started, calls = make_job()
    finished = threading.Event()
    try:
        job.start(finished.set)
        assert started.wait(3)
        job.start(lambda: pytest.fail("duplicate job"))
        assert job.status()["state"] == "running"
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ["/fake/brew", "install", "--formula", "pi-coding-agent"]
        assert "shell" not in kwargs
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["start_new_session"]
        assert kwargs["env"]["HOMEBREW_NO_AUTO_UPDATE"] == "1"
        release.set()
        job._thread.join(3)
        assert not job._thread.is_alive()
        assert finished.is_set()
        assert job.status()["state"] == "done"
        assert "brew test output" in job.status()["output"]
    finally:
        release.set()
        job._thread.join(3)
        job.close()


def test_brew_failure_does_not_call_extension_installer():
    job, release, started, _ = make_job(code=1)
    job.start(lambda: pytest.fail("must not install extension after brew failure"))
    assert started.wait(3)
    release.set()
    job._thread.join(3)
    assert job.status()["state"] == "error"
    assert "退出码 1" in job.status()["message"]
    job.close()


def test_missing_brew_fails_without_spawning():
    job = BrewInstall(which=lambda: None, popen=lambda *_a, **_kw: pytest.fail("no brew"))
    with pytest.raises(RuntimeError, match="Homebrew"):
        job.start(lambda: None)
    assert job.status()["state"] == "idle"


def test_service_installs_pi_then_extension_only_after_brew_success(tmp_path):
    job, release, started, _ = make_job()
    home = tmp_path / "home"; home.mkdir()
    source = tmp_path / "integrations/pi/lmdesk.ts"
    source.parent.mkdir(parents=True); source.write_text("// provider")
    detected = []
    svc = PiIntegrationService(tmp_path, "dev", home,
        gateway_status=lambda: {"port": 8770}, control_url=lambda: "http://127.0.0.1:8766",
        which=lambda _: "/fake/pi" if detected else None, brew_installer=job)
    try:
        assert svc.status()["state"] == "absent"
        assert job.status()["state"] == "idle", "opening settings never installs"
        assert svc.apply("install")["state"] == "installing"
        assert started.wait(3)
        assert not (home / EXTENSION).exists()
        with pytest.raises(IntegrationError): svc.apply("install")
        detected.append(True)
        release.set()
        job._thread.join(3)
        assert svc.status()["state"] == "installed"
        assert (home / EXTENSION).read_text() == "// provider"
        svc.apply("remove")
        assert detected and not (home / EXTENSION).exists(), "removing integration never uninstalls pi"
    finally:
        release.set()
        if job._thread: job._thread.join(3)
        svc.close()


def test_service_missing_brew_or_conflict_never_modifies_extension(tmp_path):
    source = tmp_path / "integrations/pi/lmdesk.ts"
    source.parent.mkdir(parents=True); source.write_text("// provider")
    svc = PiIntegrationService(tmp_path, "dev", tmp_path / "home",
        gateway_status=lambda: {"port": 8770}, control_url=lambda: "http://127.0.0.1:8766", which=lambda _: None,
        brew_installer=BrewInstall(which=lambda: None))
    with pytest.raises(IntegrationError, match="Homebrew"):
        svc.apply("install")
    assert not svc.extension.exists()
    svc.extension.parent.mkdir(parents=True); svc.extension.write_text("// user file")
    with pytest.raises(IntegrationError, match="已有同名文件"):
        svc.apply("install")
    assert svc.extension.read_text() == "// user file"
    svc.close()


def test_timeout_kills_child_and_preserves_failure_log(monkeypatch):
    calls = []
    class Hung:
        pid = 987654
        def wait(self, timeout=None):
            if timeout is not None: raise subprocess.TimeoutExpired("brew", timeout)
            return 1
    def spawn(_args, **kw):
        kw["stdout"].write(b"stuck download")
        return Hung()
    job = BrewInstall(which=lambda: "/fake/brew", popen=spawn, timeout=0.01)
    monkeypatch.setattr(job, "_signal", lambda proc, sig: calls.append((proc.pid, sig)))
    job.start(lambda: pytest.fail("timeout"))
    job._thread.join(3)
    assert job.status()["state"] == "error"
    assert "超时" in job.status()["message"]
    assert "stuck download" in job.status()["output"]
    assert calls


def test_close_stops_process_group_and_prevents_install(monkeypatch):
    release = threading.Event()
    started = threading.Event()
    class Running:
        pid = 987654
        def wait(self, timeout=None):
            assert release.wait(3)
            return -15
        def poll(self): return None
    def spawn(*_a, **_kw):
        started.set()
        return Running()
    job = BrewInstall(which=lambda: "/fake/brew", popen=spawn)
    signals = []
    monkeypatch.setattr(job, "_signal", lambda proc, sig: (signals.append(sig), release.set()))
    job.start(lambda: pytest.fail("app closed"))
    assert started.wait(3)
    job.close()
    job._thread.join(3)
    assert signals and not job._thread.is_alive()
    with pytest.raises(RuntimeError, match="退出"):
        job.start(lambda: None)
