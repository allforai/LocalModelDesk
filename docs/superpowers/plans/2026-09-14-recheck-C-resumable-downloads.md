# Cross-Exam 2026-09-13 修复 · C 真正可续传的模型下载 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取消、崩溃或退出后再点「续传」，已下的字节原样保留、进度从取消时的百分比继续；面板在取消瞬间不再掉到 0%。

**Architecture:** huggingface_hub 1.29 把每次下载写进带随机后缀的 `.incomplete`，失败即删，结构上无法续传（q04 根因）。改为自带的 stdlib 下载脚本 `desk/resources/fetch_cli.py`：按清单逐文件用 HTTP `Range` 续写 `<模型目录>/.cache/localmodeldesk/parts/<相对路径>.part`，大小对上清单才 `os.replace` 到最终位置。`Downloader` 生成该脚本的命令（保留 `--local-dir` 参数形状，测试替身 `DownloadControl` 不用变），采样器与 `verify_tree` 把 `.part` 字节算作可续传进度；旧版 hf `.incomplete` 仍按"不可续传残片"报告并在开始前清理。

**Tech Stack:** Python 3.13 stdlib（`urllib.request`、`http.server` 仅测试用）· 零依赖 ES modules · node:test · Playwright

**Spec:** `docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md` §缺口清单 G4、J18、G3，§缺陷模式 P4「hf 下载子进程 shutdown 不 cancel」；证据 `evidence/q04/`、`evidence/q30/`、`evidence/q05/`。需求：`docs/superpowers/specs/2026-08-31-resources-spec.md` R-resources-04/06（"已下载的部分必须保持可续传状态，不得清空"）、R-resources-08。

**Depends on:** Plan A Task 1（`ProductionRuntime.shutdown` 已含 `media.close()`）。本计划 Task 5 在其后加 `resources.close()`。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）；`fetch_cli.py` 作为独立脚本运行，文件内**不得**有 `desk.` 包导入。
- 前端：零依赖 ES modules；`createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文；机器码不作唯一解释。
- 测试命令：`python3 -m pytest -q`、`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`。
- 验证门必须包含 e2e（`desk/static/` 改动）。
- 测试永不联网、永不触碰 `~/LocalModelDesk`：HTTP 用本机 `ThreadingHTTPServer` 或假 opener；目录一律 `tmp_path`。
- 真机验证**不得删除已有模型权重**：只对一个当前"没下/一半"的模型做下载实验，删除操作只允许作用于本计划实验新下载的那个模型，且必须事先列出目录确认。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `desk/resources/fetch_cli.py`（新） | 独立下载脚本：`Range` 续写 `.part`、校验大小、原子落位、重试 |
| `desk/resources/parts.py`（新） | `.part` 目录约定与字节统计，供 downloader 与 verify 共用 |
| `desk/resources/downloader.py` | 生成 fetch 命令、写本次清单文件、采样计 `.part`；合并 `_InjectableDownloader` 的注入缝；`close()` |
| `desk/resources/service.py` | 删除 `_InjectableDownloader`，直接用 `Downloader`；`close()` |
| `desk/resources/verify.py` | `ModelStatus.resumable_bytes`，`.part` 计入百分比 |
| `desk/runtime.py` | `ProductionRuntime.resources`，shutdown 取消在途下载 |
| `desk/static/js/pure/model_status.js` | 「可续传」徽章、旧残片说明、未知原因中文化 |
| `desk/static/js/panes/resources.js` | 行元信息追加旧残片说明 |

---

### Task 1: `.part` 约定与独立下载脚本

**Files:**
- Create: `desk/resources/parts.py`
- Create: `desk/resources/fetch_cli.py`
- Test: `tests/test_resources_fetch_cli.py`（新）

**Interfaces:**
- Produces（`desk/resources/parts.py`）：
  - `PARTS_DIR = (".cache", "localmodeldesk", "parts")`
  - `part_path(model_dir: Path, rel_path: str) -> Path` → `model_dir/.cache/localmodeldesk/parts/<rel_path>.part`
  - `attempt_manifest_path(model_dir: Path) -> Path` → `model_dir/.cache/localmodeldesk/manifest.json`
  - `part_bytes(model_dir: Path, files) -> int` —— 对清单里每个**最终文件尚不完整**的条目，累加 `min(.part 大小, 期望大小)`
- Produces（`desk/resources/fetch_cli.py`，脚本内复制同样的目录常量，不导入 `parts.py`）：
  - 命令行：`python fetch_cli.py download REPO --local-dir DIR --manifest FILE [--endpoint URL] [--revision REV]`
  - `fetch_file(url, final, part, size, *, headers, opener=urllib.request.urlopen) -> str`，返回 `"skipped"` 或 `"done"`，大小不符抛 `OSError`
  - `main(argv=None, *, sleep=time.sleep) -> int`：成功 0，失败 1（stderr 一行中文原因）
  - `ShortRead(ConnectionError)`：收到的字节少于响应 `Content-Length`（连接中途断开）——可重试；完整收到但总大小与清单不符是普通 `OSError`——不重试
  - 环境变量：`HF_ENDPOINT`（缺省 `https://huggingface.co`）、`HF_TOKEN` 或 `HUGGING_FACE_HUB_TOKEN`

