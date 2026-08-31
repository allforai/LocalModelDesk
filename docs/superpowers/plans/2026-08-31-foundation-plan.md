# 实施计划：foundation

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-foundation-spec.md`（R-foundation-01 ~ 06）
**design** `docs/superpowers/specs/2026-08-31-foundation-design.md`
**暴露** `data:deskConfig` `data:pathRoots` `api:resolvePaths` `api:readConfig` `api:writeConfig` `api:completeFirstRun` `api:adoptLegacyModels`
**消费** 无（根模块）

## 约定

- 每个任务都是完整 TDD 循环：先写测试 → `python3 -m pytest <文件>` 确认**失败**（收集错误或断言失败均可）→ 写实现 → 重跑**通过** → `git commit`。
- 工具链：系统 `python3`（3.14.7）+ pytest 9.0.3，全部标准库实现，零第三方运行时依赖。
- 所有测试用 `tmp_path` / `monkeypatch`，不触网、不碰真实权重（`llms/`、`minimax-h3/`、`minimax-music3/`、`outputs/` 一概不读不写）。
- 全模块 reality_gate 均为 false：纯 pytest 自证，无人工 runbook。
- `desk/foundation/__init__.py` 是公开 API 的唯一 re-export 点，随任务推进逐步追加导出（多个任务 touched 它，由 DAG 串行化）。
- 设计 §5 把 A16 日志行为测试与「损坏配置启动」测试放在 `test_foundation_capabilities.py`；本计划为了任务自包含，分别放进 `test_foundation_paths.py`（T-05）与 `test_foundation_main.py`（T-12），断言内容不变。HTTP 适配层测试同理独立成 `test_foundation_routes.py`（T-11）。

## 任务 DAG

```
T-01 errors
  └─ T-02 config读 ──┬─ T-03 config写 ──┬─ T-06 firstrun ──────────┐
                     └─ T-04 paths ──┬──┴─ T-07 adopt point        │
                                     │        └─ T-08 move同卷      │
                                     │             └─ T-09 move跨卷 ┤
                                     ├─ T-05 setup_logging ────────┤
                                     └─ T-10 capabilities ─────────┴─ T-11 app+routes ─ T-12 __main__ ─ T-13 invariants
```

---

## T-foundation-01 包骨架 + 类型化异常

**目标** 建 `desk/` 包与 `desk/foundation/errors.py`（§2.5 的完整错误词汇），加 `tests/conftest.py` 让 pytest 能从仓库根 import `desk`。

### 1. 失败测试 `tests/conftest.py` + `tests/test_foundation_errors.py`

```python
# tests/conftest.py
"""Make the repo root importable and share the tiny HTTP test helper."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def http_call(app, method, path, body=None):
    """Fire one JSON request at a DeskApp bound to 127.0.0.1:<app.port>."""
    url = f"http://127.0.0.1:{app.port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())
```

```python
# tests/test_foundation_errors.py
import pytest

from desk.foundation import errors

CASES = [
    (errors.ConfigCorruptError, "config_corrupt", 500),
    (errors.NotWritableError, "not_writable", 400),
    (errors.LegacyRootError, "legacy_root_invalid", 400),
    (errors.AdoptConflictError, "adopt_conflict", 409),
    (errors.InsufficientSpaceError, "insufficient_space", 409),
    (errors.AdoptError, "adopt_failed", 500),
]


@pytest.mark.parametrize("cls,code,status", CASES)
def test_error_carries_code_status_payload(cls, code, status):
    err = cls("boom", extra=1)
    assert isinstance(err, errors.FoundationError)
    assert err.code == code
    assert err.http_status == status
    assert err.payload == {"extra": 1}
    assert err.message == "boom"
    assert str(err) == "boom"


def test_space_error_payload_names():
    err = errors.InsufficientSpaceError(
        "short", needed_bytes=10, free_bytes=4, shortfall_bytes=6)
    assert err.payload == {"needed_bytes": 10, "free_bytes": 4, "shortfall_bytes": 6}


def test_catchable_as_foundation_error():
    with pytest.raises(errors.FoundationError):
        raise errors.AdoptError("x", adopted=[], remaining=["llms"])
```

### 2. 实现

```python
# desk/__init__.py
"""LocalModelDesk desk service package."""
```

```python
# desk/foundation/__init__.py
"""foundation — single source of truth for paths and config.

The sole re-export point of the public API; grows as components land.
"""
from .errors import (AdoptConflictError, AdoptError, ConfigCorruptError,
                     FoundationError, InsufficientSpaceError, LegacyRootError,
                     NotWritableError)
```

```python
# desk/foundation/errors.py
"""Typed exceptions for the foundation module (single error vocabulary, §2.5)."""


class FoundationError(Exception):
    """Base: machine-readable code + HTTP status + structured payload."""

    code = "foundation_error"
    http_status = 500

    def __init__(self, message: str, **payload):
        super().__init__(message)
        self.message = message
        self.payload = payload


class ConfigCorruptError(FoundationError):
    code = "config_corrupt"
    http_status = 500


class NotWritableError(FoundationError):
    code = "not_writable"
    http_status = 400


class LegacyRootError(FoundationError):
    code = "legacy_root_invalid"
    http_status = 400


class AdoptConflictError(FoundationError):
    code = "adopt_conflict"
    http_status = 409


class InsufficientSpaceError(FoundationError):
    code = "insufficient_space"
    http_status = 409


class AdoptError(FoundationError):
    code = "adopt_failed"
    http_status = 500
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_errors.py`
**提交** `foundation: package skeleton + typed error vocabulary`

---

## T-foundation-02 config 读取：默认值合并 + needs_setup + 损坏即报错

**目标** `desk/foundation/config.py` 的读侧：`DeskConfig` / `GatewayConfig` 数据形状（`data:deskConfig`）、`read_config`（`api:readConfig`）、缺键逐键补默认（R-foundation-02）、`needs_setup` 派生（R-foundation-03）、损坏 JSON 抛 `ConfigCorruptError`（A3）。

### 1. 失败测试 `tests/test_foundation_config.py`

```python
# tests/test_foundation_config.py
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.foundation import config as config_mod
from desk.foundation.errors import ConfigCorruptError


def make_roots(tmp_path):
    """config.py only needs .data_root and .config_path (duck-typed roots)."""
    return SimpleNamespace(data_root=tmp_path, config_path=tmp_path / "config.json")


def test_missing_file_gives_pure_defaults_and_creates_nothing(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.read_config(roots)
    assert cfg.needs_setup is True
    assert cfg.first_run_done is False
    assert cfg.config_version == 1
    assert cfg.models_root == tmp_path / "models"
    assert cfg.outputs_root == tmp_path / "outputs"
    assert (cfg.gateway.enabled, cfg.gateway.host, cfg.gateway.port) == (True, "0.0.0.0", 8770)
    assert not roots.config_path.exists()          # read never creates the file


def test_partial_file_merges_key_by_key(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({
        "models_root": "/somewhere/models",
        "gateway": {"port": 9000},
    }), encoding="utf-8")
    cfg = config_mod.read_config(roots)
    assert cfg.models_root == Path("/somewhere/models")
    assert cfg.outputs_root == tmp_path / "outputs"       # missing key -> default
    assert cfg.gateway.port == 9000                       # file value wins
    assert cfg.gateway.host == "0.0.0.0"                  # sub-key default fills in
    assert cfg.gateway.enabled is True
    assert cfg.needs_setup is True                        # first_run_done defaulted False


def test_first_run_done_true_clears_needs_setup(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"first_run_done": True}), encoding="utf-8")
    assert config_mod.read_config(roots).needs_setup is False


def test_unknown_keys_land_in_extra(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"future_knob": 42}), encoding="utf-8")
    cfg = config_mod.read_config(roots)
    assert cfg.extra == {"future_knob": 42}
    assert cfg.to_json()["future_knob"] == 42             # survives serialization


def test_corrupt_json_raises_typed_error(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text("{definitely not json", encoding="utf-8")
    with pytest.raises(ConfigCorruptError) as exc:
        config_mod.read_config(roots)
    assert exc.value.code == "config_corrupt"
    assert exc.value.payload["path"] == str(roots.config_path)
    assert exc.value.payload["parse_error"]


def test_non_object_top_level_is_corrupt(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConfigCorruptError):
        config_mod.read_config(roots)


def test_default_config_helper_matches_missing_file(tmp_path):
    roots = make_roots(tmp_path)
    assert config_mod.default_config(tmp_path) == config_mod.read_config(roots)
```

### 2. 实现 `desk/foundation/config.py`（读侧）

```python
# desk/foundation/config.py
"""data:deskConfig — defaults merge, needs_setup, atomic persistence."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigCorruptError

