"""Output delivery helpers."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RangePlan:
    """The selected byte range, independent of any HTTP framework."""

    status: int
    start: int | None
    length: int


_RANGE = re.compile(r"bytes=(?:(\d+)-(\d*)|-(\d+))")


def parse_range(size: int, header: str | None) -> RangePlan:
    """Plan a single RFC 7233 byte range, ignoring malformed ranges."""
    if size < 0:
        raise ValueError("size must not be negative")

    full = RangePlan(200, 0, size)
    if not isinstance(header, str):
        return full
    match = _RANGE.fullmatch(header)
    if match is None:
        return full

    start_text, end_text, suffix_text = match.groups()
    if suffix_text is not None:
        suffix_length = int(suffix_text)
        if suffix_length == 0 or size == 0:
            return RangePlan(416, None, 0)
        length = min(suffix_length, size)
        return RangePlan(206, size - length, length)

    start = int(start_text)
    if end_text and start > int(end_text):
        return full
    if start >= size:
        return RangePlan(416, None, 0)
    end = min(int(end_text), size - 1) if end_text else size - 1
    return RangePlan(206, start, end - start + 1)
