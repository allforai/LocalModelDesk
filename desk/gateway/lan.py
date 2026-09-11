"""Pick a LAN address other devices can actually reach.

The default-route probe (connect() to a far address) returns the tunnel address on any
machine with a VPN up — a 100.64.0.0/10 CGNAT address that nothing on the LAN can reach
(cross-exam 2026-09-08, J8/J19). Enumerate the real interfaces instead.
"""
from __future__ import annotations

import re
import subprocess

_IFACE = re.compile(r"^(?P<name>[a-z0-9]+):", re.MULTILINE)
_INET = re.compile(r"^\s+inet (?P<addr>\d+\.\d+\.\d+\.\d+)(?P<rest>[^\n]*)", re.MULTILINE)
_SKIP_PREFIXES = ("lo", "utun", "ppp", "ipsec", "gif", "stf", "awdl", "llw")


def _private_rank(addr: str) -> int | None:
    """Lower is better; None means unusable from another device on the LAN."""
    octets = [int(part) for part in addr.split(".")]
    if octets[0] == 127 or (octets[0] == 169 and octets[1] == 254):
        return None
    if octets[0] == 100 and 64 <= octets[1] <= 127:  # CGNAT: VPN tunnels live here
        return None
    if octets[0] == 192 and octets[1] == 168:
        return 0
    if octets[0] == 10:
        return 1
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return 2
    return 3


def lan_candidates(ifconfig_output: str) -> list[str]:
    """Every reachable IPv4 address on a non-tunnel interface, best first."""
    found: list[tuple[int, int, str]] = []
    blocks = list(_IFACE.finditer(ifconfig_output))
    for index, match in enumerate(blocks):
        name = match.group("name")
        if name.startswith(_SKIP_PREFIXES):
            continue
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(ifconfig_output)
        for inet in _INET.finditer(ifconfig_output[match.end():end]):
            if "-->" in inet.group("rest"):  # point-to-point link, not a LAN
                continue
            addr = inet.group("addr")
            rank = _private_rank(addr)
            if rank is not None:
                found.append((rank, len(found), addr))
    found.sort()
    seen: set[str] = set()
    ordered: list[str] = []
    for _, _, addr in found:
        if addr not in seen:
            seen.add(addr)
            ordered.append(addr)
    return ordered


def pick_lan_host(ifconfig_output: str) -> str | None:
    candidates = lan_candidates(ifconfig_output)
    return candidates[0] if candidates else None


def read_ifconfig(run=subprocess.run) -> str:
    try:
        done = run(["/sbin/ifconfig", "-a"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout or ""
