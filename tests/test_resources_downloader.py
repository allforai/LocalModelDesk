import json
import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.resources import fetch_cli
from desk.resources.errors import DownloadBusyError, MediaBusyError
from desk.resources.errors import ManifestUnavailableError
from desk.resources.events import ResourceEvents
from desk.resources.manifest import Manifest, ManifestFile
from desk.resources.parts import attempt_manifest_path, part_path
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


def test_start_download_spawns_resumable_fetcher_and_counts_part_bytes(tmp_path):
    downloader, control, events = _downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda progress, status: finished.append((progress, status)))
    dest = tmp_path / "models" / "minimax-h3"

    progress = downloader.start("h3")

    assert progress.state == "running"
    assert control.spawns == [[
        sys.executable, "-s", fetch_cli.__file__, "download", "appautomaton/minimax-h3-base-8bit-mlx",
        "--local-dir", str(dest), "--manifest", str(attempt_manifest_path(dest)),
    ]]
    assert json.loads(attempt_manifest_path(dest).read_text()) == {
        "repo": "org/repo", "files": [{"path": "weights/a.bin", "size": 10}]}
    with pytest.raises(DownloadBusyError):
        downloader.start("music3")
    part = part_path(dest, "weights/a.bin")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"x" * 7)
    _wait_for(lambda: downloader.progress().bytes_done == 7)
    assert downloader.progress().percent == 70.0
    assert downloader.progress().current_file == "weights/a.bin"
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
    assert downloader.progress().percent == 100.0
    assert finished[-1][1].state == "present"


def test_start_without_any_manifest_refuses_with_a_reason(tmp_path):
    downloader, control, _events = _downloader(tmp_path)

    def unavailable(*_a, **_k):
        raise ManifestUnavailableError("offline")

    downloader._manifest_store = SimpleNamespace(get=unavailable)
    with pytest.raises(ManifestUnavailableError, match="文件清单"):
        downloader.start("h3")
    assert control.spawns == []


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
    part = part_path(tmp_path / "models" / "minimax-h3", "weights/a.bin")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"partial")

    assert downloader.cancel().state == "cancelled"
    assert control.handle.terminated is True
    assert control.handle.killed is False
    assert part.exists()
    with pytest.raises(DownloadBusyError):
        downloader.start("music3")

    clock.advance(8)
    _wait_for(lambda: control.handle.killed)
    _wait_for(lambda: len(finished) == 1)

    assert finished[0][0].state == "cancelled"
    assert part.exists()
    assert downloader.start("music3").state == "running"


def test_progress_counts_parts_from_earlier_attempts(tmp_path):
    """取消前下的字节就是续传的起点，不能从 0 开始（J18）。"""
    dest = tmp_path / "models" / "minimax-h3"
    part = part_path(dest, "weights/a.bin")
    part.parent.mkdir(parents=True)
    part.write_bytes(b"x" * 6)
    past = time.time() - 3600
    os.utime(part, (past, past))
    downloader, control, _events = _downloader(tmp_path)

    downloader.start("h3")

    _wait_for(lambda: downloader.progress().bytes_done == 6)
    assert part.exists()
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")


def test_start_purges_unresumable_leftovers(tmp_path):
    """hf 换新临时文件名重下时，旧残片是纯占盘死数据，必须在新 attempt 前清掉（J18）。"""
    downloader, _control, _events = _downloader(tmp_path)
    cache = tmp_path / "models" / "minimax-h3" / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    leftover = cache / "a.bin.old.incomplete"
    leftover.write_bytes(b"x" * 4096)

    downloader.start("h3")

    assert not leftover.exists()


def test_start_download_passes_hf_env_to_executor(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    downloader._resolve_paths = lambda: SimpleNamespace(
        models_root=tmp_path / "models", hf_cmd=(sys.executable,), hf_env={"PYTHONPATH": "/pylibs/desk"})
    downloader.start("h3")
    assert control.envs[-1] == {"PYTHONPATH": "/pylibs/desk"}