- [ ] **Step 1: Write the failing tests**

新建 `tests/test_resources_fetch_cli.py`：

```python
"""The resumable fetcher keeps partial bytes across attempts (R-resources-06, cross-exam 2026-09-13 G4/J18)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from desk.resources import fetch_cli
from desk.resources.parts import attempt_manifest_path, part_bytes, part_path
from desk.resources.manifest import ManifestFile

BLOB = bytes(range(256)) * 40  # 10240 bytes


class _Server:
    """Serves BLOB at /org/repo/resolve/main/<anything>, honouring Range, recording headers."""

    def __init__(self, *, ignore_range=False, cut_after=None):
        self.ranges = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                header = self.headers.get("Range")
                outer.ranges.append(header)
                start = 0
                if header and not ignore_range:
                    start = int(header.removeprefix("bytes=").split("-")[0])
                body = BLOB[start:]
                self.send_response(206 if start else 200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if cut_after is not None and not header:
                    self.wfile.write(body[:cut_after])
                    self.wfile.flush()
                    self.connection.close()
                    return
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def _manifest(tmp_path, files):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"repo": "org/repo", "files": [{"path": p, "size": s} for p, s in files]}))
    return path


def test_resume_sends_range_from_existing_part_and_moves_into_place(tmp_path):
    server = _Server()
    try:
        dest = tmp_path / "model"
        part = part_path(dest, "weights/a.bin")
        part.parent.mkdir(parents=True)
        part.write_bytes(BLOB[:4000])

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("weights/a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert server.ranges == ["bytes=4000-"]
        assert (dest / "weights/a.bin").read_bytes() == BLOB
        assert not part.exists()
    finally:
        server.close()


def test_server_ignoring_range_restarts_the_part_instead_of_appending(tmp_path):
    server = _Server(ignore_range=True)
    try:
        dest = tmp_path / "model"
        part = part_path(dest, "a.bin")
        part.parent.mkdir(parents=True)
        part.write_bytes(b"garbage!" * 10)

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert (dest / "a.bin").read_bytes() == BLOB
    finally:
        server.close()


def test_complete_final_file_is_not_requested_again(tmp_path):
    server = _Server()
    try:
        dest = tmp_path / "model"
        dest.mkdir()
        (dest / "a.bin").write_bytes(BLOB)

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert server.ranges == []
    finally:
        server.close()


def test_dropped_connection_keeps_bytes_then_retry_resumes(tmp_path):
    server = _Server(cut_after=3000)
    try:
        dest = tmp_path / "model"
        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint], sleep=lambda _s: None)

        assert code == 0
        assert server.ranges[0] is None
        assert server.ranges[1] == "bytes=3000-"
        assert (dest / "a.bin").read_bytes() == BLOB
    finally:
        server.close()


def test_size_mismatch_fails_and_keeps_the_part(tmp_path, capsys):
    server = _Server()
    try:
        dest = tmp_path / "model"
        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB) + 5)])),
                               "--endpoint", server.endpoint])

        assert code == 1
        assert "a.bin" in capsys.readouterr().err
        assert part_path(dest, "a.bin").stat().st_size == len(BLOB)
        assert not (dest / "a.bin").exists()
    finally:
        server.close()


def test_part_bytes_counts_only_incomplete_files_capped_at_expected(tmp_path):
    dest = tmp_path / "model"
    dest.mkdir()
    (dest / "done.bin").write_bytes(b"x" * 10)
    for rel, size in (("done.bin", 3), ("half.bin", 4), ("over.bin", 99)):
        part = part_path(dest, rel)
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(b"x" * size)
    files = (ManifestFile("done.bin", 10), ManifestFile("half.bin", 8), ManifestFile("over.bin", 20))
    assert part_bytes(dest, files) == 4 + 20
    assert attempt_manifest_path(dest) == dest / ".cache" / "localmodeldesk" / "manifest.json"


def test_fetch_cli_has_no_package_imports():
    source = Path(fetch_cli.__file__).read_text(encoding="utf-8")
    assert "from desk" not in source and "import desk" not in source and "from ." not in source
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_resources_fetch_cli.py -q`
Expected: FAIL，`ImportError: cannot import name 'fetch_cli'`

