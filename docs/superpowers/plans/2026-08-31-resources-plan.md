# resources 模块实现计划（Resources Implementation Plan）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 `desk/resources/`：模型目录单点、按 HF 清单的真实完整度校验、hf CLI 下载续传、删除与磁盘核算，暴露 registry 的 12 个 resources 接口。

**Architecture:** catalog 零 I/O、verify 纯函数；一切副作用（网络 fetch、hf 子进程、磁盘遍历）走可注入接口（fetcher / executor / clock / thread_factory / sleep），单测全部注入假件跑在 `tmp_path`。`ResourcesService` 门面装配各件；HTTP 层只做 JSON 编解码 + 错误码映射，由台面服务组合根挂载。

**Tech Stack:** Python 3.14 标准库 only（dataclasses / threading / urllib / os.statvfs），pytest。零新依赖。

**Spec:** `docs/superpowers/specs/2026-08-31-resources-spec.md`（设计：`docs/superpowers/specs/2026-08-31-resources-design.md`）

## Global Constraints

- **绝不触碰真实权重**：`/Users/aa/LocalModelDesk/llms`、`/Users/aa/LocalModelDesk/minimax-h3`、`/Users/aa/LocalModelDesk/minimax-music3`、`/Users/aa/LocalModelDesk/outputs` 在任何测试/验收中只读都不行——全部用 `tmp_path`。
- 测试**不触网、不真跑 hf、不加载模型**；验收命令一律 `python3 -m pytest <file>`（pytest 零收集 exit 5，非 vacuous）。
- `desk/` 内禁止 `sys.exit` / `raise SystemExit`、禁止 `Path.home()` / `expanduser`、禁止自建 `logging.FileHandler`（foundation 仓库级不变量；本模块路径一律来自注入的 `resolve_paths`，日志一律 `logging.getLogger(__name__)`）。
- 错误保持错误：结构化 `ResourceError(code, http_status)`，无任何「假装 present / 假装下载完成」的回退路径。
- 消费接口的形状（Phase 1.2 已对齐）：`resolve_paths()` 返回的对象至少有 `models_root: Path`、`data_root: Path`、`hf_cmd: tuple[str, ...]` 三个属性（foundation `data:pathRoots` 的子集；测试用 `SimpleNamespace` 注入）；`can_start_heavy()` 返回 `{"ok": bool, "reason": {"code": str, "message": str}?}`（arbiter `api:canStartHeavy` 对媒体类 kind 的回答）。
- census A01/A02 的两份旧目录（`initModels.sh`、`media-gui/server.py`）由 **packaging R-packaging-08** 删除，不在本模块动手；本模块用 T-resources-13 的仓库级守卫测试把「除这两个待删文件外不得再有第二份目录」钉死，待删文件消失后守卫自动收紧为全仓零残留。
- `git push` 未授权；每任务本地 commit。

## 文件结构

```
desk/
  __init__.py                    # 空包标记（若 foundation 已建则不动）
  resources/
    __init__.py                  # 包 docstring，无 re-export
    errors.py                    # ResourceError 体系（code + http_status）
    catalog.py                   # 目录单点：8 条 ModelEntry（R-01）
    manifest.py                  # HF 清单：fetch / 缓存 / 降级（R-02）
    disk.py                      # dir_bytes / volume_free / DiskUsage（R-04）
    verify.py                    # verify_tree 纯函数 → ModelStatus（R-02/03）
    events.py                    # 进程内事件订阅点
    downloader.py                # 单飞下载器：hf 子进程 + 采样 + 取消（R-05/06/07/09）
    service.py                   # ResourcesService 门面 + deleteModel（R-08）
    http.py                      # /api/resources/* 路由表
scripts/
  verify_real_models.py          # RG-1 人工验证助手（只读 stat 真树；人工跑）
  resources_resume_smoke.sh      # RG-2 人工断点续传冒烟（小 repo，临时目录）
tests/
  conftest.py                    # 仓库根入 sys.path
  test_resources_errors.py
  test_resources_catalog.py
  test_resources_manifest.py
  test_resources_disk.py
  test_resources_verify.py
  test_resources_events.py
  test_resources_downloader.py
  test_resources_service.py
  test_resources_delete.py
  test_resources_http.py
  test_resources_invariants.py
```

---

### Task 1（T-resources-01）: 错误体系与包骨架

**Files:**
- Create: `desk/__init__.py`（若不存在；内容为空）
- Create: `desk/resources/__init__.py`
- Create: `desk/resources/errors.py`
- Create: `tests/conftest.py`（若不存在）
- Test: `tests/test_resources_errors.py`

**Interfaces:**
- Produces: `ResourceError(message, detail=None)`，类属性 `code: str`、`http_status: int`，实例属性 `message`、`detail`，方法 `to_json() -> {"error": {"code", "message", "detail"?}}`；子类 `UnknownModelError(404)`、`ManifestUnavailableError(503)`、`DownloadBusyError(409)`、`MediaBusyError(409)`、`NotDownloadingError(409)`、`HfCliMissingError(503)`、`ConfirmRequiredError(400)`、`PathEscapeError(400)`。后续所有任务的异常都从这里来。

- [ ] **Step 1: Write the failing test**

`tests/conftest.py`（若 foundation 已创建同内容文件则保留原样）：

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

`tests/test_resources_errors.py`：

```python
import pytest

from desk.resources.errors import (
    ConfirmRequiredError, DownloadBusyError, HfCliMissingError, ManifestUnavailableError,
    MediaBusyError, NotDownloadingError, PathEscapeError, ResourceError, UnknownModelError)


def test_error_codes_and_http_status():
    cases = [
        (UnknownModelError, "unknown_model", 404),
        (ManifestUnavailableError, "manifest_unavailable", 503),
        (DownloadBusyError, "download_in_progress", 409),
        (MediaBusyError, "media_busy", 409),
        (NotDownloadingError, "not_downloading", 409),
        (HfCliMissingError, "hf_cli_missing", 503),
        (ConfirmRequiredError, "confirm_required", 400),
        (PathEscapeError, "path_escape", 400),
    ]
    for cls, code, status in cases:
        err = cls("boom")
        assert isinstance(err, ResourceError)
        assert err.code == code
        assert err.http_status == status


def test_to_json_envelope_with_detail():
    err = MediaBusyError("busy", detail={"code": "media_busy", "message": "video running"})
    assert err.to_json() == {
        "error": {"code": "media_busy", "message": "busy",
                  "detail": {"code": "media_busy", "message": "video running"}}}


def test_to_json_without_detail_omits_key():
    assert UnknownModelError("nope").to_json() == {
        "error": {"code": "unknown_model", "message": "nope"}}


def test_errors_are_raisable():
    with pytest.raises(ResourceError):
        raise DownloadBusyError("x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_errors.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk'`）

- [ ] **Step 3: Write minimal implementation**

`desk/__init__.py`：空文件。`desk/resources/__init__.py`：

```python
"""resources：模型目录、真实完整度校验、下载续传、删除与磁盘核算（R-resources-01..09）。"""
```

`desk/resources/errors.py`：

```python
"""Typed resources errors: machine-readable code + HTTP status (design §错误处理)."""
from __future__ import annotations


class ResourceError(Exception):
    code = "resource_error"
    http_status = 500

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_json(self) -> dict:
        err: dict = {"code": self.code, "message": self.message}
        if self.detail:
            err["detail"] = self.detail
        return {"error": err}


class UnknownModelError(ResourceError):
    code = "unknown_model"
    http_status = 404


class ManifestUnavailableError(ResourceError):
    code = "manifest_unavailable"
    http_status = 503


class DownloadBusyError(ResourceError):
    code = "download_in_progress"
    http_status = 409


class MediaBusyError(ResourceError):
    code = "media_busy"
    http_status = 409


class NotDownloadingError(ResourceError):
    code = "not_downloading"
    http_status = 409


class HfCliMissingError(ResourceError):
    code = "hf_cli_missing"
    http_status = 503


class ConfirmRequiredError(ResourceError):
    code = "confirm_required"
    http_status = 400


class PathEscapeError(ResourceError):
    code = "path_escape"
    http_status = 400
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_errors.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/__init__.py desk/resources/__init__.py desk/resources/errors.py tests/conftest.py tests/test_resources_errors.py
git commit -m "feat(resources): typed error hierarchy with HTTP status mapping"
```

---

### Task 2（T-resources-02）: catalog 目录单点

**Files:**
- Create: `desk/resources/catalog.py`
- Test: `tests/test_resources_catalog.py`

**Interfaces:**
- Consumes: `UnknownModelError`（Task 1）
- Produces: `ModelEntry`（frozen dataclass：`key, name, group, hf_repo, relpath, gb, vision=False, quant=None, params=None`，方法 `to_json() -> dict`）；`CATALOG: tuple[ModelEntry, ...]`（恰 8 条）；`list_catalog() -> list[ModelEntry]`；`entry(key: str) -> ModelEntry`（未知 key 抛 `UnknownModelError`）。实现 registry `data:modelEntry` / `api:listCatalog`。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_catalog.py`：

```python
import pytest

from desk.resources.catalog import CATALOG, entry, list_catalog
from desk.resources.errors import UnknownModelError

GOLDEN = [
    ("h3", "video", "appautomaton/minimax-h3-base-8bit-mlx", "minimax-h3", 103.0),
    ("music3", "music", "appautomaton/MiniMax-Music3-MLX", "minimax-music3", 27.0),
    ("glm", "chat", "huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit",
     "llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit", 16.9),
    ("superqwen", "chat", "Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
     "llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit", 16.1),
    ("qwen27", "chat", "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
     "llms/ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit", 29.5),
    ("gemma", "chat", "thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
     "llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit", 33.8),
    ("qwen35", "chat", "mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
     "llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit", 36.8),
    ("llama70", "chat", "divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
     "llms/divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx", 75.0),
]


def test_exactly_eight_entries_matching_golden_list():
    assert [(e.key, e.group, e.hf_repo, e.relpath, e.gb) for e in CATALOG] == GOLDEN


def test_keys_unique_and_group_distribution():
    keys = [e.key for e in CATALOG]
    assert len(set(keys)) == 8
    groups = [e.group for e in CATALOG]
    assert groups.count("video") == 1
    assert groups.count("music") == 1
    assert groups.count("chat") == 6


def test_chat_entries_carry_quant_params_gb():
    for e in CATALOG:
        if e.group == "chat":
            assert e.quant in ("4bit", "8bit")
            assert e.params
            assert e.gb > 0
            assert isinstance(e.vision, bool)


def test_relpaths_are_relative_and_contained():
    for e in CATALOG:
        assert not e.relpath.startswith("/")
        assert ".." not in e.relpath.split("/")


def test_list_catalog_returns_fresh_list():
    listed = list_catalog()
    assert listed == list(CATALOG)
    listed.append("junk")            # 改返回值不得影响 CATALOG
    assert len(CATALOG) == 8


def test_entry_lookup_and_unknown_key():
    assert entry("glm").hf_repo == GOLDEN[2][2]
    assert entry("glm").name == "GLM 4.7 Flash 越狱 4bit"
    with pytest.raises(UnknownModelError):
        entry("does-not-exist")


def test_entry_is_frozen():
    with pytest.raises(Exception):
        entry("h3").gb = 1.0


def test_to_json_is_plain_dict():
    d = entry("superqwen").to_json()
    assert d["key"] == "superqwen"
    assert d["vision"] is True
    assert d["quant"] == "4bit"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_catalog.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.catalog'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/catalog.py`（数据合并自旧 `initModels.sh` CATALOG 的 repo/relpath/size 与旧 `server.py` MODEL_CATALOG 的 name/vision/quant/params/gb；那两份由 packaging R-packaging-08 删除。这是仓库内**唯一**的模型 repo/路径清单，前端经 HTTP 取目录，JS 里不复制）：

