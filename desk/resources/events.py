"""In-process download event subscription points.

Subscribers observe ``downloadProgressed`` and ``downloadFinished`` events;
their failures never interrupt the download itself.
"""
from __future__ import annotations

import logging
from typing import Callable


log = logging.getLogger(__name__)


class ResourceEvents:
    def __init__(self) -> None:
        self._progress: list[Callable] = []
        self._finished: list[Callable] = []

    def subscribe_progress(self, fn: Callable) -> None:
        """Register a downloadProgressed observer. Test seam: production code never calls this
        (census 2026-09-08, F13) — tests/test_resources_downloader.py and
        tests/test_resources_service.py use it to observe emit_progress from outside."""
        self._progress.append(fn)

    def subscribe_finished(self, fn: Callable) -> None:
        """Register a downloadFinished observer. Test seam: production code never calls this
        (census 2026-09-08, F13) — tests/test_resources_downloader.py uses it to observe
        emit_finished from outside."""
        self._finished.append(fn)

    def emit_progress(self, progress) -> None:
        """Fan-out hook: no in-process subscriber today; kept as the seam downloads publish through."""
        for fn in list(self._progress):
            try:
                fn(progress)
            except Exception:
                log.exception("downloadProgressed subscriber failed")

    def emit_finished(self, progress, final_status=None) -> None:
        """Fan-out hook: no in-process subscriber today; kept as the seam downloads publish through."""
        for fn in list(self._finished):
            try:
                fn(progress, final_status)
            except Exception:
                log.exception("downloadFinished subscriber failed")
