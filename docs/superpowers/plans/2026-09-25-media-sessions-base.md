# 媒体会话底座 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把图片会话泛化成 image / video / music 三种媒体共用的会话底座，并加上续写链（作业内自动拼成片）、手动合成作业与跨会话引用机制；图片页行为不变，视频页音乐页照旧可用。

**Architecture:** `ImageSessionStore` 改名泛化为 `MediaSessionStore(kind, …)`，每种 kind 一个目录、一份参数白名单。`MediaService` 对所有 kind 挂会话；续写作业在同一个工作线程里先跑模型、再跑 ffmpeg 拼接，模型退出即释放重活许可；手动合成是只跑 ffmpeg 的作业，共用互斥与轮询。ffmpeg 命令全部由新文件 `desk/media/compose.py` 构造（纯函数、输出路径永远是最后一个参数）。

**Tech Stack:** Python 3（标准库 + pytest），ffmpeg / ffprobe 子进程，原生 ES module 前端（`node --test`），Playwright e2e（`tests/e2e`）。

**Spec:** `docs/superpowers/specs/2026-09-25-media-sessions-base-design.md`（下称 B-xx）；上游 `docs/superpowers/specs/2026-09-24-image-sessions-design.md`（下称 IS D-xx）。

## Global Constraints

- 台面未发布：不写兼容层、不谈迁移；旧名字（`ImageSessionStore`、`image_sessions_dir`、`/api/image-sessions`、`listImageSessions` 等）改完后仓库里一处不留（B-21）。
- 三个 kind：`("image", "video", "music")`；会话目录 `data_root/{kind}-sessions`（B-01）。
- 尝试记录只由后端写（B-20）；启动前任一步失败都不写会话（B-33）。
- 内存检查只提醒可确认，不新增硬拒绝；compose 与拼接不做内存检查、不走 arbiter（B-45、B-62）。
- ffmpeg 不可用只影响需要拼接或截帧的请求：503 `capability_missing`「需要 ffmpeg 才能拼接成片」（B-60）。
- 拼接常量：视频帧率 `24`、续写段丢首帧；音乐交叉淡化 `1.5` 秒，任一段短于 `3.0` 秒则该接缝直接拼接（B-50、B-51）。
- 成片文件名：`h3-joined-<stamp>-<8hex>.mp4` / `music3-joined-<stamp>-<8hex>.wav`；合成成品：`h3-compose-<stamp>-<8hex>.mp4` / `music3-compose-<stamp>-<8hex>.wav`（B-42）。
- 本块内 video/music 的 `session_id` 可省略（不挂会话、照旧运行）；带 `continues` 或 `refs` 时必填（§3.2）。
- 界面文案与图片页 DOM 一字不改（B-71）；本块不改 `panes/video.js`、`panes/music.js`（B-73）。
- 测试命令：Python 用系统 `python3 -m pytest`（`.venv-desk` 里没有 pytest）；JS 用 `node --test tests/js/`；改了 `desk/static` 必须跑 `python3 -m pytest tests/e2e -q`。
- 提交信息用中文、`feat(media-sessions): …` / `refactor(media-sessions): …` 前缀，结尾加 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## Review Focus

1. **续写链中间一段的文件被用户在访达里删了**：续写仍然生成、这一段 `done`，`joined_error.code == "segment_missing"` 且说出第几段 —— 测试在 Task 6「broken chain」。
2. **拼接进行到一半用户点取消 / 退出应用**：已生成的单段不能丢，尝试 `done` + `join_cancelled`；许可只释放一次 —— 测试在 Task 6「cancel during join」。
3. **续写请求在 `media_busy` 或内存确认被拒**：已截出的末帧 PNG 不能留在 `.inputs/`，会话不写 —— 测试在 Task 6「refused continuation cleans frame」。
4. **旧图片会话文件没有 `kind` 字段**（本机 `image-sessions/` 里已有的会话）：照常读出、不算坏文件 —— 测试在 Task 1「kindless file」。
5. **手动合成的片段尺寸不一**（不同分辨率的视频段）：按第一段尺寸缩放补边，不报错 —— 测试在 Task 3「mixed sizes」（真 ffmpeg）。

---

## File Structure

| 文件 | 动作 | 职责 |
|---|---|---|
| `desk/library/media_sessions.py` | 新建（由 `image_sessions.py` 改名泛化） | 唯一读写 `*-sessions/*.json` 的组件；kind、白名单、续写链、`record_output` |
| `desk/library/image_sessions.py` | 删除 | — |
| `desk/library/__init__.py` | 改 | `media_sessions: dict[kind, store]`；按 kind 的门面方法 |
| `desk/library/http.py` | 改 | `/api/media-sessions/{kind}[/{id}]` |
| `desk/library/history.py` | 改 | `by_output()` 同时索引 `joined_output` |
| `desk/foundation/paths.py` | 改 | `PathRoots.media_sessions_dirs` |
| `desk/foundation/routes.py`、`desk/testing/harness.py` | 改 | `/api/paths` 输出、`media_sessions=` 接通 |
| `desk/runtime.py` | 改 | `media_sessions=library.media_sessions` |
| `desk/media/compose.py` | 新建 | ffmpeg / ffprobe 命令构造与探测 |
| `desk/media/commands.py` | 改 | `--seed` |
| `desk/media/music3_cli.py` | 改 | `--seed` |
| `desk/media/service.py` | 改 | 通用会话挂接、seed、refs、continues、拼接、compose |
| `desk/media/routes.py` | 改 | 透传新字段；`POST /api/media/compose` |
| `desk/testing/fakes.py`、`tests/media_fakes.py` | 改 | 假执行器识别 ffmpeg 命令（输出取最后一个参数） |
| `desk/static/js/api.js`、`desk/static/js/panes/image.js` | 改 | `mediaSessions(kind)` 系列 |
| `desk/static/js/pure/history_fill.js` | 改 | video/music 带出会话字段；compose 条目返回 null |
| 测试 | 改/新建 | 见各任务 |

---

### Task 1: MediaSessionStore（存储泛化 + 全部 Python 调用方改名）

**Files:**
- Create: `desk/library/media_sessions.py`
- Delete: `desk/library/image_sessions.py`
- Modify: `desk/foundation/paths.py:53,149`、`desk/foundation/routes.py:72`、`desk/testing/harness.py:187,347`、`desk/runtime.py:206`、`desk/library/__init__.py`、`desk/media/service.py`（构造参数与 `_image_sessions` 引用）、`tests/media_fakes.py`
- Test: `tests/test_media_sessions.py`（由 `tests/test_image_sessions.py` 改名），`tests/test_foundation_paths.py:68`、`tests/test_library_history.py:36`、`tests/test_library_http.py:15`、`tests/test_library_no_stray_writes.py:16`、`tests/test_media_image_service.py`、`tests/test_image_sessions_wiring.py`（只改 Python 名字，路由字符串留给 Task 2）

**Interfaces:**
- Produces:
  - `desk.library.media_sessions.KINDS = ("image", "video", "music")`
  - `PARAM_KEYS: dict[str, tuple[str, ...]]`、`TITLE_FIELD: dict[str, str]`、`COMPOSE_PARAM_KEYS = ("parts",)`
  - `class SegmentMissing(Exception)`
  - `MediaSessionStore(kind: str, sessions_dir: Path, outputs_root: Path)`，方法：`list() / get(id) / exists(id) / create() / rename(id, title) / delete(id) / begin_attempt(id, attempt: dict) -> bool / record_output(id, attempt_id, output) -> bool / settle_attempt(id, attempt_id, status, output=None, error=None, joined_output=None, joined_error=None) -> bool / recover_running() -> int / find_done(id, attempt_id) -> dict / chain(id, attempt_id) -> tuple[list[dict], bool]`
  - `begin_attempt` 的 `attempt` 键：`id, job_id, params, op="generate", continues=None, refs=None, base=None`
  - `PathRoots.media_sessions_dirs: dict[str, Path]`
  - `LibraryService.media_sessions: dict[str, MediaSessionStore]`；`LibraryService.sessions_of(kind) -> MediaSessionStore`（kind 不认识 → `NotFoundError("不认识的媒体类型：<kind>")`）
  - `MediaService(..., media_sessions: dict[str, MediaSessionStore], ...)`（取代 `image_sessions=`），内部 `self._sessions`

- [ ] **Step 1: 改名测试文件并把导入与构造换成新名字**

```bash
git mv tests/test_image_sessions.py tests/test_media_sessions.py
```

在 `tests/test_media_sessions.py` 顶部把导入与辅助函数改成：

```python
from desk.library.media_sessions import MediaSessionStore, SegmentMissing, auto_title


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.media_sessions_dirs = {k: base / f"{k}-sessions" for k in ("image", "video", "music")}
        self.outputs_root = base / "outputs"


def store(tmp_path, kind="image") -> MediaSessionStore:
    return MediaSessionStore(kind, tmp_path / f"{kind}-sessions", tmp_path / "outputs")
```

文件里其余 `ImageSessionStore(...)` 全部换成 `store(tmp_path)`；`roots.image_sessions_dir` 换成 `roots.media_sessions_dirs["image"]`；`library.image_sessions` 换成 `library.media_sessions["image"]`。HTTP 路由字符串 `/api/image-sessions` 本任务不动（Task 2 改）——若本文件里有经 `routes()` 调用的测试，先保持原样，它们会在 Step 4 继续通过，因为 Task 1 保留旧路由到 Task 2。

- [ ] **Step 2: 在 `tests/test_media_sessions.py` 末尾追加新行为测试**

