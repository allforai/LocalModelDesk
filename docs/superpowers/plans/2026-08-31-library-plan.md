# library 模块实施计划（TDD）

**日期** 2026-08-31
**模块** `library` — 成品、作业历史、多会话聊天的本地持久化与回放
**spec** `docs/superpowers/specs/2026-08-31-library-spec.md`（R-library-01 … 07）
**design** `docs/superpowers/specs/2026-08-31-library-design.md`
**依赖** 消费 foundation 的 `api:resolvePaths` / `data:pathRoots`——但**仅以属性访问的方式**
（`roots.history_path` / `roots.outputs_root` / `roots.sessions_dir`）。全部测试用 `tmp_path`
构造假 roots，不 import foundation，因此本计划可与 foundation 并行执行。

**方法** 每个任务：写失败测试 → 跑确认失败 → 实现 → 跑通过 → commit。
所有验收命令在仓库根 `/Users/aa/LocalModelDesk` 下运行（`python3 -m pytest` 会把 cwd 加进
`sys.path`，`import desk.library.*` 依赖这一点；`desk/` 以 PEP 420 命名空间包工作，
不依赖 foundation 是否已建 `desk/__init__.py`）。

**零 reality gate**：spec 验收取向明说“全部纯单元测试”，且冻结环境能力表确认 pytest 可用。
本模块所有任务均可自证，无人工 runbook。

**硬边界**：绝不触碰真实 `/Users/aa/LocalModelDesk/outputs`、真权重目录；所有 IO 走 `tmp_path`。
错误就是错误：404/400/416/500 一律如实返回，无静默回退。

## 文件布局（最终形态）

```
desk/library/
  __init__.py     # LibraryService 门面 + 旧历史一次性收编（census A15）
  errors.py       # LibraryError / NotFoundError / ValidationError
  history.py      # HistoryStore：history.jsonl 追加式 JSONL
  outputs.py      # RangePlan/parse_range + OutputsStore（列表、路径安全、Range 流）
  sessions.py     # SessionStore：sessions/<id>.json 每会话一文件
  http.py         # FileSlice/LibRequest/Response + 传输无关处理函数 + 路由表
tests/
  test_library_history.py
  test_library_outputs.py
  test_library_sessions.py
  test_library_http.py
  test_library_no_stray_writes.py
```

## 接口归属（registry → 任务）

| registry 接口 | 任务 |
|---|---|
| `data:historyEntry` | T-library-01 |
| `data:chatSession` | T-library-07 |
| `api:appendHistory`（进程内，media 消费） | T-library-09 |
| `api:listOutputs` / `api:serveOutput` / `api:listHistory` | T-library-10 |
| `api:listChatSessions` / `api:createChatSession` / `api:updateChatSession` / `api:deleteChatSession` | T-library-11 |

## 任务 DAG

```
T-01 ──▶ T-02 ─────────────┐
  │                        ▼
  ├──▶ T-07 ──▶ T-08 ──▶ T-09 ──▶ T-10 ──▶ T-11 ──▶ T-12
  │                        ▲                          ▲
T-03 ──▶ T-04 ──▶ T-05 ──▶ T-06 ─────────────────────┘（T-04 另依赖 T-01）
```

## 设计内小决定（不改边界）

- `LibRequest` 携带原始 `body: bytes` 而非已解析 `json_body`：design 的错误表要求
  “请求体非合法 JSON → 400 由 http.py 在调 Store 前拦截”，解析必须发生在本模块内，
  原始字节才测得到这条路径。其余字段（path_params/query/headers）照 design。
- 时间戳格式常量 `%Y-%m-%dT%H:%M:%S` 在 history/outputs/sessions 各自文件内定义：
  design 要求三个 Store 互不依赖，一个 12 字符格式串的重复优于人为耦合。
- `resolve` 对以 `.` 开头的 name 一律拒绝（覆盖 `..` 与隐藏文件/临时文件），
  `list` 同步跳过 dot 文件——两侧口径一致。

---

## T-library-01 HistoryStore：append/list、校验与宽容读

**红** — 新建 `tests/test_library_history.py`：

```python
"""library.history — HistoryStore 单测（R-library-03 / R-library-04）。"""
import json
import threading
from pathlib import Path

import pytest

from desk.library.errors import ValidationError
from desk.library.history import HistoryStore


def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path / "history.jsonl")


def test_append_fills_id_and_ts_and_roundtrips_params(tmp_path):
    s = store(tmp_path)
    params = {"prompt": "夕阳下的猫", "steps": 12, "nested": {"a": [1, 2]}}
    entry = s.append({"kind": "video", "status": "done",
                      "output": "h3-x.mp4", "params": params})
    assert len(entry["id"]) == 32
    int(entry["id"], 16)                      # 32 位 hex
    assert "T" in entry["ts"]
    listed = s.list()
    assert len(listed) == 1
    assert listed[0]["params"] == params      # R-library-04：参数原样取回
    assert listed[0]["id"] == entry["id"]


def test_append_missing_required_field_writes_nothing(tmp_path):
    s = store(tmp_path)
    with pytest.raises(ValidationError):
        s.append({"status": "done"})          # 缺 kind
    with pytest.raises(ValidationError):
        s.append({"kind": "video"})           # 缺 status
    assert not (tmp_path / "history.jsonl").exists()   # 一个字节都不落盘


def test_list_newest_first_with_limit(tmp_path):
    s = store(tmp_path)
    for i in range(5):
        s.append({"kind": "video", "status": "done", "n": i})
    assert [e["n"] for e in s.list()] == [4, 3, 2, 1, 0]
    assert [e["n"] for e in s.list(limit=2)] == [4, 3]


def test_list_skips_bad_lines_and_never_rewrites_file(tmp_path):
    s = store(tmp_path)
    s.append({"kind": "music", "status": "done", "n": 0})
    f = tmp_path / "history.jsonl"
    with open(f, "a", encoding="utf-8") as fh:
        fh.write("not json at all\n")
        fh.write('{"kind": "video", "status": "done", "n": 1}\n')
        fh.write('{"trunca')                  # 进程崩溃留下的截断尾行
    before = f.read_bytes()
    assert [e["n"] for e in s.list()] == [1, 0]
    assert f.read_bytes() == before           # 读宽容、绝不改写文件
```

