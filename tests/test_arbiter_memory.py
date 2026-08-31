"""MemoryReader: real numbers from sysctl/vm_stat, no hard-coded constants (A09)."""
import subprocess
import sys

import pytest

from desk.arbiter.memory import (
    AVAILABLE_COUNTERS, MemoryProbeError, MemoryReader, parse_vm_stat,
)


VM_STAT_CANNED = """\
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                              105595.
Pages active:                           3646394.
Pages inactive:                         2755967.
Pages speculative:                        66177.
Pages throttled:                              0.
Pages wired down:                        538077.
Pages purgeable:                          92765.
\"Translation faults\":                 926814395.
Pages copy-on-write:                   34567890.
Pages purged:                          12345678.
"""


def _can_probe_real_memory() -> bool:
    """Whether this environment permits the macOS kernel probes."""
    return (
        sys.platform == "darwin"
        and subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
        ).returncode == 0
    )


class FakeRun:
    """Injectable subprocess.run replacement: argv-tuple -> (rc, stdout)."""

    def __init__(self, outputs):
        self.outputs = outputs

    def __call__(self, argv, **kwargs):
        rc, out = self.outputs[tuple(argv)]
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")


def reader(memsize="137438953472\n", pressure="1\n", vm=VM_STAT_CANNED):
    return MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (0, memsize),
        ("vm_stat",): (0, vm),
        ("sysctl", "-n", "kern.memorystatus_vm_pressure_level"): (0, pressure),
    }), clock=lambda: 123.0)


def test_parse_vm_stat_page_size_and_counters():
    page_size, counters = parse_vm_stat(VM_STAT_CANNED)
    assert page_size == 16384
    assert counters["Pages free"] == 105595
    assert counters["Pages inactive"] == 2755967
    assert counters["Pages purgeable"] == 92765
    assert counters["Pages speculative"] == 66177


def test_parse_vm_stat_garbage_raises():
    with pytest.raises(MemoryProbeError):
        parse_vm_stat("this is not vm_stat output")


def test_snapshot_arithmetic():
    snap = reader().snapshot()
    pages = 105595 + 2755967 + 92765 + 66177
    assert len(AVAILABLE_COUNTERS) == 4
    assert snap.page_size == 16384
    assert snap.available_bytes == pages * 16384
    assert snap.total_bytes == 137438953472
    assert snap.used_bytes + snap.available_bytes == snap.total_bytes
    assert snap.captured_at == 123.0


@pytest.mark.parametrize("level,expected", [
    ("1\n", "normal"), ("2\n", "warn"), ("4\n", "critical"), ("7\n", "unknown"),
])
def test_pressure_mapping(level, expected):
    assert reader(pressure=level).snapshot().pressure == expected


def test_pressure_probe_failure_is_unknown_not_fatal():
    r = MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (0, "137438953472\n"),
        ("vm_stat",): (0, VM_STAT_CANNED),
        ("sysctl", "-n", "kern.memorystatus_vm_pressure_level"): (1, ""),
    }), clock=lambda: 1.0)
    assert r.snapshot().pressure == "unknown"


@pytest.mark.parametrize("injected", [271_437_611_008, 96_636_764_160])
def test_total_comes_from_probe_not_a_constant(injected):
    """A09 anti-hardcode: total tracks the injected probe output exactly."""
    assert reader(memsize=f"{injected}\n").snapshot().total_bytes == injected


def test_memsize_probe_failure_raises():
    r = MemoryReader(run=FakeRun({
        ("sysctl", "-n", "hw.memsize"): (1, ""),
    }), clock=lambda: 1.0)
    with pytest.raises(MemoryProbeError):
        r.snapshot()


def test_to_dict_shape():
    d = reader().snapshot().to_dict()
    assert set(d) == {"total_bytes", "used_bytes", "available_bytes",
                      "pressure", "page_size", "captured_at"}


@pytest.mark.skipif(not _can_probe_real_memory(), reason="real macOS probes unavailable")
def test_real_snapshot_matches_sysctl():
    """Spec acceptance verbatim: total equals `sysctl -n hw.memsize`."""
    snap = MemoryReader().snapshot()
    expected = int(subprocess.run(
        ["sysctl", "-n", "hw.memsize"],
        capture_output=True, text=True, check=True).stdout.strip())
    assert snap.total_bytes == expected
    assert snap.total_bytes > 0
    assert snap.available_bytes > 0
    assert snap.used_bytes > 0
    assert snap.page_size > 0
    assert snap.captured_at > 0
    assert snap.pressure in {"normal", "warn", "critical", "unknown"}