- [ ] **Step 3: Write `desk/resources/parts.py`**

```python
"""Where resumable download bytes live, and how many of them count as progress."""
from __future__ import annotations

from pathlib import Path

PARTS_DIR = (".cache", "localmodeldesk", "parts")


def part_path(model_dir: Path, rel_path: str) -> Path:
    return Path(model_dir).joinpath(*PARTS_DIR, rel_path + ".part")


def attempt_manifest_path(model_dir: Path) -> Path:
    return Path(model_dir) / ".cache" / "localmodeldesk" / "manifest.json"


def part_bytes(model_dir: Path, files) -> int:
    """Bytes already on disk for files whose final copy is not complete yet."""
    total = 0
    for file in files:
        try:
            if (Path(model_dir) / file.path).stat().st_size == file.size:
                continue
        except OSError:
            pass
        try:
            total += min(part_path(model_dir, file.path).stat().st_size, file.size)
        except OSError:
            continue
    return total
```

- [ ] **Step 4: Write `desk/resources/fetch_cli.py`**

```python
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
```

注意：`TRANSIENT` 里的 `urllib.error.URLError`、`ConnectionError`（含 `ShortRead`）都是 `OSError` 子类，所以 `except TRANSIENT` 必须排在 `except OSError` 之前（上面已如此）；完整收到却与清单大小不符抛的是普通 `OSError`，直接失败不重试。

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_resources_fetch_cli.py -q`
Expected: PASS（7 passed）

- [ ] **Step 6: Commit**

```bash
git add desk/resources/parts.py desk/resources/fetch_cli.py tests/test_resources_fetch_cli.py
git commit -m "feat(resources): stdlib fetcher that resumes partial files with HTTP Range (G4)"
```

---

### Task 2: Downloader 改用 fetch 脚本并把 `.part` 算进进度

**Files:**
- Modify: `desk/resources/downloader.py`
- Modify: `desk/resources/service.py`（删除 `_InjectableDownloader`）
- Test: `tests/test_resources_downloader.py`、`tests/test_resources_service.py`

**Interfaces:**
- Consumes: `part_path`、`part_bytes`、`attempt_manifest_path`（Task 1）
- Produces: `Downloader(executor, manifest_store, resolve_paths, can_start_heavy, events, clock=time.monotonic, sample_interval=1.0, sleep=time.sleep, thread_factory=threading.Thread)`
- Produces: 下载命令 `[python, "-s", <fetch_cli.py 绝对路径>, "download", REPO, "--local-dir", DEST, "--manifest", DEST/.cache/localmodeldesk/manifest.json]`，`python = roots.hf_cmd[0]`；`hf_cmd` 为空或 python 不存在 → `HfCliMissingError`；清单拿不到 → `ManifestUnavailableError("拿不到 <repo> 的文件清单，检查网络后重试")`。
- Produces: `DownloadProgress.bytes_done` = 完整最终文件字节 + `.part` 字节；`stale_bytes` = 旧版 hf `.incomplete` 字节（开始前已清理，所以运行中通常为 0）。

- [ ] **Step 1: Update the tests**

`tests/test_resources_downloader.py`：顶部 import 增加

```python
from desk.resources import fetch_cli
from desk.resources.errors import ManifestUnavailableError
from desk.resources.parts import attempt_manifest_path, part_path
```

把 `test_start_download_spawns_resumable_hf_command_and_finishes` 整个替换为：

```python
def test_start_download_spawns_resumable_fetcher_and_counts_part_bytes(tmp_path):
    downloader, control, events = _downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda progress, status: finished.append((progress, status)))
    dest = tmp_path / "models" / "minimax-h3"

    progress = downloader.start("h3")

    assert progress.state == "running"
    assert control.spawns == [[
        sys.executable, "-s", fetch_cli.__file__, "download", "appautomaton/minimax-h3-base-8bit-mlx",
        "--local-dir", str(dest), "--manifest", str(attempt_manifest_path(dest)),
    ]]
    assert json.loads(attempt_manifest_path(dest).read_text()) == {
        "repo": "org/repo", "files": [{"path": "weights/a.bin", "size": 10}]}
    with pytest.raises(DownloadBusyError):
        downloader.start("music3")
    part = part_path(dest, "weights/a.bin")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"x" * 7)
    _wait_for(lambda: downloader.progress().bytes_done == 7)
    assert downloader.progress().percent == 70.0
    assert downloader.progress().current_file == "weights/a.bin"
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
    assert downloader.progress().percent == 100.0
    assert finished[-1][1].state == "present"