跑 `python3 -m pytest tests/test_library_history.py -q` → 收集失败（模块不存在）。

**绿** — 新建 `desk/library/__init__.py`（本任务仅占位 docstring，T-library-09 重写）：

```python
"""LocalModelDesk library 模块：成品、作业历史、多会话聊天的本地持久化。"""
```

新建 `desk/library/errors.py`：

```python
"""library 模块的类型化异常（http 层映射：NotFound→404、Validation→400）。"""


class LibraryError(Exception):
    """library 模块错误基类。"""


class NotFoundError(LibraryError):
    """目标不存在（或 id 格式非法，按不存在处理）。"""


class ValidationError(LibraryError):
    """入参不合法；任何字节都不会落盘。"""
```

新建 `desk/library/history.py`：

```python
"""作业历史 HistoryStore：追加式 JSONL，写严格、读宽容（R-library-03/04）。"""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .errors import ValidationError

_TS_FMT = "%Y-%m-%dT%H:%M:%S"


class HistoryStore:
    def __init__(self, history_file: Path):
        self._file = history_file
        self._lock = threading.Lock()

    def append(self, entry: dict) -> dict:
        if not isinstance(entry, dict):
            raise ValidationError("history entry must be a dict")
        for field in ("kind", "status"):
            if not entry.get(field):
                raise ValidationError(f"history entry missing required field: {field}")
        full = dict(entry)
        full.setdefault("id", uuid.uuid4().hex)
        full.setdefault("ts", datetime.now().strftime(_TS_FMT))
        line = json.dumps(full, ensure_ascii=False) + "\n"   # 锁外先组完整行
        with self._lock:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file, "a", encoding="utf-8") as f:
                f.write(line)                                # 单次 write，行原子
        return full

    def list(self, limit: int | None = None) -> list[dict]:
        entries = self._read_all()
        entries.reverse()                                    # 追加即时序 → 反转为新→旧
        if limit is not None:
            entries = entries[:limit]
        return entries

    def _read_all(self) -> list[dict]:
        if not self._file.exists():
            return []
        entries = []
        with open(self._file, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except ValueError:
                    continue                                 # 坏行跳过，绝不改写文件
                if isinstance(obj, dict):
                    entries.append(obj)
        return entries
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_history.py -q`
**commit** `library: HistoryStore append/list with strict-write tolerant-read (T-library-01)`

---

## T-library-02 HistoryStore：并发追加与 by_output

**红** — 追加到 `tests/test_library_history.py`：

```python
def test_concurrent_append_is_line_atomic(tmp_path):
    s = store(tmp_path)

    def worker():
        for _ in range(50):
            s.append({"kind": "video", "status": "done"})

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = (tmp_path / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 400                               # 恰 8×50 行
    ids = {json.loads(line)["id"] for line in lines}       # 每行都能解析
    assert len(ids) == 400                                 # 每条 id 唯一


def test_by_output_maps_filename_to_entry_and_skips_null(tmp_path):
    s = store(tmp_path)
    e1 = s.append({"kind": "video", "status": "done", "output": "h3-a.mp4"})
    s.append({"kind": "music", "status": "failed", "output": None})
    mapping = s.by_output()
    assert set(mapping) == {"h3-a.mp4"}
    assert mapping["h3-a.mp4"]["id"] == e1["id"]
```

**绿** — `desk/library/history.py` 增加方法（`by_output` 供 OutputsStore 合并孤儿用）：

```python
    def by_output(self) -> dict[str, dict]:
        mapping: dict[str, dict] = {}
        for entry in self._read_all():
            output = entry.get("output")
            if output:
                mapping[output] = entry
        return mapping
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_history.py -q`
**commit** `library: concurrent-safe history append + by_output join map (T-library-02)`

---

## T-library-03 parse_range 纯函数（RFC 7233 单区间）

**红** — 新建 `tests/test_library_outputs.py`：

```python
"""library.outputs — parse_range 与 OutputsStore 单测（R-library-01 / R-library-02）。"""
import pytest

from desk.library.outputs import RangePlan, parse_range


@pytest.mark.parametrize("size,header,expected", [
    (100, None, RangePlan(200, 0, 100)),                 # 无 Range → 全量
    (100, "chunks=0-5", RangePlan(200, 0, 100)),         # 非 bytes= 前缀 → 全量
    (100, "bytes=0-0", RangePlan(206, 0, 1)),
    (100, "bytes=10-19", RangePlan(206, 10, 10)),
    (100, "bytes=90-150", RangePlan(206, 90, 10)),       # 末端截断到 size-1
    (100, "bytes=10-", RangePlan(206, 10, 90)),
    (100, "bytes=-30", RangePlan(206, 70, 30)),
    (100, "bytes=-200", RangePlan(206, 0, 100)),         # 后缀超长 → 整个文件
    (100, "bytes=100-", RangePlan(416, 0, 0)),           # a ≥ size → 不可满足
    (100, "bytes=200-300", RangePlan(416, 0, 0)),
    (100, "bytes=-0", RangePlan(416, 0, 0)),
    (0, "bytes=0-", RangePlan(416, 0, 0)),               # 空文件带 Range
    (100, "bytes=5-2", RangePlan(200, 0, 100)),          # a>b 语法非法 → 忽略回退全量
    (100, "bytes=0-5,10-20", RangePlan(200, 0, 100)),    # 多区间不支持 → 全量
    (100, "bytes=abc-def", RangePlan(200, 0, 100)),      # 非数字 → 全量
])
def test_parse_range_table(size, header, expected):
    assert parse_range(size, header) == expected
```