```python
# ---- media-sessions base (B-03, B-04, B-06–B-08, B-12, B-22, B-38a) ---------

def vparams(**extra):
    return {"prompt": "雨夜街道", "width": 512, "height": 288, "frames": 49, "steps": 12, "seed": 7, **extra}


def begin_kind(sessions, session_id, *, attempt_id, params, op="generate", continues=None):
    assert sessions.begin_attempt(session_id, {"id": attempt_id, "job_id": 1, "params": params,
                                               "op": op, "continues": continues})
    return attempt_id


def finish(sessions, session_id, attempt_id, output, outputs_root):
    outputs_root.mkdir(parents=True, exist_ok=True)
    (outputs_root / output).write_bytes(b"x")
    assert sessions.settle_attempt(session_id, attempt_id, "done", output)


@pytest.mark.parametrize("kind", ["image", "video", "music"])
def test_each_kind_lives_in_its_own_directory_and_records_its_kind(tmp_path, kind):
    sessions = store(tmp_path, kind)
    created = sessions.create()
    assert created["kind"] == kind
    assert (tmp_path / f"{kind}-sessions" / f"{created['id']}.json").is_file()


def test_kindless_file_reads_as_its_directory_kind(tmp_path):
    sessions = store(tmp_path, "image")
    created = sessions.create()
    path = tmp_path / "image-sessions" / f"{created['id']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["kind"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert sessions.get(created["id"])["kind"] == "image"
    assert [s["id"] for s in sessions.list()] == [created["id"]]


def test_file_of_another_kind_is_corrupt(tmp_path):
    sessions = store(tmp_path, "video")
    created = sessions.create()
    path = tmp_path / "video-sessions" / f"{created['id']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["kind"] = "music"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert sessions.list() == [{"id": created["id"], "corrupt": True}]
    with pytest.raises(ValidationError):
        sessions.get(created["id"])


def test_music_title_comes_from_caption_and_params_follow_the_whitelist(tmp_path):
    sessions = store(tmp_path, "music")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32,
               params={"caption": "独立流行 110 BPM", "lyrics": "[verse]\n早晨", "duration": 20, "seed": 7, "junk": 1})
    session = sessions.get(sid)
    assert session["title"] == "独立流行 110 BPM"
    assert session["attempts"][0]["params"] == {"caption": "独立流行 110 BPM", "lyrics": "[verse]\n早晨",
                                                "duration": 20, "seed": 7}


def test_attempt_carries_op_continues_refs_and_empty_join_fields(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams())
    attempt = sessions.get(sid)["attempts"][0]
    assert attempt["op"] == "generate" and attempt["continues"] is None and attempt["refs"] == {}
    assert attempt["joined_output"] is None and attempt["joined_error"] is None and attempt["base"] is None


def test_compose_attempt_keeps_only_parts_and_never_retitles(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="c" * 32, params={"parts": ["a" * 32, "b" * 32], "prompt": "x"}, op="compose")
    attempt = sessions.get(sid)["attempts"][0]
    assert attempt["op"] == "compose" and attempt["params"] == {"parts": ["a" * 32, "b" * 32]}
    assert sessions.get(sid)["title"] == "新会话"   # 合成不参与自动标题（B-46）


def test_record_output_then_settle_done_with_joined_output(tmp_path):
    sessions, outputs = store(tmp_path, "video"), tmp_path / "outputs"
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams(), continues="f" * 32)
    assert sessions.record_output(sid, "a" * 32, "h3-seg.mp4")
    assert sessions.get(sid)["attempts"][0]["status"] == "running"
    assert sessions.get(sid)["attempts"][0]["output"] == "h3-seg.mp4"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "h3-seg.mp4").write_bytes(b"x")
    assert sessions.settle_attempt(sid, "a" * 32, "done", "h3-seg.mp4", joined_output="h3-joined.mp4")
    attempt = sessions.get(sid)["attempts"][0]
    assert attempt["joined_output"] == "h3-joined.mp4" and attempt["joined_error"] is None
    assert attempt["joined_missing"] is True  # 文件不在（B-12）


def test_record_output_ignores_settled_or_unknown_attempts(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    assert sessions.record_output(sid, "a" * 32, "x.mp4") is False
    assert sessions.record_output("0" * 32, "a" * 32, "x.mp4") is False


def test_recover_running_keeps_a_recorded_segment_as_done(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams(), continues="f" * 32)
    sessions.record_output(sid, "a" * 32, "h3-seg.mp4")
    begin_kind(sessions, sid, attempt_id="b" * 32, params=vparams())
    assert sessions.recover_running() == 2
    first, second = sessions.get(sid)["attempts"]
    assert first["status"] == "done" and first["output"] == "h3-seg.mp4"
    assert first["joined_error"] == {"code": "interrupted", "message": "应用在拼接成片时关闭"}
    assert second["status"] == "failed" and second["error"]["code"] == "interrupted"


def test_cover_prefers_joined_output(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams(), continues="f" * 32)
    sessions.settle_attempt(sid, "a" * 32, "done", "h3-seg.mp4", joined_output="h3-joined.mp4")
    assert sessions.list()[0]["cover"] == "h3-joined.mp4"


def test_find_done_distinguishes_unknown_from_missing(tmp_path):
    sessions, outputs = store(tmp_path, "video"), tmp_path / "outputs"
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams())
    with pytest.raises(SegmentMissing):
        sessions.find_done(sid, "a" * 32)          # 还在 running
    finish(sessions, sid, "a" * 32, "h3-a.mp4", outputs)
    assert sessions.find_done(sid, "a" * 32)["output"] == "h3-a.mp4"
    (outputs / "h3-a.mp4").unlink()
    with pytest.raises(SegmentMissing):
        sessions.find_done(sid, "a" * 32)          # 文件不在
    with pytest.raises(NotFoundError):
        sessions.find_done(sid, "9" * 32)          # 没有这一段


def test_chain_walks_continues_back_to_the_head_and_forks_independently(tmp_path):
    sessions, outputs = store(tmp_path, "video"), tmp_path / "outputs"
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="a" * 32, params=vparams())
    finish(sessions, sid, "a" * 32, "a.mp4", outputs)
    begin_kind(sessions, sid, attempt_id="b" * 32, params=vparams(), continues="a" * 32)
    finish(sessions, sid, "b" * 32, "b.mp4", outputs)
    begin_kind(sessions, sid, attempt_id="c" * 32, params=vparams(), continues="a" * 32)  # 分叉
    items, broken = sessions.chain(sid, "b" * 32)
    assert [i["id"] for i in items] == ["a" * 32, "b" * 32] and broken is False
    items, broken = sessions.chain(sid, "c" * 32)
    assert [i["id"] for i in items] == ["a" * 32, "c" * 32] and broken is False


def test_chain_marks_broken_on_dangling_link_and_on_cycles(tmp_path):
    sessions = store(tmp_path, "video")
    sid = sessions.create()["id"]
    begin_kind(sessions, sid, attempt_id="b" * 32, params=vparams(), continues="a" * 32)  # a 不存在
    items, broken = sessions.chain(sid, "b" * 32)
    assert [i["id"] for i in items] == ["b" * 32] and broken is True
    path = tmp_path / "video-sessions" / f"{sid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["attempts"].append({**data["attempts"][0], "id": "a" * 32, "continues": "b" * 32})
    path.write_text(json.dumps(data), encoding="utf-8")
    items, broken = sessions.chain(sid, "b" * 32)
    assert broken is True and len(items) == 2
```

- [ ] **Step 3: 跑新测试确认失败**

Run: `python3 -m pytest tests/test_media_sessions.py -q`
Expected: 导入失败 `ModuleNotFoundError: No module named 'desk.library.media_sessions'`

- [ ] **Step 4: 写 `desk/library/media_sessions.py`（改名 + 泛化）**

```bash
git mv desk/library/image_sessions.py desk/library/media_sessions.py
```

然后把文件改成下面这样（保留原有的 `_Corrupt`、`auto_title`、`_now`、`_path`、`_load`、`_load_quiet`、`_write`、`rename`、`delete`、`exists` 实现不变，只替换/新增下列部分）：

```python
"""Media generation sessions (image / video / music): one JSON file per session.

Layout and write discipline follow ``SessionStore``: ``<id>.json`` under the kind's
own directory, atomic temp-file + ``os.replace`` writes, dot-prefixed files skipped.
Every write method does read → modify → write back inside one lock and keeps no
in-memory copy, so a job settling an attempt and a request renaming or deleting
the same session never overwrite each other.
"""
# (imports unchanged)

KINDS = ("image", "video", "music")
PARAM_KEYS = {
    "image": ("prompt", "width", "height", "steps", "seed"),
    "video": ("prompt", "width", "height", "frames", "steps", "seed",
              "mode", "use_audio", "first_frame", "last_frame", "ref_video"),
    "music": ("caption", "lyrics", "duration", "seed"),
}
COMPOSE_PARAM_KEYS = ("parts",)
TITLE_FIELD = {"image": "prompt", "video": "prompt", "music": "caption"}
INTERRUPTED_JOIN_ERROR = {"code": "interrupted", "message": "应用在拼接成片时关闭"}


class SegmentMissing(Exception):
    """The attempt exists but is not done, or its file is gone."""


class MediaSessionStore:
    def __init__(self, kind: str, sessions_dir: Path, outputs_root: Path):
        if kind not in KINDS:
            raise ValueError(f"unknown media kind: {kind}")
        self.kind = kind
        self._dir = Path(sessions_dir)
        self._outputs_root = Path(outputs_root)
        self._lock = threading.Lock()

    def get(self, session_id: str) -> dict:
        session = self._load(session_id)
        for attempt in session["attempts"]:
            if isinstance(attempt, dict) and attempt.get("status") == "done":
                attempt["output_missing"] = not self._is_output(attempt.get("output"))
                if attempt.get("joined_output"):
                    attempt["joined_missing"] = not self._is_output(attempt["joined_output"])
        return session

    def create(self) -> dict:
        now = _now()
        session = {"id": uuid.uuid4().hex, "kind": self.kind, "title": DEFAULT_TITLE, "title_auto": True,
                   "created": now, "updated": now, "attempts": []}
        with self._lock:
            self._write(session)
        return session

    def begin_attempt(self, session_id: str, attempt: dict) -> bool:
        """Append a running attempt; False (never an exception) when the session is gone or unreadable."""
        op = attempt.get("op") or "generate"
        params = attempt.get("params") or {}
        keys = COMPOSE_PARAM_KEYS if op == "compose" else PARAM_KEYS[self.kind]
        record = {
            "id": attempt["id"], "job_id": attempt.get("job_id"), "ts": _now(), "finished": None,
            "status": "running", "op": op,
            "params": {key: params[key] for key in keys if key in params},
            "continues": attempt.get("continues"), "refs": dict(attempt.get("refs") or {}),
            "output": None, "joined_output": None, "joined_error": None, "error": None,
            "base": attempt.get("base"),
        }
        with self._lock:
            session = self._load_quiet(session_id)
            if session is None:
                return False
            if op == "generate" and not session["attempts"] and session.get("title_auto", True):
                source = record["params"].get(TITLE_FIELD[self.kind]) or ""
                session["title"] = auto_title(source) or DEFAULT_TITLE
            session["attempts"].append(record)
            session["updated"] = record["ts"]
            self._write(session)
        return True

    def record_output(self, session_id: str, attempt_id: str, output: str) -> bool:
        """Write the finished segment's file name into a still-running attempt (B-38a)."""
        with self._lock:
            session = self._load_quiet(session_id)
            attempt = self._running(session, attempt_id)
            if attempt is None:
                return False
            attempt["output"] = output
            self._write(session)
        return True

    def settle_attempt(self, session_id: str, attempt_id: str, status: str, output: str | None = None,
                       error: dict | None = None, joined_output: str | None = None,
                       joined_error: dict | None = None) -> bool:
        """Settle a running attempt; False when the session or a running attempt with that id is gone."""
        if status not in SETTLED_STATUSES:
            raise ValueError(f"not a settled status: {status}")
        with self._lock:
            session = self._load_quiet(session_id)
            attempt = self._running(session, attempt_id)
            if attempt is None:
                return False
            now = _now()
            done = status == "done"
            attempt.update(
                status=status, finished=now,
                output=(output or attempt.get("output")) if done else None,
                error=None if done else dict(error or {}),
                joined_output=joined_output if done else None,
                joined_error=dict(joined_error) if done and joined_error else None,
            )
            session["updated"] = now
            self._write(session)
        return True

    def recover_running(self) -> int:
        """Settle attempts a previous process left running; a recorded segment survives as done (B-38a)."""
        if not self._dir.is_dir():
            return 0
        changed = 0
        with self._lock:
            for path in sorted(self._dir.glob("*.json")):
                if path.name.startswith("."):
                    continue
                try:
                    session = self._parse(path)
                except _Corrupt:
                    continue
                stale = [item for item in session["attempts"]
                         if isinstance(item, dict) and item.get("status") == "running"]
                if not stale:
                    continue
                now = _now()
                for attempt in stale:
                    if attempt.get("output"):
                        attempt.update(status="done", finished=now, error=None, joined_output=None,
                                       joined_error=dict(INTERRUPTED_JOIN_ERROR))
                    else:
                        attempt.update(status="failed", finished=now, output=None,
                                       error=dict(INTERRUPTED_ERROR))
                session["updated"] = now
                self._write(session)
                changed += len(stale)
        return changed

    def find_done(self, session_id: str, attempt_id: str) -> dict:
        """The done attempt whose file still exists; NotFoundError / SegmentMissing otherwise."""
        session = self.get(session_id)
        attempt = next((a for a in session["attempts"]
                        if isinstance(a, dict) and a.get("id") == attempt_id), None)
        if attempt is None:
            raise NotFoundError(f"找不到这一段：{attempt_id}")
        if attempt.get("status") != "done" or attempt.get("output_missing"):
            raise SegmentMissing(attempt_id)
        return attempt

    def chain(self, session_id: str, attempt_id: str) -> tuple[list[dict], bool]:
        """Attempts from the chain head to ``attempt_id`` (inclusive), following ``continues`` (B-22)."""
        session = self.get(session_id)
        by_id = {a.get("id"): a for a in session["attempts"] if isinstance(a, dict)}
        items, seen, cursor = [], set(), attempt_id
        while cursor is not None:
            if cursor in seen or cursor not in by_id:
                return list(reversed(items)), True
            seen.add(cursor)
            items.append(by_id[cursor])
            cursor = by_id[cursor].get("continues")
        return list(reversed(items)), False

    # ---- internals -------------------------------------------------------

    def _is_output(self, name) -> bool:
        return isinstance(name, str) and bool(name) and (self._outputs_root / name).is_file()

    @staticmethod
    def _running(session: dict | None, attempt_id: str) -> dict | None:
        if session is None:
            return None
        attempt = next((item for item in session["attempts"]
                        if isinstance(item, dict) and item.get("id") == attempt_id), None)
        return attempt if attempt is not None and attempt.get("status") == "running" else None

    @staticmethod
    def _summary(session: dict) -> dict:
        attempts = [item for item in session["attempts"] if isinstance(item, dict)]
        done = [item.get("joined_output") or item.get("output") for item in attempts
                if item.get("status") == "done" and (item.get("joined_output") or item.get("output"))]
        return {
            "id": session.get("id"), "title": session.get("title"),
            "created": session.get("created"), "updated": session.get("updated"),
            "attempt_count": len(session["attempts"]),
            "running": any(item.get("status") == "running" for item in attempts),
            "cover": done[-1] if done else None,
        }

    def _parse(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise _Corrupt(str(exc)) from exc
        if not isinstance(data, dict) or not isinstance(data.get("attempts"), list):
            raise _Corrupt("session file is not a session object")
        if data.setdefault("kind", self.kind) != self.kind:
            raise _Corrupt(f"session kind {data['kind']!r} in the {self.kind} directory")
        data["id"] = path.stem  # the file name is the identity; a later write must land on the same file
        return data
```

注意：`_parse` 从 `@staticmethod` 改成实例方法（要知道 `self.kind`）；原 `list()` 里 `self._parse(path)` 调用不用改。`_load_quiet` 的日志文案把 `image session` 改成 `f"{self.kind} session"`。删掉旧的 `PARAM_KEYS = (...)` 元组常量。

- [ ] **Step 5: 路径、门面、接通**