def test_start_without_any_manifest_refuses_with_a_reason(tmp_path):
    downloader, control, _events = _downloader(tmp_path)

    def unavailable(*_a, **_k):
        raise ManifestUnavailableError("offline")

    downloader._manifest_store = SimpleNamespace(get=unavailable)
    with pytest.raises(ManifestUnavailableError, match="文件清单"):
        downloader.start("h3")
    assert control.spawns == []
```

（文件顶部补 `import json`。）

把 `test_cancel_download_terminates_then_kills_after_eight_seconds_and_keeps_lock` 里两处 `incomplete = ... / "a.incomplete"` 改为 `.part`，并断言取消后字节仍在：

```python
    part = part_path(tmp_path / "models" / "minimax-h3", "weights/a.bin")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"partial")
```

其后所有 `incomplete.exists()` 改为 `part.exists()`。

把 `test_progress_ignores_incomplete_files_from_earlier_attempts` 整个替换为：

```python
def test_progress_counts_parts_from_earlier_attempts(tmp_path):
    """取消前下的字节就是续传的起点，不能从 0 开始（J18）。"""
    dest = tmp_path / "models" / "minimax-h3"
    part = part_path(dest, "weights/a.bin")
    part.parent.mkdir(parents=True)
    part.write_bytes(b"x" * 6)
    past = time.time() - 3600
    os.utime(part, (past, past))
    downloader, control, _events = _downloader(tmp_path)

    downloader.start("h3")

    _wait_for(lambda: downloader.progress().bytes_done == 6)
    assert part.exists()
    control.finish([("weights/a.bin", 10)])
    _wait_for(lambda: downloader.progress().state == "finished")
```

`test_start_purges_unresumable_leftovers` 保持不变（旧 hf 残片仍在开始前清理）。

`tests/test_resources_service.py` 的 `test_download_facade_injects_sampling_sleep_and_thread_factory` 不改测试体；它通过 `ResourcesService(..., sleep=..., thread_factory=...)` 验证注入缝，Task 2 之后注入到 `Downloader` 本身。

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_resources_downloader.py -q`
Expected: FAIL（命令仍是 `hf download`；`.part` 不计入进度）

- [ ] **Step 3: Rewrite the downloader start/sample path**

`desk/resources/downloader.py`：

import 区改为：

```python
import json
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import fetch_cli
from .catalog import entry
from .errors import (DownloadBusyError, HfCliMissingError, ManifestUnavailableError, MediaBusyError,
                     NotDownloadingError)
from .parts import attempt_manifest_path, part_bytes, part_path
from .verify import verify_tree
```

`__init__` 签名与赋值：

```python
    def __init__(self, executor, manifest_store, resolve_paths, can_start_heavy, events,
                 clock=time.monotonic, sample_interval: float = 1.0,
                 sleep=time.sleep, thread_factory=threading.Thread):
        ...
        self._sleep = sleep
        self._thread_factory = thread_factory
```

（保留原有其它赋值。）

`start` 替换为：