**绿** — 新建 `desk/library/outputs.py`：

```python
"""成品列表与 Range 字节流（R-library-01 / R-library-02）。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RangePlan:
    status: int      # 200 | 206 | 416
    start: int
    length: int


def parse_range(size: int, header: str | None) -> RangePlan:
    """RFC 7233 单区间。语法非法/多区间 → 200 全量（RFC 允许忽略）；不可满足 → 416。"""
    full = RangePlan(200, 0, size)
    if header is None:
        return full
    header = header.strip()
    if not header.startswith("bytes="):
        return full
    spec = header[len("bytes="):].strip()
    if "," in spec or "-" not in spec:
        return full
    first, _, last = spec.partition("-")
    first, last = first.strip(), last.strip()
    if (first and not first.isdigit()) or (last and not last.isdigit()):
        return full
    if not first and not last:                       # "bytes=-"
        return full
    if not first:                                    # 后缀区间 bytes=-n
        n = int(last)
        if n == 0 or size == 0:
            return RangePlan(416, 0, 0)
        n = min(n, size)
        return RangePlan(206, size - n, n)
    start = int(first)
    if start >= size:                                # 覆盖 size == 0
        return RangePlan(416, 0, 0)
    if not last:                                     # bytes=a-
        return RangePlan(206, start, size - start)
    end = int(last)
    if end < start:
        return full
    end = min(end, size - 1)
    return RangePlan(206, start, end - start + 1)
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_outputs.py -q`
**commit** `library: parse_range pure function per RFC 7233 single-range (T-library-03)`

---

## T-library-04 OutputsStore.resolve：路径安全

**红** — 追加到 `tests/test_library_outputs.py`：

```python
from desk.library.history import HistoryStore
from desk.library.outputs import OutputsStore


def make_stores(tmp_path):
    history = HistoryStore(tmp_path / "history.jsonl")
    root = tmp_path / "outputs"
    root.mkdir()
    return OutputsStore(root, history), root, history


def test_resolve_returns_existing_regular_file(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x" * 8)
    assert outputs.resolve("h3-a.mp4") == (root / "h3-a.mp4").resolve()
    assert outputs.resolve("missing.mp4") is None


def test_resolve_rejects_escapes(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("s")
    (root / "link.mp4").symlink_to(secret)        # 指向根外的 symlink
    for name in ("../secret.txt", "/etc/passwd", "..", "a/b.mp4", "a\\b.mp4",
                 "%2e%2e%2fsecret.txt", "link.mp4", ""):
        assert outputs.resolve(name) is None, name
```

**绿** — `desk/library/outputs.py` 增加：

```python
import os
from pathlib import Path
from urllib.parse import unquote

from .history import HistoryStore


class OutputsStore:
    def __init__(self, outputs_root: Path, history: HistoryStore):
        self._root = outputs_root
        self._history = history

    def resolve(self, name: str) -> Path | None:
        """URL 解码后的裸文件名 → outputs 根内真实普通文件；任何逃逸 → None。"""
        name = unquote(name or "")
        if not name or "/" in name or "\\" in name or name.startswith("."):
            return None                              # 分隔符、..、dot 文件一律拒绝
        root = os.path.realpath(self._root)
        candidate = os.path.realpath(os.path.join(root, name))
        if not candidate.startswith(root + os.sep):
            return None                              # realpath 前缀检查拦住 symlink 逃逸
        path = Path(candidate)
        if not path.is_file():
            return None
        return path
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_outputs.py -q`
**commit** `library: OutputsStore.resolve confines serving to outputs root (T-library-04)`

---

## T-library-05 OutputsStore.list：磁盘 ⋈ 历史，孤儿可见

**红** — 追加到 `tests/test_library_outputs.py`：

```python
def test_list_joins_history_and_marks_orphans(tmp_path):
    outputs, root, history = make_stores(tmp_path)
    entry = history.append({"kind": "video", "status": "done", "output": "h3-known.mp4"})
    (root / "h3-known.mp4").write_bytes(b"a" * 10)
    (root / "h3-orphan.mp4").write_bytes(b"b" * 20)       # 磁盘有、历史无 → 孤儿
    (root / "music3-orphan.wav").write_bytes(b"c" * 30)
    (root / "mystery.webm").write_bytes(b"d" * 5)
    (root / "notes.txt").write_text("skip me")            # 非媒体后缀不出现
    history.append({"kind": "video", "status": "done", "output": "h3-gone.mp4"})  # 磁盘无

    items = {i["name"]: i for i in outputs.list()}
    assert set(items) == {"h3-known.mp4", "h3-orphan.mp4",
                          "music3-orphan.wav", "mystery.webm"}
    assert items["h3-known.mp4"] == {
        "name": "h3-known.mp4", "kind": "video", "bytes": 10,
        "ts": entry["ts"], "orphan": False, "history_id": entry["id"]}
    assert items["h3-orphan.mp4"]["orphan"] is True
    assert items["h3-orphan.mp4"]["kind"] == "video"      # h3- 前缀推断
    assert items["h3-orphan.mp4"]["history_id"] is None
    assert items["music3-orphan.wav"]["kind"] == "music"  # music3- 前缀推断
    assert items["mystery.webm"]["kind"] == "file"        # 无法推断
    assert items["h3-orphan.mp4"]["ts"]                   # 孤儿取 mtime


def test_list_missing_root_returns_empty(tmp_path):
    history = HistoryStore(tmp_path / "history.jsonl")
    assert OutputsStore(tmp_path / "nonexistent", history).list() == []
```

