"""Measure what a media worker actually produced, not what was requested (G10)."""
from __future__ import annotations

import wave
from pathlib import Path


def wav_seconds(path: Path) -> float | None:
    exact = wav_seconds_exact(path)
    return round(exact, 2) if exact is not None else None


def wav_seconds_exact(path: Path) -> float | None:
    """Unrounded duration, for boundary checks `wav_seconds`'s 0.01 s rounding would blur."""
    try:
        with wave.open(str(path), "rb") as audio:
            rate = audio.getframerate()
            return audio.getnframes() / rate if rate else None
    except (OSError, EOFError, wave.Error):
        return None