```python
    def start(self, key: str) -> DownloadProgress:
        with self._lock:
            if self._handle is not None:
                raise DownloadBusyError("a download is already running")
            allowed = self._can_start_heavy()
            if not allowed.get("ok"):
                reason = allowed.get("reason") or {}
                raise MediaBusyError(reason.get("message", "heavy work is running"), reason)
            model = entry(key)
            roots = self._resolve_paths()
            hf_cmd = tuple(roots.hf_cmd)
            if not hf_cmd or not Path(hf_cmd[0]).exists():
                raise HfCliMissingError("下载所需的 Python 运行时不可用")
            try:
                manifest = self._manifest_store.get(model, refresh=True)
            except Exception as exc:
                raise ManifestUnavailableError(f"拿不到 {model.hf_repo} 的文件清单，检查网络后重试") from exc
            destination = Path(roots.models_root) / model.relpath
            self._model = model
            self._purge_incomplete()
            manifest_file = attempt_manifest_path(destination)
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            manifest_file.write_text(json.dumps({
                "repo": manifest.repo,
                "files": [{"path": f.path, "size": f.size} for f in manifest.files],
            }, ensure_ascii=False), encoding="utf-8")
            command = [hf_cmd[0], "-s", fetch_cli.__file__, "download", model.hf_repo,
                       "--local-dir", str(destination), "--manifest", str(manifest_file)]
            try:
                handle = self._executor.spawn(
                    command, cwd=None, extra_env=dict(getattr(roots, "hf_env", {}) or {}))
            except FileNotFoundError as exc:
                raise HfCliMissingError("下载所需的 Python 运行时不可用") from exc
            result = self._begin(model, manifest, handle)
            self._thread_factory(target=self._sample_loop, daemon=True).start()
            return result
```

`_sample_loop` 最后一行 `time.sleep(self._sample_interval)` 改为 `self._sleep(self._sample_interval)`。

`_sample` 中从 `root = ...` 到 `done = min(done + incomplete_bytes, total)` 替换为：

```python
            root = Path(self._resolve_paths().models_root) / model.relpath
            done, current = 0, None
            newest = -1.0
            for file in manifest.files:
                try:
                    size = (root / file.path).stat().st_size
                except OSError:
                    size = 0
                if size == file.size:
                    done += file.size
                    continue
                try:
                    stat = part_path(root, file.path).stat()
                except OSError:
                    continue
                if stat.st_mtime >= newest:
                    current, newest = file.path, stat.st_mtime
            total = manifest.total_bytes
            done = min(done + part_bytes(root, manifest.files), total)
            stale_bytes = 0
            try:
                for path in (root / ".cache" / "huggingface" / "download").rglob("*.incomplete"):
                    if path.is_file():
                        stale_bytes += path.stat().st_size
            except OSError:
                pass
```

`_finish` 里成功分支 `self._purge_incomplete()` 之后加一行 `self._purge_attempt_files()`，并新增方法：

```python
    def _purge_attempt_files(self) -> None:
        """After a verified finish the parts directory and attempt manifest are empty husks."""
        model = self._model
        if model is None:
            return
        shutil.rmtree(Path(self._resolve_paths().models_root) / model.relpath / ".cache" / "localmodeldesk",
                      ignore_errors=True)
```

