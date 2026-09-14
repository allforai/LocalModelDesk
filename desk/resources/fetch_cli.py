"""Resumable Hugging Face model fetcher (spawned by the desk service as a plain script).

huggingface_hub writes each attempt to a random-suffixed ``.incomplete`` and deletes it on
failure, so nothing is ever resumed (cross-exam 2026-09-13 G4). This script keeps every byte
in ``<local-dir>/.cache/localmodeldesk/parts/<path>.part``, continues it with an HTTP Range
request, and only moves a file into place once its size matches the manifest.

Stdlib only and no package imports: the service runs it with the bundled python by path.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHUNK = 1 << 20
PARTS_DIR = (".cache", "localmodeldesk", "parts")
RETRIES = 5


class ShortRead(ConnectionError):
    """The connection ended before the response body did; the bytes we got are kept."""


TRANSIENT = (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead)


def part_path(local_dir: Path, rel_path: str) -> Path:
    return Path(local_dir).joinpath(*PARTS_DIR, rel_path + ".part")


def file_url(endpoint: str, repo: str, rel_path: str, revision: str) -> str:
    return f"{endpoint.rstrip('/')}/{repo}/resolve/{urllib.parse.quote(revision)}/{urllib.parse.quote(rel_path)}"


def fetch_file(url: str, final: Path, part: Path, size: int, *, headers: dict,
               opener=urllib.request.urlopen) -> str:
    if final.exists() and final.stat().st_size == size:
        return "skipped"
    part.parent.mkdir(parents=True, exist_ok=True)
    final.parent.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    if have > size:
        part.unlink()
        have = 0
    if have < size:
        request_headers = dict(headers)
        if have:
            request_headers["Range"] = f"bytes={have}-"
        request = urllib.request.Request(url, headers=request_headers)
        with opener(request, timeout=60) as response:
            append = have > 0 and getattr(response, "status", 200) == 206
            announced = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
            received = 0
            with open(part, "ab" if append else "wb", buffering=0) as handle:
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
                    received += len(chunk)
            # http.client returns b"" instead of raising when the peer closes early.
            if announced is not None and received < int(announced):
                raise ShortRead(f"{final.name}: 连接中断，已收到 {received}/{announced} 字节")
    got = part.stat().st_size
    if got != size:
        raise OSError(f"{final.name}: 期望 {size} 字节，实际 {got} 字节")
    os.replace(part, final)
    return "done"


def _headers() -> dict:
    headers = {"User-Agent": "LocalModelDesk"}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def main(argv: list[str] | None = None, *, sleep=time.sleep) -> int:
    parser = argparse.ArgumentParser(prog="fetch_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    download = sub.add_parser("download")
    download.add_argument("repo")
    download.add_argument("--local-dir", required=True)
    download.add_argument("--manifest", required=True)
    download.add_argument("--endpoint", default=os.environ.get("HF_ENDPOINT", "https://huggingface.co"))
    download.add_argument("--revision", default="main")
    args = parser.parse_args(argv)

    local_dir = Path(args.local_dir)
    files = json.loads(Path(args.manifest).read_text(encoding="utf-8"))["files"]
    headers = _headers()
    for item in files:
        rel, size = item["path"], int(item["size"])
        url = file_url(args.endpoint, args.repo, rel, args.revision)
        for attempt in range(1, RETRIES + 1):
            try:
                result = fetch_file(url, local_dir / rel, part_path(local_dir, rel), size, headers=headers)
                print(f"{result} {rel}", flush=True)
                break
            except TRANSIENT as exc:
                if attempt == RETRIES:
                    print(f"下载 {rel} 失败：{exc}", file=sys.stderr, flush=True)
                    return 1
                sleep(min(2 ** attempt, 30))
            except OSError as exc:
                print(f"下载 {rel} 失败：{exc}", file=sys.stderr, flush=True)
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
