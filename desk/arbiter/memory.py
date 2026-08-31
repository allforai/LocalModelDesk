"""Real memory snapshot from macOS sysctl/vm_stat (R-arbiter-02)."""
from __future__ import annotations

import re
import subprocess
import time
from dataclasses import asdict, dataclass


class MemoryProbeError(RuntimeError):
    """Total or available memory could not be read."""


PRESSURE_LEVELS = {1: "normal", 2: "warn", 4: "critical"}

AVAILABLE_COUNTERS = (
    "Pages free",
    "Pages inactive",
    "Pages purgeable",
    "Pages speculative",
)

_PAGE_SIZE_RE = re.compile(r"page size of (\d+) bytes")
_COUNTER_RE = re.compile(r"^(.+?):\s+([\d.]+)\.?$")


@dataclass(frozen=True)
class MemorySnapshot:
    total_bytes: int
    used_bytes: int
    available_bytes: int
    pressure: str
    page_size: int
    captured_at: float

    def to_dict(self) -> dict:
        return asdict(self)


def parse_vm_stat(text: str) -> tuple[int, dict[str, int]]:
    """Parse vm_stat output into its page size and page counters."""
    match = _PAGE_SIZE_RE.search(text)
    if not match:
        raise MemoryProbeError("vm_stat output missing page size")
    counters: dict[str, int] = {}
    for line in text.splitlines():
        counter = _COUNTER_RE.match(line.strip())
        if counter:
            counters[counter.group(1).strip('"')] = int(float(counter.group(2)))
    return int(match.group(1)), counters


class MemoryReader:
    def __init__(self, run=subprocess.run, clock=time.time):
        self._run = run
        self._clock = clock

    def _out(self, argv: list[str]) -> str:
        proc = self._run(argv, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            raise MemoryProbeError(
                f"{' '.join(argv)} failed: rc={proc.returncode} stderr={proc.stderr!r}")
        return proc.stdout

    def snapshot(self) -> MemorySnapshot:
        try:
            total_bytes = int(self._out(["sysctl", "-n", "hw.memsize"]).strip())
            page_size, counters = parse_vm_stat(self._out(["vm_stat"]))
        except MemoryProbeError:
            raise
        except Exception as exc:
            raise MemoryProbeError(f"memory probe failed: {exc}") from exc

        available_bytes = sum(counters.get(name, 0) for name in AVAILABLE_COUNTERS) * page_size
        used_bytes = total_bytes - available_bytes
        try:
            level = int(self._out(
                ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip())
            pressure = PRESSURE_LEVELS.get(level, "unknown")
        except Exception:
            pressure = "unknown"
        return MemorySnapshot(
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            available_bytes=available_bytes,
            pressure=pressure,
            page_size=page_size,
            captured_at=self._clock(),
        )