`desk/foundation/paths.py`：字段 `image_sessions_dir: Path` 改为 `media_sessions_dirs: dict`；构造处（原第 149 行）改为

```python
        media_sessions_dirs={kind: static.data_root / f"{kind}-sessions" for kind in ("image", "video", "music")},
```

`desk/foundation/routes.py:72` 与 `desk/testing/harness.py:187` 的 `"image_sessions_dir": str(roots.image_sessions_dir),` 都改为

```python
            "media_sessions_dirs": {kind: str(path) for kind, path in roots.media_sessions_dirs.items()},
```

`desk/library/__init__.py`：

```python
from .media_sessions import KINDS, MediaSessionStore
...
        self.media_sessions = {kind: MediaSessionStore(kind, roots.media_sessions_dirs[kind], roots.outputs_root)
                               for kind in KINDS}
        # 上次进程被杀时还在跑的尝试不会再有人落定；启动时一次性收尾（IS D-25、B-38a）。
        for store in self.media_sessions.values():
            store.recover_running()
```

把 `list_image_sessions / create_image_session / get_image_session / rename_image_session / delete_image_session` 五个方法替换为：

```python
    def sessions_of(self, kind: str) -> MediaSessionStore:
        store = self.media_sessions.get(kind)
        if store is None:
            raise NotFoundError(f"不认识的媒体类型：{kind}")
        return store
```

`desk/library/http.py` 暂时把五个 `handle_*_image_session` 改为调 `service.sessions_of("image").list()` 等（路由字符串 Task 2 再改）：

```python
def handle_list_image_sessions(service, request: LibRequest) -> Response:
    return _json_response(200, service.sessions_of("image").list())
# create → .create()；get → .get(id)；rename → .rename(id, title)；delete → .delete(id)
```

模块 docstring 首行改为 `"""Local persistence for outputs, job history, chat sessions and media sessions."""`。

`desk/media/service.py`：构造参数 `image_sessions` 改名 `media_sessions`，`self._image_sessions = image_sessions` 改为 `self._sessions = media_sessions`；docstring 里描述 `image_sessions` 的段落改为描述 `media_sessions: dict[kind, store]`；文件内所有 `self._image_sessions` 改为 `self._sessions["image"]`（Task 5 再泛化）。

`desk/runtime.py:206` 与 `desk/testing/harness.py:347`：`image_sessions=library.image_sessions,` 改为 `media_sessions=library.media_sessions,`。

`tests/media_fakes.py`：

```python
from desk.library.media_sessions import KINDS, MediaSessionStore
...
def make_service(tmp_path: Path, *, executor=None, memory_warning=None, media_sessions=None):
    """The session stores are real file stores under ``tmp_path`` unless given."""
    executor = executor or FakeExecutor()
    media_sessions = media_sessions or {kind: MediaSessionStore(kind, tmp_path / f"{kind}-sessions", tmp_path / "outputs")
                                        for kind in KINDS}
    ...
        append_history=history.append, executor=executor, media_sessions=media_sessions,
    ...
    return service, SimpleNamespace(executor=executor, arbiter=arbiter, history=history,
                                    media_sessions=media_sessions, image_sessions=media_sessions["image"])
```

（`deps.image_sessions` 作为测试便利别名保留在测试辅助里，指向 image 存储，避免改写 `test_media_image_service.py` 里几十处。）

`tests/test_media_image_service.py`：`from desk.library.image_sessions import ImageSessionStore` 改为 `from desk.library.media_sessions import KINDS, MediaSessionStore`；两处子类 `class VanishingStore(ImageSessionStore)` / `class BrokenStore(ImageSessionStore)` 改继承 `MediaSessionStore`，构造改为 `VanishingStore("image", tmp_path / "image-sessions", tmp_path / "outputs")`，传参改为

```python
    stores = {kind: MediaSessionStore(kind, tmp_path / f"{kind}-sessions", tmp_path / "outputs") for kind in KINDS}
    stores["image"] = store
    service, deps = image_service(tmp_path, media_sessions=stores)
```

其余测试的 FakeRoots（`test_library_history.py:36`、`test_library_http.py:15`、`test_library_no_stray_writes.py:16`）把 `self.image_sessions_dir = base / "image-sessions"` 改为 `self.media_sessions_dirs = {k: base / f"{k}-sessions" for k in ("image", "video", "music")}`。`tests/test_foundation_paths.py:68` 改为

```python
    assert roots.media_sessions_dirs == {k: roots.data_root / f"{k}-sessions" for k in ("image", "video", "music")}
```

`tests/test_image_sessions_wiring.py` 里 `runtime.media._image_sessions` 改为 `runtime.media._sessions["image"]`。

- [ ] **Step 6: 跑受影响的测试**

Run: `python3 -m pytest tests/test_media_sessions.py tests/test_media_image_service.py tests/test_image_sessions_wiring.py tests/test_library_http.py tests/test_library_history.py tests/test_library_no_stray_writes.py tests/test_foundation_paths.py tests/test_media_service.py -q`
Expected: 全部 PASS

- [ ] **Step 7: 全量 Python 单测 + 旧名字扫描**

Run: `python3 -m pytest -q --ignore=tests/e2e && grep -rn "ImageSessionStore\|image_sessions_dir\|desk.library.image_sessions\|_image_sessions" desk tests --include='*.py'`
Expected: 测试全部 PASS；grep 无输出

- [ ] **Step 8: Commit**

```bash
git add -A desk tests
git commit -m "refactor(media-sessions): 图片会话存储泛化为按 kind 分的媒体会话存储

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `/api/media-sessions/{kind}` 路由与前端调用

**Files:**
- Modify: `desk/library/http.py:139-199`、`desk/static/js/api.js:12,139-143`、`desk/static/js/panes/image.js`（6 处 api 调用）
- Test: `tests/test_media_sessions.py`（HTTP 部分）、`tests/test_library_http.py:86-90`、`tests/test_image_sessions_wiring.py`、`tests/js/api.test.js:59-79,138`、`tests/js/image_pane.test.js:102-105,414-439`、`tests/e2e/test_image_sessions.py`

**Interfaces:**
- Consumes: `LibraryService.sessions_of(kind)`（Task 1）
- Produces: HTTP `GET/POST /api/media-sessions/{kind}`、`GET/PATCH/DELETE /api/media-sessions/{kind}/{id}`；JS `listMediaSessions(kind)`、`createMediaSession(kind)`、`getMediaSession(kind, id)`、`renameMediaSession(kind, id, title)`、`deleteMediaSession(kind, id)`

- [ ] **Step 1: 写失败的 HTTP 测试（追加到 `tests/test_media_sessions.py`）**

```python
@pytest.mark.parametrize("kind", ["image", "video", "music"])
def test_media_session_routes_round_trip_per_kind(tmp_path, kind):
    library, roots = make_library(tmp_path)
    table = {(m, p): h for m, p, h in routes(library)}
    created = json.loads(table[("POST", "/api/media-sessions/{kind}")](
        LibRequest(path_params={"kind": kind}, body=b"{}")).body)
    assert created["kind"] == kind
    listed = json.loads(table[("GET", "/api/media-sessions/{kind}")](LibRequest(path_params={"kind": kind})).body)
    assert [s["id"] for s in listed] == [created["id"]]
    other = "music" if kind != "music" else "video"
    assert json.loads(table[("GET", "/api/media-sessions/{kind}")](LibRequest(path_params={"kind": other})).body) == []
    renamed = table[("PATCH", "/api/media-sessions/{kind}/{id}")](
        LibRequest(path_params={"kind": kind, "id": created["id"]}, body=json.dumps({"title": "新名字"}).encode()))
    assert renamed.status == 200 and json.loads(renamed.body)["title"] == "新名字"
    deleted = table[("DELETE", "/api/media-sessions/{kind}/{id}")](LibRequest(path_params={"kind": kind, "id": created["id"]}))
    assert json.loads(deleted.body) == {"deleted": created["id"]}


def test_unknown_media_kind_is_404(tmp_path):
    library, _ = make_library(tmp_path)
    table = {(m, p): h for m, p, h in routes(library)}
    response = table[("GET", "/api/media-sessions/{kind}")](LibRequest(path_params={"kind": "gif"}))
    assert response.status == 404 and json.loads(response.body) == {"error": "不认识的媒体类型：gif"}
```

`LibRequest` 是 dataclass（`path_params`、`query`、`headers`、`body: bytes`），`Response.body` 是 UTF-8 JSON 的 bytes，所以上面直接 `json.loads(response.body)`。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_media_sessions.py -q -k "routes_round_trip or unknown_media_kind"`
Expected: FAIL，`KeyError: ('POST', '/api/media-sessions/{kind}')`

- [ ] **Step 3: 改路由**

`desk/library/http.py`：五个 handler 改名并按 kind 取存储：

```python
def _store(service, request: LibRequest):
    return service.sessions_of(request.path_params["kind"])


def handle_list_media_sessions(service, request: LibRequest) -> Response:
    return _json_response(200, _store(service, request).list())


def handle_create_media_session(service, request: LibRequest) -> Response:
    store = _store(service, request)
    _only_keys(_json_body(request) if request.body else {}, set())
    return _json_response(200, store.create())


def handle_get_media_session(service, request: LibRequest) -> Response:
    return _json_response(200, _store(service, request).get(request.path_params["id"]))


def handle_rename_media_session(service, request: LibRequest) -> Response:
    store = _store(service, request)
    payload = _json_body(request)
    _only_keys(payload, {"title"})
    return _json_response(200, store.rename(request.path_params["id"], payload.get("title")))


def handle_delete_media_session(service, request: LibRequest) -> Response:
    session_id = request.path_params["id"]
    _store(service, request).delete(session_id)
    return _json_response(200, {"deleted": session_id})
```

路由表五行替换为：

```python
        ("GET", "/api/media-sessions/{kind}", bind(handle_list_media_sessions)),
        ("POST", "/api/media-sessions/{kind}", bind(handle_create_media_session)),
        ("GET", "/api/media-sessions/{kind}/{id}", bind(handle_get_media_session)),
        ("PATCH", "/api/media-sessions/{kind}/{id}", bind(handle_rename_media_session)),
        ("DELETE", "/api/media-sessions/{kind}/{id}", bind(handle_delete_media_session)),
```

`tests/test_library_http.py:86-90` 的期望路由表五行同样替换。`tests/test_media_sessions.py` 里原 `/api/image-sessions` 的 HTTP 测试把路由键换成 `/api/media-sessions/{kind}…`、`path_params` 加 `"kind": "image"`。`tests/test_image_sessions_wiring.py` 里所有 `"/api/image-sessions"` 换成 `"/api/media-sessions/image"`（`f"/api/image-sessions/{x}"` → `f"/api/media-sessions/image/{x}"`），目录 `data_root / "image-sessions"` 不变。

- [ ] **Step 4: 跑 Python 测试**

Run: `python3 -m pytest tests/test_media_sessions.py tests/test_library_http.py tests/test_image_sessions_wiring.py -q`
Expected: PASS

- [ ] **Step 5: 改 JS 测试期望**

`tests/js/api.test.js:59-63` 改为：

```js
    ["listMediaSessions", ["image"], "/api/media-sessions/image", "GET"],
    ["createMediaSession", ["video"], "/api/media-sessions/video", "POST", {}],
    ["getMediaSession", ["music", "ab/c"], "/api/media-sessions/music/ab%2Fc", "GET"],
    ["renameMediaSession", ["image", "s1", "橘猫"], "/api/media-sessions/image/s1", "PATCH", { title: "橘猫" }],
    ["deleteMediaSession", ["image", "s1"], "/api/media-sessions/image/s1", "DELETE"],
```

第 79 行导出名单同步改为 `"listMediaSessions", "createMediaSession", "getMediaSession", "renameMediaSession", "deleteMediaSession",`；第 138 行 `api.getImageSession("abc")` 改为 `api.getMediaSession("image", "abc")`。

`tests/js/image_pane.test.js`：第 102–105 行与 414–439 行的 URL 匹配把 `/api/image-sessions` 换成 `/api/media-sessions/image`，正则 `^\/api\/image-sessions\/(\w+)$` 换成 `^\/api\/media-sessions\/image\/(\w+)$`。

Run: `node --test tests/js/`
Expected: FAIL（`api.listMediaSessions is not a function` 等）

- [ ] **Step 6: 改 `api.js` 与 `image.js`**

`desk/static/js/api.js`：`ROUTES` 里 `imageSessions: "/api/image-sessions",` 改为 `mediaSessions: "/api/media-sessions",`；第 139–143 行替换为：

```js
const mediaSessionsUrl = (kind) => `${ROUTES.mediaSessions}/${encoded(kind)}`;
export const listMediaSessions = (kind) => request(mediaSessionsUrl(kind));
export const createMediaSession = (kind) => json(mediaSessionsUrl(kind), "POST", {});
export const getMediaSession = (kind, id) => request(`${mediaSessionsUrl(kind)}/${encoded(id)}`);
export const renameMediaSession = (kind, id, title) => json(`${mediaSessionsUrl(kind)}/${encoded(id)}`, "PATCH", { title });
export const deleteMediaSession = (kind, id) => json(`${mediaSessionsUrl(kind)}/${encoded(id)}`, "DELETE");
```

