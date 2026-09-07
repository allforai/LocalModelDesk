import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.resources.errors import DownloadBusyError, MediaBusyError
from desk.resources.events import ResourceEvents
from desk.resources.manifest import Manifest, ManifestFile
from desk.testing.fakes import FakeDownloadExecutor, FixedClock
from desk.testing.scripts import DownloadControl


def _wait_for(predicate):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    assert predicate()


def _downloader(tmp_path, *, can_start=lambda: {"ok": True, "reason": None}, clock=time.monotonic):
    from desk.resources.downloader import Downloader

    control = DownloadControl()
    manifest = Manifest("org/repo", (ManifestFile("weights/a.bin", 10),), "now", "fresh")
    roots = SimpleNamespace(models_root=tmp_path / "models", hf_cmd=(sys.executable,))
    events = ResourceEvents()
    downloader = Downloader(FakeDownloadExecutor(control), SimpleNamespace(get=lambda *_a, **_k: manifest),
                            lambda: roots, can_start, events, clock=clock, sample_interval=.01)
    return downloader, control, events


def test_start_download_spawns_resumable_hf_command_and_finishes(tmp_path):
    downloader, control, events = _downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda progress, status: finished.append((progress, status)))

    progress = downloader.start("h3")

    assert progress.state == "running"
    assert control.spawns == [[sys.executable, "download", "appautomaton/minimax-h3-base-8bit-mlx", "--local-dir", str(tmp_path / "models" / "minimax-h3")]]
    with pytest.raises(DownloadBusyError):
        downloader.start("music3")
    incomplete = tmp_path / "models" / "minimax-h3" / ".cache" / "huggingface" / "download" / "a.incomplete"
    incomplete.parent.mkdir(parents=True)
    incomplete.write_bytes(b"x" * 7)
    _wait_for(lambda: downloader.progress().bytes_done == 7)
    assert downloader.progress().percent == 70.0
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
    assert downloader.progress().percent == 100.0
    assert finished[-1][1].state == "present"


def test_start_download_forwards_media_busy_reason(tmp_path):
    downloader, _control, _events = _downloader(
        tmp_path, can_start=lambda: {"ok": False, "reason": {"code": "media_busy", "message": "video running"}}
    )

    with pytest.raises(MediaBusyError, match="video running"):
        downloader.start("h3")


def test_cancel_download_terminates_then_kills_after_eight_seconds_and_keeps_lock(tmp_path):
    clock = FixedClock()
    downloader, control, events = _downloader(tmp_path, clock=clock)
    finished = []
    events.subscribe_finished(lambda progress, status: finished.append((progress, status)))

    downloader.start("h3")
    incomplete = tmp_path / "models" / "minimax-h3" / ".cache" / "huggingface" / "download" / "a.incomplete"
    incomplete.parent.mkdir(parents=True)
    incomplete.write_bytes(b"partial")

    assert downloader.cancel().state == "cancelled"
    assert control.handle.terminated is True
    assert control.handle.killed is False
    assert incomplete.exists()
    with pytest.raises(DownloadBusyError):
        downloader.start("music3")

    clock.advance(8)
    _wait_for(lambda: control.handle.killed)
    _wait_for(lambda: len(finished) == 1)

    assert finished[0][0].state == "cancelled"
    assert incomplete.exists()
    assert downloader.start("music3").state == "running"


def test_progress_ignores_incomplete_files_from_earlier_attempts(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    cache = tmp_path / "models" / "minimax-h3" / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    stale = cache / "old.incomplete"
    stale.write_bytes(b"x" * 5)
    past = time.time() - 3600
    os.utime(stale, (past, past))
    downloader.start("h3")
    fresh = cache / "new.incomplete"
    fresh.write_bytes(b"x" * 3)
    _wait_for(lambda: downloader.progress().bytes_done == 3)
    assert downloader.progress().stale_bytes == 5
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
    assert not stale.exists() and not fresh.exists()


def test_start_download_passes_hf_env_to_executor(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    downloader._resolve_paths = lambda: SimpleNamespace(
        models_root=tmp_path / "models", hf_cmd=(sys.executable,), hf_env={"PYTHONPATH": "/pylibs/desk"})
    downloader.start("h3")
    assert control.envs[-1] == {"PYTHONPATH": "/pylibs/desk"}
