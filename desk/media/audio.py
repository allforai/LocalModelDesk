"""Measure what a media worker actually produced, not what was requested (G10)."""
from __future__ import annotations

import wave
from pathlib import Path


def wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as audio:
            rate = audio.getframerate()
            return round(audio.getnframes() / rate, 2) if rate else None
    except (OSError, EOFError, wave.Error):
        return None