`toError` 里注释「library 路由（会话、图片会话）」改为「library 路由（会话、媒体会话）」。

`desk/static/js/panes/image.js`：在 `createImagePane` 顶部加 `const KIND = "image";`，并替换调用：
- `api.renameImageSession(summary.id, title)` → `api.renameMediaSession(KIND, summary.id, title)`
- `api.deleteImageSession(summary.id)` → `api.deleteMediaSession(KIND, summary.id)`
- `api.listImageSessions()`（3 处）→ `api.listMediaSessions(KIND)`
- `api.createImageSession()`（2 处）→ `api.createMediaSession(KIND)`
- `api.getImageSession(id)`、`api.getImageSession(plan.session_id)` → `api.getMediaSession(KIND, …)`

Run: `node --test tests/js/ && grep -rn "ImageSession\|image-sessions" desk/static`
Expected: PASS；grep 只剩 `widgets/image_session_card.js`、`widgets/image_session_list.js`、`pure/image_session.js` 这些**文件名/导入路径**（它们是图片专属的卡片与纯逻辑，本块不改名），不出现 `/api/image-sessions` 或 `*ImageSession(` 调用。

- [ ] **Step 7: 改 e2e 并跑**

`tests/e2e/test_image_sessions.py`：所有 `/api/image-sessions` 换成 `/api/media-sessions/image`；第 499 行 `harness.roots.image_sessions_dir` 换成 `harness.roots.media_sessions_dirs["image"]`。

Run: `python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add -A desk tests
git commit -m "refactor(media-sessions): 会话接口改为 /api/media-sessions/{kind}，图片页改用新接口

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `compose.py` —— ffmpeg 原语

**Files:**
- Create: `desk/media/compose.py`
- Test: `tests/test_media_compose.py`

**Interfaces:**
- Produces:
  - 常量 `FPS = 24`、`CROSSFADE_S = 1.5`、`SHORT_SEGMENT_S = 3.0`、`FFMPEG_MISSING = "需要 ffmpeg 才能拼接成片"`
  - `ffmpeg_path() -> str | None`、`ffprobe_path() -> str | None`
  - `probe_size(ffprobe: str, video: Path) -> tuple[int, int]`（失败抛 `ValueError`）
  - `last_frame_command(ffmpeg: str, video: Path, png: Path) -> list[str]`
  - `concat_video_command(ffmpeg: str, parts: list[tuple[Path, bool]], size: tuple[int, int], output: Path) -> list[str]`（`bool` = 这一段丢首帧）
  - `crossfade_audio_command(ffmpeg: str, parts: list[tuple[Path, float]], output: Path) -> list[str]`（`float` = 这一段秒数）
  - `replace_audio_command(ffmpeg: str, video: Path, audio: Path, output: Path) -> list[str]`
  - 不变量：每个命令以 `-y` 开头（在可执行文件之后）、**最后一个参数是输出路径**（假执行器依赖这一点）。

- [ ] **Step 1: 写失败测试**

```python
"""ffmpeg primitives: argv shape (always) and real runs on lavfi clips (when ffmpeg exists)."""
import shutil
import subprocess
from pathlib import Path

import pytest

from desk.media import compose

FF = shutil.which("ffmpeg")
FP = shutil.which("ffprobe")
needs_ffmpeg = pytest.mark.skipif(not (FF and FP), reason="ffmpeg/ffprobe not installed")


def test_every_command_ends_with_its_output(tmp_path):
    out = tmp_path / "o"
    for cmd in (compose.last_frame_command("ff", Path("v.mp4"), out),
                compose.concat_video_command("ff", [(Path("a.mp4"), False), (Path("b.mp4"), True)], (512, 288), out),
                compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 20.0)], out),
                compose.replace_audio_command("ff", Path("v.mp4"), Path("a.wav"), out)):
        assert cmd[0] == "ff" and cmd[1] == "-y" and cmd[-1] == str(out)


def test_concat_drops_first_frame_only_where_asked(tmp_path):
    cmd = compose.concat_video_command("ff", [(Path("a.mp4"), False), (Path("b.mp4"), True)], (512, 288), tmp_path / "o.mp4")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[0:v]trim" not in graph and "[1:v]trim=start_frame=1" in graph
    assert "[1:a]atrim=start=0.041667" in graph and "[0:a]atrim" not in graph
    assert "scale=512:288:force_original_aspect_ratio=decrease,pad=512:288" in graph
    assert "concat=n=2:v=1:a=1" in graph


def test_crossfade_skips_fade_next_to_a_short_segment(tmp_path):
    cmd = compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 2.0), (Path("c.wav"), 20.0)],
                                          tmp_path / "o.wav")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "acrossfade" not in graph and graph.count("concat=n=2:v=0:a=1") == 2
    cmd = compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 20.0)], tmp_path / "o.wav")
    assert "acrossfade=d=1.5:c1=tri:c2=tri" in cmd[cmd.index("-filter_complex") + 1]


def test_ffmpeg_path_honours_override_and_reports_absence(tmp_path, monkeypatch):
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(fake))
    assert compose.ffmpeg_path() == str(fake)
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(tmp_path / "nope"))
    assert compose.ffmpeg_path() is None
    monkeypatch.delenv("LOCALMODELDESK_FFMPEG")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert compose.ffmpeg_path() is None


def lavfi_video(path: Path, size="512x288", seconds=1):
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=24",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000", "-t", str(seconds),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


def lavfi_wav(path: Path, seconds):
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100",
                    "-t", str(seconds), "-ac", "2", str(path)], check=True)


def duration(path: Path) -> float:
    out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


@needs_ffmpeg
def test_real_concat_with_mixed_sizes_and_dropped_frame(tmp_path):
    lavfi_video(tmp_path / "a.mp4", "512x288")
    lavfi_video(tmp_path / "b.mp4", "768x448")
    out = tmp_path / "joined.mp4"
    subprocess.run(compose.concat_video_command(FF, [(tmp_path / "a.mp4", False), (tmp_path / "b.mp4", True)],
                                                compose.probe_size(FP, tmp_path / "a.mp4"), out), check=True)
    assert compose.probe_size(FP, out) == (512, 288)
    assert abs(duration(out) - (2 - 1 / 24)) < 0.1


@needs_ffmpeg
def test_real_crossfade_and_last_frame_and_replace_audio(tmp_path):
    lavfi_wav(tmp_path / "a.wav", 5); lavfi_wav(tmp_path / "b.wav", 5)
    song = tmp_path / "song.wav"
    subprocess.run(compose.crossfade_audio_command(FF, [(tmp_path / "a.wav", 5.0), (tmp_path / "b.wav", 5.0)], song), check=True)
    assert abs(duration(song) - 8.5) < 0.1
    lavfi_video(tmp_path / "v.mp4")
    png = tmp_path / "last.png"
    subprocess.run(compose.last_frame_command(FF, tmp_path / "v.mp4", png), check=True)
    assert png.stat().st_size > 0
    swapped = tmp_path / "swapped.mp4"
    subprocess.run(compose.replace_audio_command(FF, tmp_path / "v.mp4", song, swapped), check=True)
    assert abs(duration(swapped) - 1.0) < 0.1