`desk/resources/service.py`：删除整个 `class _InjectableDownloader`，并把 `ResourcesService.__init__` 中的 `self._downloader = _InjectableDownloader(` 改为 `self._downloader = Downloader(`（参数不变）。

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_resources_downloader.py tests/test_resources_service.py tests/test_resources_http.py tests/test_e2e_fakes.py tests/test_e2e_scripts.py -q`
Expected: PASS。若 `tests/test_resources_http.py` / `test_resources_service.py` 的 manifest fetcher 在某个用例里抛错并期望下载仍能开始，把期望改为 503 `manifest_unavailable`（这是有意的行为改变：没有清单就不知道该下什么）。

- [ ] **Step 5: Commit**

```bash
git add desk/resources/downloader.py desk/resources/service.py tests/test_resources_downloader.py tests/test_resources_service.py tests/test_resources_http.py
git commit -m "fix(resources): download through the resumable fetcher; parts count as progress (G4, J18)"
```

---

### Task 3: 校验把 `.part` 算作可续传进度

**Files:**
- Modify: `desk/resources/verify.py`
- Test: `tests/test_resources_verify.py`

**Interfaces:**
- Consumes: `part_bytes`（Task 1）
- Produces: `ModelStatus.resumable_bytes: int = 0`；`percent` = `(bytes_local + in_flight + resumable_bytes) / bytes_expected`（上限 100）；只要 `resumable_bytes > 0`，state 至少是 `partial`。

- [ ] **Step 1: Write the failing test**

在 `tests/test_resources_verify.py` 末尾追加：

```python
def test_part_bytes_keep_percent_after_cancel(tmp_path):
    """取消后面板不能从 21% 掉到 0%（cross-exam 2026-09-13 G4）。"""
    from desk.resources.parts import part_path

    directory = model_dir(tmp_path)
    (directory / "tokenizer.json").write_bytes(b"x" * 60)
    part = part_path(directory, "model.safetensors")
    part.parent.mkdir(parents=True)
    part.write_bytes(b"x" * 50)

    status = verify_tree(GLM, MANIFEST, tmp_path)

    assert status.state == "partial"
    assert status.bytes_local == 60
    assert status.resumable_bytes == 50
    assert status.percent == 55.0
    assert status.to_json()["resumable_bytes"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_resources_verify.py -k part_bytes -q`
Expected: FAIL，`AttributeError: 'ModelStatus' object has no attribute 'resumable_bytes'`

- [ ] **Step 3: Write minimal implementation**

`desk/resources/verify.py`：import 加 `from .parts import part_bytes`；`ModelStatus` 末尾加字段 `resumable_bytes: int = 0`；`verify_tree` 中计算段改为：

```python
    fresh, stale = _incomplete_bytes(model_dir, active_since)
    resumable = 0 if not gaps else part_bytes(model_dir, manifest.files)
    in_flight = 0 if not gaps else min(fresh, max(expected_total - local_total - resumable, 0))
    counted = local_total + resumable + in_flight
```

并在 `return ModelStatus(...)` 里加 `resumable_bytes=resumable,`。

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_resources_verify.py tests/test_resources_service.py tests/test_resources_http.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/verify.py tests/test_resources_verify.py
git commit -m "fix(resources): verify counts resumable part bytes so cancel keeps the percent (G4)"
```

---

### Task 4: 面板显示「可续传」、旧残片说明与中文未知原因

**Files:**
- Modify: `desk/static/js/pure/model_status.js`
- Modify: `desk/static/js/panes/resources.js`（非下载中的 meta 行）
- Test: `tests/js/model_status.test.js`、`tests/e2e/test_resources_panel.py`

**Interfaces:**
- Consumes: `status.resumable_bytes`（Task 3）、`status.stale_bytes`（已存在）
- Produces: `rowView(...)` 新字段 `note: string | null`：
  - `resumable_bytes > 0` 且未在下载 → `已下 X 可续传`
  - `stale_bytes > 0` → `另有 Y 旧版残片无法续传，开始下载时会清理`（两者都有时用「；」连接）
- Produces: 未知状态徽章：`reason === "manifest_unavailable"` → `未知：拿不到文件清单`；其它 reason → `未知：${reason}`。

- [ ] **Step 1: Write the failing tests**

在 `tests/js/model_status.test.js` 里把 `unknown：如实带 reason，无控件` 测试改为：

```javascript
test("unknown：中文说明原因，无控件", () => {
  const v = rowView(entry, { ...base, state: "unknown", percent: 0, reason: "manifest_unavailable" });
  assert.equal(v.badge, "未知：拿不到文件清单");
  assert.deepEqual(v.actions, []);
});
```

末尾追加：

```javascript
test("取消后的一半：说明已下多少可续传；旧残片单独说明", () => {
  const v = rowView(entry, { ...base, state: "partial", percent: 21.2, resumable_bytes: 3 * 1024 ** 3, stale_bytes: 0 });
  assert.equal(v.badge, "一半 21%");
  assert.equal(v.note, "已下 3.0 GiB 可续传");
  const w = rowView(entry, { ...base, state: "partial", percent: 5, resumable_bytes: 0, stale_bytes: 2 * 1024 ** 3 });
  assert.equal(w.note, "另有 2.0 GiB 旧版残片无法续传，开始下载时会清理");
  const idle = rowView(entry, { ...base, state: "present", percent: 100 });
  assert.equal(idle.note, null);
});
```

（`formatBytes` 对 ≥1 GiB 输出一位小数，如 `3.0 GiB`。）

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/model_status.test.js`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

`desk/static/js/pure/model_status.js`：

```javascript
  else badge = status.reason === "manifest_unavailable" || !status.reason ? "未知：拿不到文件清单" : `未知：${status.reason}`;
```

（替换原 `else badge = \`未知（...）\`` 行。）在 `return {` 之前加：

```javascript
  const notes = [];
  if (!isDownloading && status.state === "partial" && status.resumable_bytes > 0) notes.push(`已下 ${formatBytes(status.resumable_bytes)} 可续传`);
  if (status.stale_bytes > 0) notes.push(`另有 ${formatBytes(status.stale_bytes)} 旧版残片无法续传，开始下载时会清理`);
```

返回对象里加 `note: notes.length ? notes.join("；") : null,`。

`desk/static/js/panes/resources.js`：非下载中分支改为：

```javascript
      meta.textContent = [`预计 ${view.sizeText} · 占用 ${view.diskText}`, view.note].filter(Boolean).join(" · ");
```

- [ ] **Step 4: Add an e2e check**

在 `tests/e2e/test_resources_panel.py` 末尾追加（沿用该文件的 `_row`、`harness.seeded`、`harness.download_control`）：

```python
def test_cancelled_download_keeps_percent_and_says_resumable(page, tmp_path, wait_until):
    from desk.resources.parts import part_path

    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.get_by_text("资源", exact=True).click()
        key = next(key for key, state in harness.seeded.items() if state == "missing")
        row = _row(page, key)

        row.get_by_role("button", name="下载").click()
        wait_until(lambda: len(harness.download_control.spawns) == 1)
        destination = harness.download_control.dest_dir(harness.download_control.spawns[0])
        part = part_path(destination, "weights/a.safetensors")
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(b"x" * 300)

        row.get_by_role("button", name="取消").click()
        wait_until(lambda: harness.download_control.handle.terminated)
        harness.download_control.exit_terminated()
        page.get_by_role("button", name="重新校验").click()

        expect(row).to_contain_text("30%")
        expect(row.locator(".res-meta")).to_contain_text("可续传")
        expect(row.get_by_role("button", name="续传")).to_be_visible()
        assert part.stat().st_size == 300
```

（`desk/testing/seed.py` 的 `MANIFEST_FILES` 为 `a.safetensors` 600 字节 + `b.safetensors` 400 字节，300 字节即 30%；现有 `test_resources_panel_download_cancel_resume_and_finish` 用同一算法。）

- [ ] **Step 5: Run tests**

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/e2e/test_resources_panel.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/pure/model_status.js desk/static/js/panes/resources.js tests/js/model_status.test.js tests/e2e/test_resources_panel.py
git commit -m "fix(ui): resources pane says how much is resumable and explains old leftovers (J18, G3)"
```

---

### Task 5: 服务关闭时取消在途下载

**Files:**
- Modify: `desk/resources/downloader.py`（`close`）
- Modify: `desk/resources/service.py`（`close`）
- Modify: `desk/runtime.py`（`ProductionRuntime.resources`、`shutdown`、`build_runtime` 返回）
- Test: `tests/test_resources_downloader.py`、`tests/test_production_runtime.py`

**Interfaces:**
- Consumes: Plan A 的 `ProductionRuntime(app, gateway, llm, media)` 与 `test_shutdown_closes_media_before_llm`
- Produces: `Downloader.close(timeout_s: float = 3.0) -> None`、`ResourcesService.close() -> None`；`ProductionRuntime(app, gateway, llm, media, resources)`，shutdown 顺序 `gateway → resources → media → llm → app`。

- [ ] **Step 1: Write the failing tests**

`tests/test_resources_downloader.py` 末尾追加：

```python
def test_close_terminates_a_running_download_and_keeps_parts(tmp_path):
    downloader, control, _events = _downloader(tmp_path)
    downloader.start("h3")
    part = part_path(tmp_path / "models" / "minimax-h3", "weights/a.bin")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"xx")

    closer = threading.Thread(target=downloader.close, kwargs={"timeout_s": 2.0})
    closer.start()
    _wait_for(lambda: control.handle.terminated)
    control.exit_terminated()
    closer.join(3.0)

    assert not closer.is_alive()
    assert part.exists()