**绿** — `desk/library/outputs.py` 增加（`datetime` 进 import）：

```python
from datetime import datetime

_TS_FMT = "%Y-%m-%dT%H:%M:%S"
_MEDIA_SUFFIXES = frozenset({".mp4", ".wav", ".m4a", ".webm"})


def _infer_kind(name: str) -> str:
    if name.startswith("h3-"):
        return "video"
    if name.startswith("music3-"):
        return "music"
    return "file"
```

`OutputsStore` 增加方法：

```python
    def list(self) -> list[dict]:
        if not self._root.is_dir():
            return []
        by_output = self._history.by_output()
        items = []
        for child in self._root.iterdir():
            if child.name.startswith(".") or child.suffix.lower() not in _MEDIA_SUFFIXES:
                continue
            if not child.is_file():
                continue
            st = child.stat()
            mtime_ts = datetime.fromtimestamp(st.st_mtime).strftime(_TS_FMT)
            entry = by_output.get(child.name)
            if entry is None:
                items.append({"name": child.name, "kind": _infer_kind(child.name),
                              "bytes": st.st_size, "ts": mtime_ts,
                              "orphan": True, "history_id": None})
            else:
                items.append({"name": child.name,
                              "kind": entry.get("kind") or _infer_kind(child.name),
                              "bytes": st.st_size,
                              "ts": entry.get("ts") or mtime_ts,
                              "orphan": False, "history_id": entry.get("id")})
        items.sort(key=lambda item: item["ts"], reverse=True)
        return items
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_outputs.py -q`
**commit** `library: outputs listing joins history and surfaces orphans (T-library-05)`

---

## T-library-06 wire 载体 + OutputsStore.serve（Range 字节流）

**红** — 追加到 `tests/test_library_outputs.py`：

```python
def test_serve_full_and_range_bytes(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    payload = bytes(range(256)) * 8                       # 2048 字节
    (root / "h3-a.mp4").write_bytes(payload)

    full = outputs.serve("h3-a.mp4", None)
    assert full.status == 200
    assert full.headers["Accept-Ranges"] == "bytes"
    assert full.headers["Content-Type"] == "video/mp4"
    assert full.headers["Content-Length"] == "2048"
    assert full.body.read() == payload

    part = outputs.serve("h3-a.mp4", "bytes=0-1023")
    assert part.status == 206
    assert part.headers["Content-Range"] == "bytes 0-1023/2048"
    assert part.headers["Content-Length"] == "1024"
    got = part.body.read()
    assert len(got) == 1024 and got == payload[:1024]     # 恰 1024 字节、逐字节相等

    tail = outputs.serve("h3-a.mp4", "bytes=-100")
    assert tail.status == 206
    assert tail.headers["Content-Range"] == "bytes 1948-2047/2048"
    assert tail.body.read() == payload[-100:]


def test_serve_content_types(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    for name, ctype in [("a.wav", "audio/wav"), ("a.m4a", "audio/mp4"),
                        ("a.webm", "video/webm")]:
        (root / name).write_bytes(b"x")
        assert outputs.serve(name, None).headers["Content-Type"] == ctype


def test_serve_unsatisfiable_and_missing(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x" * 10)
    r = outputs.serve("h3-a.mp4", "bytes=10-")
    assert r.status == 416
    assert r.headers["Content-Range"] == "bytes */10"
    assert outputs.serve("../h3-a.mp4", None).status == 404   # 逃逸 → 404
    assert outputs.serve("missing.mp4", None).status == 404
```

**绿** — 新建 `desk/library/http.py`（本任务仅 wire 载体，处理函数在 T-10/T-11）：

```python
"""传输无关载体：FileSlice / LibRequest / Response（服务组装层负责真正写 socket）。"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileSlice:
    """文件区间描述符：组装层分块写 socket；测试直接 read() 断言字节。"""
    path: Path
    start: int
    length: int

    def read(self) -> bytes:
        with open(self.path, "rb") as f:
            f.seek(self.start)
            return f.read(self.length)


@dataclass(frozen=True)
class LibRequest:
    path_params: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: object          # bytes | FileSlice
```

`desk/library/outputs.py` 增加（import `json` 与 `from .http import FileSlice, Response`；
`_MEDIA_SUFFIXES` 改由 `_CONTENT_TYPES` 派生）：

```python
_CONTENT_TYPES = {".mp4": "video/mp4", ".wav": "audio/wav",
                  ".m4a": "audio/mp4", ".webm": "video/webm"}
_MEDIA_SUFFIXES = frozenset(_CONTENT_TYPES)
```

`OutputsStore` 增加方法：

```python
    def serve(self, name: str, range_header: str | None = None) -> Response:
        path = self.resolve(name)
        if path is None:
            return Response(404, {"Content-Type": "application/json"},
                            json.dumps({"error": "output not found"}).encode("utf-8"))
        size = path.stat().st_size
        plan = parse_range(size, range_header)
        headers = {"Accept-Ranges": "bytes",
                   "Content-Type": _CONTENT_TYPES[path.suffix.lower()]}
        if plan.status == 416:
            headers["Content-Range"] = f"bytes */{size}"
            return Response(416, headers, b"")
        headers["Content-Length"] = str(plan.length)
        if plan.status == 206:
            end = plan.start + plan.length - 1
            headers["Content-Range"] = f"bytes {plan.start}-{end}/{size}"
        return Response(plan.status, headers, FileSlice(path, plan.start, plan.length))
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_outputs.py -q`
**commit** `library: serve outputs with RFC 7233 ranges via FileSlice (T-library-06)`