```

- [ ] **Step 2: 确认失败**

Run: `python3 -m pytest tests/test_media_compose.py -q`
Expected: FAIL，`ImportError: cannot import name 'compose'`

- [ ] **Step 3: 实现 `desk/media/compose.py`**

```python
"""ffmpeg argv builders for joining, composing and frame extraction (design B-50/B-51/§6).

Pure functions: no session knowledge, no business rules. Every command puts `-y`
right after the executable and the output path last, so the job runner and the
test executors can find what a command writes without parsing ffmpeg syntax.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FPS = 24                 # H3 output frame rate
CROSSFADE_S = 1.5
SHORT_SEGMENT_S = 3.0    # a seam next to a shorter segment is a plain cut
FFMPEG_MISSING = "需要 ffmpeg 才能拼接成片"


def _find(name: str) -> str | None:
    override = os.environ.get("LOCALMODELDESK_" + name.upper())
    if override:
        return override if Path(override).is_file() else None
    return shutil.which(name)


def ffmpeg_path() -> str | None:
    return _find("ffmpeg")


def ffprobe_path() -> str | None:
    return _find("ffprobe")


def probe_size(ffprobe: str, video: Path) -> tuple[int, int]:
    result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
                            capture_output=True, text=True, timeout=30)
    try:
        width, height = (int(n) for n in result.stdout.strip().split("x"))
    except ValueError as exc:
        raise ValueError(f"cannot read video size of {video.name}") from exc
    return width, height


def last_frame_command(ffmpeg: str, video: Path, png: Path) -> list[str]:
    return [ffmpeg, "-y", "-v", "error", "-sseof", "-0.1", "-i", str(video),
            "-frames:v", "1", "-update", "1", str(png)]


def concat_video_command(ffmpeg: str, parts: list[tuple[Path, bool]], size: tuple[int, int],
                         output: Path) -> list[str]:
    width, height = size
    inputs, chains, labels = [], [], []
    for i, (path, drop_first) in enumerate(parts):
        inputs += ["-i", str(path)]
        v = f"[{i}:v]" + ("trim=start_frame=1,setpts=PTS-STARTPTS," if drop_first else "")
        v += (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}[v{i}]")
        a = f"[{i}:a]" + (f"atrim=start={1 / FPS:.6f},asetpts=PTS-STARTPTS," if drop_first else "")
        a += f"aresample=48000[a{i}]"
        chains += [v, a]
        labels.append(f"[v{i}][a{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    return [ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)]


def crossfade_audio_command(ffmpeg: str, parts: list[tuple[Path, float]], output: Path) -> list[str]:
    inputs, steps = [], []
    for path, _seconds in parts:
        inputs += ["-i", str(path)]
    current = "[0:a]"
    for i in range(1, len(parts)):
        short = min(parts[i - 1][1], parts[i][1]) < SHORT_SEGMENT_S
        seam = ("concat=n=2:v=0:a=1" if short else f"acrossfade=d={CROSSFADE_S}:c1=tri:c2=tri")
        label = f"[x{i}]"
        steps.append(f"{current}[{i}:a]{seam}{label}")
        current = label
    graph = ";".join(steps)
    return [ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", current,
            "-c:a", "pcm_s16le", str(output)]


def replace_audio_command(ffmpeg: str, video: Path, audio: Path, output: Path) -> list[str]:
    return [ffmpeg, "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)]
```

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest tests/test_media_compose.py -q`
Expected: PASS（本机有 ffmpeg，两个真跑测试也通过）

- [ ] **Step 5: Commit**

```bash
git add desk/media/compose.py tests/test_media_compose.py
git commit -m "feat(media-sessions): ffmpeg 原语——拼接、交叉淡化、截末帧、换音轨

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 视频、音乐记录并传递种子

**Files:**
- Modify: `desk/media/commands.py`、`desk/media/music3_cli.py`、`desk/media/service.py:86-120`、`desk/media/routes.py:34-48`
- Test: `tests/test_media_commands.py`、`tests/test_media_music3_cli.py`、`tests/test_media_service.py:12-14,68-100,150-170`、`tests/test_media_routes.py`

**Interfaces:**
- Produces: `build_h3_command(..., seed: int | None = None)`（非 None 时在 `--budget` 之后追加 `--seed <n>`）；`build_music_command(..., seed: int | None = None)`（追加 `--seed <n>`）；`start_video_job(..., seed=None)`、`start_music_job(..., seed=None)`：省略则 `secrets.randbelow(2**32)`，`params["seed"]` 记实际值；非法 → 400 `invalid_params`「种子须为 0–4294967295 的整数」
- 共享校验：`service._check_seed(seed)`，`start_image_job` 里的内联校验改为调用它

- [ ] **Step 1: 写失败测试**

`tests/test_media_commands.py` 追加：

```python
def test_seed_flags_are_appended_only_when_given(tmp_path):
    base = dict(prompt="p", width=512, height=288, frames=49, steps=12, output=tmp_path / "o.mp4")
    without = build_h3_command(("mlx-h3",), tmp_path, **base)
    with_seed = build_h3_command(("mlx-h3",), tmp_path, **base, seed=7)
    assert "--seed" not in without
    assert with_seed[with_seed.index("--seed") + 1] == "7"
    music = build_music_command(Path("py"), Path("cli.py"), tmp_path, caption="c", lyrics="l", duration=20.0,
                                output=tmp_path / "o.wav", seed=9)
    assert music[music.index("--seed") + 1] == "9"
```

`tests/test_media_music3_cli.py`：第一个测试的 flag 元组加 `"--seed"`。

`tests/test_media_service.py` 追加：

```python
def test_video_seed_is_recorded_and_passed(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: service.start_video_job(
        prompt="p", width=512, height=288, frames=49, steps=12, seed=123))
    assert snap["params"]["seed"] == 123
    cmd = deps.executor.spawned[0]["cmd"]
    assert cmd[cmd.index("--seed") + 1] == "123"


def test_video_omitted_seed_is_random_and_recorded(tmp_path, monkeypatch):
    from desk.media import service as service_mod
    monkeypatch.setattr(service_mod.secrets, "randbelow", lambda n: 424242)
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: service.start_video_job(prompt="p", width=512, height=288, frames=49, steps=12))
    assert snap["params"]["seed"] == 424242


@pytest.mark.parametrize("bad", [-1, 2**32, 1.5, True, "7"])
def test_bad_video_or_music_seed_is_400(tmp_path, bad):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        service.start_video_job(prompt="p", width=512, height=288, frames=49, steps=12, seed=bad)
    assert (exc.value.code, exc.value.message) == ("invalid_params", "种子须为 0–4294967295 的整数")
    with pytest.raises(MediaError):
        service.start_music_job(caption="c", lyrics="l", duration=10, seed=bad)
    assert deps.executor.spawned == []
```

- [ ] **Step 2: 确认失败**

Run: `python3 -m pytest tests/test_media_commands.py tests/test_media_music3_cli.py tests/test_media_service.py -q -k "seed or help_runs"`
Expected: FAIL（`unexpected keyword argument 'seed'`、`--seed` 不在 help 里）

- [ ] **Step 3: 实现**

`desk/media/commands.py`：`build_h3_command` 签名加 `seed: int | None = None,`（放在 `use_audio` 之后），在 `"--output", str(output),` 那一行之后、`for flag, path` 之前加：

```python
    if seed is not None:
        command.extend(("--seed", str(seed)))
```

`build_music_command` 签名加 `seed: int | None = None`，返回前：

```python
    command = [str(music_python), str(music3_cli), "--root", str(music3_root), "--caption", caption,
               "--lyrics", lyrics, "--duration", str(duration), "--output", str(output)]
    if seed is not None:
        command += ["--seed", str(seed)]
    return command
```

（`--output` 仍在 `--seed` 之前，但假执行器用 `index("--output")` 取值，不依赖它是最后一个。）

`desk/media/music3_cli.py`：`build_parser` 加 `parser.add_argument("--seed", type=int, default=0, help="random seed")`；`GenerationRequest(... seed=args.seed)`。

`desk/media/service.py`：

```python
SEED_MESSAGE = "种子须为 0–4294967295 的整数"

def _check_seed(seed) -> int:
    """The seed to use: a given one validated, or a fresh random one (IS D-19, B §3.2)."""
    if seed is None:
        return secrets.randbelow(2**32)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise MediaError("invalid_params", SEED_MESSAGE, 400)
    return seed
```

（模块级函数，放在 `_positive_int` 之后。）`start_image_job` 里的内联种子校验与 `if seed is None: seed = secrets.randbelow(2**32)` 两段删掉，改成在参数校验处写 `seed = _check_seed(seed)`（保持原来的校验顺序：宽高、步数之后，force 之前）。

`start_video_job` 签名加 `seed=None`，在 `_positive_int` 循环之后 `seed = _check_seed(seed)`，`params` 构造改为 `{"prompt": ..., "steps": steps, "seed": seed}`。`start_music_job` 签名加 `seed=None`，在 lyrics 检查之后 `seed = _check_seed(seed)`，params 加 `"seed": seed`。`_start` 里视频 `command_params = dict(params)` 已包含 seed，直接进 `build_h3_command`；音乐 `build_music_command(..., **params)` 同理。

`desk/media/routes.py`：`start_video` 与 `start_music` 的调用都加 `seed=payload.get("seed"),`。

`tests/test_media_service.py` 里已有断言随之更新：`start_video` 辅助函数加 `seed=7`；第 74 行期望 params 加 `"seed": 7`；第 92 行 `build_h3_command(...)` 期望加 `seed=7`；音乐成功测试调用加 `seed=7`，第 164 行期望加 `seed=7`；`TestStartDiscipline.VALID` 加 `seed=7`。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest tests/test_media_commands.py tests/test_media_music3_cli.py tests/test_media_service.py tests/test_media_routes.py tests/test_media_image_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A desk tests
git commit -m "feat(media-sessions): 视频与音乐生成记录并传递实际种子

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 所有 kind 挂会话、refs 机制、history 带会话字段

**Files:**
- Modify: `desk/media/service.py`（`start_video_job`、`start_music_job`、`_start`、`_begin_attempt`、`_settle_attempt`、`_history_entry`、构造参数）、`desk/media/routes.py`
- Test: `tests/test_media_sessions_service.py`（新建）

**Interfaces:**
- Consumes: `MediaSessionStore.exists / begin_attempt / settle_attempt / find_done`、`SegmentMissing`（Task 1）
- Produces:
  - `MediaService(..., ref_slots: dict[str, dict[str, str]] | None = None)`：`{kind: {ref_name: target_kind}}`，默认 `{}`（B-58）
  - `start_video_job(..., session_id=None, refs=None)`、`start_music_job(..., session_id=None, refs=None)`
  - `service._check_session(kind, session_id, *, required: bool) -> str | None`
  - `service._resolve_refs(kind, refs) -> tuple[dict, dict[str, Path]]`（存储用三元组、解析出的路径）
  - `_start(kind, params, *, force=False, session_id=None, attempt_extra=None)`；`attempt_extra` 键 `continues`、`refs`、`base`、`op`
  - `_begin_attempt(kind, session_id, job_id, params, attempt_extra)`
  - history 条目对所有 kind 带 `session_id`、`attempt_id`

- [ ] **Step 1: 写失败测试 `tests/test_media_sessions_service.py`**

```python
"""MediaService × media sessions for video and music (design B §3.2, §5)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service


def music_ready(service, tmp_path):
    roots = SimpleNamespace(outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
                            music_python=Path("/fake/py"), media_cli_dir=Path("/fake/media"), music_env={},
                            mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={})
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {"music_runtime": SimpleNamespace(present=True, detail=""),
                                           "mlx_h3": SimpleNamespace(present=True, detail="")}
    service._list_catalog = lambda: [SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0),
                                     SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)]


def video(service, **kw):
    return service.start_video_job(**{"prompt": "雨夜", "width": 512, "height": 288, "frames": 49, "steps": 12, **kw})


def music(service, **kw):
    return service.start_music_job(**{"caption": "独立流行", "lyrics": "[verse]\n早晨", "duration": 20.0, **kw})


def test_video_in_a_session_appends_and_settles_an_attempt(tmp_path):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, seed=7))
    attempt = deps.media_sessions["video"].get(sid)["attempts"][0]
    assert attempt["status"] == "done" and attempt["output"] == snap["output"]
    assert attempt["params"]["seed"] == 7 and attempt["op"] == "generate"
    assert snap["session_id"] == sid and snap["attempt_id"] == attempt["id"]
    assert deps.history.entries[-1]["session_id"] == sid and deps.history.entries[-1]["attempt_id"] == attempt["id"]


def test_music_in_a_session_takes_its_title_from_the_caption(tmp_path):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    sid = deps.media_sessions["music"].create()["id"]
    finished_snapshot(service, lambda: music(service, session_id=sid))
    assert deps.media_sessions["music"].get(sid)["title"] == "独立流行"


def test_video_and_music_without_session_still_run_unattached(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: video(service))
    assert snap["status"] == "done" and snap["session_id"] is None and snap["attempt_id"] is None
    assert deps.history.entries[-1]["session_id"] is None


@pytest.mark.parametrize("session_id, code, status", [(123, "session_required", 400), ("f" * 32, "session_not_found", 404)])
def test_bad_session_is_refused_before_anything_starts(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == [] and deps.arbiter.acquired == []


def test_refs_without_a_session_is_session_required(tmp_path):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, refs={"x": {}})
    assert exc.value.code == "session_required"


def test_unregistered_ref_name_is_400(tmp_path):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, refs={"soundtrack": {"kind": "music", "session_id": "a" * 32, "attempt_id": "b" * 32}})
    assert exc.value.code == "invalid_params"
    assert deps.media_sessions["video"].get(sid)["attempts"] == []


def done_image(deps, tmp_path):
    images = deps.media_sessions["image"]
    sid = images.create()["id"]
    images.begin_attempt(sid, {"id": "a" * 32, "job_id": 1, "params": {"prompt": "猫", "width": 1024, "height": 1024, "steps": 40, "seed": 1}})
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / "cat.png").write_bytes(b"png")
    images.settle_attempt(sid, "a" * 32, "done", "cat.png")
    return sid