CONFIG_VERSION = 1
_KNOWN_KEYS = {"config_version", "first_run_done", "models_root", "outputs_root", "gateway"}
_GATEWAY_KEYS = {"enabled", "host", "port"}
_LOCK = threading.Lock()


@dataclass(frozen=True)
class GatewayConfig:
    enabled: bool
    host: str
    port: int


@dataclass(frozen=True)
class DeskConfig:
    config_version: int
    first_run_done: bool
    models_root: Path
    outputs_root: Path
    gateway: GatewayConfig
    needs_setup: bool                       # derived; never persisted
    extra: dict = field(default_factory=dict)  # unknown keys, round-tripped verbatim

    def to_json(self) -> dict:
        out = dict(self.extra)
        out.update({
            "config_version": self.config_version,
            "first_run_done": self.first_run_done,
            "models_root": str(self.models_root),
            "outputs_root": str(self.outputs_root),
            "gateway": {"enabled": self.gateway.enabled,
                        "host": self.gateway.host,
                        "port": self.gateway.port},
        })
        return out


def _defaults(data_root: Path) -> dict:
    return {
        "config_version": CONFIG_VERSION,
        "first_run_done": False,
        "models_root": str(data_root / "models"),
        "outputs_root": str(data_root / "outputs"),
        "gateway": {"enabled": True, "host": "0.0.0.0", "port": 8770},
    }


def _load_raw(config_path: Path) -> dict | None:
    """None when absent (not an error, R-foundation-03); ConfigCorruptError when unparsable."""
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigCorruptError(
            f"config.json is corrupt: {config_path}: {exc}",
            path=str(config_path), parse_error=str(exc)) from exc
    if not isinstance(raw, dict):
        raise ConfigCorruptError(
            f"config.json is corrupt: {config_path}: top level is not an object",
            path=str(config_path), parse_error="top level is not an object")
    return raw


def _from_raw(raw: dict | None, data_root: Path) -> DeskConfig:
    defaults = _defaults(data_root)
    merged = dict(defaults)
    file_gateway: dict = {}
    if raw:
        for key, value in raw.items():
            if key == "gateway" and isinstance(value, dict):
                file_gateway = value
            elif key in _KNOWN_KEYS:
                merged[key] = value
    gateway = dict(defaults["gateway"])
    gateway.update({k: v for k, v in file_gateway.items() if k in _GATEWAY_KEYS})
    extra = {k: v for k, v in (raw or {}).items() if k not in _KNOWN_KEYS}
    return DeskConfig(
        config_version=int(merged["config_version"]),
        first_run_done=bool(merged["first_run_done"]),
        models_root=Path(merged["models_root"]),
        outputs_root=Path(merged["outputs_root"]),
        gateway=GatewayConfig(enabled=bool(gateway["enabled"]),
                              host=str(gateway["host"]),
                              port=int(gateway["port"])),
        needs_setup=(raw is None) or (not bool(merged["first_run_done"])),
        extra=extra,
    )


def default_config(data_root: Path) -> DeskConfig:
    """Pure defaults, as if config.json were absent (corrupt-config assembly path)."""
    return _from_raw(None, data_root)


def read_config(roots) -> DeskConfig:
    """api:readConfig — roots needs .config_path and .data_root."""
    with _LOCK:
        raw = _load_raw(roots.config_path)
    return _from_raw(raw, roots.data_root)
```

`desk/foundation/__init__.py` 追加：

```python
from .config import (DeskConfig, GatewayConfig, default_config, read_config)
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_config.py`
**提交** `foundation: config read side — defaults merge, needs_setup, corrupt stays an error`

---

## T-foundation-03 config 写入：原子替换 + update_config + 并发

**目标** 写侧：`write_config`（`api:writeConfig`）、`_atomic_write`（R-foundation-06：同目录 tmp → fsync → `os.replace`，失败清 tmp 后上抛）、`update_config`（锁内读-改-写）。

### 1. 追加失败测试到 `tests/test_foundation_config.py`

```python
import os
import threading


