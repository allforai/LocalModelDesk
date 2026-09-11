"""Estimate a media job's peak memory from its parameters, not from the model's disk size.

Calibration (cross-exam 2026-09-08, worker logs in
docs/cross-exam/2026-09-08-localmodeldesk/evidence/q20, q24, q12):

  h3 512x288x49 frames, 16 steps -> peak 27.0 GiB (text-encoder stage dominates)
  h3 1024x576x73 frames, 16 steps -> exceeded the worker's own budget while active 21.2 /
                                      peak 33.9 GiB (evidence/q23)

So: a fixed stage cost plus a term that grows with the latent volume. Reporting the
model's 102.7 GiB on-disk size for every job made the warning meaningless (F4).
"""
from __future__ import annotations

GIB = 1024 ** 3

_DRAFT_VOLUME = 512 * 288 * 49

# (fixed stage bytes, bytes added per draft-volume unit above the first)
_VIDEO = (27.0 * GIB, 1.4 * GIB)
_MUSIC_BASE = 27.0 * GIB
_MUSIC_PER_SECOND = 0.05 * GIB


def estimate_bytes(kind: str, params: dict) -> int:
    """Peak resident bytes this job is expected to need."""
    if kind == "music":
        duration = float(params.get("duration") or 10)
        return int(_MUSIC_BASE + _MUSIC_PER_SECOND * duration)
    fixed, per_unit = _VIDEO
    width = float(params.get("width") or 512)
    height = float(params.get("height") or 288)
    frames = float(params.get("frames") or 49)
    volume = (width * height * frames) / _DRAFT_VOLUME
    return int(fixed + per_unit * max(volume - 1.0, 0.0))