---

## T-library-07 SessionStore：create/list/delete 与「重启后仍在」

**红** — 新建 `tests/test_library_sessions.py`：

```python
"""library.sessions — 多会话聊天持久化单测（R-library-05 / R-library-06）。"""
from pathlib import Path

import pytest

from desk.library.errors import NotFoundError, ValidationError
from desk.library.sessions import SessionStore


def test_create_list_roundtrip_and_restart(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create()
    b = s.create(title="配色讨论", model="qwen3")
    assert a["title"] == "新会话" and a["model"] is None and a["messages"] == []
    assert len(a["id"]) == 32
    assert a["created"] == a["updated"]
    assert {x["id"] for x in s.list()} == {a["id"], b["id"]}
    # 「重启」：同目录重新构造对象，状态全在磁盘（R-library-06）
    s2 = SessionStore(tmp_path / "sessions")
    got_b = next(x for x in s2.list() if x["id"] == b["id"])
    assert got_b["title"] == "配色讨论" and got_b["model"] == "qwen3"


def test_delete_removes_file(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create()
    path = tmp_path / "sessions" / f"{a['id']}.json"
    assert path.is_file()
    s.delete(a["id"])
    assert not path.exists()                    # 删除会话即删除其持久化文件
    assert s.list() == []
    with pytest.raises(NotFoundError):          # 不假装成功
        s.delete(a["id"])


def test_list_empty_when_dir_missing(tmp_path):
    assert SessionStore(tmp_path / "sessions").list() == []
```

**绿** — 新建 `desk/library/sessions.py`：

```python
"""多会话聊天 SessionStore：sessions/<id>.json 每会话一文件（R-library-05/06/07）。"""
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .errors import NotFoundError, ValidationError

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_TS_FMT = "%Y-%m-%dT%H:%M:%S"


class SessionStore:
    def __init__(self, sessions_dir: Path):
        self._dir = sessions_dir
        self._lock = threading.Lock()

    def list(self) -> list[dict]:
        if not self._dir.is_dir():
            return []
        sessions = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("session file is not an object")
            except ValueError:
                sessions.append({"id": path.stem, "corrupt": True})   # 不隐藏、不伪造
                continue
            sessions.append(data)
        sessions.sort(key=lambda s: s.get("updated", ""), reverse=True)
        return sessions

    def create(self, title: str | None = None, model: str | None = None) -> dict:
        now = datetime.now().strftime(_TS_FMT)
        session = {"id": uuid.uuid4().hex, "title": title or "新会话", "model": model,
                   "created": now, "updated": now, "messages": []}
        with self._lock:
            self._write(session)
        return session

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        with self._lock:
            if path is None or not path.is_file():
                raise NotFoundError(f"session not found: {session_id}")
            path.unlink()

    def _path(self, session_id) -> Path | None:
        if not isinstance(session_id, str) or not _ID_RE.match(session_id):
            return None                          # 非法 id 按不存在处理，顺带杜绝路径注入
        return self._dir / f"{session_id}.json"

    def _write(self, session: dict) -> None:
        payload = json.dumps(session, ensure_ascii=False, indent=2)   # 先序列化再动盘
        self._dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._dir, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self._dir / f"{session['id']}.json")      # 原子落盘
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_sessions.py -q`
**commit** `library: SessionStore create/list/delete with on-disk truth (T-library-07)`

---

## T-library-08 SessionStore.update：patch 校验、原子写、损坏占位

**红** — 追加到 `tests/test_library_sessions.py`：

```python
def test_update_rename_model_messages_and_persists(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create()
    msgs = [{"role": "user", "content": "你好"},
            {"role": "assistant", "content": "在", "reasoning": "…"}]
    updated = s.update(a["id"], {"title": "新名字", "model": "qwen3", "messages": msgs})
    assert updated["title"] == "新名字" and updated["model"] == "qwen3"
    assert updated["messages"] == msgs           # 消息结构原样存取，不解释
    assert updated["created"] == a["created"]
    s2 = SessionStore(tmp_path / "sessions")     # 重启后仍在
    got = next(x for x in s2.list() if x["id"] == a["id"])
    assert got["messages"] == msgs and got["title"] == "新名字"


def test_update_unknown_key_or_bad_messages_rejected(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create()
    with pytest.raises(ValidationError):
        s.update(a["id"], {"nope": 1})
    with pytest.raises(ValidationError):
        s.update(a["id"], {"messages": "not-a-list"})


def test_unknown_or_malformed_id_is_not_found(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    s.create()
    for bad in ("0" * 32, "../../x", "zz", ""):
        with pytest.raises(NotFoundError):
            s.update(bad, {"title": "x"})
        with pytest.raises(NotFoundError):
            s.delete(bad)
    assert len(s.list()) == 1                    # update 不静默新建


def test_write_failure_keeps_old_file_intact(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create(title="保住我")
    path = tmp_path / "sessions" / f"{a['id']}.json"
    before = path.read_bytes()
    with pytest.raises(TypeError):
        s.update(a["id"], {"messages": [object()]})       # 不可 JSON 化
    assert path.read_bytes() == before                    # 旧文件完好
    assert list((tmp_path / "sessions").glob(".tmp-*")) == []   # 无残留临时文件


def test_corrupt_file_yields_placeholder(tmp_path):
    s = SessionStore(tmp_path / "sessions")
    a = s.create()
    (tmp_path / "sessions" / ("f" * 32 + ".json")).write_text("{oops", encoding="utf-8")
    listed = s.list()
    assert a["id"] in {x["id"] for x in listed}           # 其余会话正常
    assert {"id": "f" * 32, "corrupt": True} in listed    # 单文件损坏只出占位
```

**绿** — `desk/library/sessions.py` 增加：