def test_write_read_round_trip(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.default_config(tmp_path)
    config_mod.write_config(roots, cfg)
    again = config_mod.read_config(roots)
    assert again.to_json() == cfg.to_json()
    assert json.loads(roots.config_path.read_text())["config_version"] == 1


def test_update_config_changes_only_named_fields(tmp_path):
    roots = make_roots(tmp_path)
    cfg = config_mod.update_config(roots, first_run_done=True,
                                   models_root=tmp_path / "elsewhere")
    assert cfg.first_run_done is True
    assert cfg.needs_setup is False
    assert cfg.models_root == tmp_path / "elsewhere"
    assert cfg.gateway.port == 8770                       # untouched field keeps default
    cfg2 = config_mod.update_config(roots, gateway={"port": 9001})
    assert cfg2.gateway.port == 9001
    assert cfg2.gateway.host == "0.0.0.0"                 # gateway merge is key-by-key
    assert cfg2.models_root == tmp_path / "elsewhere"     # earlier update survived


def test_unknown_keys_round_trip_through_update(tmp_path):
    roots = make_roots(tmp_path)
    roots.config_path.write_text(json.dumps({"future_knob": 42}), encoding="utf-8")
    config_mod.update_config(roots, first_run_done=True)
    on_disk = json.loads(roots.config_path.read_text())
    assert on_disk["future_knob"] == 42


def test_atomic_write_replace_failure_keeps_old_file(tmp_path, monkeypatch):
    roots = make_roots(tmp_path)
    config_mod.update_config(roots, first_run_done=True)
    before = roots.config_path.read_bytes()

    def boom(src, dst):
        raise OSError("injected replace failure")

    monkeypatch.setattr(config_mod.os, "replace", boom)
    with pytest.raises(OSError, match="injected replace failure"):
        config_mod.update_config(roots, first_run_done=False)
    assert roots.config_path.read_bytes() == before       # old file byte-identical
    leftovers = [p for p in tmp_path.iterdir() if "tmp" in p.name]
    assert leftovers == []                                # no temp residue


def test_atomic_write_serialization_failure_keeps_old_file(tmp_path, monkeypatch):
    roots = make_roots(tmp_path)
    config_mod.update_config(roots, first_run_done=True)
    before = roots.config_path.read_bytes()

    def boom(*a, **kw):
        raise ValueError("injected dump failure")

    monkeypatch.setattr(config_mod.json, "dump", boom)
    with pytest.raises(ValueError, match="injected dump failure"):
        config_mod.update_config(roots, first_run_done=False)
    assert roots.config_path.read_bytes() == before
    assert [p for p in tmp_path.iterdir() if "tmp" in p.name] == []


def test_concurrent_updates_lose_no_fields(tmp_path):
    roots = make_roots(tmp_path)
    n = 40

    def bump(key):
        for i in range(n):
            config_mod.update_config(roots, **{key: i})

    threads = [threading.Thread(target=bump, args=(k,)) for k in ("knob_a", "knob_b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    on_disk = json.loads(roots.config_path.read_text())   # file stays parseable
    assert on_disk["knob_a"] == n - 1
    assert on_disk["knob_b"] == n - 1                     # neither thread's writes lost
```

### 2. 实现：追加到 `desk/foundation/config.py`

```python
def _atomic_write(config_path: Path, payload: dict) -> None:
    """R-foundation-06: same-dir tmp -> fsync -> os.replace; never a torn file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config_path.with_name(
        f"{config_path.name}.tmp-{os.getpid()}-{os.urandom(4).hex()}")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, config_path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_config(roots, config: DeskConfig) -> None:
    """api:writeConfig — atomic full-document write."""
    with _LOCK:
        _atomic_write(roots.config_path, config.to_json())


def update_config(roots, **fields) -> DeskConfig:
    """Locked read-modify-write so concurrent HTTP PUTs cannot drop each other's fields."""
    with _LOCK:
        raw = _load_raw(roots.config_path)
        current = _from_raw(raw, roots.data_root)
        merged = current.to_json()
        for key, value in fields.items():
            if key == "gateway" and isinstance(value, dict):
                gw = dict(merged["gateway"])
                gw.update({k: v for k, v in value.items() if k in _GATEWAY_KEYS})
                merged["gateway"] = gw
            elif isinstance(value, Path):
                merged[key] = str(value)
            else:
                merged[key] = value
        _atomic_write(roots.config_path, merged)
        return _from_raw(merged, roots.data_root)
```

`desk/foundation/__init__.py` 追加 `update_config, write_config` 到 config 导入行。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_config.py`
**提交** `foundation: atomic config writes + locked update_config`

---

## T-foundation-04 paths.py：模式判定 + PathRoots + resolve_paths

**目标** `desk/foundation/paths.py`：bundle 标记单点判定（§1.3）、完整 `PathRoots`（`data:pathRoots`）、`resolve_paths`（`api:resolvePaths`，每次现读 config，A9）、`normalize_user_path`（唯一的 `expanduser` 落点，保 R-foundation-01 静态不变量）。

### 1. 失败测试 `tests/test_foundation_paths.py`

```python
# tests/test_foundation_paths.py
import sys
from pathlib import Path

import pytest

from desk.foundation import paths as paths_mod


@pytest.fixture()
def fake_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "desk" / "static").mkdir(parents=True)
    (repo / "desk" / "media").mkdir(parents=True)
    return repo


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    d = tmp_path / "data"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(d))
    return d


def test_dev_mode_without_bundle_marker(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.mode == "dev"
    assert roots.resources_root == fake_repo
    assert roots.static_dir == fake_repo / "desk" / "static"
    assert roots.media_cli_dir == fake_repo / "desk" / "media"
    assert roots.venv_python == Path(sys.executable)
    assert roots.music_python == roots.venv_python
    assert roots.mlx_h3_env == {} and roots.music_env == {}


def test_bundle_mode_with_marker(fake_repo, data_root):
    (fake_repo / "bundle.json").write_text("{}", encoding="utf-8")
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.mode == "bundle"
    py = fake_repo / "python" / "bin" / "python3.13"
    assert roots.venv_python == py
    assert roots.mlx_h3_cmd == (str(py), "-s", "-c", "from mlx_h3.cli import main; main()")
    assert roots.mlx_h3_env == {"PYTHONPATH": str(fake_repo / "pylibs" / "h3")}
    assert roots.music_env == {"PYTHONPATH": str(fake_repo / "pylibs" / "music")}
    assert roots.hf_cmd == (str(py), "-s", "-c",
                            "from huggingface_hub.cli.hf import main; main()")


def test_env_data_root_and_param_precedence(fake_repo, tmp_path, monkeypatch):
    env_root = tmp_path / "from-env"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(env_root))
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.data_root == env_root.resolve()
    assert roots.config_path == roots.data_root / "config.json"
    explicit = tmp_path / "explicit"
    roots2 = paths_mod.resolve_paths(resources_root=fake_repo, data_root=explicit)
    assert roots2.data_root == explicit.resolve()          # param beats env var


def test_derived_paths_and_config_roots(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.logs_dir == roots.data_root / "logs"
    assert roots.sessions_dir == roots.data_root / "sessions"
    assert roots.history_path == roots.data_root / "history.jsonl"
    assert roots.models_root == roots.data_root / "models"     # config defaults
    assert roots.outputs_root == roots.data_root / "outputs"


def test_resolve_creates_data_and_logs_but_not_models(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.data_root.is_dir()
    assert roots.logs_dir.is_dir()
    assert not roots.models_root.exists()                  # first-run owns creating it


def test_resolve_sees_config_changes_immediately(fake_repo, data_root):
    from desk.foundation import config as config_mod
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    config_mod.update_config(roots, models_root=data_root / "ext-disk")
    again = paths_mod.resolve_paths(resources_root=fake_repo)
    assert again.models_root == data_root.resolve() / "ext-disk"   # A9: no caching


def test_mlx_h3_dev_cmd_resolution_order(fake_repo, data_root, monkeypatch):
    fake_bin = fake_repo / "mlx-h3"
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", str(fake_bin))
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.mlx_h3_cmd == (str(fake_bin),)


def test_hf_dev_cmd_empty_when_unresolvable(fake_repo, data_root, monkeypatch):
    monkeypatch.delenv("LOCALMODELDESK_HF", raising=False)
    monkeypatch.setattr(paths_mod.shutil, "which", lambda name: None)
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.hf_cmd == ()                              # resources reports hf_cli_missing


def test_corrupt_config_propagates_by_default(fake_repo, data_root):
    from desk.foundation.errors import ConfigCorruptError
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "config.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(ConfigCorruptError):
        paths_mod.resolve_paths(resources_root=fake_repo)
    roots = paths_mod.resolve_paths(resources_root=fake_repo,
                                    default_config_on_corrupt=True)
    assert roots.models_root == data_root.resolve() / "models"


def test_normalize_user_path_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths_mod.normalize_user_path("~/x") == (tmp_path / "x").resolve()
```

### 2. 实现 `desk/foundation/paths.py`

```python
# desk/foundation/paths.py
"""Single source of truth for every path (R-foundation-01) and the sole
file-logging configuration point (census A16). No other file in desk/ may
call Path.home()/expanduser or attach a FileHandler (static-tested)."""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from .errors import ConfigCorruptError

_MLX_H3_ENTRY = "from mlx_h3.cli import main; main()"
_HF_ENTRY = "from huggingface_hub.cli.hf import main; main()"


def normalize_user_path(value) -> Path:
    """The one place user-supplied paths get ~ expansion + resolution."""
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class PathRoots:
    mode: str                     # "bundle" | "dev"
    resources_root: Path
    static_dir: Path
    venv_python: Path
    mlx_h3_cmd: tuple
    mlx_h3_env: dict
    music_python: Path
    music_env: dict
    media_cli_dir: Path
    hf_cmd: tuple
    data_root: Path
    config_path: Path
    logs_dir: Path
    sessions_dir: Path
    history_path: Path
    models_root: Path
    outputs_root: Path


@dataclass(frozen=True)
class _StaticRoots:
    mode: str
    resources_root: Path
    data_root: Path
    config_path: Path


def _static_roots(data_root=None, resources_root=None) -> _StaticRoots:
    if resources_root is None:
        import desk
        resources_root = Path(desk.__file__).resolve().parent.parent
    resources_root = normalize_user_path(resources_root)
    mode = "bundle" if (resources_root / "bundle.json").exists() else "dev"
    if data_root is None:
        env = os.environ.get("LOCALMODELDESK_DATA_ROOT")
        data_root = (Path(env) if env
                     else Path.home() / "Library" / "Application Support" / "LocalModelDesk")
    data_root = normalize_user_path(data_root)
    return _StaticRoots(mode, resources_root, data_root, data_root / "config.json")


def _mlx_h3_dev_cmd() -> tuple:
    override = os.environ.get("LOCALMODELDESK_MLX_H3")
    if override:
        return (override,)
    found = shutil.which("mlx-h3")
    if found:
        return (found,)
    return (str(Path.home() / ".local" / "bin" / "mlx-h3"),)


def _hf_dev_cmd() -> tuple:
    override = os.environ.get("LOCALMODELDESK_HF")
    if override:
        return (override,)
    found = shutil.which("hf")
    return (found,) if found else ()          # empty: resources reports hf_cli_missing


def resolve_paths(*, data_root=None, resources_root=None,
                  default_config_on_corrupt: bool = False) -> PathRoots:
    """api:resolvePaths — static roots, then a fresh config read (A9, no cache)."""
    static = _static_roots(data_root=data_root, resources_root=resources_root)
    try:
        cfg = config_mod.read_config(static)
    except ConfigCorruptError:
        if not default_config_on_corrupt:
            raise
        cfg = config_mod.default_config(static.data_root)   # assembly-only fallback (§1.4)
    res = static.resources_root
    if static.mode == "bundle":
        venv_python = res / "python" / "bin" / "python3.13"
        mlx_h3_cmd = (str(venv_python), "-s", "-c", _MLX_H3_ENTRY)
        mlx_h3_env = {"PYTHONPATH": str(res / "pylibs" / "h3")}
        music_env = {"PYTHONPATH": str(res / "pylibs" / "music")}
        hf_cmd = (str(venv_python), "-s", "-c", _HF_ENTRY)
    else:
        venv_python = Path(sys.executable)
        mlx_h3_cmd = _mlx_h3_dev_cmd()
        mlx_h3_env = {}
        music_env = {}
        hf_cmd = _hf_dev_cmd()
    roots = PathRoots(
        mode=static.mode,
        resources_root=res,
        static_dir=res / "desk" / "static",
        venv_python=venv_python,
        mlx_h3_cmd=mlx_h3_cmd,
        mlx_h3_env=mlx_h3_env,
        music_python=venv_python,
        music_env=music_env,
        media_cli_dir=res / "desk" / "media",
        hf_cmd=hf_cmd,
        data_root=static.data_root,
        config_path=static.config_path,
        logs_dir=static.data_root / "logs",
        sessions_dir=static.data_root / "sessions",
        history_path=static.data_root / "history.jsonl",
        models_root=cfg.models_root,
        outputs_root=cfg.outputs_root,
    )
    roots.data_root.mkdir(parents=True, exist_ok=True)
    roots.logs_dir.mkdir(parents=True, exist_ok=True)
    return roots
```

`desk/foundation/__init__.py` 追加：

```python
from .paths import PathRoots, normalize_user_path, resolve_paths
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_paths.py`
**提交** `foundation: single-point path resolution with bundle/dev mode marker`

---

## T-foundation-05 setup_logging：文件日志唯一配置点（census A16）

**目标** `paths.py` 增加 `setup_logging(roots)`：根 logger 挂 `FileHandler(logs_dir/"desk.log")` + stderr `StreamHandler`，幂等；日志只落用户数据根，代码目录零 `.log`。

### 1. 追加失败测试到 `tests/test_foundation_paths.py`

```python
import logging


def test_setup_logging_writes_under_data_root_only(fake_repo, data_root, monkeypatch):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    monkeypatch.setattr(paths_mod, "_LOGGING_CONFIGURED", False)
    root_logger = logging.getLogger()
    saved = root_logger.handlers[:]
    for h in saved:
        root_logger.removeHandler(h)
    try:
        paths_mod.setup_logging(roots)
        logging.getLogger("desk.test").info("hello-a16")
        for h in logging.getLogger().handlers:
            h.flush()
        log_file = roots.logs_dir / "desk.log"
        assert log_file.exists()
        assert "hello-a16" in log_file.read_text(encoding="utf-8")
        paths_mod.setup_logging(roots)                     # idempotent: no handler pile-up
        file_handlers = [h for h in logging.getLogger().handlers
                         if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
    finally:
        for h in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(h)
            h.close()
        for h in saved:
            root_logger.addHandler(h)
    repo_root = Path(__file__).resolve().parent.parent
    assert list(repo_root.glob("*.log")) == []             # nothing lands in the repo
    assert list((repo_root / "desk").rglob("*.log")) == []
```

### 2. 实现：追加到 `desk/foundation/paths.py`

```python
import logging

_LOGGING_CONFIGURED = False


def setup_logging(roots: PathRoots) -> None:
    """The ONLY FileHandler in the whole codebase (census A16). Idempotent."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    file_handler = logging.FileHandler(roots.logs_dir / "desk.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(file_handler)
    root.addHandler(logging.StreamHandler(sys.stderr))
    _LOGGING_CONFIGURED = True
```

（`import logging` 放到文件顶部 import 区；此处分开列出只为标注新增。）
`desk/foundation/__init__.py` 的 paths 导入行追加 `setup_logging`。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_paths.py`
**提交** `foundation: setup_logging as the sole file-logging point (A16)`

---

## T-foundation-06 firstrun.complete_first_run（R-foundation-03）

**目标** `desk/foundation/firstrun.py`：可写性探测（写删 `.lmd-write-probe`）→ 失败抛 `NotWritableError` 且配置不落盘 → 成功 `update_config(models_root=..., first_run_done=True)`。

### 1. 失败测试 `tests/test_foundation_firstrun.py`

```python
# tests/test_foundation_firstrun.py
import os

import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import NotWritableError


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


def test_default_models_root_created_and_persisted(roots):
    cfg = firstrun.complete_first_run(roots)
    assert cfg.models_root == roots.data_root / "models"
    assert cfg.models_root.is_dir()
    assert cfg.first_run_done is True
    assert cfg.needs_setup is False
    on_disk = config_mod.read_config(roots)
    assert on_disk.first_run_done is True                  # actually persisted


def test_explicit_models_root_wins(roots, tmp_path):
    ext = tmp_path / "ext-disk" / "models"
    cfg = firstrun.complete_first_run(roots, models_root=ext)
    assert cfg.models_root == ext.resolve()
    assert ext.is_dir()


def test_probe_file_never_survives(roots):
    firstrun.complete_first_run(roots)
    assert list((roots.data_root / "models").iterdir()) == []


def test_unwritable_dir_raises_and_config_untouched(roots, tmp_path):
    fenced = tmp_path / "fenced"
    fenced.mkdir()
    os.chmod(fenced, 0o500)                                # r-x: mkdir/probe must fail
    try:
        with pytest.raises(NotWritableError) as exc:
            firstrun.complete_first_run(roots, models_root=fenced / "models")
        assert exc.value.code == "not_writable"
        assert exc.value.payload["os_error"]               # OS error text included
        assert not roots.config_path.exists()              # nothing persisted, no fallback
    finally:
        os.chmod(fenced, 0o700)
```

### 2. 实现 `desk/foundation/firstrun.py`

```python
# desk/foundation/firstrun.py
"""api:completeFirstRun / api:adoptLegacyModels (R-foundation-03/04)."""
from __future__ import annotations

from pathlib import Path

from . import config as config_mod
from .errors import NotWritableError
from .paths import normalize_user_path


def complete_first_run(roots, models_root: Path | None = None) -> config_mod.DeskConfig:
    """Validate writability, then persist models_root + first_run_done atomically.
    Unwritable target -> NotWritableError; config untouched, no silent fallback."""
    target = (normalize_user_path(models_root) if models_root
              else roots.data_root / "models")
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".lmd-write-probe"
        probe.write_bytes(b"lmd")
        probe.unlink()
    except OSError as exc:
        raise NotWritableError(
            f"models root not writable: {target}: {exc}",
            path=str(target), os_error=str(exc)) from exc
    return config_mod.update_config(roots, models_root=target, first_run_done=True)
```

`desk/foundation/__init__.py` 追加：

```python
from .firstrun import complete_first_run
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_firstrun.py`
**提交** `foundation: completeFirstRun with writability probe, no silent fallback`

---

## T-foundation-07 adopt：point 模式 + legacy 根校验

**目标** `adopt_legacy_models` 的识别逻辑（`llms/`、`minimax-h3/`、`minimax-music3/`）、`LegacyRootError`、point 模式（零字节 IO，改 `models_root` 指向 legacy 根并置 `first_run_done`）。

### 1. 失败测试 `tests/test_foundation_adopt.py`

```python
# tests/test_foundation_adopt.py
"""Adoption tests. Fake weights only: a few tens-of-bytes .safetensors files.
The real 339G under llms/ / minimax-h3/ / minimax-music3/ is NEVER touched."""
import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import LegacyRootError


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


def make_legacy(tmp_path, name="legacy"):
    legacy = tmp_path / name
    files = {
        "llms/org/repo-a/model-00001.safetensors": b"A" * 40,
        "llms/org/repo-a/config.json": b"{}",
        "minimax-h3/dit.safetensors": b"H" * 64,
        "minimax-music3/music.safetensors": b"M" * 32,
    }
    for rel, content in files.items():
        p = legacy / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return legacy, sum(len(c) for c in files.values())


def snapshot(root):
    return sorted((str(p.relative_to(root)), p.read_bytes())
                  for p in root.rglob("*") if p.is_file())


def test_point_mode_repoints_without_touching_source(roots, tmp_path):
    legacy, _total = make_legacy(tmp_path)
    before = snapshot(legacy)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")
    assert result.mode == "point"
    assert result.models_root == legacy.resolve()
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert result.moved_bytes == 0
    assert result.source_retained is False
    assert snapshot(legacy) == before                      # source byte-identical
    cfg = config_mod.read_config(roots)
    assert cfg.models_root == legacy.resolve()
    assert cfg.first_run_done is True                      # A5: adoption completes first-run


def test_partial_legacy_tree_is_accepted(roots, tmp_path):
    legacy = tmp_path / "only-llms"
    (legacy / "llms" / "o" / "r").mkdir(parents=True)
    (legacy / "llms" / "o" / "r" / "w.safetensors").write_bytes(b"x" * 10)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")
    assert result.adopted == ["llms"]


def test_no_known_subtree_raises(roots, tmp_path):
    empty = tmp_path / "nothing"
    (empty / "unrelated").mkdir(parents=True)
    with pytest.raises(LegacyRootError) as exc:
        firstrun.adopt_legacy_models(roots, empty, mode="point")
    assert exc.value.code == "legacy_root_invalid"
    assert not roots.config_path.exists()                  # config untouched


def test_unknown_mode_raises(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="copy")
```

### 2. 实现：追加到 `desk/foundation/firstrun.py`

```python
import os
import shutil
from dataclasses import dataclass

from .errors import (AdoptConflictError, AdoptError, InsufficientSpaceError,
                     LegacyRootError)

LEGACY_SUBTREES = ("llms", "minimax-h3", "minimax-music3")
_SAFETY_MARGIN_BYTES = 1 << 30          # 1 GiB margin on cross-volume moves (A6)
_copy2 = shutil.copy2                   # module-level indirection: tests inject/count here


@dataclass(frozen=True)
class AdoptResult:
    mode: str
    models_root: Path
    adopted: list
    moved_bytes: int
    source_retained: bool


def adopt_legacy_models(roots, legacy_root, mode: str,
                        target_root=None) -> AdoptResult:
    """api:adoptLegacyModels — never re-downloads, never deletes the source."""
    legacy = normalize_user_path(legacy_root)
    found = [name for name in LEGACY_SUBTREES if (legacy / name).is_dir()]
    if not found:
        raise LegacyRootError(
            f"no known model subtrees ({', '.join(LEGACY_SUBTREES)}) under {legacy}",
            path=str(legacy))
    if mode == "point":
        config_mod.update_config(roots, models_root=legacy, first_run_done=True)
        return AdoptResult("point", legacy, found, 0, False)
    if mode != "move":
        raise LegacyRootError(f"unknown adopt mode: {mode!r}", mode=str(mode))
    return _adopt_move(roots, legacy, found, target_root)
```

（`_adopt_move` 在 T-08/T-09 落地；本任务先 `raise NotImplementedError` 会违反「无占位」——因此本任务只注册 point 分支，`mode == "move"` 分支在本任务的代码里**尚不存在**，`if mode != "move"` 的校验写成对非 point 模式一律 `LegacyRootError`，T-08 再改为放行 move：）

```python
    # T-07 实际落地版本（T-08 将替换为上面的三分支形态）：
    raise LegacyRootError(f"unknown adopt mode: {mode!r}", mode=str(mode))
```

`desk/foundation/__init__.py` 追加 `AdoptResult, adopt_legacy_models`。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_adopt.py`
**提交** `foundation: adoptLegacyModels point mode + legacy-root validation`

---

## T-foundation-08 adopt：move 同卷（rename、冲突、幂等重试）

**目标** `_adopt_move` 的同卷路径：`st_dev` 判卷、`os.rename` 逐子树搬动、目标同名非空目录抛 `AdoptConflictError`、目标位于 legacy 内拒绝、中途失败抛 `AdoptError` 且不写配置、重试幂等。

### 1. 追加失败测试到 `tests/test_foundation_adopt.py`

```python
from desk.foundation.errors import AdoptConflictError, AdoptError


def test_move_same_volume_renames_everything(roots, tmp_path):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "new-home"
    before = snapshot(legacy)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert result.mode == "move"
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert result.moved_bytes == total
    assert result.source_retained is False                 # rename, not copy
    for name in ("llms", "minimax-h3", "minimax-music3"):
        assert not (legacy / name).exists()                # gone from source side
    assert snapshot(target) == before                      # arrived intact
    assert config_mod.read_config(roots).models_root == target.resolve()


def test_move_default_target_is_data_root_models(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move")
    assert result.models_root == roots.data_root / "models"
    assert (roots.data_root / "models" / "llms").is_dir()


def test_move_conflict_on_nonempty_target_subtree(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    target = tmp_path / "occupied"
    (target / "llms" / "already").mkdir(parents=True)
    (target / "llms" / "already" / "x.bin").write_bytes(b"1")
    with pytest.raises(AdoptConflictError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert exc.value.code == "adopt_conflict"
    assert exc.value.payload["subtree"] == "llms"
    assert (legacy / "llms").is_dir()                      # source untouched
    assert not roots.config_path.exists()                  # config not written


def test_move_target_inside_legacy_rejected(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="move",
                                     target_root=legacy / "sub")
    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=legacy)


def test_move_midway_failure_reports_ledger_and_retry_completes(roots, tmp_path, monkeypatch):
    legacy, _ = make_legacy(tmp_path)
    target = tmp_path / "halfway"
    real_rename = os.rename
    calls = {"n": 0}

    def flaky_rename(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:                                # first subtree ok, second dies
            raise OSError("injected rename failure")
        return real_rename(src, dst)

    monkeypatch.setattr(firstrun.os, "rename", flaky_rename)
    with pytest.raises(AdoptError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert exc.value.code == "adopt_failed"
    assert len(exc.value.payload["adopted"]) == 1
    assert len(exc.value.payload["remaining"]) == 2
    assert not roots.config_path.exists()                  # config not written on failure
    monkeypatch.setattr(firstrun.os, "rename", real_rename)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]  # idempotent
    assert config_mod.read_config(roots).first_run_done is True
```

### 2. 实现：`firstrun.py` 放行 move 分支并加 `_adopt_move`（同卷部分）

把 T-07 的「非 point 一律拒绝」替换为设计形态的三分支（point / move / 其它拒绝），并落地：

```python
def _tree_bytes(root: Path) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_symlink():
                total += p.stat().st_size
    return total


def _same_volume(a: Path, b: Path) -> bool:
    return a.stat().st_dev == b.stat().st_dev


def _adopt_move(roots, legacy: Path, found: list, target_root) -> AdoptResult:
    target = (normalize_user_path(target_root) if target_root
              else roots.data_root / "models")
    if target == legacy or target.is_relative_to(legacy):
        raise LegacyRootError(
            f"target root {target} lies inside legacy root {legacy}", path=str(target))
    target.mkdir(parents=True, exist_ok=True)
    if _same_volume(legacy, target):
        return _move_same_volume(roots, legacy, found, target)
    return _move_cross_volume(roots, legacy, found, target)   # lands in T-09


def _move_same_volume(roots, legacy: Path, found: list, target: Path) -> AdoptResult:
    adopted: list = []
    moved_bytes = 0
    for name in found:
        src, dst = legacy / name, target / name
        if not src.exists():                     # idempotent retry: already moved
            adopted.append(name)
            continue
        if dst.exists() and any(dst.iterdir()):
            raise AdoptConflictError(
                f"target already has a non-empty {name!r}: {dst}",
                subtree=name, path=str(dst))
        size = _tree_bytes(src)
        try:
            os.rename(src, dst)
        except OSError as exc:
            raise AdoptError(
                f"move failed on subtree {name!r}: {exc}",
                adopted=list(adopted),
                remaining=[n for n in found if n not in adopted]) from exc
        adopted.append(name)
        moved_bytes += size
    config_mod.update_config(roots, models_root=target, first_run_done=True)
    return AdoptResult("move", target, adopted, moved_bytes, False)
```

T-08 落地时 `_move_cross_volume` 尚不存在；本任务把 `_adopt_move` 末行暂写为
`raise AdoptError("cross-volume move not yet supported", adopted=[], remaining=list(found))`
——这不是占位假成功，而是真实报错；T-09 用真实现替换它（本任务的测试全部走同卷路径，不触达该行）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_adopt.py`
**提交** `foundation: same-volume adopt move — rename, conflict, idempotent retry`

---

## T-foundation-09 adopt：move 跨卷（空间校验、可续复制、保源）

**目标** `_move_cross_volume`：`disk_usage` + 1 GiB 余量校验 → 不足抛 `InsufficientSpaceError`（差额精确）；逐文件 `copy2`，同字节目标跳过（中断可续）；复制后**保留源**（`source_retained=True`）；中途失败 `AdoptError` 带清单、不写配置。完成后 `api:adoptLegacyModels` 全语义可用。

### 1. 追加失败测试到 `tests/test_foundation_adopt.py`

```python
from desk.foundation.errors import InsufficientSpaceError

GIB = 1 << 30


def force_cross_volume(monkeypatch, free_bytes):
    monkeypatch.setattr(firstrun, "_same_volume", lambda a, b: False)

    class FakeUsage:
        def __init__(self, free):
            self.free = free

    monkeypatch.setattr(firstrun.shutil, "disk_usage",
                        lambda path: FakeUsage(free_bytes))


def test_cross_volume_copy_retains_source(roots, tmp_path, monkeypatch):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "other-volume"
    before = snapshot(legacy)
    force_cross_volume(monkeypatch, free_bytes=10 * GIB)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert result.source_retained is True
    assert result.moved_bytes == total
    assert snapshot(legacy) == before                      # source fully retained
    assert snapshot(target) == before                      # copy is complete
    assert config_mod.read_config(roots).models_root == target.resolve()


def test_cross_volume_insufficient_space_exact_shortfall(roots, tmp_path, monkeypatch):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "small-volume"
    force_cross_volume(monkeypatch, free_bytes=GIB)        # margin alone eats it all
    with pytest.raises(InsufficientSpaceError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    p = exc.value.payload
    assert p["needed_bytes"] == total + GIB
    assert p["free_bytes"] == GIB
    assert p["shortfall_bytes"] == total                   # exact difference
    assert not roots.config_path.exists()


def test_cross_volume_failure_then_resumed_retry_skips_copied(roots, tmp_path, monkeypatch):
    legacy, _total = make_legacy(tmp_path)
    target = tmp_path / "flaky-volume"
    force_cross_volume(monkeypatch, free_bytes=10 * GIB)
    real_copy2 = firstrun._copy2
    state = {"copies": 0}

    def flaky_copy2(src, dst):
        state["copies"] += 1
        if state["copies"] == 3:
            raise OSError("injected copy failure")
        return real_copy2(src, dst)

    monkeypatch.setattr(firstrun, "_copy2", flaky_copy2)
    with pytest.raises(AdoptError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert exc.value.payload["remaining"]                  # something left undone
    assert not roots.config_path.exists()

    counted = {"copies": 0}

    def counting_copy2(src, dst):
        counted["copies"] += 1
        return real_copy2(src, dst)

    monkeypatch.setattr(firstrun, "_copy2", counting_copy2)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    total_files = 4
    already_copied = 2                                     # copies 1 and 2 succeeded
    assert counted["copies"] == total_files - already_copied   # resume skipped them
    assert snapshot(legacy)                                # source still intact
```

### 2. 实现：追加 `_copy_tree_resumable` 与 `_move_cross_volume` 到 `firstrun.py`

```python
def _copy_tree_resumable(src: Path, dst: Path) -> int:
    """copy2 file-by-file; an existing same-size target file is skipped so an
    interrupted move can resume without re-copying. Returns bytes copied now."""
    copied = 0
    for dirpath, _dirnames, filenames in os.walk(src):
        rel = Path(dirpath).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for name in sorted(filenames):
            s = Path(dirpath) / name
            d = dst / rel / name
            if d.exists() and d.stat().st_size == s.stat().st_size:
                continue
            _copy2(s, d)
            copied += s.stat().st_size
    return copied


def _move_cross_volume(roots, legacy: Path, found: list, target: Path) -> AdoptResult:
    total = sum(_tree_bytes(legacy / name) for name in found)
    needed = total + _SAFETY_MARGIN_BYTES
    free = shutil.disk_usage(target).free
    if free < needed:
        raise InsufficientSpaceError(
            f"not enough space on target volume: need {needed} bytes "
            f"(incl. 1 GiB margin), free {free} bytes, short {needed - free} bytes",
            needed_bytes=needed, free_bytes=free, shortfall_bytes=needed - free)
    adopted: list = []
    moved_bytes = 0
    for name in found:
        try:
            moved_bytes += _copy_tree_resumable(legacy / name, target / name)
        except OSError as exc:
            raise AdoptError(
                f"copy failed on subtree {name!r}: {exc}",
                adopted=list(adopted),
                remaining=[n for n in found if n not in adopted]) from exc
        adopted.append(name)
    config_mod.update_config(roots, models_root=target, first_run_done=True)
    # Source deliberately retained (A6): the caller reclaims it manually.
    return AdoptResult("move", target, adopted, moved_bytes, True)
```

同时删除 T-08 在 `_adopt_move` 末行的临时 `AdoptError`，改为调用 `_move_cross_volume`。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_adopt.py`
**提交** `foundation: cross-volume adopt move — space check, resumable copy, source retained`

---

## T-foundation-10 capabilities.py 能力探测（R-foundation-05）

**目标** `probe_capabilities(roots)`：固定五键 `mlx_h3` / `venv` / `models_root` / `music_runtime` / `config`；只读快速；全缺也正常返回、永不抛。

### 1. 失败测试 `tests/test_foundation_capabilities.py`

```python
# tests/test_foundation_capabilities.py
import sys

import pytest

from desk.foundation import capabilities as caps_mod
from desk.foundation import paths as paths_mod

KEYS = {"mlx_h3", "venv", "models_root", "music_runtime", "config"}


@pytest.fixture()
def dev_roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


@pytest.fixture()
def bundle_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    res = tmp_path / "Resources"
    (res / "desk").mkdir(parents=True)
    (res / "bundle.json").write_text("{}", encoding="utf-8")
    return res


def test_all_five_keys_always_present_and_probe_never_raises(dev_roots, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", "/definitely/not/there")
    caps = caps_mod.probe_capabilities(dev_roots)
    assert set(caps) == KEYS
    assert caps["mlx_h3"].present is False
    assert caps["mlx_h3"].detail                            # says why
    assert caps["models_root"].present is False             # first run not done
    assert caps["venv"].present is True                     # dev: sys.executable
    assert caps["venv"].path == sys.executable
    assert caps["config"].present is True                   # absent file is not corrupt


def test_dev_mlx_h3_present_when_executable(dev_roots, tmp_path, monkeypatch):
    fake = tmp_path / "mlx-h3"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", str(fake))
    repo = dev_roots.resources_root
    roots = paths_mod.resolve_paths(resources_root=repo)    # re-resolve with env set
    caps = caps_mod.probe_capabilities(roots)
    assert caps["mlx_h3"].present is True
    assert caps["mlx_h3"].detail == ""


def test_bundle_probes_are_directory_stats(bundle_tree, monkeypatch):
    roots = paths_mod.resolve_paths(resources_root=bundle_tree)
    caps = caps_mod.probe_capabilities(roots)
    assert caps["mlx_h3"].present is False                  # no pylibs/h3/mlx_h3
    assert caps["music_runtime"].present is False
    assert caps["venv"].present is False                    # no embedded python
    (bundle_tree / "pylibs" / "h3" / "mlx_h3").mkdir(parents=True)
    (bundle_tree / "pylibs" / "music" / "mlx_minimax_music3").mkdir(parents=True)
    py = bundle_tree / "python" / "bin" / "python3.13"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    caps = caps_mod.probe_capabilities(roots)
    assert caps["mlx_h3"].present is True
    assert caps["music_runtime"].present is True
    assert caps["venv"].present is True


def test_models_root_present_after_first_run(dev_roots):
    from desk.foundation import firstrun
    firstrun.complete_first_run(dev_roots)
    roots = paths_mod.resolve_paths(resources_root=dev_roots.resources_root)
    assert caps_mod.probe_capabilities(roots)["models_root"].present is True


def test_corrupt_config_reported_not_raised(dev_roots):
    dev_roots.config_path.write_text("{nope", encoding="utf-8")
    caps = caps_mod.probe_capabilities(dev_roots)           # must NOT raise
    assert caps["config"].present is False
    assert "config" in caps["config"].detail or caps["config"].detail
```

### 2. 实现 `desk/foundation/capabilities.py`

```python
# desk/foundation/capabilities.py
"""R-foundation-05: missing pieces become queryable state, never a dead service."""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from .errors import ConfigCorruptError


@dataclass(frozen=True)
class Capability:
    present: bool
    path: str
    detail: str = ""          # why it is missing; "" when present


def _executable(p: Path) -> bool:
    return p.exists() and os.access(p, os.X_OK)


def probe_capabilities(roots) -> dict:
    """Read-only, fast (pure stat / one find_spec). Never raises; a probe
    failure changes a status field and must not stop startup."""
    caps: dict = {}

    if roots.mode == "bundle":
        pkg = roots.resources_root / "pylibs" / "h3" / "mlx_h3"
        ok = pkg.is_dir()
        caps["mlx_h3"] = Capability(ok, str(pkg),
                                    "" if ok else "mlx_h3 package dir missing from bundle")
    else:
        exe = Path(roots.mlx_h3_cmd[0]) if roots.mlx_h3_cmd else None
        ok = exe is not None and _executable(exe)
        caps["mlx_h3"] = Capability(ok, str(exe) if exe else "",
                                    "" if ok else "mlx-h3 executable not found")

    ok = _executable(roots.venv_python)
    caps["venv"] = Capability(ok, str(roots.venv_python),
                              "" if ok else "python interpreter missing or not executable")

    ok = roots.models_root.is_dir()
    caps["models_root"] = Capability(ok, str(roots.models_root),
                                     "" if ok else "models root directory does not exist")

    if roots.mode == "bundle":
        pkg = roots.resources_root / "pylibs" / "music" / "mlx_minimax_music3"
        ok = pkg.is_dir()
        caps["music_runtime"] = Capability(
            ok, str(pkg), "" if ok else "mlx_minimax_music3 package dir missing from bundle")
    else:
        ok = importlib.util.find_spec("mlx_minimax_music3") is not None
        caps["music_runtime"] = Capability(
            ok, "mlx_minimax_music3", "" if ok else "mlx_minimax_music3 not importable")

    try:
        config_mod.read_config(roots)
        caps["config"] = Capability(True, str(roots.config_path))
    except ConfigCorruptError as exc:
        caps["config"] = Capability(False, str(roots.config_path), str(exc))

    return caps
```

`desk/foundation/__init__.py` 追加：

```python
from .capabilities import Capability, probe_capabilities
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_capabilities.py`
**提交** `foundation: capability probing — absence is state, not death`

---

## T-foundation-11 HTTP 骨架 + foundation 端点（A1 / §2.6）

**目标** `desk/app.py`（`DeskApp` 路由表 + `ThreadingHTTPServer`，零业务，统一错误信封）与 `desk/foundation/routes.py`（§2.6 五端点，纯适配层）。

### 1. 失败测试 `tests/test_foundation_routes.py`

```python
# tests/test_foundation_routes.py
import json
import os

import pytest

from conftest import http_call
from desk.app import DeskApp
from desk.foundation import routes as routes_mod


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    app = DeskApp("127.0.0.1", 0)                          # ephemeral port
    app.add_routes(routes_mod.build_routes())
    app.start_background()
    yield app
    app.shutdown()


def test_get_config_reports_needs_setup(server):
    status, payload = http_call(server, "GET", "/api/config")
    assert status == 200
    assert payload["needs_setup"] is True
    assert payload["gateway"]["port"] == 8770


def test_put_config_merges_subset(server):
    status, payload = http_call(server, "PUT", "/api/config",
                                {"gateway": {"port": 9100}})
    assert status == 200
    assert payload["gateway"]["port"] == 9100
    assert payload["gateway"]["host"] == "0.0.0.0"


def test_get_paths_includes_capabilities(server):
    status, payload = http_call(server, "GET", "/api/paths")
    assert status == 200
    assert payload["mode"] == "dev"
    assert set(payload["capabilities"]) == {"mlx_h3", "venv", "models_root",
                                            "music_runtime", "config"}
    assert payload["models_root"]


def test_first_run_endpoint_happy_and_unwritable(server, tmp_path):
    status, payload = http_call(server, "POST", "/api/first-run", {})
    assert status == 200
    assert payload["first_run_done"] is True
    fenced = tmp_path / "fenced"
    fenced.mkdir()
    os.chmod(fenced, 0o500)
    try:
        status, payload = http_call(server, "POST", "/api/first-run",
                                    {"models_root": str(fenced / "m")})
        assert status == 400
        assert payload["error"]["code"] == "not_writable"
    finally:
        os.chmod(fenced, 0o700)


def test_adopt_endpoint_point_and_bad_body(server, tmp_path):
    legacy = tmp_path / "legacy"
    (legacy / "llms" / "o" / "r").mkdir(parents=True)
    (legacy / "llms" / "o" / "r" / "w.safetensors").write_bytes(b"x" * 8)
    status, payload = http_call(server, "POST", "/api/adopt",
                                {"legacy_root": str(legacy), "mode": "point"})
    assert status == 200
    assert payload["adopted"] == ["llms"]
    assert payload["moved_bytes"] == 0
    status, payload = http_call(server, "POST", "/api/adopt", {"mode": "sideways"})
    assert status == 400
    assert payload["error"]["code"] == "legacy_root_invalid"


def test_unknown_route_404_and_invalid_json_400(server):
    status, payload = http_call(server, "GET", "/api/nope")
    assert status == 404
    assert payload["error"]["code"] == "not_found"
    import urllib.request
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/adopt",
        data=b"not-json", method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
        raised = None
    except urllib.error.HTTPError as exc:
        raised = exc.code, json.loads(exc.read())
    assert raised[0] == 400
    assert raised[1]["error"]["code"] == "bad_request"
```

### 2. 实现 `desk/app.py`

```python
# desk/app.py
"""Ultra-thin HTTP skeleton (design A1): route table + ThreadingHTTPServer.
Dispatch, JSON codec, error envelope — zero business logic. Sibling modules
register endpoints via add_routes()."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .foundation.errors import FoundationError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: dict


class DeskApp:
    def __init__(self, host: str = "127.0.0.1", port: int = 8766):
        self._routes: list = []
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):              # no stderr spam; goes to logger
                log.info("http %s", fmt % args)

            def _dispatch(self, method: str) -> None:
                path = self.path.split("?", 1)[0]
                handler = app._find(method, path)
                if handler is None:
                    self._send(404, {"error": {"code": "not_found",
                                               "message": f"no route for {method} {path}"}})
                    return
                body: dict = {}
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    try:
                        body = json.loads(self.rfile.read(length).decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        self._send(400, {"error": {"code": "bad_request",
                                                   "message": f"invalid JSON body: {exc}"}})
                        return
                try:
                    result = handler(Request(method, path, body))
                except FoundationError as exc:
                    self._send(exc.http_status,
                               {"error": {"code": exc.code, "message": exc.message,
                                          **exc.payload}})
                except Exception as exc:    # errors stay errors: surfaced, never faked green
                    log.exception("unhandled error on %s %s", method, path)
                    self._send(500, {"error": {"code": "internal", "message": str(exc)}})
                else:
                    self._send(200, result)

            def _send(self, status: int, payload: dict) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def do_PUT(self):
                self._dispatch("PUT")

            def do_DELETE(self):
                self._dispatch("DELETE")

        self._server = ThreadingHTTPServer((host, port), Handler)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def add_routes(self, routes) -> None:
        """routes: iterable of (method, path_prefix, handler)."""
        self._routes.extend(routes)

    def _find(self, method: str, path: str):
        best, best_len = None, -1
        for m, prefix, handler in self._routes:
            if m != method:
                continue
            if (path == prefix or path.startswith(prefix.rstrip("/") + "/")) \
                    and len(prefix) > best_len:
                best, best_len = handler, len(prefix)
        return best

    def start_background(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
```

### 3. 实现 `desk/foundation/routes.py`

```python
# desk/foundation/routes.py
"""HTTP adapter for foundation (§2.6). Parse -> call library -> map. No logic."""
from __future__ import annotations

from . import capabilities as caps_mod
from . import config as config_mod
from . import firstrun
from . import paths as paths_mod
from .errors import LegacyRootError
from .paths import normalize_user_path


def _roots():
    # A9: re-resolve per request so config changes are visible immediately.
    return paths_mod.resolve_paths()


def _config_json(cfg: config_mod.DeskConfig) -> dict:
    out = cfg.to_json()
    out["needs_setup"] = cfg.needs_setup
    return out


def get_config(_req) -> dict:
    roots = _roots()
    return _config_json(config_mod.read_config(roots))


def put_config(req) -> dict:
    roots = _roots()
    return _config_json(config_mod.update_config(roots, **req.body))


def get_paths(_req) -> dict:
    # Status endpoint stays alive on corrupt config (§1.4): default-derived
    # paths for display; the corruption shows up in capabilities["config"].
    roots = paths_mod.resolve_paths(default_config_on_corrupt=True)
    caps = caps_mod.probe_capabilities(roots)
    return {
        "mode": roots.mode,
        "resources_root": str(roots.resources_root),
        "static_dir": str(roots.static_dir),
        "venv_python": str(roots.venv_python),
        "mlx_h3_cmd": list(roots.mlx_h3_cmd),
        "mlx_h3_env": dict(roots.mlx_h3_env),
        "music_python": str(roots.music_python),
        "music_env": dict(roots.music_env),
        "media_cli_dir": str(roots.media_cli_dir),
        "hf_cmd": list(roots.hf_cmd),
        "data_root": str(roots.data_root),
        "config_path": str(roots.config_path),
        "logs_dir": str(roots.logs_dir),
        "sessions_dir": str(roots.sessions_dir),
        "history_path": str(roots.history_path),
        "models_root": str(roots.models_root),
        "outputs_root": str(roots.outputs_root),
        "capabilities": {name: {"present": c.present, "path": c.path, "detail": c.detail}
                         for name, c in caps.items()},
    }


def post_first_run(req) -> dict:
    roots = _roots()
    raw = req.body.get("models_root")
    cfg = firstrun.complete_first_run(
        roots, normalize_user_path(raw) if raw else None)
    return _config_json(cfg)


def post_adopt(req) -> dict:
    legacy_root = req.body.get("legacy_root")
    mode = req.body.get("mode")
    if not legacy_root or mode not in ("point", "move"):
        raise LegacyRootError(
            "body must include legacy_root and mode 'point'|'move'")
    roots = _roots()
    raw_target = req.body.get("target_root")
    result = firstrun.adopt_legacy_models(
        roots, normalize_user_path(legacy_root), mode,
        target_root=normalize_user_path(raw_target) if raw_target else None)
    return {
        "mode": result.mode,
        "models_root": str(result.models_root),
        "adopted": list(result.adopted),
        "moved_bytes": result.moved_bytes,
        "source_retained": result.source_retained,
    }


def build_routes() -> list:
    return [
        ("GET", "/api/config", get_config),
        ("PUT", "/api/config", put_config),
        ("GET", "/api/paths", get_paths),
        ("POST", "/api/first-run", post_first_run),
        ("POST", "/api/adopt", post_adopt),
    ]
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_routes.py`
**提交** `foundation: DeskApp HTTP skeleton + foundation endpoints with error envelope`

---

## T-foundation-12 `desk/__main__.py`：组装入口 + 损坏配置下的启动韧性

**目标** `build_app()`（resolve → setup_logging → probe → DeskApp → 注册路由）与 `main()`；损坏 `config.json` 不阻止绑定端口，`/api/config` 持续报 500 `config_corrupt`、`/api/paths` 的 `capabilities.config.present == false`。全程无 `SystemExit`（census A19）。

### 1. 失败测试 `tests/test_foundation_main.py`

```python
# tests/test_foundation_main.py
import pytest

from conftest import http_call
from desk.__main__ import build_app


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    d = tmp_path / "data"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(d))
    return d


def run_app(port=0):
    app = build_app(port=port)
    app.start_background()
    return app


def test_build_app_serves_foundation_routes(data_root):
    app = run_app()
    try:
        status, payload = http_call(app, "GET", "/api/config")
        assert status == 200
        assert payload["needs_setup"] is True
        status, payload = http_call(app, "GET", "/api/paths")
        assert status == 200
        assert "capabilities" in payload
    finally:
        app.shutdown()


def test_startup_survives_corrupt_config(data_root):
    data_root.mkdir(parents=True)
    (data_root / "config.json").write_text("{not json at all", encoding="utf-8")
    app = run_app()                                        # bind must succeed (§1.4)
    try:
        status, payload = http_call(app, "GET", "/api/config")
        assert status == 500
        assert payload["error"]["code"] == "config_corrupt"   # error stays an error
        status, payload = http_call(app, "GET", "/api/paths")
        assert status == 200                               # status endpoint stays alive
        assert payload["capabilities"]["config"]["present"] is False
        assert payload["capabilities"]["config"]["detail"]
    finally:
        app.shutdown()


def test_startup_with_all_capabilities_missing(data_root, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", "/no/such/binary")
    app = run_app()                                        # R-foundation-05: still boots
    try:
        status, payload = http_call(app, "GET", "/api/paths")
        assert status == 200
        assert payload["capabilities"]["mlx_h3"]["present"] is False
        assert payload["capabilities"]["models_root"]["present"] is False
    finally:
        app.shutdown()
```

### 2. 实现 `desk/__main__.py`

```python
# desk/__main__.py
"""python -m desk — assemble and start the desk service.

R-foundation-05: missing mlx-h3 / venv / models directory / even a corrupt
config must never stop the bind. There is no SystemExit anywhere in desk/
(census A19, statically enforced by tests/test_foundation_invariants.py).
"""
from __future__ import annotations

import logging

from .app import DeskApp
from .foundation import capabilities as caps_mod
from .foundation import paths as paths_mod
from .foundation import routes as foundation_routes

log = logging.getLogger(__name__)


def build_app(host: str = "127.0.0.1", port: int = 8766) -> DeskApp:
    # Corrupt config must not stop assembly: default-derived roots are used for
    # binding/logging only; config-dependent endpoints keep raising config_corrupt.
    roots = paths_mod.resolve_paths(default_config_on_corrupt=True)
    paths_mod.setup_logging(roots)
    caps = caps_mod.probe_capabilities(roots)
    for name, cap in caps.items():
        log.info("capability %s present=%s %s", name, cap.present, cap.detail)
    app = DeskApp(host, port)
    app.add_routes(foundation_routes.build_routes())
    # Sibling modules append their route registrations here as they land
    # (registered even when a capability is absent; they answer with typed
    # errors at call time instead of dying at startup).
    return app


def main() -> None:
    app = build_app()
    log.info("desk listening on 127.0.0.1:8766")
    app.serve_forever()


if __name__ == "__main__":
    main()
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_main.py`
**提交** `foundation: python -m desk entrypoint — binds even with corrupt config, no SystemExit`

---

## T-foundation-13 仓库级静态不变量（census A16/A19 站岗）

**目标** `tests/test_foundation_invariants.py`：四条静态断言，防止后续模块把散落定义带回来。

### 1. 失败→通过测试（对已有代码直接应为通过；先跑一次确认收集数 > 0）

```python
# tests/test_foundation_invariants.py
"""Repo-level static guards. These stand watch for census A16/A19 and
R-foundation-01/05 across EVERY module that lands after foundation."""
import re
from pathlib import Path

DESK = Path(__file__).resolve().parent.parent / "desk"
PATHS_PY = DESK / "foundation" / "paths.py"


def _py_files():
    files = sorted(DESK.rglob("*.py"))
    assert files, "desk/ package missing"
    return files


def test_home_expansion_only_in_paths_py():
    # R-foundation-01: no second place may build paths from the home directory.
    offenders = []
    for f in _py_files():
        if f == PATHS_PY:
            continue
        text = f.read_text(encoding="utf-8")
        if "Path.home(" in text or "expanduser" in text:
            offenders.append(str(f))
    assert offenders == [], f"home-dir path building outside paths.py: {offenders}"


def test_no_system_exit_anywhere_in_desk():
    # census A19 / R-foundation-05: startup never dies by design.
    offenders = []
    for f in _py_files():
        text = f.read_text(encoding="utf-8")
        if "raise SystemExit" in text or "sys.exit(" in text:
            offenders.append(str(f))
    assert offenders == [], f"SystemExit/sys.exit found: {offenders}"


def test_file_logging_configured_in_exactly_one_place():
    # census A16: logs go to the data root via setup_logging, nowhere else.
    offenders = []
    for f in _py_files():
        if f == PATHS_PY:
            continue
        text = f.read_text(encoding="utf-8")
        for needle in ("logging.FileHandler", "RotatingFileHandler",
                       "logging.basicConfig"):
            if needle in text:
                offenders.append(f"{f}: {needle}")
    assert offenders == [], f"file logging outside setup_logging: {offenders}"
    assert "logging.FileHandler" in PATHS_PY.read_text(encoding="utf-8")


def test_foundation_imports_no_sibling_packages():
    # Root module consumes nothing (spec: 消费无).
    pattern = re.compile(r"^\s*(?:from|import)\s+desk\.(\w+)", re.MULTILINE)
    for f in (DESK / "foundation").rglob("*.py"):
        for match in pattern.finditer(f.read_text(encoding="utf-8")):
            assert match.group(1) == "foundation", \
                f"{f} imports desk.{match.group(1)}"
```

### 2. 实现

无新实现——若任一断言失败，修正对应源文件（这正是本任务存在的意义）。按前面任务的代码，四条应当直接通过；本任务同时是对 T-01~T-12 的整体复核，验收跑**全部** foundation 测试。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_foundation_errors.py tests/test_foundation_config.py tests/test_foundation_paths.py tests/test_foundation_firstrun.py tests/test_foundation_adopt.py tests/test_foundation_capabilities.py tests/test_foundation_routes.py tests/test_foundation_main.py tests/test_foundation_invariants.py`
**提交** `foundation: repo-level invariants — single path point, no SystemExit, single log point`

---

## Reality gates

无。全部 13 个任务都是 pytest + `tmp_path` 自证：不触网、不加载模型、不碰 `/Users/aa/LocalModelDesk/llms`、`minimax-h3/`、`minimax-music3/`、`outputs/`，不写 `/Applications` 或 LaunchAgents。

## 遗留物清理边界

census A13~A19 涉及的旧文件（`media-gui/`、根目录脚本）**不在本模块删除**——删除归属吸收它们的各模块与 packaging 的收尾任务；foundation 只负责让新路径/配置/日志单点成立并用 T-13 的静态测试站岗。