```python
"""目录单点（R-resources-01）：8 条 ModelEntry，纯数据、零 I/O。

仓库内唯一的模型 repo/路径清单。旧的两份拷贝（initModels.sh、media-gui/server.py）
由 packaging（R-packaging-08）删除；tests/test_resources_invariants.py 守卫不再出现第三份。"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import UnknownModelError

GROUP_CHAT = "chat"
GROUP_VIDEO = "video"
GROUP_MUSIC = "music"


@dataclass(frozen=True)
class ModelEntry:                 # data:modelEntry
    key: str                      # 短稳定 id
    name: str                     # 展示名（沿用 server.py 的中文名）
    group: str                    # "chat" | "video" | "music"
    hf_repo: str                  # HF 仓库 id
    relpath: str                  # 相对 models_root 的落盘路径
    gb: float                     # 人类可读体积估算
    vision: bool = False          # 仅 chat 组有意义
    quant: str | None = None
    params: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


CATALOG: tuple[ModelEntry, ...] = (
    ModelEntry(key="h3", name="MiniMax H3 视频 8bit", group=GROUP_VIDEO,
               hf_repo="appautomaton/minimax-h3-base-8bit-mlx",
               relpath="minimax-h3", gb=103.0),
    ModelEntry(key="music3", name="MiniMax Music 3", group=GROUP_MUSIC,
               hf_repo="appautomaton/MiniMax-Music3-MLX",
               relpath="minimax-music3", gb=27.0),
    ModelEntry(key="glm", name="GLM 4.7 Flash 越狱 4bit", group=GROUP_CHAT,
               hf_repo="huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit",
               relpath="llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit",
               gb=16.9, vision=False, quant="4bit", params="30B-A3B"),
    ModelEntry(key="superqwen", name="SuperQwen3.8 27B 越狱 4bit", group=GROUP_CHAT,
               hf_repo="Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
               relpath="llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
               gb=16.1, vision=True, quant="4bit", params="27B"),
    ModelEntry(key="qwen27", name="Qwen3.8 27B 越狱 8bit", group=GROUP_CHAT,
               hf_repo="ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
               relpath="llms/ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
               gb=29.5, vision=True, quant="8bit", params="27B"),
    ModelEntry(key="gemma", name="Gemma 4 31B 越狱 8bit 视觉", group=GROUP_CHAT,
               hf_repo="thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               relpath="llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               gb=33.8, vision=True, quant="8bit", params="31B"),
    ModelEntry(key="qwen35", name="Qwen3.6 35B-A3B 越狱 8bit", group=GROUP_CHAT,
               hf_repo="mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               relpath="llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               gb=36.8, vision=False, quant="8bit", params="35B-A3B"),
    ModelEntry(key="llama70", name="Llama 3.3 70B 越狱 8bit", group=GROUP_CHAT,
               hf_repo="divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
               relpath="llms/divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
               gb=75.0, vision=False, quant="8bit", params="70B"),
)


def list_catalog() -> list[ModelEntry]:       # api:listCatalog
    return list(CATALOG)


def entry(key: str) -> ModelEntry:
    for e in CATALOG:
        if e.key == key:
            return e
    raise UnknownModelError(f"unknown model key: {key!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_catalog.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/catalog.py tests/test_resources_catalog.py
git commit -m "feat(resources): single-source model catalog with 8 entries (R-resources-01)"
```

---

### Task 3（T-resources-03）: ManifestStore 缓存与降级

**Files:**
- Create: `desk/resources/manifest.py`
- Test: `tests/test_resources_manifest.py`

**Interfaces:**
- Consumes: `ModelEntry`/`entry`（Task 2）、`ManifestUnavailableError`（Task 1）
- Produces: `ManifestFile(path: str, size: int)`；`Manifest(repo, files: tuple[ManifestFile, ...], fetched_at: str, source: str)`，属性 `total_bytes: int`；`ManifestStore(cache_dir_provider: Callable[[], Path], fetcher: Callable[[str], list[ManifestFile]])`，方法 `get(entry, refresh=False) -> Manifest`。语义：磁盘缓存命中 → `source="cached"` 且保留原 `fetched_at`；fetch 成功 → `source="fresh"` 并原子覆写缓存；fetch 失败有缓存 → 回落缓存；失败且无缓存 → `ManifestUnavailableError`；损坏缓存视同无缓存。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_manifest.py`：

```python
import json

import pytest

from desk.resources.catalog import entry
from desk.resources.errors import ManifestUnavailableError
from desk.resources.manifest import ManifestFile, ManifestStore

GLM = entry("glm")


def make_store(tmp_path, fetcher):
    return ManifestStore(cache_dir_provider=lambda: tmp_path / "manifests", fetcher=fetcher)


def test_fresh_fetch_writes_cache_atomically(tmp_path):
    store = make_store(tmp_path, lambda repo: [ManifestFile("a.safetensors", 100),
                                               ManifestFile("sub/b.bin", 60)])
    m = store.get(GLM)
    assert m.source == "fresh"
    assert m.repo == GLM.hf_repo
    assert m.total_bytes == 160
    raw = json.loads((tmp_path / "manifests" / "glm.json").read_text())
    assert raw["files"] == [{"path": "a.safetensors", "size": 100},
                            {"path": "sub/b.bin", "size": 60}]
    assert not list((tmp_path / "manifests").glob("*.tmp"))


def test_cache_hit_skips_fetch_and_reports_cached(tmp_path):
    calls = []

    def fetcher(repo):
        calls.append(repo)
        return [ManifestFile("a", 1)]

    store = make_store(tmp_path, fetcher)
    first = store.get(GLM)
    second = store.get(GLM)               # refresh=False → 走磁盘缓存，不碰网
    assert calls == [GLM.hf_repo]
    assert second.source == "cached"
    assert second.fetched_at == first.fetched_at
    assert second.files == first.files


def test_fetch_failure_falls_back_to_cache(tmp_path):
    state = {"fail": False}

    def fetcher(repo):
        if state["fail"]:
            raise OSError("network down")
        return [ManifestFile("a", 1)]

    store = make_store(tmp_path, fetcher)
    first = store.get(GLM)
    state["fail"] = True
    fallback = store.get(GLM, refresh=True)
    assert fallback.source == "cached"
    assert fallback.fetched_at == first.fetched_at


def test_fetch_failure_without_cache_raises(tmp_path):
    def fetcher(repo):
        raise OSError("network down")

    with pytest.raises(ManifestUnavailableError) as exc:
        make_store(tmp_path, fetcher).get(GLM)
    assert exc.value.code == "manifest_unavailable"


