import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.resources.errors import DownloadBusyError, MediaBusyError
from desk.resources.events import ResourceEvents
from desk.resources.manifest import Manifest, ManifestFile
from desk.testing.fakes import FakeDownloadExecutor
from desk.testing.scripts import DownloadControl


def _wait_for(predicate):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    assert predicate()


def _downloader(tmp_path, *, can_start=lambda: {"ok": True, "reason": None}):
    from desk.resources.downloader import Downloader

    control = DownloadControl()
    manifest = Manifest("org/repo", (ManifestFile("weights/a.bin", 10),), "now", "fresh")
    roots = SimpleNamespace(models_root=tmp_path / "models", hf_cmd=(sys.executable,))
    events = ResourceEvents()
    downloader = Downloader(FakeDownloadExecutor(control), SimpleNamespace(get=lambda *_a, **_k: manifest),
                            lambda: roots, can_start, events, sample_interval=.01)
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
