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
        self._progress.append(fn)

    def subscribe_finished(self, fn: Callable) -> None:
        self._finished.append(fn)

    def emit_progress(self, progress) -> None:
        for fn in list(self._progress):
            try:
                fn(progress)
            except Exception:
                log.exception("downloadProgressed subscriber failed")

    def emit_finished(self, progress, final_status=None) -> None:
        for fn in list(self._finished):
            try:
                fn(progress, final_status)
            except Exception:
                log.exception("downloadFinished subscriber failed")