def test_registered_ref_resolves_to_a_file_and_is_stored_as_a_pointer(tmp_path):
    service, deps = make_service(tmp_path)
    service._ref_slots = {"video": {"probe": "image"}}
    image_sid = done_image(deps, tmp_path)
    ref = {"kind": "image", "session_id": image_sid, "attempt_id": "a" * 32}
    stored, paths = service._resolve_refs("video", {"probe": ref})
    assert stored == {"probe": ref} and paths == {"probe": tmp_path / "outputs" / "cat.png"}
    sid = deps.media_sessions["video"].create()["id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, refs={"probe": ref}))
    assert deps.media_sessions["video"].get(sid)["attempts"][0]["refs"] == {"probe": ref}


@pytest.mark.parametrize("mutate", ["wrong_kind", "gone_session", "gone_file"])
def test_broken_ref_is_404_ref_missing(tmp_path, mutate):
    service, deps = make_service(tmp_path)
    service._ref_slots = {"video": {"probe": "image"}}
    image_sid = done_image(deps, tmp_path)
    ref = {"kind": "image", "session_id": image_sid, "attempt_id": "a" * 32}
    if mutate == "wrong_kind":
        ref = {**ref, "kind": "music"}
    elif mutate == "gone_session":
        deps.media_sessions["image"].delete(image_sid)
    else:
        (tmp_path / "outputs" / "cat.png").unlink()
    code = "invalid_params" if mutate == "wrong_kind" else "ref_missing"
    with pytest.raises(MediaError) as exc:
        service._resolve_refs("video", {"probe": ref})
    assert exc.value.code == code
    if code == "ref_missing":
        assert exc.value.http_status == 404 and exc.value.message == "引用的图片已不在"


@pytest.mark.parametrize("extra", [{"continues": "a" * 32}, {"refs": {}}])
def test_image_refuses_continues_and_refs(tmp_path, extra):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["image"].create()["id"]
    with pytest.raises(MediaError) as exc:
        service.start_image_job(session_id=sid, prompt="猫", **extra)
    assert exc.value.code == "invalid_params"                       # B-00b
    assert deps.media_sessions["image"].get(sid)["attempts"] == []


def test_routes_pass_session_and_refs_through(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    seen = {}
    monkeypatch.setattr(service, "start_video_job", lambda **kw: seen.update(kw) or {"ok": True})
    handler = next(h for m, p, h in build_routes(service) if p == "/api/media/video")
    handler({"prompt": "p", "width": 512, "height": 288, "frames": 49, "steps": 12,
             "session_id": "s", "refs": {"a": 1}, "continues": "c", "seed": 3}, {})
    assert (seen["session_id"], seen["refs"], seen["continues"], seen["seed"]) == ("s", {"a": 1}, "c", 3)
```

（最后一个测试同时覆盖 Task 6 的 `continues` 透传；Task 5 实现时 `start_video_job` 已接受 `continues=None` 参数，但在 Task 6 之前遇到非 None 的 `continues` 抛 400 `invalid_params`「暂不支持续写」——Task 6 会删掉这句。）

- [ ] **Step 2: 确认失败**

Run: `python3 -m pytest tests/test_media_sessions_service.py -q`
Expected: FAIL（`unexpected keyword argument 'session_id'` 等）

- [ ] **Step 3: 实现**

`desk/media/service.py`：

```python
KIND_NAMES = {"image": "图片", "video": "视频", "music": "音乐"}
```

构造函数加 `ref_slots: dict | None = None`，`self._ref_slots = ref_slots or {}`。

新增：

```python
    def _check_session(self, kind: str, session_id, *, required: bool) -> str | None:
        if session_id is None and not required:
            return None
        if not isinstance(session_id, str):
            raise MediaError("session_required", SESSION_REQUIRED_MESSAGE, 400)
        if not self._sessions[kind].exists(session_id):
            raise MediaError("session_not_found", SESSION_NOT_FOUND_MESSAGE, 404)
        return session_id

    def _resolve_refs(self, kind: str, refs) -> tuple[dict, dict]:
        """Validate cross-session references (B-55): pointers to store, files to use."""
        if refs is None:
            return {}, {}
        if not isinstance(refs, dict):
            raise MediaError("invalid_params", "引用参数有误", 400)
        slots = self._ref_slots.get(kind, {})
        stored, paths = {}, {}
        for name, ref in refs.items():
            target = slots.get(name)
            if target is None or not isinstance(ref, dict) or ref.get("kind") != target \
                    or not isinstance(ref.get("session_id"), str) or not isinstance(ref.get("attempt_id"), str):
                raise MediaError("invalid_params", f"引用参数有误：{name}", 400)
            try:
                attempt = self._sessions[target].find_done(ref["session_id"], ref["attempt_id"])
            except (NotFoundError, SegmentMissing):
                raise MediaError("ref_missing", f"引用的{KIND_NAMES[target]}已不在", 404) from None
            stored[name] = {"kind": target, "session_id": ref["session_id"], "attempt_id": ref["attempt_id"]}
            paths[name] = Path(self._resolve_paths().outputs_root) / attempt["output"]
        return stored, paths
```

导入：`from desk.library.errors import NotFoundError` 与 `from desk.library.media_sessions import SegmentMissing`。

`start_video_job` 签名改为 `(self, *, prompt, width, height, frames, steps, mode="text", first_frame=None, last_frame=None, ref_video=None, use_audio=True, seed=None, session_id=None, continues=None, refs=None, force=False)`；在现有参数校验（含 seed）之后、素材解析之前：

```python
        if continues is not None:
            raise MediaError("invalid_params", "暂不支持续写", 400)   # Task 6 replaces this
        session_id = self._check_session("video", session_id, required=refs is not None)
        stored_refs, _ref_paths = self._resolve_refs("video", refs)
```

结尾改为 `return self._start("video", params, force=force, session_id=session_id, attempt_extra={"refs": stored_refs})`。

`start_music_job` 签名 `(self, *, caption, lyrics, duration, seed=None, session_id=None, continues=None, refs=None, force=False)`，同样的三句（kind 换成 `"music"`），结尾 `self._start("music", {...}, force=force, session_id=session_id, attempt_extra={"refs": stored_refs})`。

`start_image_job` 签名加 `continues=None, refs=None`，参数校验最前面加：

```python
        if continues is not None or refs is not None:
            raise MediaError("invalid_params", "图片不支持续写或引用", 400)   # B-00b
```

`desk/media/routes.py` 的 `start_image` 也透传 `continues=payload.get("continues"), refs=payload.get("refs"),`。

`start_image_job`：把 `if not isinstance(session_id, str) ... session_not_found` 两段替换为 `session_id = self._check_session("image", session_id, required=True)`；结尾传 `attempt_extra={"base": ...}` —— 把原来 `_begin_attempt` 里从 `params["base"]` 取 `{"attempt_id", "strength"}` 的逻辑移到这里：

```python
        extra = {"base": {"attempt_id": params["base"]["attempt_id"], "strength": params["base"]["strength"]}} \
            if params.get("base") else {}
        return self._start("image", params, force=force, session_id=session_id, attempt_extra=extra)
```

`_start` 签名加 `attempt_extra: dict | None = None`；把 `if kind == "image": self._begin_attempt(session_id, job_id, params)` 改为

```python
            if session_id is not None:
                self._begin_attempt(kind, session_id, job_id, params, attempt_extra or {})
```

`_begin_attempt` 改为：

```python
    def _begin_attempt(self, kind: str, session_id: str, job_id: int, params: dict, extra: dict) -> None:
        """Attach the now-running job to its session (IS D-20 step 5, B-32).

        A session deleted since the check, or a store failure, leaves the job
        running unattached (IS D-23): the output still reaches outputs and history."""
        attempt_id = uuid.uuid4().hex
        try:
            attached = self._sessions[kind].begin_attempt(session_id, {
                "id": attempt_id, "job_id": job_id, "params": dict(params),
                "op": extra.get("op", "generate"), "continues": extra.get("continues"),
                "refs": extra.get("refs") or {}, "base": extra.get("base")})
        except Exception:
            log.exception("begin_attempt failed; %s job runs without a session", kind)
            attached = False
        if attached:
            self._state.update(session_id=session_id, attempt_id=attempt_id)
```

`_settle_attempt`：`self._sessions["image"].settle_attempt(` 改为 `self._sessions[snap["kind"]].settle_attempt(`，日志文案 `"image attempt %s"` 改为 `"%s attempt %s", snap["kind"],`。

`_history_entry`：删掉 `if snap["kind"] == "image":` 条件，所有 kind 都 `entry.update(session_id=snap.get("session_id"), attempt_id=snap.get("attempt_id"))`。

`desk/media/routes.py`：`start_video` 调用加 `session_id=payload.get("session_id"), continues=payload.get("continues"), refs=payload.get("refs"),`；`start_music` 同样三项。

更新受影响的旧断言：`tests/test_media_service.py:80` 的 history 期望加 `"session_id": None, "attempt_id": None`；`tests/test_media_image_service.py:394` 的 `assert "session_id" not in deps.history.entries[-1]` 改为 `assert deps.history.entries[-1]["session_id"] is None and deps.history.entries[-1]["attempt_id"] is None`。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest tests/test_media_sessions_service.py tests/test_media_service.py tests/test_media_image_service.py tests/test_media_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A desk tests
git commit -m "feat(media-sessions): 视频与音乐作业可挂会话，跨会话引用机制，history 统一带会话字段

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 续写与作业内自动拼接

**Files:**
- Modify: `desk/media/service.py`（`start_video_job`、`start_music_job`、`_start`、`_worker`、`_finalize`、`_settle_attempt`、`_history_entry`、新增 `_join_plan`、`_run_join`、`_extract_last_frame`）、`tests/media_fakes.py`（`FakeExecutor.spawn`）、`desk/testing/fakes.py`（`FakeMediaExecutor.spawn`）
- Test: `tests/test_media_continue.py`（新建）

**Interfaces:**
- Consumes: `compose.*`（Task 3）、`store.chain / find_done / record_output / settle_attempt(joined_…)`（Task 1）、`_check_session / _begin_attempt`（Task 5）
- Produces:
  - `start_video_job(..., continues=<attempt_id>)`：截末帧为 `first_frame`、`mode="image"`；`start_music_job(..., continues=…)`
  - 错误：`segment_not_found` 404「找不到要接着的那一段」、`segment_missing` 404「那一段的文件已不在，无法接着生成」、`frame_extract_failed` 500「没能从上一段截出最后一帧」、`capability_missing` 503 `compose.FFMPEG_MISSING`、`invalid_params` 400「续写会用上一段的最后一帧作首帧，不能另选首帧或参考视频」
  - 尝试落定时 `joined_output` / `joined_error`（`segment_missing` | `join_failed` | `join_cancelled`）；history 条目在拼接成功时带 `joined_output`
  - `service._segment(kind, session_id, attempt_id) -> dict`（把存储异常映射成上面两个 404）

- [ ] **Step 1: 假执行器识别 ffmpeg 命令**

`tests/media_fakes.py` 的 `FakeExecutor.spawn`：

```python
    def spawn(self, cmd, *, extra_env=None):
        self.spawned.append({"cmd": list(cmd), "extra_env": dict(extra_env or {})})
        output = Path(cmd[cmd.index("--output") + 1]) if "--output" in cmd else Path(cmd[-1])
        script = self.join_script if "--output" not in cmd else self.script
        return FakeHandle(script, output, self.lines, ignore_term=self.ignore_term)
```

构造函数加 `join_script="success"` 参数存为 `self.join_script`（让测试单独控制拼接那一步成功 / 失败 / 阻塞）。`desk/testing/fakes.py:232` 同理：`output_path = Path(argv[argv.index("--output") + 1]) if "--output" in argv else Path(argv[-1])`。

- [ ] **Step 2: 写失败测试 `tests/test_media_continue.py`**

```python
"""Continuation: frame hand-off, chain joining, and every way a join can end (B §3.3–3.4)."""
import threading
from pathlib import Path

import pytest

from desk.media import compose
from desk.media import service as service_mod
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_sessions_service import music, music_ready, video


@pytest.fixture(autouse=True)
def fake_ffmpeg(monkeypatch, tmp_path):
    """Frame extraction and size probing run synchronously; fake both, keep argv builders real."""
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(compose, "ffprobe_path", lambda: "/fake/ffprobe")
    monkeypatch.setattr(compose, "probe_size", lambda _probe, _video: (512, 288))
    def fake_run(cmd, **_kw):
        Path(cmd[-1]).write_bytes(b"png")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(service_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(service_mod, "wav_seconds", lambda _p: 20.0)


def first_segment(service, deps, kind="video"):
    sid = deps.media_sessions[kind].create()["id"]
    run = video if kind == "video" else music
    snap = finished_snapshot(service, lambda: run(service, session_id=sid))
    return sid, snap["attempt_id"]


def attempts(deps, kind, sid):
    return deps.media_sessions[kind].get(sid)["attempts"]


def test_video_continuation_uses_last_frame_and_joins_the_chain(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    assert second["continues"] == first and second["params"]["mode"] == "image"
    assert (tmp_path / "outputs" / ".inputs" / second["params"]["first_frame"]).is_file()
    assert second["status"] == "done" and second["output"] == snap["output"]
    assert second["joined_output"].startswith("h3-joined-") and second["joined_error"] is None
    join_cmd = deps.executor.spawned[-1]["cmd"]
    graph = join_cmd[join_cmd.index("-filter_complex") + 1]
    assert "[0:v]trim" not in graph and "[1:v]trim=start_frame=1" in graph
    assert deps.history.entries[-1]["joined_output"] == second["joined_output"]


def test_permit_is_released_when_the_model_exits_and_only_once(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="block"))
    sid, first = first_segment(service, deps)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    video(service, session_id=sid, continues=first)
    deadline = __import__("time").time() + 5
    while deps.arbiter.released.count("permit-2") == 0 and __import__("time").time() < deadline:
        __import__("time").sleep(0.01)
    assert service.job_status()["status"] == "running"          # 还在拼接
    assert deps.arbiter.released.count("permit-2") == 1           # 许可已释放
    service.cancel_job()
    assert finished.wait(5)
    assert deps.arbiter.released.count("permit-2") == 1


def test_cancel_during_join_keeps_the_segment_as_done(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="block"))
    sid, first = first_segment(service, deps)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    video(service, session_id=sid, continues=first)
    import time
    deadline = time.time() + 5
    while attempts(deps, "video", sid)[1]["output"] is None and time.time() < deadline:
        time.sleep(0.01)
    service.cancel_job()
    assert finished.wait(5)
    second = attempts(deps, "video", sid)[1]
    assert second["status"] == "done" and second["output"]
    assert second["joined_output"] is None and second["joined_error"]["code"] == "join_cancelled"


def test_join_failure_keeps_the_segment_as_done(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="fail"))
    sid, first = first_segment(service, deps)
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    assert second["status"] == "done" and second["joined_error"]["code"] == "join_failed"


def test_broken_chain_still_generates_and_names_the_missing_segment(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    (tmp_path / "outputs" / attempts(deps, "video", sid)[0]["output"]).unlink()   # 删掉第 1 段
    spawned_before = len(deps.executor.spawned)
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=second["id"]))
    third = attempts(deps, "video", sid)[2]
    assert third["status"] == "done"
    assert third["joined_error"] == {"code": "segment_missing", "message": "第 1 段的文件已不在，无法拼成成片"}
    assert len(deps.executor.spawned) == spawned_before + 1       # 只跑了模型，没跑拼接


def test_music_continuation_crossfades_without_touching_model_inputs(tmp_path):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    sid, first = first_segment(service, deps, "music")
    finished_snapshot(service, lambda: music(service, session_id=sid, continues=first, lyrics="[verse]\n晚上"))
    second = attempts(deps, "music", sid)[1]
    assert second["params"]["lyrics"] == "[verse]\n晚上" and second["joined_output"].startswith("music3-joined-")
    join_cmd = deps.executor.spawned[-1]["cmd"]
    assert "acrossfade=d=1.5:c1=tri:c2=tri" in join_cmd[join_cmd.index("-filter_complex") + 1]


@pytest.mark.parametrize("arrange, code, status", [
    (lambda deps, sid, first: "9" * 32, "segment_not_found", 404),
    (lambda deps, sid, first: (Path(deps.outputs) / deps.first_output).unlink() or first, "segment_missing", 404),
])
def test_bad_continues_is_refused_and_writes_nothing(tmp_path, arrange, code, status):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    deps.outputs = tmp_path / "outputs"
    deps.first_output = attempts(deps, "video", sid)[0]["output"]
    target = arrange(deps, sid, first)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=target)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert len(attempts(deps, "video", sid)) == 1


def test_continues_conflicts_with_an_explicit_first_frame(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first, mode="image", first_frame="a" * 32 + ".png")
    assert exc.value.code == "invalid_params"


def test_continues_without_session_is_session_required(tmp_path):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, continues="a" * 32)
    assert exc.value.code == "session_required"