```python
_PATCH_KEYS = frozenset({"title", "model", "messages"})
```

`SessionStore` 增加方法：

```python
    def update(self, session_id: str, patch: dict) -> dict:
        if not isinstance(patch, dict):
            raise ValidationError("patch must be an object")
        unknown = set(patch) - _PATCH_KEYS
        if unknown:
            raise ValidationError(f"unknown patch keys: {sorted(unknown)}")
        if "messages" in patch and not isinstance(patch["messages"], list):
            raise ValidationError("messages must be a list")
        with self._lock:
            session = self._load(session_id)
            session.update(patch)
            session["updated"] = datetime.now().strftime(_TS_FMT)
            self._write(session)
        return session

    def _load(self, session_id) -> dict:
        path = self._path(session_id)
        if path is None or not path.is_file():
            raise NotFoundError(f"session not found: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))
```

（损坏文件上的 `update` 让 `json.loads` 的 `ValueError` 原样冒泡为 500——错误就是错误。）

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_sessions.py -q`
**commit** `library: session update with patch validation and atomic replace (T-library-08)`

---

## T-library-09 LibraryService 门面 + 旧历史一次性收编（census A15）

**红** — 追加到 `tests/test_library_history.py`：

```python
from desk.library import LibraryService


class FakeRoots:
    """data:pathRoots 的最小假实现——library 只做属性访问，不 import foundation。"""

    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


def test_service_wires_stores_end_to_end(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    svc = LibraryService(roots)
    entry = svc.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 4)
    assert svc.list_history()[0]["id"] == entry["id"]
    assert svc.list_outputs()[0]["history_id"] == entry["id"]
    assert svc.serve_output("h3-a.mp4", "bytes=0-1").status == 206
    session = svc.create_chat_session(title="t")
    svc.update_chat_session(session["id"], {"model": "m"})
    assert svc.list_chat_sessions()[0]["model"] == "m"
    svc.delete_chat_session(session["id"])
    assert svc.list_chat_sessions() == []