def test_corrupt_cache_treated_as_missing(tmp_path):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "glm.json").write_text("{ not json")

    def failing(repo):
        raise OSError("down")

    with pytest.raises(ManifestUnavailableError):
        make_store(tmp_path, failing).get(GLM)
    # fetcher 恢复后：损坏缓存被 fresh 结果原子替换，不崩
    m = make_store(tmp_path, lambda repo: [ManifestFile("a", 2)]).get(GLM)
    assert m.source == "fresh"
    raw = json.loads((tmp_path / "manifests" / "glm.json").read_text())
    assert raw["files"] == [{"path": "a", "size": 2}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_manifest.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.manifest'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/manifest.py`（本任务 fetcher 是必传参数；Task 4 再补 `default_fetcher` 并设为默认值）：

```python
"""HF 文件清单：取得 / 缓存 / 降级（R-resources-02）。

降级语义：fetch 成功 → source="fresh" 覆写缓存；失败有缓存 → source="cached" 保留原
fetched_at；失败且无缓存 → ManifestUnavailableError —— 绝不假装校验过。"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .catalog import ModelEntry
from .errors import ManifestUnavailableError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManifestFile:
    path: str        # 仓库内相对路径
    size: int        # 字节数


@dataclass(frozen=True)
class Manifest:
    repo: str
    files: tuple[ManifestFile, ...]
    fetched_at: str          # 成功 fetch 的 ISO 时间戳
    source: str              # "fresh"（刚取到）| "cached"（来自磁盘缓存）

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files)


class ManifestStore:
    """缓存位于 <data root>/manifests/<key>.json；写入用 临时文件 + os.replace 原子替换。"""

    def __init__(self, cache_dir_provider: Callable[[], Path],
                 fetcher: Callable[[str], list[ManifestFile]]):
        self._cache_dir_provider = cache_dir_provider
        self._fetcher = fetcher

    def get(self, entry: ModelEntry, refresh: bool = False) -> Manifest:
        cache_path = Path(self._cache_dir_provider()) / f"{entry.key}.json"
        cached = self._load_cache(cache_path)
        if cached is not None and not refresh:
            return cached
        try:
            files = tuple(self._fetcher(entry.hf_repo))
        except Exception as exc:  # noqa: BLE001 — 任何 fetch 失败都走诚实降级
            if cached is not None:
                log.warning("manifest fetch failed for %s; serving cache from %s: %s",
                            entry.hf_repo, cached.fetched_at, exc)
                return cached
            raise ManifestUnavailableError(
                f"no manifest for {entry.hf_repo}: fetch failed and no cache exists ({exc})"
            ) from exc
        manifest = Manifest(repo=entry.hf_repo, files=files,
                            fetched_at=datetime.now(timezone.utc).isoformat(),
                            source="fresh")
        self._write_cache(cache_path, manifest)
        return manifest

    def _load_cache(self, cache_path: Path) -> Manifest | None:
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            files = tuple(ManifestFile(path=f["path"], size=int(f["size"]))
                          for f in raw["files"])
            return Manifest(repo=raw["repo"], files=files,
                            fetched_at=raw["fetched_at"], source="cached")
        except (OSError, ValueError, KeyError, TypeError):
            return None   # 缓存缺失或损坏 == 无缓存；绝不因此崩

    def _write_cache(self, cache_path: Path, manifest: Manifest) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"repo": manifest.repo, "fetched_at": manifest.fetched_at,
                   "files": [{"path": f.path, "size": f.size} for f in manifest.files]}
        fd, tmp = tempfile.mkstemp(dir=str(cache_path.parent),
                                   prefix=cache_path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, cache_path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_manifest.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/manifest.py tests/test_resources_manifest.py
git commit -m "feat(resources): manifest store with atomic cache and honest degradation (R-resources-02)"
```

---

### Task 4（T-resources-04）: default_fetcher — HF tree API 分页

**Files:**
- Modify: `desk/resources/manifest.py`（追加 `HF_TREE_URL`、`_NEXT_LINK`、`_urllib_get`、`default_fetcher`；`ManifestStore.__init__` 的 `fetcher` 参数改为默认 `default_fetcher`）
- Test: `tests/test_resources_manifest.py`（追加 2 个测试）

**Interfaces:**
- Produces: `default_fetcher(repo: str, http_get=...) -> list[ManifestFile]`（跟随 Link rel="next" 分页；blob 取 `path`+`size`，LFS 文件取 `lfs.size`；只取路径与字节数，不做哈希）；`HF_TREE_URL: str`。`http_get(url) -> (body: bytes, next_url: str | None)` 可注入，默认 `_urllib_get`（urllib，30s 超时）。

- [ ] **Step 1: Write the failing test**

在 `tests/test_resources_manifest.py` 末尾追加：

```python
def test_default_fetcher_follows_pagination_and_uses_lfs_size():
    from desk.resources.manifest import HF_TREE_URL, default_fetcher
    base = HF_TREE_URL.format(repo="org/repo")
    page2 = base + "&cursor=abc"
    pages = {
        base: (json.dumps([
            {"type": "file", "path": "config.json", "size": 123},
            {"type": "file", "path": "model.safetensors", "size": 134,
             "lfs": {"size": 5000000, "oid": "x"}},
            {"type": "directory", "path": "sub"},
        ]).encode(), page2),
        page2: (json.dumps([{"type": "file", "path": "sub/x.bin", "size": 7}]).encode(), None),
    }
    files = default_fetcher("org/repo", http_get=lambda url: pages[url])
    assert files == [ManifestFile("config.json", 123),
                     ManifestFile("model.safetensors", 5000000),
                     ManifestFile("sub/x.bin", 7)]


def test_default_fetcher_is_manifest_store_default():
    import inspect
    from desk.resources.manifest import ManifestStore, default_fetcher
    sig = inspect.signature(ManifestStore.__init__)
    assert sig.parameters["fetcher"].default is default_fetcher
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_manifest.py -v`
Expected: 新增 2 个 FAIL（`ImportError: cannot import name 'default_fetcher'`），原 5 个 PASS

- [ ] **Step 3: Write minimal implementation**

在 `desk/resources/manifest.py` 中，`log = logging.getLogger(__name__)` 之后追加（并在文件头 import 区加入 `import re` 与 `import urllib.request`）：

```python
HF_TREE_URL = "https://huggingface.co/api/models/{repo}/tree/main?recursive=true"
_NEXT_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="next"')


def _urllib_get(url: str) -> tuple[bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "LocalModelDesk"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        m = _NEXT_LINK.search(resp.headers.get("Link") or "")
        return resp.read(), (m.group(1) if m else None)
```

`ManifestFile`/`Manifest` 定义之后、`ManifestStore` 之前追加：

```python
def default_fetcher(repo: str,
                    http_get: Callable[[str], tuple[bytes, str | None]] = _urllib_get
                    ) -> list[ManifestFile]:
    """列出 HF 仓库 main 分支每个 blob 的 路径+字节数，跟随分页；LFS 文件取 lfs.size。
    只取路径与字节数，不做哈希（spec 的完整度基准）。"""
    url: str | None = HF_TREE_URL.format(repo=repo)
    files: list[ManifestFile] = []
    while url:
        body, url = http_get(url)
        for item in json.loads(body):
            if item.get("type") != "file":
                continue
            lfs = item.get("lfs") or {}
            files.append(ManifestFile(path=item["path"],
                                      size=int(lfs.get("size") or item.get("size") or 0)))
    return files
```

`ManifestStore.__init__` 签名改为：

```python
    def __init__(self, cache_dir_provider: Callable[[], Path],
                 fetcher: Callable[[str], list[ManifestFile]] = default_fetcher):
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_manifest.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/manifest.py tests/test_resources_manifest.py
git commit -m "feat(resources): HF tree default_fetcher with pagination and lfs.size"
```

---

### Task 5（T-resources-05）: disk 磁盘核算

**Files:**
- Create: `desk/resources/disk.py`
- Test: `tests/test_resources_disk.py`

**Interfaces:**
- Consumes: `ModelEntry`/`CATALOG`（Task 2）
- Produces: `dir_bytes(path: Path) -> int`（os.walk + lstat 求和，不跟符号链接，缺失→0）；`volume_free(path: Path) -> tuple[int, int]`（(free, total)，路径不存在时向上找最近存在的父目录）；`DiskUsage(models_root: str, free_bytes: int, total_bytes: int, per_model: dict[str, int])` + `to_json()`；`disk_usage(models_root, entries) -> DiskUsage`。实现 registry `api:diskUsage` 的数据面。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_disk.py`：

```python
import os

from desk.resources.catalog import CATALOG
from desk.resources.disk import DiskUsage, dir_bytes, disk_usage, volume_free


def test_dir_bytes_sums_recursively(tmp_path):
    d = tmp_path / "m"
    (d / "sub").mkdir(parents=True)
    (d / "a.bin").write_bytes(b"x" * 100)
    (d / "sub" / "b.bin").write_bytes(b"y" * 60)
    assert dir_bytes(d) == 160


def test_dir_bytes_missing_dir_is_zero(tmp_path):
    assert dir_bytes(tmp_path / "nope") == 0


def test_dir_bytes_does_not_follow_symlinked_dirs(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"z" * 10_000)
    d = tmp_path / "m"
    d.mkdir()
    (d / "a.bin").write_bytes(b"x" * 10)
    os.symlink(outside, d / "link")
    assert dir_bytes(d) < 10_000


def test_volume_free_positive_and_climbs_missing_parents(tmp_path):
    free, total = volume_free(tmp_path / "does" / "not" / "exist")
    assert free > 0
    assert total >= free


def test_disk_usage_per_model_matches_manual_sums(tmp_path):
    root = tmp_path / "models"
    (root / "minimax-h3").mkdir(parents=True)
    (root / "minimax-h3" / "w.safetensors").write_bytes(b"a" * 50)
    usage = disk_usage(root, CATALOG)
    assert isinstance(usage, DiskUsage)
    assert usage.models_root == str(root)
    assert set(usage.per_model) == {e.key for e in CATALOG}
    assert usage.per_model["h3"] == 50
    assert usage.per_model["glm"] == 0
    assert usage.free_bytes > 0 and usage.total_bytes > 0
    assert usage.to_json()["per_model"]["h3"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_disk.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.disk'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/disk.py`：

```python
"""占盘核算 + 卷剩余空间（R-resources-04）。"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .catalog import ModelEntry


def dir_bytes(path: Path) -> int:
    """path 下所有文件 lstat 大小之和；不跟符号链接；不存在 → 0。"""
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.lstat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):   # os.walk 默认不跟目录符号链接
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:
                continue
    return total


def volume_free(path: Path) -> tuple[int, int]:
    """(free_bytes, total_bytes)：statvfs 该路径所在卷；路径不存在时向上取最近存在的父目录。"""
    probe = Path(path)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    st = os.statvfs(probe)
    return st.f_bavail * st.f_frsize, st.f_blocks * st.f_frsize


@dataclass(frozen=True)
class DiskUsage:
    models_root: str
    free_bytes: int          # f_bavail * f_frsize（普通用户可用）
    total_bytes: int
    per_model: dict[str, int]

    def to_json(self) -> dict:
        return asdict(self)


def disk_usage(models_root: Path, entries: Iterable[ModelEntry]) -> DiskUsage:
    free, total = volume_free(models_root)
    per = {e.key: dir_bytes(Path(models_root) / e.relpath) for e in entries}
    return DiskUsage(models_root=str(models_root), free_bytes=free,
                     total_bytes=total, per_model=per)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_disk.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/disk.py tests/test_resources_disk.py
git commit -m "feat(resources): per-model disk accounting and volume free space (R-resources-04)"
```

---

### Task 6（T-resources-06）: verify 纯函数校验

**Files:**
- Create: `desk/resources/verify.py`
- Test: `tests/test_resources_verify.py`

**Interfaces:**
- Consumes: `ModelEntry`（Task 2）、`Manifest`/`ManifestFile`（Task 3）、`dir_bytes`（Task 5）
- Produces: `FileGap(path, expected_size, local_size)`；`ModelStatus(key, state, percent, bytes_expected, bytes_local, disk_bytes, gaps: tuple[FileGap, ...], manifest_source, manifest_fetched_at, reason=None)` + `to_json()`；`verify_tree(entry, manifest, models_root) -> ModelStatus`（纯函数，只 stat 不读内容）；`unknown_status(entry, disk_bytes_) -> ModelStatus`（降级态）。实现 registry `data:modelStatus`。判定：全部 local==expected → present；bytes_local==0 → missing；其余 partial；percent 按**字节** `sum(min(local,expected))/sum(expected)*100`（round 2 位）。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_verify.py`：

```python
import json

from desk.resources.catalog import entry
from desk.resources.manifest import Manifest, ManifestFile
from desk.resources.verify import FileGap, unknown_status, verify_tree

GLM = entry("glm")

MANIFEST = Manifest(
    repo=GLM.hf_repo,
    files=(ManifestFile("model.safetensors", 100),
           ManifestFile("tokenizer.json", 60),
           ManifestFile("sub/weights.bin", 40)),
    fetched_at="2026-08-31T00:00:00+00:00",
    source="fresh")


def model_dir(tmp_path):
    d = tmp_path / GLM.relpath
    (d / "sub").mkdir(parents=True)
    return d


def test_full_tree_is_present(tmp_path):
    d = model_dir(tmp_path)
    (d / "model.safetensors").write_bytes(b"a" * 100)
    (d / "tokenizer.json").write_bytes(b"b" * 60)
    (d / "sub" / "weights.bin").write_bytes(b"c" * 40)
    s = verify_tree(GLM, MANIFEST, tmp_path)
    assert s.state == "present"
    assert s.percent == 100.0
    assert s.gaps == ()
    assert s.bytes_expected == 200
    assert s.bytes_local == 200
    assert s.manifest_source == "fresh"
    assert s.manifest_fetched_at == "2026-08-31T00:00:00+00:00"


def test_half_tree_is_partial_with_byte_percent_and_gaps(tmp_path):
    d = model_dir(tmp_path)
    (d / "model.safetensors").write_bytes(b"a" * 100)      # 完整
    (d / "tokenizer.json").write_bytes(b"b" * 30)          # 短缺：30/60
    # sub/weights.bin 完全缺失
    s = verify_tree(GLM, MANIFEST, tmp_path)
    assert s.state == "partial"
    assert s.bytes_local == 130
    assert s.percent == 65.0                               # 按字节：130/200
    assert s.gaps == (FileGap("tokenizer.json", 60, 30),
                      FileGap("sub/weights.bin", 40, 0))


def test_empty_tree_is_missing(tmp_path):
    s = verify_tree(GLM, MANIFEST, tmp_path)               # 目录根本不存在
    assert s.state == "missing"
    assert s.percent == 0.0
    assert s.bytes_local == 0
    assert len(s.gaps) == 3


def test_junk_files_do_not_change_state_but_count_in_disk_bytes(tmp_path):
    d = model_dir(tmp_path)
    (d / "model.safetensors").write_bytes(b"a" * 100)
    (d / "tokenizer.json").write_bytes(b"b" * 60)
    (d / "sub" / "weights.bin").write_bytes(b"c" * 40)
    (d / "junk.tmp").write_bytes(b"j" * 500)
    s = verify_tree(GLM, MANIFEST, tmp_path)
    assert s.state == "present"
    assert s.percent == 100.0
    assert s.bytes_local == 200
    assert s.disk_bytes == 700


def test_oversized_local_file_is_truncated_in_percent(tmp_path):
    d = model_dir(tmp_path)
    (d / "model.safetensors").write_bytes(b"a" * 120)      # 比清单多 20 字节
    s = verify_tree(GLM, MANIFEST, tmp_path)
    assert s.bytes_local == 100                            # min(local, expected) 截断
    assert s.state == "partial"
    assert FileGap("model.safetensors", 100, 120) in s.gaps


def test_unknown_status_reports_degradation_honestly():
    s = unknown_status(GLM, disk_bytes_=1234)
    assert s.state == "unknown"
    assert s.reason == "manifest_unavailable"
    assert s.percent == 0.0
    assert s.bytes_expected == 0
    assert s.disk_bytes == 1234
    assert s.manifest_source == "none"
    assert s.manifest_fetched_at is None


def test_to_json_is_plain_data(tmp_path):
    s = verify_tree(GLM, MANIFEST, tmp_path)
    payload = s.to_json()
    assert json.dumps(payload)
    assert payload["gaps"][0]["expected_size"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_verify.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.verify'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/verify.py`：

```python
"""纯函数校验：清单 × 本地树 → ModelStatus（R-resources-02/03）。

取代旧的「见到任一 .safetensors 即算齐」（census A20/A21）：present 只能出自
逐文件 路径+字节数 比对；只 stat 不读内容。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .catalog import ModelEntry
from .disk import dir_bytes
from .manifest import Manifest


@dataclass(frozen=True)
class FileGap:
    path: str
    expected_size: int
    local_size: int      # 0 = 完全缺失；0 < local < expected = 短缺；> expected = 超长异常


@dataclass(frozen=True)
class ModelStatus:               # data:modelStatus
    key: str
    state: str                   # "present" | "partial" | "missing" | "unknown"
    percent: float               # 按字节，不是按文件数
    bytes_expected: int
    bytes_local: int             # 逐文件 min(local, expected) 之和
    disk_bytes: int              # 实际占盘（含清单外杂物与 .cache 半成品）
    gaps: tuple[FileGap, ...]
    manifest_source: str         # "fresh" | "cached" | "none"
    manifest_fetched_at: str | None
    reason: str | None = None    # state=="unknown" 时 = "manifest_unavailable"

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["gaps"] = [asdict(g) for g in self.gaps]
        return payload


def verify_tree(entry: ModelEntry, manifest: Manifest, models_root: Path) -> ModelStatus:
    model_dir = Path(models_root) / entry.relpath
    expected_total = manifest.total_bytes
    local_total = 0
    gaps: list[FileGap] = []
    for f in manifest.files:
        try:
            local = (model_dir / f.path).lstat().st_size
        except OSError:
            local = 0
        local_total += min(local, f.size)
        if local != f.size:      # 缺失、短缺、超长——都是对清单的偏离
            gaps.append(FileGap(path=f.path, expected_size=f.size, local_size=local))
    if not gaps:
        state = "present"
    elif local_total == 0:
        state = "missing"
    else:
        state = "partial"
    percent = round(local_total / expected_total * 100.0, 2) if expected_total > 0 else 0.0
    return ModelStatus(
        key=entry.key, state=state, percent=percent,
        bytes_expected=expected_total, bytes_local=local_total,
        disk_bytes=dir_bytes(model_dir), gaps=tuple(gaps),
        manifest_source=manifest.source, manifest_fetched_at=manifest.fetched_at)


def unknown_status(entry: ModelEntry, disk_bytes_: int) -> ModelStatus:
    """R-02 降级：无网且无缓存——绝不假装校验过，也绝不报 present/missing。"""
    return ModelStatus(
        key=entry.key, state="unknown", percent=0.0, bytes_expected=0, bytes_local=0,
        disk_bytes=disk_bytes_, gaps=(), manifest_source="none",
        manifest_fetched_at=None, reason="manifest_unavailable")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_verify.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/verify.py tests/test_resources_verify.py
git commit -m "feat(resources): byte-accurate completeness verification (R-resources-02/03)"
```

---

### Task 7（T-resources-07）: 进程内事件

**Files:**
- Create: `desk/resources/events.py`
- Test: `tests/test_resources_events.py`

**Interfaces:**
- Produces: `ResourceEvents`：`subscribe_progress(fn: Callable[[DownloadProgress], None])`、`subscribe_finished(fn: Callable[[DownloadProgress, ModelStatus | None], None])`、`emit_progress(progress)`、`emit_finished(progress, final_status=None)`。回调异常被捕获记日志，不打断下载。实现 registry `event:downloadProgressed` / `event:downloadFinished`（进程内观察者；运行期消费方是 HTTP 轮询快照，两者同源——Phase 1.2 裁定，无 SSE/WebSocket）。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_events.py`：

```python
from desk.resources.events import ResourceEvents


def test_progress_subscribers_called_in_order():
    ev = ResourceEvents()
    seen = []
    ev.subscribe_progress(lambda p: seen.append(("a", p)))
    ev.subscribe_progress(lambda p: seen.append(("b", p)))
    ev.emit_progress("snapshot")
    assert seen == [("a", "snapshot"), ("b", "snapshot")]


def test_finished_subscribers_receive_progress_and_final_status():
    ev = ResourceEvents()
    seen = []
    ev.subscribe_finished(lambda p, s: seen.append((p, s)))
    ev.emit_finished("progress", "status")
    ev.emit_finished("progress-only")
    assert seen == [("progress", "status"), ("progress-only", None)]


def test_raising_subscriber_does_not_break_the_emit(caplog):
    ev = ResourceEvents()
    seen = []

    def boom(p):
        raise RuntimeError("subscriber bug")

    ev.subscribe_progress(boom)
    ev.subscribe_progress(lambda p: seen.append(p))
    ev.emit_progress("x")                     # 不得上抛
    assert seen == ["x"]
    assert any("downloadProgressed" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_events.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.events'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/events.py`：

```python
"""进程内事件：downloadProgressed / downloadFinished 的订阅点。

运行期唯一消费方是 HTTP 轮询的 data:downloadProgress 快照（与事件载荷同源）；
订阅点作为进程内扩展点保留（registry 词汇冻结）。回调异常绝不打断下载。"""
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)


class ResourceEvents:
    def __init__(self) -> None:
        self._progress: list[Callable] = []
        self._finished: list[Callable] = []

    def subscribe_progress(self, fn: Callable) -> None:   # event:downloadProgressed
        self._progress.append(fn)

    def subscribe_finished(self, fn: Callable) -> None:   # event:downloadFinished
        self._finished.append(fn)

    def emit_progress(self, progress) -> None:
        for fn in list(self._progress):
            try:
                fn(progress)
            except Exception:  # noqa: BLE001 — 观察者不得破坏下载主体
                log.exception("downloadProgressed subscriber failed")

    def emit_finished(self, progress, final_status=None) -> None:
        for fn in list(self._finished):
            try:
                fn(progress, final_status)
            except Exception:  # noqa: BLE001
                log.exception("downloadFinished subscriber failed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_events.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/events.py tests/test_resources_events.py
git commit -m "feat(resources): in-process download event observers"
```

---

### Task 8（T-resources-08）: Downloader — start / 采样进度 / 收尾

**Files:**
- Create: `desk/resources/downloader.py`
- Test: `tests/test_resources_downloader.py`

**Interfaces:**
- Consumes: `entry`（Task 2）、`ManifestStore`/`Manifest`（Task 3/4）、`verify_tree`（Task 6）、`ResourceEvents`（Task 7）、错误类（Task 1）；注入的 `can_start_heavy()`（arbiter `api:canStartHeavy`：`{"ok": bool, "reason": {code, message}?}`）与 `resolve_paths()`（foundation：`.models_root`、`.data_root`、`.hf_cmd`）
- Produces: `DownloadProgress(key, state, bytes_done=0, bytes_total=0, percent=0.0, current_file=None, rate_bps=0.0, eta_seconds=None, started_at=None, error=None)` + `to_json()`；常量 `IDLE`；`Handle`/`Executor` Protocol（`spawn(cmd, cwd=None) -> Handle`；Handle：`poll/terminate/kill/stderr_tail`）；`SubprocessExecutor`；`Downloader(executor, manifest_store, resolve_paths, can_start_heavy, events, clock=time.monotonic, sleep=time.sleep, sample_interval=1.0, thread_factory=threading.Thread)`：`start(key) -> DownloadProgress`、`progress() -> DownloadProgress`、`sample_once() -> DownloadProgress | None`（采样线程循环体；测试直接调用它做确定性步进）。实现 registry `data:downloadProgress` / `api:startDownload`。**cancel 在 Task 9 加。**

- [ ] **Step 1: Write the failing test**

`tests/test_resources_downloader.py`：

```python
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.resources.catalog import entry
from desk.resources.downloader import Downloader
from desk.resources.errors import (DownloadBusyError, HfCliMissingError, MediaBusyError,
                                   NotDownloadingError)
from desk.resources.events import ResourceEvents
from desk.resources.manifest import ManifestFile, ManifestStore

GLM = entry("glm")


class FakeHandle:
    def __init__(self):
        self.rc = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.rc

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def stderr_tail(self):
        return "" if self.rc in (None, 0) else "hf: boom"


class FakeExecutor:
    def __init__(self):
        self.calls = []
        self.handles = []
        self.raise_file_not_found = False

    def spawn(self, cmd, cwd=None):
        if self.raise_file_not_found:
            raise FileNotFoundError("hf")
        self.calls.append(list(cmd))
        handle = FakeHandle()
        self.handles.append(handle)
        return handle


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class NoThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


MANIFEST_FILES = [ManifestFile("a.safetensors", 100), ManifestFile("b.bin", 60)]


def make_downloader(tmp_path, *, can_start_heavy=None, fetcher=None, executor=None,
                    clock=None, hf_cmd=None):
    hf = tmp_path / "bin" / "hf"
    hf.parent.mkdir(parents=True, exist_ok=True)
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    roots = SimpleNamespace(models_root=tmp_path / "models",
                            data_root=tmp_path / "data",
                            hf_cmd=(str(hf),) if hf_cmd is None else hf_cmd)
    store = ManifestStore(cache_dir_provider=lambda: roots.data_root / "manifests",
                          fetcher=fetcher or (lambda repo: list(MANIFEST_FILES)))
    executor = executor if executor is not None else FakeExecutor()
    clock = clock or FakeClock()
    events = ResourceEvents()
    downloader = Downloader(
        executor=executor, manifest_store=store, resolve_paths=lambda: roots,
        can_start_heavy=can_start_heavy or (lambda: {"ok": True}),
        events=events, clock=clock, sleep=lambda s: None,
        sample_interval=1.0, thread_factory=NoThread)
    return downloader, executor, clock, roots, events


def dest_dir(roots):
    return Path(roots.models_root) / GLM.relpath


def test_idle_before_any_download(tmp_path):
    d, *_ = make_downloader(tmp_path)
    p = d.progress()
    assert p.state == "idle"
    assert p.key is None


def test_start_spawns_hf_with_exact_command(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    progress = d.start("glm")
    assert progress.state == "running"
    assert progress.key == "glm"
    assert progress.bytes_total == 160
    assert progress.started_at is not None
    assert executor.calls == [[roots.hf_cmd[0], "download", GLM.hf_repo,
                               "--local-dir", str(dest_dir(roots))]]


def test_second_start_while_running_is_refused(tmp_path):
    d, *_ = make_downloader(tmp_path)
    d.start("glm")
    with pytest.raises(DownloadBusyError):
        d.start("glm")
    with pytest.raises(DownloadBusyError):
        d.start("h3")


def test_media_busy_verdict_refuses_with_arbiter_reason(tmp_path):
    verdict = {"ok": False,
               "reason": {"code": "media_busy", "message": "video job j-1 running"}}
    d, *_ = make_downloader(tmp_path, can_start_heavy=lambda: verdict)
    with pytest.raises(MediaBusyError) as exc:
        d.start("glm")
    assert "media_busy" in str(exc.value)
    assert "video job j-1 running" in str(exc.value)
    assert exc.value.detail == verdict["reason"]


def test_llm_resident_does_not_block_download(tmp_path):
    d, *_ = make_downloader(
        tmp_path, can_start_heavy=lambda: {"ok": True, "action": "evict_then_grant"})
    assert d.start("glm").state == "running"


def test_empty_hf_cmd_fails_fast(tmp_path):
    d, executor, *_ = make_downloader(tmp_path, hf_cmd=())
    with pytest.raises(HfCliMissingError):
        d.start("glm")
    assert executor.calls == []


def test_spawn_file_not_found_maps_to_hf_cli_missing_and_releases_lock(tmp_path):
    executor = FakeExecutor()
    executor.raise_file_not_found = True
    d, executor, *_ = make_downloader(tmp_path, executor=executor)
    with pytest.raises(HfCliMissingError):
        d.start("glm")
    executor.raise_file_not_found = False
    assert d.start("glm").state == "running"     # 单飞锁没有泄漏


def test_manifest_unavailable_still_downloads_with_unknown_total(tmp_path):
    def failing(repo):
        raise OSError("offline")

    d, executor, *_ = make_downloader(tmp_path, fetcher=failing)
    progress = d.start("glm")
    assert progress.state == "running"
    assert progress.bytes_total == 0             # 如实报：总量不可知
    assert progress.percent == 0.0
    assert len(executor.calls) == 1              # hf 自己知道清单，照样下


def test_sampling_measures_bytes_rate_eta_and_current_file(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    d.start("glm")
    d.sample_once()                              # 基线采样：0 字节 @ t0
    dest = dest_dir(roots)
    dest.mkdir(parents=True)
    (dest / "a.safetensors").write_bytes(b"x" * 50)          # 100 字节文件的一半
    cache = dest / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "b.bin.incomplete").write_bytes(b"y" * 30)
    clock.advance(2.0)
    p = d.sample_once()
    assert p.bytes_done == 80                    # 50 + 30 半成品
    assert p.bytes_total == 160
    assert p.percent == 50.0
    assert p.current_file == "a.safetensors"
    assert p.rate_bps == pytest.approx(40.0)     # 80 字节 / 2 秒（EWMA 首样本）
    assert p.eta_seconds == pytest.approx(2.0)   # (160-80)/40


def test_incomplete_bytes_are_capped_at_manifest_total(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    d.start("glm")
    cache = dest_dir(roots) / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "a.safetensors.incomplete").write_bytes(b"x" * 500)   # 超过总量 160
    p = d.sample_once()
    assert p.bytes_done == 160
    assert p.percent == 100.0


def test_progress_returns_self_consistent_snapshot(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    d.start("glm")
    dest = dest_dir(roots)
    dest.mkdir(parents=True)
    (dest / "a.safetensors").write_bytes(b"x" * 100)
    d.sample_once()
    p = d.progress()
    assert p.percent == pytest.approx(p.bytes_done / p.bytes_total * 100)
    assert p.state == "running"


def test_clean_exit_finishes_with_final_verify_in_event(tmp_path):
    d, executor, clock, roots, events = make_downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda p, status: finished.append((p, status)))
    d.start("glm")
    dest = dest_dir(roots)
    dest.mkdir(parents=True)
    (dest / "a.safetensors").write_bytes(b"x" * 100)
    (dest / "b.bin").write_bytes(b"y" * 60)
    executor.handles[0].rc = 0
    final = d.sample_once()
    assert final.state == "finished"
    assert len(finished) == 1
    progress, status = finished[0]
    assert progress.state == "finished"
    assert status is not None and status.state == "present" and status.percent == 100.0
    # 单飞锁已释放：可再次 start（这正是续传的入口，R-05）
    assert d.start("glm").state == "running"


def test_nonzero_exit_fails_with_rc_and_stderr_tail(tmp_path):
    d, executor, clock, roots, events = make_downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda p, s: finished.append(p))
    d.start("glm")
    executor.handles[0].rc = 1
    final = d.sample_once()
    assert final.state == "failed"
    assert final.error["code"] == "download_failed"
    assert final.error["rc"] == 1
    assert "boom" in final.error["stderr_tail"]
    assert [p.state for p in finished] == ["failed"]
    assert d.progress().state == "failed"        # 事后可轮询（R-07）


def test_progress_events_are_throttled_to_one_per_second(tmp_path):
    d, executor, clock, roots, events = make_downloader(tmp_path)
    emitted = []
    events.subscribe_progress(lambda p: emitted.append(p))
    d.start("glm")                               # start 立即发一次
    assert len(emitted) == 1
    clock.advance(0.2)
    d.sample_once()
    assert len(emitted) == 1                     # 节流
    clock.advance(1.0)
    d.sample_once()
    assert len(emitted) == 2


def test_raising_subscribers_do_not_break_completion(tmp_path):
    d, executor, clock, roots, events = make_downloader(tmp_path)

    def boom_progress(p):
        raise RuntimeError("ui bug")

    def boom_finished(p, s):
        raise RuntimeError("ui bug")

    events.subscribe_progress(boom_progress)
    events.subscribe_finished(boom_finished)
    d.start("glm")
    executor.handles[0].rc = 0
    assert d.sample_once().state == "finished"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_downloader.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.downloader'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/downloader.py`：

```python
"""单飞下载器：hf 子进程 + 目录采样进度 + 事件（R-resources-05/07/09；取消在 R-06，见 cancel）。

进度不解析 hf stdout（脆弱私有格式）：以清单口径的目录字节采样为准，
current_file / rate / eta 标注为最佳努力估算。"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .catalog import ModelEntry, entry as catalog_entry
from .errors import (DownloadBusyError, HfCliMissingError, ManifestUnavailableError,
                     MediaBusyError, NotDownloadingError)
from .manifest import Manifest, ManifestStore
from .verify import verify_tree

log = logging.getLogger(__name__)

EWMA_ALPHA = 0.3
EMIT_MIN_INTERVAL = 1.0


class Handle(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def stderr_tail(self) -> str: ...


class Executor(Protocol):
    def spawn(self, cmd: list[str], cwd: Path | None = None) -> Handle: ...


class _PopenHandle:
    def __init__(self, proc: subprocess.Popen, stderr_path: Path):
        self._proc = proc
        self._stderr_path = stderr_path

    def poll(self) -> int | None:
        return self._proc.poll()

    def terminate(self) -> None:
        self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()

    def stderr_tail(self) -> str:
        try:
            return self._stderr_path.read_text(errors="replace")[-2000:]
        except OSError:
            return ""


class SubprocessExecutor:
    """真实执行器：stderr 落到临时文件，失败时取尾部进 error。"""

    def __init__(self, stderr_dir: Path | None = None):
        self._stderr_dir = stderr_dir

    def spawn(self, cmd, cwd=None):
        directory = str(self._stderr_dir) if self._stderr_dir else None
        fd, path = tempfile.mkstemp(prefix="hf-stderr-", suffix=".log", dir=directory)
        stderr = os.fdopen(fd, "wb")
        try:
            proc = subprocess.Popen(list(cmd), cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=stderr)
        finally:
            stderr.close()
        return _PopenHandle(proc, Path(path))


@dataclass(frozen=True)
class DownloadProgress:          # data:downloadProgress
    key: str | None              # 当前（或最后一次）下载的目录项；从未下载过 → None
    state: str                   # "idle" | "running" | "finished" | "cancelled" | "failed"
    bytes_done: int = 0
    bytes_total: int = 0
    percent: float = 0.0
    current_file: str | None = None   # 最佳努力：清单内最近 mtime 且未达 expected 的文件
    rate_bps: float = 0.0             # 采样窗口 EWMA
    eta_seconds: float | None = None
    started_at: str | None = None
    error: dict | None = None         # state=="failed" 时 {code, message, rc, stderr_tail}

    def to_json(self) -> dict:
        return asdict(self)


IDLE = DownloadProgress(key=None, state="idle")


class Downloader:
    KILL_AFTER_SECONDS = 8.0

    def __init__(self, executor, manifest_store: ManifestStore, resolve_paths,
                 can_start_heavy, events, clock=time.monotonic, sleep=time.sleep,
                 sample_interval: float = 1.0, thread_factory=threading.Thread):
        self._executor = executor
        self._manifest_store = manifest_store
        self._resolve_paths = resolve_paths
        self._can_start_heavy = can_start_heavy
        self._events = events
        self._clock = clock
        self._sleep = sleep
        self._sample_interval = sample_interval
        self._thread_factory = thread_factory
        self._lock = threading.Lock()
        self._active = False          # 单飞；直到子进程确认退出才释放
        self._progress: DownloadProgress = IDLE
        self._handle: Handle | None = None
        self._ctx: tuple[ModelEntry, Manifest | None, Path] | None = None
        self._rate_state: tuple[float, int, float] | None = None
        self._last_emit_at: float | None = None

    # -- api:startDownload ---------------------------------------------------
    def start(self, key: str) -> DownloadProgress:
        entry = catalog_entry(key)
        with self._lock:
            if self._active:
                raise DownloadBusyError(
                    "a download is already in progress; at most one runs at a time")
            verdict = self._can_start_heavy() or {}
            if not verdict.get("ok", False):
                reason = verdict.get("reason") or {
                    "code": "media_busy", "message": "heavy work in progress"}
                raise MediaBusyError(
                    f"download refused: {reason.get('code')}: {reason.get('message', '')}",
                    detail=reason)
            roots = self._resolve_paths()
            hf_cmd = tuple(roots.hf_cmd)
            if not hf_cmd or not Path(hf_cmd[0]).exists():
                raise HfCliMissingError(
                    "hf CLI not found (pathRoots.hf_cmd empty or missing executable)")
            try:
                manifest = self._manifest_store.get(entry, refresh=True)
                total = manifest.total_bytes
            except ManifestUnavailableError:
                manifest, total = None, 0    # hf 自己知道清单；总量不可算，如实报出
            dest = Path(roots.models_root) / entry.relpath
            cmd = [*hf_cmd, "download", entry.hf_repo, "--local-dir", str(dest)]
            try:
                handle = self._executor.spawn(cmd, cwd=None)
            except FileNotFoundError as exc:
                raise HfCliMissingError(f"cannot spawn hf CLI: {exc}") from exc
            self._active = True
            self._handle = handle
            self._ctx = (entry, manifest, dest)
            self._rate_state = None
            self._last_emit_at = self._clock()
            self._progress = DownloadProgress(
                key=entry.key, state="running", bytes_total=total,
                started_at=datetime.now(timezone.utc).isoformat())
            snapshot = self._progress
        self._events.emit_progress(snapshot)
        self._thread_factory(target=self._run, daemon=True).start()
        return snapshot

    # -- 采样线程 --------------------------------------------------------------
    def _run(self) -> None:
        while self._is_active():
            self.sample_once()
            if self._is_active():
                self._sleep(self._sample_interval)

    def _is_active(self) -> bool:
        with self._lock:
            return self._active

    def sample_once(self) -> DownloadProgress | None:
        """一次采样迭代（poll + 目录字节统计 + 进度更新）。采样线程循环调用；
        测试直接调用以做确定性步进。无进行中下载 → None。"""
        with self._lock:
            if not self._active or self._ctx is None or self._handle is None:
                return None
            entry, manifest, dest = self._ctx
            handle = self._handle
        rc = handle.poll()
        done, current = self._measure(manifest, dest)
        now = self._clock()
        with self._lock:
            total = self._progress.bytes_total
            rate = self._update_rate(now, done)
            percent = round(done / total * 100.0, 2) if total > 0 else 0.0
            eta = ((total - done) / rate) if (total > 0 and rate > 0 and done < total) else None
            if self._progress.state == "running":
                self._progress = replace(self._progress, bytes_done=done, percent=percent,
                                         current_file=current, rate_bps=rate,
                                         eta_seconds=eta)
            snapshot = self._progress
        if rc is not None:
            return self._finish(rc, entry, handle)
        self._maybe_emit(snapshot, now)
        return snapshot

    def _measure(self, manifest: Manifest | None, dest: Path) -> tuple[int, str | None]:
        if manifest is None:
            return 0, None
        done = 0
        current: str | None = None
        newest = -1.0
        for f in manifest.files:
            try:
                st = (dest / f.path).lstat()
            except OSError:
                continue
            done += min(st.st_size, f.size)
            if st.st_size < f.size and st.st_mtime > newest:
                newest, current = st.st_mtime, f.path
        cache_dir = dest / ".cache" / "huggingface" / "download"
        if cache_dir.is_dir():
            for root_dir, _dirs, names in os.walk(cache_dir):
                for name in names:
                    if not name.endswith(".incomplete"):
                        continue
                    try:
                        done += (Path(root_dir) / name).lstat().st_size
                    except OSError:
                        pass
        return min(done, manifest.total_bytes), current

    def _update_rate(self, now: float, done: int) -> float:
        # 调用方持 self._lock
        if self._rate_state is None:
            self._rate_state = (now, done, 0.0)
            return 0.0
        t0, b0, r0 = self._rate_state
        dt = now - t0
        if dt <= 0:
            return r0
        inst = max(0.0, (done - b0) / dt)
        rate = inst if r0 == 0.0 else (EWMA_ALPHA * inst + (1 - EWMA_ALPHA) * r0)
        self._rate_state = (now, done, rate)
        return rate

    def _maybe_emit(self, snapshot: DownloadProgress, now: float) -> None:
        with self._lock:
            if (self._last_emit_at is not None
                    and now - self._last_emit_at < EMIT_MIN_INTERVAL):
                return
            self._last_emit_at = now
        self._events.emit_progress(snapshot)

    def _finish(self, rc: int, entry: ModelEntry, handle: Handle) -> DownloadProgress:
        final_status = None
        with self._lock:
            prev = self._progress
            if rc == 0:
                final = replace(prev, state="finished")
            else:
                final = replace(prev, state="failed",
                                error={"code": "download_failed", "rc": rc,
                                       "message": f"hf exited with rc={rc}",
                                       "stderr_tail": handle.stderr_tail()})
            self._progress = final
            self._active = False    # 单飞锁只在进程确认退出后释放
            self._handle = None
            self._ctx = None
        if final.state == "finished":
            try:
                roots = self._resolve_paths()
                manifest = self._manifest_store.get(entry)
                final_status = verify_tree(entry, manifest, Path(roots.models_root))
            except ManifestUnavailableError:
                final_status = None
        self._events.emit_finished(final, final_status)
        return final

    # -- 查询 ------------------------------------------------------------------
    def progress(self) -> DownloadProgress:
        with self._lock:
            return self._progress
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_downloader.py -v`
Expected: 15 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/downloader.py tests/test_resources_downloader.py
git commit -m "feat(resources): single-flight hf downloader with sampled progress (R-resources-05/07/09)"
```

---

### Task 9（T-resources-09）: Downloader — cancel / KILL 升级 / 锁保持

**Files:**
- Modify: `desk/resources/downloader.py`
- Test: `tests/test_resources_downloader.py`（追加取消相关测试）

**Interfaces:**
- Produces: `Downloader.cancel() -> DownloadProgress`（无进行中 → `NotDownloadingError`；发 TERM、状态置 cancelled、立即返回；KILL 升级由采样线程在 8 秒后执行；**绝不清理**半成品；单飞锁保持到子进程确认退出）；`Downloader.active_key() -> str | None`（Task 11 的 deleteModel 消费）。实现 registry `api:cancelDownload`。

- [ ] **Step 1: Write the failing test**

在 `tests/test_resources_downloader.py` 末尾追加：

```python
def test_cancel_without_download_is_refused(tmp_path):
    d, *_ = make_downloader(tmp_path)
    with pytest.raises(NotDownloadingError):
        d.cancel()


def test_cancel_sends_term_and_keeps_partials(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    d.start("glm")
    dest = dest_dir(roots)
    dest.mkdir(parents=True)
    (dest / "a.safetensors").write_bytes(b"x" * 50)
    p = d.cancel()
    assert p.state == "cancelled"
    handle = executor.handles[0]
    assert handle.terminated and not handle.killed
    assert (dest / "a.safetensors").read_bytes() == b"x" * 50   # 绝不清理（R-06）


def test_kill_escalation_after_eight_seconds(tmp_path):
    d, executor, clock, *_ = make_downloader(tmp_path)
    d.start("glm")
    d.cancel()
    handle = executor.handles[0]
    clock.advance(7.9)
    d.sample_once()
    assert not handle.killed
    clock.advance(0.2)
    d.sample_once()
    assert handle.killed


def test_start_after_cancel_waits_for_process_exit(tmp_path):
    d, executor, clock, roots, _ = make_downloader(tmp_path)
    d.start("glm")
    d.cancel()
    with pytest.raises(DownloadBusyError):
        d.start("glm")               # 旧 hf 还活着 → 不许并发写同一目录
    executor.handles[0].rc = -15     # 进程终于退出
    final = d.sample_once()
    assert final.state == "cancelled"    # 取消导致的 rc!=0 不是 failed
    assert final.error is None
    assert d.start("glm").state == "running"
    assert len(executor.calls) == 2      # 第二次 spawn = 续传（目的目录未被清）


def test_cancelled_exit_emits_finished_event(tmp_path):
    d, executor, clock, roots, events = make_downloader(tmp_path)
    finished = []
    events.subscribe_finished(lambda p, s: finished.append(p))
    d.start("glm")
    d.cancel()
    executor.handles[0].rc = -15
    d.sample_once()
    assert [p.state for p in finished] == ["cancelled"]


def test_active_key_reports_running_download(tmp_path):
    d, executor, *_ = make_downloader(tmp_path)
    assert d.active_key() is None
    d.start("glm")
    assert d.active_key() == "glm"
    d.cancel()
    assert d.active_key() == "glm"   # 进程未确认退出前仍占用
    executor.handles[0].rc = -15
    d.sample_once()
    assert d.active_key() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_downloader.py -v`
Expected: 新增 6 个 FAIL（`AttributeError: 'Downloader' object has no attribute 'cancel'` 等），原 15 个 PASS

- [ ] **Step 3: Write minimal implementation**

对 `desk/resources/downloader.py` 做四处修改：

(a) `__init__` 中 `self._rate_state ...` 之前加两行状态：

```python
        self._cancelled_at: float | None = None
        self._killed = False
```

(b) `start()` 里设置 `self._active = True` 的同一块中（`self._rate_state = None` 旁）加：

```python
            self._cancelled_at = None
            self._killed = False
```

(c) `sample_once()` 中 `if rc is not None:` 之前的锁块补取消状态快照，整个尾段改为：

```python
        with self._lock:
            total = self._progress.bytes_total
            rate = self._update_rate(now, done)
            percent = round(done / total * 100.0, 2) if total > 0 else 0.0
            eta = ((total - done) / rate) if (total > 0 and rate > 0 and done < total) else None
            if self._progress.state == "running":
                self._progress = replace(self._progress, bytes_done=done, percent=percent,
                                         current_file=current, rate_bps=rate,
                                         eta_seconds=eta)
            elif self._progress.state == "cancelled":
                self._progress = replace(self._progress, bytes_done=done)
            snapshot = self._progress
            cancelled_at = self._cancelled_at
            killed = self._killed
        if rc is not None:
            return self._finish(rc, entry, handle)
        if (cancelled_at is not None and not killed
                and now - cancelled_at >= self.KILL_AFTER_SECONDS):
            handle.kill()                      # TERM 8 秒未退 → KILL 升级
            with self._lock:
                self._killed = True
        self._maybe_emit(snapshot, now)
        return snapshot
```

(d) `_finish()` 的分支头改为（cancelled 保持 cancelled，不算 failed），并在收尾块清理取消状态：

```python
        with self._lock:
            prev = self._progress
            if prev.state == "cancelled":
                final = prev                   # 取消不是失败；半成品保持可续传
            elif rc == 0:
                final = replace(prev, state="finished")
            else:
                final = replace(prev, state="failed",
                                error={"code": "download_failed", "rc": rc,
                                       "message": f"hf exited with rc={rc}",
                                       "stderr_tail": handle.stderr_tail()})
            self._progress = final
            self._active = False    # 单飞锁只在进程确认退出后释放
            self._handle = None
            self._ctx = None
            self._cancelled_at = None
```

(e) 类末尾（`progress()` 之前）加两个公开方法：

```python
    # -- api:cancelDownload ----------------------------------------------------
    def cancel(self) -> DownloadProgress:
        """发 TERM、置 cancelled、立即返回（不阻塞 HTTP 线程）；KILL 升级与
        锁释放由采样线程负责。绝不清理目的目录与 .cache 半成品（R-06）。"""
        with self._lock:
            if not self._active or self._handle is None or self._progress.state != "running":
                raise NotDownloadingError("no download in progress")
            self._cancelled_at = self._clock()
            self._progress = replace(self._progress, state="cancelled")
            handle = self._handle
            snapshot = self._progress
        handle.terminate()
        self._events.emit_progress(snapshot)
        return snapshot

    def active_key(self) -> str | None:
        """单飞占用中的目录项 key（含 cancelled 但进程未确认退出的窗口）；空闲 → None。"""
        with self._lock:
            return self._progress.key if self._active else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_downloader.py -v`
Expected: 21 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/downloader.py tests/test_resources_downloader.py
git commit -m "feat(resources): cancel with TERM->KILL escalation, resumable partials (R-resources-06)"
```

---

### Task 10（T-resources-10）: ResourcesService — verify/catalog/disk/download 装配

**Files:**
- Create: `desk/resources/service.py`
- Test: `tests/test_resources_service.py`

**Interfaces:**
- Consumes: 全部前序组件；注入的 `resolve_paths`（foundation `api:resolvePaths` → `data:pathRoots` 子集：`.models_root`、`.data_root`、`.hf_cmd`）与 `can_start_heavy`（arbiter）
- Produces: `ResourcesService(resolve_paths, can_start_heavy, fetcher=default_fetcher, executor=None, clock=..., sleep=..., sample_interval=1.0, thread_factory=...)`：`list_catalog()`、`verify_model(key, refresh=False) -> ModelStatus`、`verify_all_models(refresh=False) -> list[ModelStatus]`、`disk_usage() -> DiskUsage`、`start_download(key)`、`cancel_download()`、`download_progress()`、属性 `events: ResourceEvents`。实现 registry `api:verifyModel` / `api:verifyAllModels`。manifest 缓存目录 = `<data_root>/manifests`。每次操作现调 `resolve_paths()`，不缓存。**deleteModel 在 Task 11 加。**

- [ ] **Step 1: Write the failing test**

`tests/test_resources_service.py`：

```python
from pathlib import Path
from types import SimpleNamespace

from desk.resources.catalog import CATALOG, entry
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService

GLM = entry("glm")


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        return SimpleNamespace(poll=lambda: None, terminate=lambda: None,
                               kill=lambda: None, stderr_tail=lambda: "")


class NoThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


def make_service(tmp_path, *, fetcher=None, can_start_heavy=None):
    hf = tmp_path / "hf"
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    holder = {"roots": SimpleNamespace(models_root=tmp_path / "models",
                                       data_root=tmp_path / "data",
                                       hf_cmd=(str(hf),))}
    svc = ResourcesService(
        resolve_paths=lambda: holder["roots"],
        can_start_heavy=can_start_heavy or (lambda: {"ok": True}),
        fetcher=fetcher or (lambda repo: [ManifestFile("model.safetensors", 100),
                                          ManifestFile("tokenizer.json", 60)]),
        executor=FakeExecutor(), thread_factory=NoThread)
    return svc, holder


def fill_model(root, entry_, sizes):
    d = Path(root) / entry_.relpath
    d.mkdir(parents=True, exist_ok=True)
    for name, size in sizes.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)
    return d


def test_list_catalog_passthrough(tmp_path):
    svc, _ = make_service(tmp_path)
    assert [e.key for e in svc.list_catalog()] == [e.key for e in CATALOG]


def test_verify_model_present(tmp_path):
    svc, holder = make_service(tmp_path)
    fill_model(holder["roots"].models_root, GLM,
               {"model.safetensors": 100, "tokenizer.json": 60})
    s = svc.verify_model("glm")
    assert s.state == "present" and s.percent == 100.0


def test_verify_model_partial_percent_by_bytes(tmp_path):
    svc, holder = make_service(tmp_path)
    fill_model(holder["roots"].models_root, GLM, {"model.safetensors": 100})
    s = svc.verify_model("glm")
    assert s.state == "partial"
    assert s.percent == 62.5                     # 100 / 160 字节


def test_verify_all_returns_all_eight_and_isolates_manifest_failures(tmp_path):
    def fetcher(repo):
        if repo == GLM.hf_repo:
            raise OSError("offline")
        return [ManifestFile("a", 10)]

    svc, holder = make_service(tmp_path, fetcher=fetcher)
    statuses = svc.verify_all_models()
    assert [s.key for s in statuses] == [e.key for e in CATALOG]
    by_key = {s.key: s for s in statuses}
    assert by_key["glm"].state == "unknown"          # 单条失败不拖垮整体
    assert by_key["glm"].reason == "manifest_unavailable"
    assert by_key["h3"].state == "missing"


def test_disk_usage_covers_all_keys(tmp_path):
    svc, _ = make_service(tmp_path)
    usage = svc.disk_usage()
    assert set(usage.per_model) == {e.key for e in CATALOG}


def test_resolve_paths_is_consulted_on_every_operation(tmp_path):
    svc, holder = make_service(tmp_path)
    fill_model(holder["roots"].models_root, GLM,
               {"model.safetensors": 100, "tokenizer.json": 60})
    assert svc.verify_model("glm").state == "present"
    holder["roots"] = SimpleNamespace(models_root=tmp_path / "elsewhere",
                                      data_root=holder["roots"].data_root,
                                      hf_cmd=holder["roots"].hf_cmd)
    assert svc.verify_model("glm").state == "missing"    # 新根即时生效，无缓存


def test_manifest_cache_lands_under_data_root(tmp_path):
    svc, _ = make_service(tmp_path)
    svc.verify_model("glm")
    assert (tmp_path / "data" / "manifests" / "glm.json").exists()


def test_events_facade_is_exposed(tmp_path):
    svc, _ = make_service(tmp_path)
    seen = []
    svc.events.subscribe_progress(seen.append)
    svc.events.emit_progress("x")
    assert seen == ["x"]


def test_download_wiring_start_progress_cancel(tmp_path):
    svc, _ = make_service(tmp_path)
    assert svc.download_progress().state == "idle"
    assert svc.start_download("glm").state == "running"
    assert svc.download_progress().state == "running"
    assert svc.cancel_download().state == "cancelled"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_service.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.service'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/service.py`：

```python
"""ResourcesService 门面：把 catalog/manifest/verify/disk/downloader 装配成 api:* 接口。

所有路径来自注入的 resolve_paths（foundation api:resolvePaths）；每次操作现调，
不缓存——首运/收编改根后立即生效。"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from . import catalog
from .catalog import CATALOG, ModelEntry
from .disk import DiskUsage, dir_bytes, disk_usage
from .downloader import Downloader, DownloadProgress, SubprocessExecutor
from .errors import ManifestUnavailableError
from .events import ResourceEvents
from .manifest import ManifestStore, default_fetcher
from .verify import ModelStatus, unknown_status, verify_tree


class ResourcesService:
    def __init__(self, resolve_paths: Callable, can_start_heavy: Callable,
                 fetcher: Callable = default_fetcher, executor=None,
                 clock=time.monotonic, sleep=time.sleep,
                 sample_interval: float = 1.0, thread_factory=threading.Thread):
        self._resolve_paths = resolve_paths
        self.events = ResourceEvents()
        self._manifests = ManifestStore(
            cache_dir_provider=lambda: Path(self._resolve_paths().data_root) / "manifests",
            fetcher=fetcher)
        self._downloader = Downloader(
            executor=executor if executor is not None else SubprocessExecutor(),
            manifest_store=self._manifests, resolve_paths=resolve_paths,
            can_start_heavy=can_start_heavy, events=self.events,
            clock=clock, sleep=sleep, sample_interval=sample_interval,
            thread_factory=thread_factory)

    # api:listCatalog
    def list_catalog(self) -> list[ModelEntry]:
        return catalog.list_catalog()

    # api:verifyModel
    def verify_model(self, key: str, refresh: bool = False) -> ModelStatus:
        entry = catalog.entry(key)
        roots = self._resolve_paths()
        model_dir = Path(roots.models_root) / entry.relpath
        try:
            manifest = self._manifests.get(entry, refresh=refresh)
        except ManifestUnavailableError:
            return unknown_status(entry, dir_bytes(model_dir))
        return verify_tree(entry, manifest, Path(roots.models_root))

    # api:verifyAllModels —— 单条 manifest 失败不拖垮整体
    def verify_all_models(self, refresh: bool = False) -> list[ModelStatus]:
        return [self.verify_model(e.key, refresh=refresh) for e in CATALOG]

    # api:diskUsage
    def disk_usage(self) -> DiskUsage:
        return disk_usage(Path(self._resolve_paths().models_root), CATALOG)

    # api:startDownload / api:cancelDownload / data:downloadProgress 轮询
    def start_download(self, key: str) -> DownloadProgress:
        return self._downloader.start(key)

    def cancel_download(self) -> DownloadProgress:
        return self._downloader.cancel()

    def download_progress(self) -> DownloadProgress:
        return self._downloader.progress()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_service.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/service.py tests/test_resources_service.py
git commit -m "feat(resources): ResourcesService facade wiring verify/disk/download"
```

---

### Task 11（T-resources-11）: deleteModel — 确认参数与路径逃逸防护

**Files:**
- Modify: `desk/resources/service.py`
- Test: `tests/test_resources_delete.py`

**Interfaces:**
- Produces: `ResourcesService.delete_model(key, confirm=None) -> {"key": str, "freed_bytes": int}`（`confirm` 必须**等于目标 key**，否则 `ConfirmRequiredError`；resolve 后必须位于 models_root 之下且不等于根，否则 `PathEscapeError`——符号链接逃逸同样被拒；同 key 下载中 → `DownloadBusyError`；目录不存在 → 幂等成功 freed=0）；模块级 `_resolve_delete_target(models_root, entry) -> Path`（防御测试直接调用）。实现 registry `api:deleteModel`。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_delete.py`：

```python
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.resources.catalog import ModelEntry, entry
from desk.resources.errors import (ConfirmRequiredError, DownloadBusyError, PathEscapeError,
                                   UnknownModelError)
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService, _resolve_delete_target

GLM = entry("glm")


class NoThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        return SimpleNamespace(poll=lambda: None, terminate=lambda: None,
                               kill=lambda: None, stderr_tail=lambda: "")


def make_service(tmp_path):
    hf = tmp_path / "hf"
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    roots = SimpleNamespace(models_root=tmp_path / "models", data_root=tmp_path / "data",
                            hf_cmd=(str(hf),))
    svc = ResourcesService(resolve_paths=lambda: roots,
                           can_start_heavy=lambda: {"ok": True},
                           fetcher=lambda repo: [ManifestFile("a", 10)],
                           executor=FakeExecutor(), thread_factory=NoThread)
    return svc, roots


def make_weights(roots, entry_=GLM, size=50):
    d = Path(roots.models_root) / entry_.relpath
    d.mkdir(parents=True, exist_ok=True)
    (d / "w.safetensors").write_bytes(b"x" * size)
    return d


def test_delete_without_confirm_is_refused(tmp_path):
    svc, roots = make_service(tmp_path)
    d = make_weights(roots)
    with pytest.raises(ConfirmRequiredError):
        svc.delete_model("glm")
    with pytest.raises(ConfirmRequiredError):
        svc.delete_model("glm", confirm="yes")   # 布尔式确认不够：必须等于 key
    assert (d / "w.safetensors").exists()        # 目录原样


def test_delete_with_matching_confirm_removes_and_reports_freed_bytes(tmp_path):
    svc, roots = make_service(tmp_path)
    d = make_weights(roots, size=50)
    result = svc.delete_model("glm", confirm="glm")
    assert result == {"key": "glm", "freed_bytes": 50}
    assert not d.exists()


def test_second_delete_is_idempotent(tmp_path):
    svc, roots = make_service(tmp_path)
    make_weights(roots)
    svc.delete_model("glm", confirm="glm")
    assert svc.delete_model("glm", confirm="glm") == {"key": "glm", "freed_bytes": 0}


def test_symlink_escape_is_rejected_and_target_untouched(tmp_path):
    svc, roots = make_service(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "victim.bin").write_bytes(b"v" * 10)
    link_parent = Path(roots.models_root) / Path(GLM.relpath).parent
    link_parent.mkdir(parents=True)
    os.symlink(outside, Path(roots.models_root) / GLM.relpath)
    with pytest.raises(PathEscapeError):
        svc.delete_model("glm", confirm="glm")
    assert (outside / "victim.bin").read_bytes() == b"v" * 10   # 链接目标完好
    assert (Path(roots.models_root) / GLM.relpath).is_symlink() # 链接本身也没动


def test_dotdot_relpath_is_rejected_by_target_resolution(tmp_path):
    evil = ModelEntry(key="evil", name="evil", group="chat", hf_repo="x/y",
                      relpath="../evil", gb=1.0)
    with pytest.raises(PathEscapeError):
        _resolve_delete_target(tmp_path / "models", evil)


def test_relpath_equal_to_root_is_rejected(tmp_path):
    evil = ModelEntry(key="evil", name="evil", group="chat", hf_repo="x/y",
                      relpath=".", gb=1.0)
    with pytest.raises(PathEscapeError):
        _resolve_delete_target(tmp_path / "models", evil)


def test_delete_while_same_key_downloading_is_refused(tmp_path):
    svc, roots = make_service(tmp_path)
    make_weights(roots)
    svc.start_download("glm")
    with pytest.raises(DownloadBusyError):
        svc.delete_model("glm", confirm="glm")


def test_delete_unknown_key(tmp_path):
    svc, _ = make_service(tmp_path)
    with pytest.raises(UnknownModelError):
        svc.delete_model("nope", confirm="nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_delete.py -v`
Expected: FAIL（`ImportError: cannot import name '_resolve_delete_target'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/service.py`：文件头 import 区补 `import shutil`，并把 `.errors` 的 import 行改为：

```python
from .errors import (ConfirmRequiredError, DownloadBusyError, ManifestUnavailableError,
                     PathEscapeError)
```

模块级（`ResourcesService` 类定义之前）加：

```python
def _resolve_delete_target(models_root: Path, entry: ModelEntry) -> Path:
    """resolve 后必须仍在 models_root 之下且不等于根；符号链接逃逸在 resolve 后同样被拒。"""
    root = Path(models_root).resolve()
    target = (Path(models_root) / entry.relpath).resolve()
    if target == root or not target.is_relative_to(root):
        raise PathEscapeError(
            f"refusing to delete: {entry.relpath!r} resolves outside the models root",
            detail={"target": str(target), "models_root": str(root)})
    return target
```

`ResourcesService` 类末尾加：

```python
    # api:deleteModel（R-resources-08）
    def delete_model(self, key: str, confirm: str | None = None) -> dict:
        entry = catalog.entry(key)
        if confirm != entry.key:
            raise ConfirmRequiredError(
                f"deleteModel refused: pass confirm={entry.key!r} to delete this model")
        roots = self._resolve_paths()
        target = _resolve_delete_target(Path(roots.models_root), entry)
        if self._downloader.active_key() == entry.key:
            raise DownloadBusyError(
                f"{entry.key!r} is currently downloading; cancel the download first")
        freed = dir_bytes(target)
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        return {"key": entry.key, "freed_bytes": freed}
```

（本模块从不接收绝对路径参数——只收 catalog key，目标永远由 relpath 推导；resolve 校验兜底符号链接与 `..`。）

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_delete.py -v`
Expected: 8 PASS。回归：`python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_service.py -v` 仍 9 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/service.py tests/test_resources_delete.py
git commit -m "feat(resources): deleteModel with key-confirm and path-escape guard (R-resources-08)"
```

---

### Task 12（T-resources-12）: HTTP 路由层

**Files:**
- Create: `desk/resources/http.py`
- Test: `tests/test_resources_http.py`

**Interfaces:**
- Consumes: `ResourcesService`（Task 10/11）、`ResourceError.to_json()/http_status`（Task 1）
- Produces: `build_routes(service) -> list[tuple[str, str, Handler]]`（`Handler(query: dict, body: dict, **path_params) -> (status: int, payload: dict)`）；`match_route(routes, method, path) -> (handler, params) | None`。端点即设计 §8 的表：GET catalog / GET status(+?refresh) / GET status/{key} / GET download / POST download{key} / POST download/cancel / POST delete{key,confirm} / GET disk。组合根（desk/app.py，foundation 交付）后续用 `add_routes` 挂载这张表——本模块不 import foundation。

- [ ] **Step 1: Write the failing test**

`tests/test_resources_http.py`：

```python
import json
from types import SimpleNamespace

from desk.resources.catalog import CATALOG
from desk.resources.http import build_routes, match_route
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService


class NoThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        return SimpleNamespace(poll=lambda: None, terminate=lambda: None,
                               kill=lambda: None, stderr_tail=lambda: "")


def make_routes(tmp_path):
    hf = tmp_path / "hf"
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    roots = SimpleNamespace(models_root=tmp_path / "models", data_root=tmp_path / "data",
                            hf_cmd=(str(hf),))
    svc = ResourcesService(resolve_paths=lambda: roots,
                           can_start_heavy=lambda: {"ok": True},
                           fetcher=lambda repo: [ManifestFile("a.bin", 10)],
                           executor=FakeExecutor(), thread_factory=NoThread)
    return build_routes(svc), svc, roots


def call(routes, method, path, query=None, body=None):
    matched = match_route(routes, method, path)
    assert matched is not None, f"no route for {method} {path}"
    handler, params = matched
    return handler(query or {}, body or {}, **params)


def test_get_catalog_returns_all_eight(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/catalog")
    assert status == 200
    assert [m["key"] for m in payload["models"]] == [e.key for e in CATALOG]
    json.dumps(payload)                          # 全链路可 JSON 序列化


def test_get_status_bundles_models_and_disk(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status")
    assert status == 200
    assert len(payload["models"]) == 8
    assert payload["disk"]["free_bytes"] > 0
    json.dumps(payload)


def test_get_status_single_key_and_unknown_key_404(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status/glm")
    assert status == 200 and payload["key"] == "glm"
    status, payload = call(routes, "GET", "/api/resources/status/nope")
    assert status == 404
    assert payload["error"]["code"] == "unknown_model"


def test_download_roundtrip_and_conflict(tmp_path):
    routes, svc, roots = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/download")
    assert status == 200 and payload["state"] == "idle"
    status, payload = call(routes, "POST", "/api/resources/download", body={"key": "glm"})
    assert status == 200 and payload["state"] == "running"
    status, payload = call(routes, "POST", "/api/resources/download", body={"key": "h3"})
    assert status == 409
    assert payload["error"]["code"] == "download_in_progress"
    status, payload = call(routes, "POST", "/api/resources/download/cancel")
    assert status == 200 and payload["state"] == "cancelled"


def test_cancel_without_download_is_409(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "POST", "/api/resources/download/cancel")
    assert status == 409
    assert payload["error"]["code"] == "not_downloading"


def test_delete_requires_confirm(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "POST", "/api/resources/delete", body={"key": "glm"})
    assert status == 400
    assert payload["error"]["code"] == "confirm_required"
    status, payload = call(routes, "POST", "/api/resources/delete",
                           body={"key": "glm", "confirm": "glm"})
    assert status == 200
    assert payload == {"key": "glm", "freed_bytes": 0}


def test_get_disk(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/disk")
    assert status == 200
    assert set(payload["per_model"]) == {e.key for e in CATALOG}


def test_match_route_none_for_unknown_path(tmp_path):
    routes, *_ = make_routes(tmp_path)
    assert match_route(routes, "GET", "/api/resources/nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_http.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'desk.resources.http'`）

- [ ] **Step 3: Write minimal implementation**

`desk/resources/http.py`：

```python
"""/api/resources/* 路由表：只做 JSON 编解码 + 错误码→HTTP 状态映射，业务全在 service。

由台面服务组合根（desk/app.py，foundation 交付）挂载；本模块不 import foundation。"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from .errors import ResourceError

Handler = Callable[..., tuple[int, dict]]
Route = tuple[str, str, Handler]     # (method, pattern, handler)；pattern 段可为 "{key}"


def _guarded(fn: Handler) -> Handler:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ResourceError as exc:
            return exc.http_status, exc.to_json()
    return wrapper


def match_route(routes: list[Route], method: str, path: str):
    """返回第一条匹配路由的 (handler, path_params)；无匹配 → None。"""
    parts = [p for p in path.split("?", 1)[0].split("/") if p != ""]
    for m, pattern, handler in routes:
        if m != method:
            continue
        pparts = [p for p in pattern.split("/") if p != ""]
        if len(pparts) != len(parts):
            continue
        params: dict[str, str] = {}
        for pp, actual in zip(pparts, parts):
            if pp.startswith("{") and pp.endswith("}"):
                params[pp[1:-1]] = actual
            elif pp != actual:
                break
        else:
            return handler, params
    return None


def _truthy(value) -> bool:
    return str(value).lower() in ("1", "true", "yes")


def build_routes(service) -> list[Route]:
    @_guarded
    def get_catalog(query, body):
        return 200, {"models": [e.to_json() for e in service.list_catalog()]}

    @_guarded
    def get_status(query, body):
        refresh = _truthy(query.get("refresh", "0"))
        return 200, {
            "models": [s.to_json() for s in service.verify_all_models(refresh=refresh)],
            "disk": service.disk_usage().to_json()}

    @_guarded
    def get_status_one(query, body, key):
        refresh = _truthy(query.get("refresh", "0"))
        return 200, service.verify_model(key, refresh=refresh).to_json()

    @_guarded
    def get_download(query, body):
        return 200, service.download_progress().to_json()

    @_guarded
    def post_download(query, body):
        return 200, service.start_download(str((body or {}).get("key", ""))).to_json()

    @_guarded
    def post_cancel(query, body):
        return 200, service.cancel_download().to_json()

    @_guarded
    def post_delete(query, body):
        body = body or {}
        return 200, service.delete_model(str(body.get("key", "")), body.get("confirm"))

    @_guarded
    def get_disk(query, body):
        return 200, service.disk_usage().to_json()

    return [
        ("GET", "/api/resources/catalog", get_catalog),
        ("GET", "/api/resources/status", get_status),
        ("GET", "/api/resources/status/{key}", get_status_one),
        ("GET", "/api/resources/download", get_download),
        ("POST", "/api/resources/download", post_download),
        ("POST", "/api/resources/download/cancel", post_cancel),
        ("POST", "/api/resources/delete", post_delete),
        ("GET", "/api/resources/disk", get_disk),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_http.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/resources/http.py tests/test_resources_http.py
git commit -m "feat(resources): JSON route table for /api/resources with error mapping"
```

---

### Task 13（T-resources-13）: 仓库级守卫 — 单一目录与弱判定灭绝

**Files:**
- Test: `tests/test_resources_invariants.py`

**Interfaces:**
- Consumes: `CATALOG`（Task 2）
- Produces: 无运行时代码——census A01/A02（双份目录）与 A20/A21（弱完整度判定）的可执行检查点。两个旧文件（`initModels.sh`、`media-gui/server.py`）由 packaging R-packaging-08 删除，删除前是唯一容忍项；删除后本守卫自动收紧为全仓零残留。`tests/` 目录被排除：目录钉死测试（Task 2 的 GOLDEN）本身就是防漂移守卫，不是消费方拷贝。

- [ ] **Step 1: Write the failing test（先写守卫，红在「desk 之外还有第三份」时触发；当下即应绿——它守的是未来）**

`tests/test_resources_invariants.py`：

```python
"""R-resources-01 与 census A01/A02/A20/A21 的仓库级守卫。

initModels.sh 与 media-gui/server.py 是仅有的两份待删旧拷贝（packaging R-packaging-08
负责删除）；在此之外任何文件（JS/HTML/Swift/py/sh 一视同仁）出现目录 repo id 或
弱完整度判定即失败。旧文件删除后，本守卫自动收紧为全仓零残留。"""
import os
from pathlib import Path

from desk.resources.catalog import CATALOG

REPO = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "docs",
             ".venv-desk", ".venv-music3", "llms", "minimax-h3", "minimax-music3",
             "outputs"}
TEXT_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".html", ".css", ".swift", ".json",
                 ".md", ".txt", ".plist", ".yml", ".yaml", ".toml"}

ALLOWED = {"desk/resources/catalog.py"}          # 目录单点本尊
LEGACY = {"initModels.sh", "media-gui/server.py"}  # 待 packaging R-packaging-08 删除
TESTS_PREFIX = "tests/"                          # 钉死测试是守卫，不是消费方拷贝


def iter_text_files():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            p = Path(root) / name
            if p.suffix not in TEXT_SUFFIXES:
                continue
            try:
                if p.stat().st_size > 5_000_000:
                    continue
            except OSError:
                continue
            yield p


def rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def test_no_second_catalog_copy_anywhere():
    needles = [e.hf_repo for e in CATALOG]
    offenders = []
    for p in iter_text_files():
        r = rel(p)
        if r in ALLOWED or r in LEGACY or r.startswith(TESTS_PREFIX):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle in text:
                offenders.append((r, needle))
    assert offenders == [], f"second catalog copy found: {offenders}"


def test_no_weak_presence_checks_outside_legacy():
    offenders = []
    for p in iter_text_files():
        r = rel(p)
        if r in LEGACY or r.startswith(TESTS_PREFIX):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "model_present" in text:
            offenders.append(r)
    assert offenders == [], f"weak presence check found outside legacy files: {offenders}"


def test_no_catalog_arrays_outside_legacy():
    offenders = []
    for p in iter_text_files():
        r = rel(p)
        if r in LEGACY or r in ALLOWED or r.startswith(TESTS_PREFIX):
            continue
        if p.suffix not in {".sh", ".py"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "CATALOG=(" in text or "MODEL_CATALOG" in text:
            offenders.append(r)
    assert offenders == [], f"catalog array found outside legacy files: {offenders}"


def test_legacy_allowlist_entries_are_files_while_present():
    for r in LEGACY:
        p = REPO / r
        if p.exists():          # packaging 删除后自动跳过
            assert p.is_file()
```

- [ ] **Step 2: Run test to verify the guard bites**

Run: `python3 -m pytest /Users/aa/LocalModelDesk/tests/test_resources_invariants.py -v`
Expected: 4 PASS（当下仓库只有 LEGACY 两处旧拷贝）。红测验证：往任意新 `.py` 里临时塞一个 `hf_repo` 字符串（如 `desk/resources/scratch.py` 写入 `"appautomaton/MiniMax-Music3-MLX"`），重跑应 FAIL 并点名该文件；随后删除临时文件恢复绿。

- [ ] **Step 3: Commit**

```bash
git add tests/test_resources_invariants.py
git commit -m "test(resources): repo-wide guard against catalog copies and weak presence checks (A01/A02/A20/A21)"
```

---

### Task 14（T-resources-14, reality_gate）: RG-1 真树全量校验助手与 runbook

**Files:**
- Create: `scripts/verify_real_models.py`

**Interfaces:**
- Consumes: `ResourcesService`（Task 10）
- Produces: 人工验证助手脚本（只读 stat；**只许人工运行**，自动验收永不触碰真树）。runbook 见本文末尾「RG-1 人工验收 runbook」。

- [ ] **Step 1: Write the helper script**

`scripts/verify_real_models.py`：

```python
#!/usr/bin/env python3
"""RG-1 助手：对真实 models 树跑一次 verifyAllModels（只读 stat 扫描）+ diskUsage。

慢（要 stat 整棵 339G 目录树）且依赖真实磁盘状态，因此是 reality gate：
只许人工运行，绝不进自动验收。用法：
    python3 scripts/verify_real_models.py --models-root /Users/aa/LocalModelDesk \
        --data-root /tmp/lmd-rg1 --refresh
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.resources.service import ResourcesService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models-root", required=True,
                    help="真实模型根（现状：/Users/aa/LocalModelDesk，其下有 llms/ minimax-h3/ minimax-music3/）")
    ap.add_argument("--data-root", default=None,
                    help="manifest 缓存目录（默认临时目录，不污染用户数据根）")
    ap.add_argument("--refresh", action="store_true", help="强制重取 HF 清单")
    args = ap.parse_args()
    data_root = Path(args.data_root or tempfile.mkdtemp(prefix="lmd-rg1-"))
    roots = SimpleNamespace(models_root=Path(args.models_root).resolve(),
                            data_root=data_root, hf_cmd=())
    svc = ResourcesService(resolve_paths=lambda: roots,
                           can_start_heavy=lambda: {"ok": True})
    statuses = svc.verify_all_models(refresh=args.refresh)
    disk = svc.disk_usage()
    print(json.dumps({"models": [s.to_json() for s in statuses],
                      "disk": disk.to_json()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify it compiles and the runbook is in place**

Run: `python3 -m py_compile /Users/aa/LocalModelDesk/scripts/verify_real_models.py && grep -q "RG-1 人工验收 runbook" /Users/aa/LocalModelDesk/docs/superpowers/plans/2026-08-31-resources-plan.md && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_real_models.py
git commit -m "chore(resources): RG-1 helper for human verification against the real model tree"
```

---

### Task 15（T-resources-15, reality_gate）: RG-2 真实断点续传冒烟脚本与 runbook

**Files:**
- Create: `scripts/resources_resume_smoke.sh`

**Interfaces:**
- Produces: 人工断点续传冒烟脚本（真实网络 + 真实 hf CLI + 小 repo + 临时目录；**只许人工运行**）。runbook 见本文末尾「RG-2 人工验收 runbook」。R-05 的「已完整文件不得重下」由 hf CLI 原生行为承担，FakeExecutor 测不到它——这是发布前必做一次的真实验证点。

- [ ] **Step 1: Write the helper script**

`scripts/resources_resume_smoke.sh`：

```bash
#!/bin/bash
# RG-2 助手：真实断点续传冒烟（人工运行；真实网络 + 真实 hf CLI）。
# 用一个 <1G 的小 HF repo 与临时目录验证：中断后重跑，已完整文件被跳过、
# .incomplete 半成品被续传而非从零重下。临时目录不进 models_root，事后手工删除。
set -euo pipefail

REPO="${1:-hf-internal-testing/tiny-random-gpt2}"
DEST="${DEST_OVERRIDE:-$(mktemp -d /tmp/lmd-rg2.XXXXXX)}"

echo "== RG-2 resume smoke =="
echo "repo: $REPO"
echo "dest: $DEST"
echo "第一遍下载中途按 Ctrl-C 中断；然后用同一目录重跑："
echo "  DEST_OVERRIDE=$DEST bash scripts/resources_resume_smoke.sh $REPO"
echo

hf download "$REPO" --local-dir "$DEST"

echo
echo "完成。观察上方 hf 输出：已完整文件应被跳过（秒过），.incomplete 应续传。"
echo "清理：rm -rf $DEST"
```

- [ ] **Step 2: Verify the script parses and the runbook is in place**

Run: `bash -n /Users/aa/LocalModelDesk/scripts/resources_resume_smoke.sh && grep -q "RG-2 人工验收 runbook" /Users/aa/LocalModelDesk/docs/superpowers/plans/2026-08-31-resources-plan.md && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/resources_resume_smoke.sh
git commit -m "chore(resources): RG-2 real resume smoke helper for pre-release verification"
```

---

## RG-1 人工验收 runbook（T-resources-14）

**目的**：对真实 8 项跑一次 `verifyAllModels`，与磁盘吻合（spec 验收取向最后一条）。
**为什么是 reality gate**：要 stat 整棵 339G 目录树（慢），且结论取决于真实磁盘状态与 HF 网络；自动验收被授权红线禁止扫描真权重。

**前置**：网络可达 huggingface.co（离线也可跑，结果会如实报 `unknown` + `manifest_unavailable`，那不算失败，算降级语义的现场验证）。

**步骤**：

1. `cd /Users/aa/LocalModelDesk`
2. `python3 scripts/verify_real_models.py --models-root /Users/aa/LocalModelDesk --data-root /tmp/lmd-rg1 --refresh | tee /tmp/lmd-rg1.json`
   （现状真权重就住在仓库根：`llms/`、`minimax-h3/`、`minimax-music3/`，与 catalog relpath 布局一致；脚本只读 stat，不写不删。）
3. 对照 `du`：`du -sk llms minimax-h3 minimax-music3`（KB 计）。
4. 对照 `df`：`df -k /Users/aa/LocalModelDesk`。

**通过判据**：

- 输出含恰好 8 个 model 状态；每项 `state` 为 `present`，或（若某项确实没下全）如实的 `partial` + 非空 `gaps` + 按字节的 `percent`；**不允许**出现「半个 H3 报 present」——若 minimax-h3 目录不完整而报了 present，即 FAIL（这正是 A20/A21 要灭绝的行为）。
- 每项 `bytes_local` 与 `disk_bytes` 同 `du` 的对应子树量级吻合（±5% 内；`disk_bytes` 含杂物允许略大）。
- `disk.free_bytes` 与 `df -k` 的 avail（×1024）吻合（±2% 内，磁盘在动属正常）。
- 断网复跑（可选）：关 Wi-Fi 后不带 `--refresh` 重跑 → 各项 `manifest_source` 应为 `cached` 且结论不变；删掉 `/tmp/lmd-rg1` 再断网跑 → 全部 `unknown` + `reason: manifest_unavailable`，绝无假 present。

**记录**：把 `/tmp/lmd-rg1.json`、`du`/`df` 输出与结论存档进执行记录。

## RG-2 人工验收 runbook（T-resources-15）

**目的**：R-05「中断后再次发起必须续传，已完整的文件不得重下」的真实验证。单测里 hf 是 FakeExecutor，跳过/续传是 hf CLI 的原生行为，必须真跑一次。
**为什么是 reality gate**：需要真实网络与真实 hf 二进制，且中断时机靠人手。

**步骤**：

1. `cd /Users/aa/LocalModelDesk`
2. `bash scripts/resources_resume_smoke.sh` —— 记下它打印的 `dest: /tmp/lmd-rg2.XXXXXX`。
3. 传输进行中（进度条走到中途）按 **Ctrl-C** 中断。
4. `ls -la <dest> <dest>/.cache/huggingface/download/ 2>/dev/null` —— 应看到已完成的文件和/或 `*.incomplete` 半成品；**不得**为空目录。
5. 用脚本提示的命令带 `DEST_OVERRIDE=<dest>` 重跑同一 repo。
6. 观察第二遍 hf 输出。

**通过判据**：

- 第二遍中，第一遍已完整落盘的文件被瞬间跳过（无重新传输）；
- `.incomplete` 半成品从中断点续传（第二遍总传输量明显小于 repo 全量）；
- 结束后 `<dest>` 内文件齐全；
- 若把默认小 repo 换成任一 catalog 项做全量验证，**必须**另指临时目录，绝不可指向真实 models 根。

**清理**：`rm -rf <dest>`（只删这次冒烟的临时目录本身）。

**记录**：两遍 hf 输出各截尾 30 行与结论存档。

---

## Self-Review

- **Spec coverage**：R-01→T2+T13；R-02→T3+T4+T6（降级 unknown 语义 T6/T10）；R-03→T6；R-04→T5；R-05→T8（同命令重跑=续传入口）+T9（目的树不清理）+RG-2（hf 原生跳过/续传的真实验证）；R-06→T9；R-07→T8（bytes/total/current/rate/eta + 事后可轮询）；R-08→T11；R-09→T8（单飞 + media_busy 透传 arbiter reason）。12 个 registry 接口全部有唯一归属任务。
- **Placeholder scan**：无 TBD/TODO；所有任务含完整测试与实现代码。
- **Type consistency**：`ModelEntry/Manifest/ManifestFile/ModelStatus/FileGap/DiskUsage/DownloadProgress` 的字段与方法名在 T2–T12 间逐一核对一致；`resolve_paths()` 鸭子类型三属性（models_root/data_root/hf_cmd）在 T8/T10/T11/T12/RG 脚本一致；`can_start_heavy()` 返回形状在 T8 与设计 Assumption 8 一致。