def test_refused_continuation_cleans_its_extracted_frame(tmp_path):
    service, deps = make_service(tmp_path, memory_warning={"code": "insufficient_memory",
                                                            "required_bytes": 10, "available_bytes": 1})
    sid = deps.media_sessions["video"].create()["id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, force=True))
    first = attempts(deps, "video", sid)[0]["id"]
    inputs = tmp_path / "outputs" / ".inputs"
    before = set(inputs.iterdir()) if inputs.is_dir() else set()
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert exc.value.code == "insufficient_memory"
    assert (set(inputs.iterdir()) if inputs.is_dir() else set()) == before
    assert len(attempts(deps, "video", sid)) == 1


def test_missing_ffmpeg_refuses_continuation_but_not_plain_generation(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: None)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert (exc.value.code, exc.value.http_status, exc.value.message) == ("capability_missing", 503, compose.FFMPEG_MISSING)
    assert finished_snapshot(service, lambda: video(service, session_id=sid))["status"] == "done"


def test_frame_extraction_failure_is_500_and_writes_nothing(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    monkeypatch.setattr(service_mod.subprocess, "run",
                        lambda cmd, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})())
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert (exc.value.code, exc.value.http_status) == ("frame_extract_failed", 500)
    assert len(attempts(deps, "video", sid)) == 1
```

- [ ] **Step 3: 确认失败**

Run: `python3 -m pytest tests/test_media_continue.py -q`
Expected: FAIL（「暂不支持续写」400 等）

- [ ] **Step 4: 实现续写入口**

`desk/media/service.py` 顶部导入 `import subprocess` 与 `from . import compose`。新增常量与辅助：

```python
SEGMENT_NOT_FOUND = "找不到要接着的那一段"
SEGMENT_MISSING = "那一段的文件已不在，无法接着生成"
CONTINUE_CONFLICT = "续写会用上一段的最后一帧作首帧，不能另选首帧或参考视频"

    def _segment(self, kind: str, session_id: str, attempt_id) -> dict:
        if not isinstance(attempt_id, str):
            raise MediaError("invalid_params", SEGMENT_NOT_FOUND, 400)
        try:
            return self._sessions[kind].find_done(session_id, attempt_id)
        except NotFoundError:
            raise MediaError("segment_not_found", SEGMENT_NOT_FOUND, 404) from None
        except SegmentMissing:
            raise MediaError("segment_missing", SEGMENT_MISSING, 404) from None

    def _join_plan(self, kind: str, session_id: str, continues: str) -> dict:
        """What to join once the new segment exists (B-39/B-40); an 'error' plan skips the join."""
        items, broken = self._sessions[kind].chain(session_id, continues)
        for number, item in enumerate(items, 1):
            if broken or item.get("status") != "done" or item.get("output_missing") or not item.get("output"):
                return {"error": {"code": "segment_missing",
                                  "message": f"第 {1 if broken else number} 段的文件已不在，无法拼成成片"}}
        root = Path(self._resolve_paths().outputs_root)
        paths = [root / item["output"] for item in items]
        drops = [False] + [items[i].get("continues") == items[i - 1]["id"] for i in range(1, len(items))]
        return {"parts": list(zip(paths, drops))}

    def _extract_last_frame(self, video: Path) -> str:
        """Save the continued video's last frame as an input asset; returns its asset id (B-36/B-37)."""
        ffmpeg = compose.ffmpeg_path()
        if ffmpeg is None:
            raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
        directory = Path(self._resolve_paths().outputs_root) / ".inputs"
        directory.mkdir(parents=True, exist_ok=True)
        png = directory / f"{uuid.uuid4().hex}.png"
        result = subprocess.run(compose.last_frame_command(ffmpeg, video, png), capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not png.is_file():
            png.unlink(missing_ok=True)
            raise MediaError("frame_extract_failed", "没能从上一段截出最后一帧", 500)
        return png.name
```

`start_video_job`：删掉 Task 5 的「暂不支持续写」那句。在 seed 校验之后、`mode` 校验之前插入：

```python
        if continues is not None and (mode not in ("text", "image") or first_frame or last_frame or ref_video):
            raise MediaError("invalid_params", CONTINUE_CONFLICT, 400)
```

`session_id = self._check_session("video", session_id, required=refs is not None or continues is not None)` 之后：

```python
        join, frame = None, None
        if continues is not None:
            source = self._segment("video", session_id, continues)
            join = self._join_plan("video", session_id, continues)
            root = Path(self._resolve_paths().outputs_root)
            frame = self._extract_last_frame(root / (source.get("joined_output")
                                                     if source.get("joined_output") and not source.get("joined_missing")
                                                     else source["output"]))
            mode, first_frame = "image", frame
```

（放在素材解析 `assets = {}` 之前，这样截出的帧走现有 `resolve_input` 校验。）结尾：

```python
        try:
            return self._start("video", params, force=force, session_id=session_id,
                               attempt_extra={"refs": stored_refs, "continues": continues}, join=join)
        except MediaError:
            if frame:
                (Path(self._resolve_paths().outputs_root) / ".inputs" / frame).unlink(missing_ok=True)
            raise
```

同样把素材解析 `resolve_input` 抛 `invalid_input` 的那段也放进 try 覆盖范围——最简单的做法：从 `if continues is not None:` 截帧之后到 `return self._start(...)` 整段都包在这个 `try/except MediaError` 里。

`start_music_job`：`session_id = self._check_session("music", session_id, required=refs is not None or continues is not None)` 之后：

```python
        join = None
        if continues is not None:
            self._segment("music", session_id, continues)
            join = self._join_plan("music", session_id, continues)
```

结尾 `self._start("music", params, force=force, session_id=session_id, attempt_extra={"refs": stored_refs, "continues": continues}, join=join)`。

- [ ] **Step 5: 实现拼接阶段**

`_start` 签名加 `join: dict | None = None`。在内存提醒检查之后、`job_id = ...` 之前：

```python
            if join and "parts" in join and compose.ffmpeg_path() is None:
                raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
```

spawn 成功后设置 `self._join = join; self._permit_released = False; self._joined = {"joined_output": None, "joined_error": None}; self._phase = "model"`（与 `self._reset_log()` 同一行附近）。构造函数里把这四个字段初始化为 `None / False / {...} / "model"`。

`_worker` 改为：

```python
    def _worker(self, handle, permit: str | None, output: Path, kind: str) -> None:
        try:
            try:
                for line in handle.iter_output(): self._append_log(line)
                code, failure = handle.wait(), None
            except Exception as exc:
                code, failure = None, str(exc)
            with self._lock:
                if self._cancel_requested: status, error = "cancelled", None
                elif failure is not None: status, error = "error", {"code": "worker_failed", "message": failure}
                elif code == 0 and output.is_file(): status, error = "done", None
                elif code == 0: status, error = "error", {"code": "no_output", "message": "exit 0 but output file missing"}
                else: status, error = "error", {"code": "exit_nonzero", "message": f"exit {code}", "log_tail": self._log_tail(5)}
                join = self._join if status == "done" else None
                session_id, attempt_id = self._state["session_id"], self._state["attempt_id"]
                if join is None:
                    self._state.update(status=status, output=output.name if status == "done" else None,
                                       error=error, finished_at=self._clock())
                    self._handle = None
            if join is not None:
                self._release_permit(permit)          # 模型已退出：拼接只用 ffmpeg（B-38b）
                if session_id:
                    try:
                        self._sessions[kind].record_output(session_id, attempt_id, output.name)   # B-38a
                    except Exception:
                        log.exception("record_output failed")
                self._joined = self._run_join(kind, join, output)
                with self._lock:
                    self._state.update(status="done", output=output.name, error=None, finished_at=self._clock())
                    self._handle = None
        finally:
            self._finalize(permit)

    def _release_permit(self, permit: str | None) -> None:
        with self._lock:
            if permit is None or self._permit_released:
                return
            self._permit_released = True
        try: self._arbiter.release_heavy(permit)
        except Exception: log.exception("release_heavy failed")

    def _run_join(self, kind: str, join: dict, segment: Path) -> dict:
        """Join the chain plus the new segment (B-38–B-42); never raises, never fails the segment."""
        if "error" in join:
            return {"joined_output": None, "joined_error": dict(join["error"])}
        ffmpeg = compose.ffmpeg_path()
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self._clock()))
        suffix, prefix = (".mp4", "h3") if kind == "video" else (".wav", "music3")
        target = segment.parent / f"{prefix}-joined-{stamp}-{uuid.uuid4().hex[:8]}{suffix}"
        try:
            if kind == "video":
                parts = [*join["parts"], (segment, True)]
                size = compose.probe_size(compose.ffprobe_path() or "ffprobe", parts[0][0])
                command = compose.concat_video_command(ffmpeg, parts, size, target)
            else:
                parts = [(path, wav_seconds(path) or 0.0) for path, _drop in join["parts"]] + [(segment, wav_seconds(segment) or 0.0)]
                command = compose.crossfade_audio_command(ffmpeg, parts, target)
            with self._lock:
                if self._cancel_requested:
                    return {"joined_output": None, "joined_error": dict(JOIN_CANCELLED)}
                self._phase = "join"
                handle = self._executor.spawn(command)
                self._handle = handle
            self._append_log("[join] 正在拼接成片…")
            for line in handle.iter_output(): self._append_log(line)
            code = handle.wait()
        except Exception as exc:
            target.unlink(missing_ok=True)
            return {"joined_output": None, "joined_error": {"code": "join_failed", "message": "拼接成片失败", "log_tail": str(exc)}}
        with self._lock:
            cancelled = self._cancel_requested
        if cancelled:
            target.unlink(missing_ok=True)
            return {"joined_output": None, "joined_error": dict(JOIN_CANCELLED)}
        if code != 0 or not target.is_file():
            target.unlink(missing_ok=True)
            return {"joined_output": None, "joined_error": {"code": "join_failed", "message": "拼接成片失败",
                                                            "log_tail": self._log_tail(5)}}
        return {"joined_output": target.name, "joined_error": None}
```

常量：`JOIN_CANCELLED = {"code": "join_cancelled", "message": "成片拼接被中止"}`。

`_finalize(permit)`：把 `self._arbiter.release_heavy(permit)` 那两行换成 `self._release_permit(permit)`；在 lock 内同时取出 `joined = dict(self._joined)`，传给 `_history_entry(snap, joined)` 与 `_settle_attempt(snap, origin, joined)`。

`_settle_attempt(snap, cancel_origin, joined)`：`settle_attempt(...)` 调用加 `joined_output=joined["joined_output"], joined_error=joined["joined_error"]`。

`_history_entry(snap, joined)`：`if joined.get("joined_output"): entry["joined_output"] = joined["joined_output"]`。

`_start` 的 spawn 失败分支 `self._finalize(permit)` 之前先确保 `self._joined = {"joined_output": None, "joined_error": None}`、`self._permit_released = False`。

- [ ] **Step 6: 跑测试**

Run: `python3 -m pytest tests/test_media_continue.py tests/test_media_sessions_service.py tests/test_media_service.py tests/test_media_image_service.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add -A desk tests
git commit -m "feat(media-sessions): 续写——视频尾帧接首帧、音乐接下一段，作业内自动拼成片

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 手动合成作业 `POST /api/media/compose`

**Files:**
- Modify: `desk/media/service.py`（新增 `start_compose_job`；`_start` 支持 compose）、`desk/media/routes.py`
- Test: `tests/test_media_compose_job.py`（新建）

**Interfaces:**
- Consumes: `_segment`（Task 6）、`compose.*`（Task 3）、`_start / _worker / _release_permit`（Task 6）
- Produces: `start_compose_job(*, kind, session_id, parts, force=False) -> dict`；HTTP `POST /api/media/compose`，体 `{kind, session_id, parts, force}`；成功落定 `op="compose"`、`output` 为 `h3-compose-…mp4` / `music3-compose-…wav`；失败 `error.code == "join_failed"`

- [ ] **Step 1: 写失败测试**

