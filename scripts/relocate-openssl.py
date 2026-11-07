"""Relocate statically linked OpenSSL's C-string defaults before signing.

The cryptography macOS wheel bundles OpenSSL but retains its build's Homebrew
certificate directory. Use macOS's system certificate paths. No instructions,
offsets, library load commands or other binary bytes are changed.
"""
from pathlib import Path
import sys


def relocate(data: bytes) -> bytes:
    replacements = {
        b'OPENSSLDIR: "/opt/homebrew/etc/openssl@3"\0': b'OPENSSLDIR: "/etc/ssl"\0',
        b'/opt/homebrew/etc/openssl@3/cert.pem\0': b'/etc/ssl/cert.pem\0',
        b'/opt/homebrew/etc/openssl@3/certs\0': b'/etc/ssl/certs\0',
        b'/opt/homebrew/etc/openssl@3\0': b'/etc/ssl\0',
    }
    size = len(data)
    for old, new in replacements.items():
        data = data.replace(old, new + b'\0' * (len(old) - len(new)))
    if b'/opt/homebrew' in data:
        raise ValueError("unexpected Homebrew path in cryptography; review wheel before shipping")
    assert len(data) == size
    return data


if __name__ == '__main__':
    root = Path(sys.argv[1])
    binaries = list(root.glob('cryptography/hazmat/bindings/_rust*.so'))
    if len(binaries) != 1:
        raise SystemExit(f"expected one cryptography binary, found {len(binaries)}")
    path = binaries[0]
    path.write_bytes(relocate(path.read_bytes()))