def test_legacy_history_adopted_by_copy(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    legacy = roots.outputs_root / "history.jsonl"
    legacy_bytes = b'{"kind": "video", "status": "done", "output": "h3-old.mp4"}\n'
    legacy.write_bytes(legacy_bytes)
    svc = LibraryService(roots)
    assert roots.history_path.read_bytes() == legacy_bytes   # 数据根出现同字节副本
    assert legacy.read_bytes() == legacy_bytes               # 源文件原封不动（只 copy）
    assert svc.list_history()[0]["output"] == "h3-old.mp4"   # 缺 id 的旧行照常展示


def test_legacy_adoption_is_idempotent_and_never_overwrites(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    legacy_bytes = b'{"kind": "video", "status": "done"}\n'
    (roots.outputs_root / "history.jsonl").write_bytes(legacy_bytes)
    mine = b'{"kind": "music", "status": "done"}\n'
    roots.history_path.write_bytes(mine)
    LibraryService(roots)
    assert roots.history_path.read_bytes() == mine           # 目标已存在 → 什么都不做
    assert (roots.outputs_root / "history.jsonl").read_bytes() == legacy_bytes
```

**绿** — 重写 `desk/library/__init__.py`：

```python
"""LocalModelDesk library 模块：成品、作业历史、多会话聊天的本地持久化。

LibraryService 消费 foundation 的 data:pathRoots（仅属性访问：history_path /
outputs_root / sessions_dir），把三个 Store 装配起来，并按 registry 名暴露方法。
api:appendHistory 只走进程内 Python 调用（唯一消费者 media 与本服务同进程）。
"""
import os
import tempfile

from .errors import LibraryError, NotFoundError, ValidationError
from .history import HistoryStore
from .outputs import OutputsStore
from .sessions import SessionStore

__all__ = ["LibraryService", "LibraryError", "NotFoundError", "ValidationError"]


class LibraryService:
    def __init__(self, roots):
        _adopt_legacy_history(roots)                    # census A15：先收编再开店
        self.history = HistoryStore(roots.history_path)
        self.outputs = OutputsStore(roots.outputs_root, self.history)
        self.sessions = SessionStore(roots.sessions_dir)

    # api:appendHistory —— media 进程内调用
    def append_history(self, entry: dict) -> dict:
        return self.history.append(entry)

    # api:listHistory
    def list_history(self, limit: int | None = None) -> list[dict]:
        return self.history.list(limit)

    # api:listOutputs
    def list_outputs(self) -> list[dict]:
        return self.outputs.list()

    # api:serveOutput
    def serve_output(self, name: str, range_header: str | None = None):
        return self.outputs.serve(name, range_header)

    # api:listChatSessions
    def list_chat_sessions(self) -> list[dict]:
        return self.sessions.list()

    # api:createChatSession
    def create_chat_session(self, title: str | None = None, model: str | None = None) -> dict:
        return self.sessions.create(title, model)

    # api:updateChatSession
    def update_chat_session(self, session_id: str, patch: dict) -> dict:
        return self.sessions.update(session_id, patch)

    # api:deleteChatSession
    def delete_chat_session(self, session_id: str) -> None:
        self.sessions.delete(session_id)


def _adopt_legacy_history(roots) -> None:
    """旧 outputs/history.jsonl 一次性逐字节复制到数据根。

    只 copy、绝不移动或删除源（outputs 目录冻结不可动）；目标已存在则什么都不做
    （幂等，不合并不覆盖）。经同目录临时文件 + os.replace 原子落地。
    """
    target = roots.history_path
    legacy = roots.outputs_root / "history.jsonl"
    if target.exists() or not legacy.is_file():
        return
    data = legacy.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-history-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_history.py -q`
**commit** `library: LibraryService facade + one-shot legacy history adoption (T-library-09)`

---

## T-library-10 http 处理函数：outputs 与 history 路由

**红** — 新建 `tests/test_library_http.py`：

```python
"""library.http — 传输无关处理函数与错误映射单测。"""
import json
from pathlib import Path

import pytest

from desk.library import LibraryService
from desk.library.http import LibRequest, routes


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


def make_service(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    return LibraryService(roots), roots


def route_map(service):
    return {(method, path): handler for method, path, handler in routes(service)}


def body_json(resp):
    return json.loads(resp.body.decode("utf-8"))


def test_list_history_and_outputs_routes(tmp_path):
    svc, roots = make_service(tmp_path)
    svc.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
    svc.append_history({"kind": "music", "status": "done", "output": None})
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 4)
    rm = route_map(svc)
    hist = rm[("GET", "/api/history")](LibRequest(query={"limit": "1"}))
    assert hist.status == 200 and len(body_json(hist)) == 1
    outs = rm[("GET", "/api/outputs")](LibRequest())
    assert outs.status == 200 and body_json(outs)[0]["name"] == "h3-a.mp4"


def test_serve_output_route_maps_range_404_416(tmp_path):
    svc, roots = make_service(tmp_path)
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 10)
    handler = route_map(svc)[("GET", "/api/outputs/{name}")]
    ok = handler(LibRequest(path_params={"name": "h3-a.mp4"},
                            headers={"range": "bytes=2-3"}))       # 头名大小写不敏感
    assert ok.status == 206
    assert ok.headers["Content-Range"] == "bytes 2-3/10"
    assert ok.body.read() == b"xx"
    assert handler(LibRequest(path_params={"name": "../evil"})).status == 404
    r416 = handler(LibRequest(path_params={"name": "h3-a.mp4"},
                              headers={"Range": "bytes=99-"}))
    assert r416.status == 416


def test_bad_limit_is_400(tmp_path):
    svc, _ = make_service(tmp_path)
    resp = route_map(svc)[("GET", "/api/history")](LibRequest(query={"limit": "abc"}))
    assert resp.status == 400 and "error" in body_json(resp)
```

**绿** — `desk/library/http.py` 增加（import `json` 与 `from .errors import NotFoundError, ValidationError`）：

```python
def _json_response(status: int, payload) -> Response:
    return Response(status, {"Content-Type": "application/json"},
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _json_body(request: LibRequest) -> dict:
    """在调 Store 前解析请求体；非法 JSON / 非对象 → ValidationError → 400。"""
    try:
        parsed = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValidationError(f"request body is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValidationError("request body must be a JSON object")
    return parsed


def _header(request: LibRequest, name: str) -> str | None:
    for key, value in request.headers.items():
        if key.lower() == name.lower():
            return value
    return None


def handle_list_outputs(service, request: LibRequest) -> Response:
    return _json_response(200, service.list_outputs())


def handle_serve_output(service, request: LibRequest) -> Response:
    return service.serve_output(request.path_params["name"], _header(request, "Range"))


def handle_list_history(service, request: LibRequest) -> Response:
    raw = request.query.get("limit")
    limit = None
    if raw is not None:
        if not str(raw).isdigit():
            raise ValidationError("limit must be a non-negative integer")
        limit = int(raw)
    return _json_response(200, service.list_history(limit))


def dispatch(service, handler, request: LibRequest) -> Response:
    """NotFound→404、Validation→400；其余异常（OSError 等）冒泡给组装层作 500。"""
    try:
        return handler(service, request)
    except NotFoundError as exc:
        return _json_response(404, {"error": str(exc)})
    except ValidationError as exc:
        return _json_response(400, {"error": str(exc)})


def routes(service) -> list[tuple[str, str, object]]:
    """(method, path, handler) 路由表，由服务组装层统一挂载。"""

    def bind(handler):
        return lambda request: dispatch(service, handler, request)

    return [
        ("GET", "/api/outputs/{name}", bind(handle_serve_output)),
        ("GET", "/api/outputs", bind(handle_list_outputs)),
        ("GET", "/api/history", bind(handle_list_history)),
    ]
```

（本任务只挂 outputs/history 三条路由；覆盖全表的
`test_route_table_covers_module_contract` 属于 T-library-11 的红。）

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_http.py -q`
**commit** `library: transport-agnostic handlers for outputs and history (T-library-10)`

---

## T-library-11 http 处理函数：session CRUD 路由

**红** — 追加到 `tests/test_library_http.py`（含上一任务说明中移过来的全表用例）：

```python
def test_route_table_covers_module_contract(tmp_path):
    svc, _ = make_service(tmp_path)
    assert set(route_map(svc)) == {
        ("GET", "/api/outputs"), ("GET", "/api/outputs/{name}"),
        ("GET", "/api/history"),
        ("GET", "/api/sessions"), ("POST", "/api/sessions"),
        ("PATCH", "/api/sessions/{id}"), ("DELETE", "/api/sessions/{id}"),
    }


def test_session_crud_over_http(tmp_path):
    svc, _ = make_service(tmp_path)
    rm = route_map(svc)
    created = rm[("POST", "/api/sessions")](
        LibRequest(body=json.dumps({"title": "t"}).encode()))
    assert created.status == 200
    sid = body_json(created)["id"]
    patched = rm[("PATCH", "/api/sessions/{id}")](LibRequest(
        path_params={"id": sid},
        body=json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode()))
    assert patched.status == 200 and len(body_json(patched)["messages"]) == 1
    listed = rm[("GET", "/api/sessions")](LibRequest())
    assert body_json(listed)[0]["id"] == sid
    deleted = rm[("DELETE", "/api/sessions/{id}")](LibRequest(path_params={"id": sid}))
    assert deleted.status == 200 and body_json(deleted) == {"deleted": sid}


def test_create_with_empty_body_uses_defaults(tmp_path):
    svc, _ = make_service(tmp_path)
    resp = route_map(svc)[("POST", "/api/sessions")](LibRequest())
    assert resp.status == 200 and body_json(resp)["title"] == "新会话"


def test_http_error_mapping(tmp_path):
    svc, _ = make_service(tmp_path)
    rm = route_map(svc)
    # 404：不存在的会话
    assert rm[("DELETE", "/api/sessions/{id}")](
        LibRequest(path_params={"id": "0" * 32})).status == 404
    # 400：请求体非法 JSON（在调 Store 前拦截）
    assert rm[("PATCH", "/api/sessions/{id}")](
        LibRequest(path_params={"id": "0" * 32}, body=b"{oops")).status == 400
    # 400：未知 patch 键
    sid = body_json(rm[("POST", "/api/sessions")](LibRequest()))["id"]
    assert rm[("PATCH", "/api/sessions/{id}")](LibRequest(
        path_params={"id": sid},
        body=json.dumps({"nope": 1}).encode())).status == 400
    # 400：POST 未知键
    assert rm[("POST", "/api/sessions")](
        LibRequest(body=json.dumps({"weird": 1}).encode())).status == 400
```

**绿** — `desk/library/http.py` 增加处理函数并把 `routes` 扩成全表：

```python
def handle_list_sessions(service, request: LibRequest) -> Response:
    return _json_response(200, service.list_chat_sessions())


def handle_create_session(service, request: LibRequest) -> Response:
    payload = _json_body(request) if request.body else {}
    unknown = set(payload) - {"title", "model"}
    if unknown:
        raise ValidationError(f"unknown keys: {sorted(unknown)}")
    return _json_response(
        200, service.create_chat_session(payload.get("title"), payload.get("model")))


def handle_update_session(service, request: LibRequest) -> Response:
    return _json_response(
        200, service.update_chat_session(request.path_params["id"], _json_body(request)))


def handle_delete_session(service, request: LibRequest) -> Response:
    session_id = request.path_params["id"]
    service.delete_chat_session(session_id)
    return _json_response(200, {"deleted": session_id})
```

`routes()` 的返回表追加：

```python
        ("GET", "/api/sessions", bind(handle_list_sessions)),
        ("POST", "/api/sessions", bind(handle_create_session)),
        ("PATCH", "/api/sessions/{id}", bind(handle_update_session)),
        ("DELETE", "/api/sessions/{id}", bind(handle_delete_session)),
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_http.py -q`
**commit** `library: session CRUD handlers complete the route table (T-library-11)`

---

## T-library-12 R-library-07 强制点：无旁路写 + 源码静态断言

**红→绿** — 新建 `tests/test_library_no_stray_writes.py`（禁止性需求，直接写全套断言）：

```python
"""R-library-07：library 只写注入 roots 之下——只读 cwd 陷阱 + 源码静态扫描。"""
import json
import os
from pathlib import Path

from desk.library import LibraryService
from desk.library.http import LibRequest, routes

MODULE_DIR = Path(__file__).resolve().parents[1] / "desk" / "library"


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


def test_full_flow_writes_only_under_roots(tmp_path):
    jail = tmp_path / "jail"                 # 只读 cwd：任何相对路径写都会当场炸
    jail.mkdir()
    base = tmp_path / "data"
    base.mkdir()
    roots = FakeRoots(base)
    roots.outputs_root.mkdir()
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 16)
    old_cwd = os.getcwd()
    os.chmod(jail, 0o500)
    os.chdir(jail)
    try:
        svc = LibraryService(roots)
        svc.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
        svc.list_history()
        svc.list_outputs()
        assert svc.serve_output("h3-a.mp4", "bytes=0-3").body.read() == b"xxxx"
        sid = svc.create_chat_session(title="t")["id"]
        svc.update_chat_session(sid, {"messages": [{"role": "user", "content": "hi"}]})
        svc.delete_chat_session(sid)
        for method, path, handler in routes(svc):
            if method == "GET":              # 全部读路由也跑一遍
                handler(LibRequest(path_params={"name": "h3-a.mp4", "id": "0" * 32}))
    finally:
        os.chdir(old_cwd)
        os.chmod(jail, 0o700)
    assert list(jail.iterdir()) == []        # 只读 cwd 仍为空
    for p in tmp_path.rglob("*"):            # roots 之外无新文件
        assert p == jail or p == base or base in p.parents, p


def test_module_source_has_no_hardcoded_user_paths():
    banned = ["Path.home(", "expanduser(", "/Users", "/Applications", '"~', "'~"]
    sources = list(MODULE_DIR.glob("*.py"))
    assert len(sources) >= 5                 # errors/history/outputs/sessions/http/__init__
    for src in sources:
        text = src.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{src.name} contains banned path token {token!r}"
```

第一次运行若发现任何实现文件有 cwd 相对写或硬编码路径，此测试变红——修实现，不改测试。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_library_no_stray_writes.py tests/test_library_history.py tests/test_library_outputs.py tests/test_library_sessions.py tests/test_library_http.py -q`
（最后一个任务同时回归全模块。）
**commit** `library: enforce no writes outside injected roots (T-library-12)`

---

## 收尾核对单

- [ ] `python3 -m pytest tests/test_library_*.py -q` 全绿（模块整体回归）。
- [ ] `desk/library/` 内 grep 不到 `Path.home(` / `expanduser(` / 绝对用户路径（T-12 已自动强制）。
- [ ] 未触碰 `/Users/aa/LocalModelDesk/outputs`、任何真权重目录；未写 `/Applications`。
- [ ] 每任务一次 commit，信息如上；不 push。