```python
"""Manual compose jobs (B §3.5)."""
import threading
from pathlib import Path

import pytest

from desk.media import compose
from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_continue import attempts, fake_ffmpeg, first_segment  # noqa: F401  (autouse fixture)
from test_media_sessions_service import video


def two_segments(service, deps):
    sid, first = first_segment(service, deps)
    second = finished_snapshot(service, lambda: video(service, session_id=sid))["attempt_id"]
    return sid, first, second


def test_compose_appends_a_compose_attempt_without_arbiter_or_memory(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    acquired = len(deps.arbiter.acquired); prechecks = len(deps.arbiter.precheck_calls)
    snap = finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[second, first, second]))
    assert len(deps.arbiter.acquired) == acquired and len(deps.arbiter.precheck_calls) == prechecks
    made = attempts(deps, "video", sid)[-1]
    assert made["op"] == "compose" and made["params"] == {"parts": [second, first, second]}
    assert made["status"] == "done" and made["output"].startswith("h3-compose-") and snap["output"] == made["output"]
    graph = deps.executor.spawned[-1]["cmd"][deps.executor.spawned[-1]["cmd"].index("-filter_complex") + 1]
    assert "trim" not in graph            # 手动乱序：没有续写关系，不丢帧（B-50）
    assert deps.history.entries[-1]["params"]["op"] == "compose"


def test_compose_can_be_continued(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    composed = finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[first, second]))["attempt_id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=composed))
    last = attempts(deps, "video", sid)[-1]
    assert last["joined_output"] and last["continues"] == composed


@pytest.mark.parametrize("kwargs, code, status", [
    ({"kind": "image"}, "invalid_params", 400),
    ({"parts": ["only-one"]}, "invalid_params", 400),
    ({"parts": "nope"}, "invalid_params", 400),
    ({"parts": ["9" * 32, "8" * 32]}, "segment_not_found", 404),
])
def test_bad_compose_requests_write_nothing(tmp_path, kwargs, code, status):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    request = {"kind": "video", "session_id": sid, "parts": [first, second], **kwargs}
    before = len(attempts(deps, "video", sid))
    with pytest.raises(MediaError) as exc:
        service.start_compose_job(**request)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert len(attempts(deps, "video", sid)) == before


def test_compose_is_mutually_exclusive_with_a_running_job(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    deps.executor.script = "block"
    video(service, session_id=sid)
    with pytest.raises(MediaError) as exc:
        service.start_compose_job(kind="video", session_id=sid, parts=[first, second])
    assert exc.value.code == "media_busy"
    service.cancel_job()


def test_compose_failure_settles_failed_join_failed(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first, second = two_segments(service, deps)
    deps.executor.join_script = "fail"
    finished_snapshot(service, lambda: service.start_compose_job(kind="video", session_id=sid, parts=[first, second]))
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "failed" and made["error"]["code"] == "join_failed"


def test_compose_route(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    seen = {}
    monkeypatch.setattr(service, "start_compose_job", lambda **kw: seen.update(kw) or {"ok": True})
    handler = next(h for m, p, h in build_routes(service) if (m, p) == ("POST", "/api/media/compose"))
    assert handler({"kind": "music", "session_id": "s", "parts": ["a", "b"]}, {}) == (200, {"ok": True})
    assert seen == {"kind": "music", "session_id": "s", "parts": ["a", "b"], "force": False}
```

- [ ] **Step 2: 确认失败**

Run: `python3 -m pytest tests/test_media_compose_job.py -q`
Expected: FAIL（`no attribute 'start_compose_job'`）

- [ ] **Step 3: 实现**

`desk/media/service.py`：

```python
    def start_compose_job(self, *, kind, session_id, parts, force=False) -> dict:
        """Join chosen segments into one file (B-44–B-48): ffmpeg only, no arbiter, no memory check."""
        if kind not in ("video", "music"):
            raise MediaError("invalid_params", "只有视频和音乐可以合成成片", 400)
        if not isinstance(parts, list) or len(parts) < 2 or not all(isinstance(p, str) for p in parts):
            raise MediaError("invalid_params", "至少选两段来合成", 400)
        if not isinstance(force, bool):
            raise MediaError("invalid_params", "force 必须为布尔值", 400)
        session_id = self._check_session(kind, session_id, required=True)
        items = [self._segment(kind, session_id, part) for part in parts]
        root = Path(self._resolve_paths().outputs_root)
        paths = [root / item["output"] for item in items]
        drops = [False] + [items[i].get("continues") == items[i - 1]["id"] for i in range(1, len(items))]
        return self._start(kind, {"op": "compose", "parts": list(parts)}, session_id=session_id,
                           attempt_extra={"op": "compose"}, compose_parts=list(zip(paths, drops)))
```

`_start` 签名加 `compose_parts: list | None = None`。在 `_start` 里用 `heavy = compose_parts is None` 包住「能力检查、模型检查、估算、arbiter 预检、内存提醒、acquire_heavy」这一整段（`media_busy` 检查仍在最前面、对两者都生效）；非 heavy 时：

```python
            if not heavy and compose.ffmpeg_path() is None:
                raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
            ...
            permit = grant["token"] if heavy else None
            now = self._clock()
```

`roots = self._resolve_paths()` 移到分支之外（两种都要）。命令构造分支最前面加：

```python
                if not heavy:
                    suffix, prefix = (".mp4", "h3") if kind == "video" else (".wav", "music3")
                    output = root / f"{prefix}-compose-{stamp}-{uuid.uuid4().hex[:8]}{suffix}"
                    ffmpeg = compose.ffmpeg_path()
                    if kind == "video":
                        size = compose.probe_size(compose.ffprobe_path() or "ffprobe", compose_parts[0][0])
                        command = compose.concat_video_command(ffmpeg, compose_parts, size, output)
                    else:
                        command = compose.crossfade_audio_command(
                            ffmpeg, [(p, wav_seconds(p) or 0.0) for p, _d in compose_parts], output)
                    extra_env = {}
                elif kind == "video":
```

`self._compose = not heavy` 与其他作业字段一起设置。`_worker` 的错误分支：若 `self._compose` 且 `status == "error"`，把 `error` 改为 `{"code": "join_failed", "message": "拼接成片失败", "log_tail": self._log_tail(5)}`。`_finalize` / `_release_permit` 已能处理 `permit is None`（Task 6）。

`desk/media/routes.py`：

```python
    def start_compose(body, _query):
        payload = body or {}
        return _run(lambda: service.start_compose_job(
            kind=payload.get("kind"), session_id=payload.get("session_id"),
            parts=payload.get("parts"), force=payload.get("force", False)))
```

路由表加 `("POST", "/api/media/compose", start_compose),`。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest tests/test_media_compose_job.py tests/test_media_continue.py tests/test_media_service.py tests/test_media_image_service.py tests/test_media_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A desk tests
git commit -m "feat(media-sessions): 手动合成成片作业 POST /api/media/compose

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 素材库认得成片、回填识别会话与合成

**Files:**
- Modify: `desk/library/history.py:42-48`、`desk/static/js/pure/history_fill.js`
- Test: `tests/test_library_history.py`、`tests/js/history_fill.test.js`（已存在，追加）

**Interfaces:**
- Produces: `HistoryStore.by_output()` 以 `output` 与 `joined_output` 两个键建索引；`fillPlan(entry)` 对 video/music 返回带 `session_id`、`attempt_id` 的计划，对 `params.op === "compose"` 返回 `null`

- [ ] **Step 1: 写失败测试**

Python（追加到 `tests/test_library_history.py`，用该文件已有的建库辅助）：

```python
def test_by_output_also_indexes_joined_output(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    entry = store.append({"kind": "video", "status": "done", "params": {}, "output": "h3-seg.mp4",
                          "joined_output": "h3-joined.mp4", "duration_s": 1.0, "error": None})
    mapping = store.by_output()
    assert mapping["h3-seg.mp4"]["id"] == entry["id"] and mapping["h3-joined.mp4"]["id"] == entry["id"]
```

JS（追加到 `tests/js/history_fill.test.js`，沿用文件里已有的 `test` / `assert` / `fillPlan` 导入）：

```js
test("fillPlan carries session fields for video and music, and skips compose entries", () => {
  const video = fillPlan({ kind: "video", session_id: "s", attempt_id: "a", params: { prompt: "p", width: 512, height: 288, frames: 49, steps: 12 } });
  assert.equal(video.session_id, "s"); assert.equal(video.attempt_id, "a");
  const music = fillPlan({ kind: "music", session_id: "m", attempt_id: "b", params: { caption: "c", lyrics: "l", duration: 20 } });
  assert.equal(music.session_id, "m"); assert.equal(music.attempt_id, "b");
  assert.equal(fillPlan({ kind: "video", params: { op: "compose", parts: ["a", "b"] } }), null);
  assert.equal(fillPlan({ kind: "video", params: { prompt: "p" } }).session_id, null);
});
```

- [ ] **Step 2: 确认失败**

Run: `python3 -m pytest tests/test_library_history.py -q -k joined && node --test tests/js/`
Expected: 两边都 FAIL

- [ ] **Step 3: 实现**

`desk/library/history.py`：

```python
    def by_output(self) -> dict[str, dict]:
        mapping: dict[str, dict] = {}
        for entry in self._read_all():
            for key in ("output", "joined_output"):
                name = entry.get(key)
                if name:
                    mapping[name] = entry
        return mapping
```

`desk/static/js/pure/history_fill.js`：在 `const params = entry.params; if (!params ...) return null;` 之后加

```js
  if (params.op === "compose") return null; // 合成成品没有可回填的参数（B-74）
  const session = { session_id: entry.session_id ?? null, attempt_id: entry.attempt_id ?? null };
```

video 与 music 两个 `return { pane: …, fields: … }` 改为 `return { pane: "video", ...session, fields: {...} }` / `return { pane: "music", ...session, fields: {...} }`。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest tests/test_library_history.py tests/test_library_outputs.py -q && node --test tests/js/`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A desk tests
git commit -m "feat(media-sessions): 素材库认得成片文件，回填带出视频音乐会话、跳过合成条目

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 完成标准验证（真 ffmpeg 走通全流程 + 全量回归）

**Files:**
- Test: `tests/test_media_sessions_flow.py`（新建）

**Interfaces:**
- Consumes: 全部前序任务

- [ ] **Step 1: 写端到端（HTTP 层、真 ffmpeg、假模型）测试**

```python
"""Completion criterion 2: new session → generate → continue → joined → compose, real ffmpeg, fake models."""
import shutil
import subprocess
from pathlib import Path

import pytest

from desk.media.executor import SubprocessExecutor
from desk.media.routes import build_routes
from media_fakes import finished_snapshot, make_service
from test_media_sessions_service import music_ready

FF, FP = shutil.which("ffmpeg"), shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(not (FF and FP), reason="ffmpeg/ffprobe not installed")


class LavfiExecutor:
    """Model commands produce a real 1 s clip at --output; ffmpeg commands really run."""
    def __init__(self):
        self.real = SubprocessExecutor()

    def spawn(self, cmd, *, extra_env=None):
        if "--output" not in cmd:
            return self.real.spawn(cmd)
        out = cmd[cmd.index("--output") + 1]
        if out.endswith(".mp4"):
            synth = [FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=512x288:rate=24", "-f", "lavfi",
                     "-i", "sine=frequency=440:sample_rate=32000", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-shortest", out]
        else:
            synth = [FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                     "-t", "5", "-ac", "2", out]
        return self.real.spawn(synth)


def duration(path: Path) -> float:
    return float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def post(service, path, body):
    handler = next(h for m, p, h in build_routes(service) if (m, p) == ("POST", path))
    status, payload = handler(body, {})
    assert status == 200, payload
    return payload


@pytest.mark.parametrize("kind", ["video", "music"])
def test_generate_continue_join_compose(tmp_path, kind):
    service, deps = make_service(tmp_path, executor=LavfiExecutor())
    music_ready(service, tmp_path)
    store = deps.media_sessions[kind]
    sid = store.create()["id"]
    body = ({"prompt": "p", "width": 512, "height": 288, "frames": 24, "steps": 4} if kind == "video"
            else {"caption": "c", "lyrics": "[verse]\nla", "duration": 5.0})
    path = f"/api/media/{kind}"
    first = finished_snapshot(service, lambda: post(service, path, {**body, "session_id": sid}))["attempt_id"]
    finished_snapshot(service, lambda: post(service, path, {**body, "session_id": sid, "continues": first}))
    second = store.get(sid)["attempts"][1]
    assert second["status"] == "done" and second["joined_error"] is None, second
    joined = tmp_path / "outputs" / second["joined_output"]
    expected = 2 - 1 / 24 if kind == "video" else 10 - 1.5
    assert abs(duration(joined) - expected) < 0.15
    finished_snapshot(service, lambda: post(service, "/api/media/compose",
                                            {"kind": kind, "session_id": sid, "parts": [first, second["id"]]}))
    made = store.get(sid)["attempts"][2]
    assert made["op"] == "compose" and made["status"] == "done" and (tmp_path / "outputs" / made["output"]).is_file()
```

- [ ] **Step 2: 跑**

Run: `python3 -m pytest tests/test_media_sessions_flow.py -q`
Expected: PASS（2 passed）。若失败，按报错回到对应任务修，不要改这个测试的期望值。

- [ ] **Step 3: 接通与旧名字检查（B-21）**

Run:
```bash
grep -rn "image-sessions\"\|/api/image-sessions\|ImageSessionStore\|image_sessions_dir\|listImageSessions\|getImageSession\|createImageSession\|renameImageSession\|deleteImageSession" desk tests --include='*.py' --include='*.js'
grep -n "media_sessions=library.media_sessions" desk/runtime.py desk/testing/harness.py
```
Expected: 第一条无输出；第二条两个文件各一行

- [ ] **Step 4: 全量回归**

Run: `python3 -m pytest -q --ignore=tests/e2e && node --test tests/js/ && python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_media_sessions_flow.py
git commit -m "test(media-sessions): 真 ffmpeg 走通生成、续写拼成片、手动合成

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