```

（顶部补 `import threading`。）

`tests/test_production_runtime.py` 里 Plan A 写的 `test_shutdown_closes_media_before_llm` 改为：

```python
def test_shutdown_closes_downloads_and_media_before_llm(tmp_path, monkeypatch):
    _configured_data_root(tmp_path, monkeypatch)
    runtime = build_runtime(port=0)
    order = []
    runtime.gateway.stop = lambda: order.append("gateway")
    runtime.resources.close = lambda: order.append("resources")
    runtime.media.close = lambda: order.append("media")
    runtime.llm.close = lambda: order.append("llm")
    real_app_shutdown = runtime.app.shutdown
    runtime.app.shutdown = lambda: (order.append("app"), real_app_shutdown())
    runtime.start_background()
    runtime.shutdown()
    runtime.shutdown()
    assert order == ["gateway", "resources", "media", "llm", "app"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_resources_downloader.py -k close tests/test_production_runtime.py -k shutdown -q`
Expected: FAIL（`close` 不存在）

- [ ] **Step 3: Write the implementation**

`desk/resources/downloader.py` 新增：

```python
    def close(self, timeout_s: float = 3.0) -> None:
        """Stop a running fetch on shutdown; its .part files stay for the next resume."""
        with self._lock:
            handle = self._handle
            running = handle is not None and self._progress.state == "running"
        if not running:
            return
        try:
            self.cancel()
        except NotDownloadingError:
            return
        deadline = time.monotonic() + timeout_s
        while handle.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if handle.poll() is None:
            handle.kill()
```

`desk/resources/service.py` 新增：

```python
    def close(self) -> None:
        self._downloader.close()
```

`desk/runtime.py`：dataclass 字段在 `media: MediaService` 后加 `resources: ResourcesService`；`shutdown` 在 `self.gateway.stop()` 后加 `self.resources.close()`；`build_runtime` 返回改为 `ProductionRuntime(app, gateway, llm, media, resources)`。

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/downloader.py desk/resources/service.py desk/runtime.py tests/test_resources_downloader.py tests/test_production_runtime.py
git commit -m "fix(resources): shutdown stops an in-flight download and keeps its parts (P4)"
```

---

### Task 6: 构建包里确认脚本在位，真机复核 J18

**Files:**
- Modify: `scripts/verify-app.sh`（新增一条存在性检查）
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

在 `tests/test_packaging.py` 末尾追加（该文件已有读取脚本文本的辅助；若没有，直接读文件）：

```python
def test_verify_app_checks_the_resumable_fetcher_is_bundled():
    text = (REPO / "scripts" / "verify-app.sh").read_text(encoding="utf-8")
    assert "desk/resources/fetch_cli.py" in text
```

（`REPO` 已由 `packaging_fixture` 导入。）

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_packaging.py -k fetcher -q`
Expected: FAIL

- [ ] **Step 3: Add the check**

`scripts/verify-app.sh` 的 V5 结构项循环改为：

```bash
for path in "$RES/desk" "$RES/desk/resources/fetch_cli.py" "$RES/pylibs/desk" "$RES/pylibs/music" "$RES/pylibs/h3" \
            "$RES/bundle.json" "$RES/AppIcon.icns"; do
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packaging.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/verify-app.sh tests/test_packaging.py
git commit -m "build: verify-app requires the resumable fetcher in the bundle"
```

- [ ] **Step 6: 真机复核 J18（只动一个未下载的模型）**

1. `curl -s 127.0.0.1:8766/api/resources/status | python3 -m json.tool` 找一个 `state` 为 `missing` 或 `partial` 的模型（2026-09-13 run 用的是 `superqwen`，若它已 `present` 就换一个没下的；**不得**挑已完整的模型）。
2. 构建隔离副本（数据根 `/tmp/lmd-planC-iso/data`，模型根沿用 `~/LocalModelDesk`，端口 8839），在资源页点「下载」，等面板显示 ≥15%，记下百分比 P 与 `find <模型目录>/.cache/localmodeldesk/parts -name '*.part' -exec stat -f '%z %N' {} +`。
3. 点「取消」。Expected: 徽章仍为「一半 P%」附近（±1%），meta 含「可续传」，`.part` 文件大小不变。
4. 退出副本 app 再重开。Expected: 同上。
5. 点「续传」。Expected: 1 秒后 `download/status` 的 `bytes_done` ≥ 取消时的值；`.part` 文件大小从原值继续增长而非归零；完成后 `state=present`、`.cache/localmodeldesk` 目录已删除。
6. 清理：`pkill -f 'lmd-planC-iso'; rm -rf /tmp/lmd-planC /tmp/lmd-planC-iso`（**不删除**模型目录）。
