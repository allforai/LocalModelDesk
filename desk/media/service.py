"""H3 video and Music 3 job runner."""
from __future__ import annotations

import logging
import math
import secrets
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from . import compose
from .audio import wav_seconds, wav_seconds_exact
from .commands import build_h3_command, build_music_command, build_image_command
from .inputs import save_input, resolve_input
from desk.library.errors import NotFoundError
from desk.library.media_sessions import SegmentMissing

log = logging.getLogger(__name__)
DEFAULT_LOG_LIMIT = 1024 * 1024
KIND_NAMES = {"image": "图片", "video": "视频", "music": "音乐"}


# Image-to-image presets (design D-40/D-46 rev. 2026-09-24): 「在这张基础上改」 keeps the composition,
# 「换个构图」 keeps subject and colour. Higher strength = closer to the base (mflux convention).
BASE_STRENGTHS = (0.6, 0.35)
SESSION_REQUIRED_MESSAGE = "请先选择或新建一个会话"
SESSION_NOT_FOUND_MESSAGE = "这个会话已被删除，请选择或新建一个会话"
CANCEL_ERRORS = {
    "user": {"code": "cancelled", "message": "已取消：这次生成被手动停止"},
    "quit": {"code": "cancelled_on_quit", "message": "应用退出时停止了这次生成"},
}


class MediaError(Exception):
    def __init__(self, code: str, message: str, http_status: int, detail: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.http_status, self.detail = code, message, http_status, detail or {}


class JoinInputError(Exception):
    """A join input the ffmpeg command cannot be built from (`segment` is its 1-based position).

    Raised by `_timed_parts` before anything is spawned; `_run_join` reports it as `join_failed`
    with this message, and a compose job is refused with it (500, nothing written)."""
    def __init__(self, segment: int):
        self.segment = segment
        super().__init__(f"读不出第 {segment} 段的时长，无法拼成成片")


def _nonempty(name: str, value: Any, *, code: str = "invalid_params", message: str | None = None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MediaError(code, message or f"{name} must be a non-empty string", 400)


def _positive_int(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MediaError("invalid_params", f"{name} must be a positive integer", 400)


SEED_MESSAGE = "种子须为 0–4294967295 的整数"
SEGMENT_NOT_FOUND = "找不到要接着的那一段"
SEGMENT_MISSING = "那一段的文件已不在，无法接着生成"
CONTINUE_CONFLICT = "续写会用上一段的最后一帧作首帧，不能另选首帧或参考视频"
MUSIC_REF_CONFLICT = "配乐参考不能和首帧、尾帧或续写同时使用"
# Which cross-session references each video request may carry (S-11); any other name is a 400.
VIDEO_REF_NAMES = {"text": {"first_frame"}, "image": {"first_frame"}, "reference": {"first_frame"},
                   "music_ref": {"ref_image", "ref_audio"}, "soundtrack": {"soundtrack"}}
CLIP_MIN_S, CLIP_MAX_S = 2, 15   # H3 --ref-audio accepts 2–15 s (S-12)
JOIN_CANCELLED = {"code": "join_cancelled", "message": "成片拼接被中止"}


def _validate_seed(seed) -> None:
    """Refuse a malformed seed; `None` ("pick one") passes. Draws nothing."""
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32):
        raise MediaError("invalid_params", SEED_MESSAGE, 400)


def _check_seed(seed) -> int:
    """The seed to use: a given one validated, or a fresh random one (IS D-19, B §3.2).

    Called only once every other check has passed, so a refused request draws nothing."""
    _validate_seed(seed)
    return seed if seed is not None else secrets.randbelow(2**32)


def _check_force(force) -> None:
    if not isinstance(force, bool):
        raise MediaError("invalid_params", "force 必须为布尔值", 400)


def _video_assets(mode: str, first_frame, last_frame, ref_video, ref_image=None, *, first_from_ref: bool = False) -> dict:
    """Input assets a video mode uses: {param: (asset id, asset kind)}.

    `first_from_ref=True` means the mode's image (the first frame, or the
    music_ref reference image) comes from `refs` (an image-session reference)
    instead of an uploaded asset id, so it is not part of this asset table (V-04)."""
    if mode == "image":
        assets = {} if first_from_ref else {"first_frame": (first_frame, "image")}
        if last_frame: assets["last_frame"] = (last_frame, "image")
        return assets
    if mode == "reference":
        return {"ref_video": (ref_video, "video")}
    if mode == "music_ref":
        return {} if first_from_ref else {"ref_image": (ref_image, "image")}
    return {}


def _check_ref_names(refs, allowed: set) -> None:
    """Refuse any reference name this request cannot use (S-11)."""
    for name in (refs or {}) if isinstance(refs, dict) else ():
        if name not in allowed:
            raise MediaError("invalid_params", f"引用参数有误：{name}", 400)


def _drop_flags(items: list[dict]) -> list[bool]:
    """Per segment: drop its first frame? Only a continuation joined right after its source does (B-50)."""
    return [False] + [items[i].get("continues") == items[i - 1]["id"] for i in range(1, len(items))]


def _timed_parts(parts: list) -> list[tuple[Path, float]]:
    """[(path, seconds)] for a music join; `JoinInputError(n)` when segment n's (1-based) duration is
    unreadable: a guessed length would silently turn its crossfade into a hard cut."""
    timed = []
    for number, (path, _drop) in enumerate(parts, 1):
        seconds = wav_seconds(path)
        if seconds is None:
            raise JoinInputError(number)
        timed.append((path, seconds))
    return timed


class MediaService:
    def __init__(self, *, resolve_paths, probe_capabilities, arbiter, list_catalog,
                 append_history, executor, media_sessions, ref_slots: dict | None = None,
                 clock: Callable[[], float] = time.time,
                 term_grace_s: float = 5.0, log_limit: int = DEFAULT_LOG_LIMIT):
        """`measurements`/`measurements_path`/`available_bytes` are Task 7's media
        calibration seam (R-budget-06): optional, off by default. When all three
        are wired, a job's peak resident bytes (baseline available_bytes right
        before start, minus the lowest point sampled every `mem_sample_interval_s`
        while it runs) is recorded via `Measurements.record_media` and persisted,
        so the next job of that kind gets a `measured` estimate instead of the
        parameter-based `predicted` one. With none wired (the production default
        today — see Task 7 deviations, desk/runtime.py has not been updated to
        build and pass these in), behaviour is unchanged from before this task.

        `media_sessions` is `dict[kind, store]`, one `MediaSessionStore` per media
        kind, where jobs of that kind record their attempts. MediaService only
        calls three methods on a kind's store and never touches the session file
        format: `exists(session_id) -> bool`, `begin_attempt(session_id, {"id",
        "job_id", "params"}) -> bool` once the job is really running, and
        `settle_attempt(session_id, attempt_id, status, output, error) -> bool`
        when it ends (status one of done / failed / cancelled)."""
        self._resolve_paths, self._probe_capabilities, self._arbiter = resolve_paths, probe_capabilities, arbiter
        self._list_catalog, self._append_history, self._executor = list_catalog, append_history, executor
        self._sessions = media_sessions
        self._ref_slots = ref_slots if ref_slots is not None else {"video": {
            "first_frame": "image", "soundtrack": "music", "ref_image": "image", "ref_audio": "music"}}
        self._clock, self._term_grace_s, self._log_limit = clock, term_grace_s, log_limit
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {"job_id": 0, "status": "idle", "kind": None, "params": None,
            "output": None, "error": None, "started_at": None, "finished_at": None,
            "session_id": None, "attempt_id": None, "refs": None}
        self._log = ""; self._log_dropped = 0; self._log_truncated = False
        self._cancel_requested = False; self._cancel_origin = "user"
        self._handle = None; self._worker_thread: threading.Thread | None = None
        self._callbacks: list[Callable[[dict], None]] = []

    def upload_input(self, *, name=None, data=None) -> dict:
        try:
            return save_input(self._resolve_paths().outputs_root, name, data)
        except ValueError as exc:
            raise MediaError("invalid_input", str(exc), 400) from exc

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
            output = attempt["output"]
            if target == "music" and attempt.get("joined_output") and not attempt.get("joined_missing"):
                output = attempt["joined_output"]   # a continued song's finished file is the whole song
            paths[name] = Path(self._resolve_paths().outputs_root) / output
        return stored, paths

    def _segment(self, kind: str, session_id: str, attempt_id) -> dict:
        """The done attempt being continued (B-35), with store errors mapped to 404s."""
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
        return {"parts": list(zip(paths, _drop_flags(items)))}

    def _refuse_if_busy(self) -> None:
        """Caller holds `self._lock`: one job at a time (the single busy refusal)."""
        if self._state["status"] == "running":
            raise MediaError("media_busy", "a media job is already running", 409)

    def _check_idle(self) -> None:
        """Refuse early while another job runs, before any costly ffmpeg work outside the lock."""
        with self._lock:
            self._refuse_if_busy()

    def _run_to_input(self, builder: Callable[[Path], list[str]], suffix: str, code: str, message: str) -> Path:
        """Run the ffmpeg argv `builder(path)` writing `.inputs/<hex><suffix>`; on any failure delete it and
        raise `MediaError(code, message, 500)`."""
        directory = Path(self._resolve_paths().outputs_root) / ".inputs"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid.uuid4().hex}{suffix}"
        try:
            result = subprocess.run(builder(path), capture_output=True, text=True, timeout=60)
            ok = result.returncode == 0 and path.is_file()
        except (OSError, subprocess.SubprocessError):
            ok = False
        if not ok:
            path.unlink(missing_ok=True)
            raise MediaError(code, message, 500)
        return path

    def _extract_last_frame(self, video: Path) -> str:
        """Save the continued video's last frame as an input asset; returns its asset id (B-36/B-37)."""
        ffmpeg = compose.ffmpeg_path()
        if ffmpeg is None:
            raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
        return self._run_to_input(lambda png: compose.last_frame_command(ffmpeg, video, png), ".png",
                                  "frame_extract_failed", "没能从上一段截出最后一帧").name

    def _clip_audio(self, song: Path, start: float, seconds: float) -> Path:
        """Cut the clip a music_ref job hears into `.inputs/<hex>.wav` (S-12); refusals leave no file."""
        length = wav_seconds_exact(song)   # unrounded: `wav_seconds`'s 0.01 s rounding would let e.g. 1.996 s pass here (S-14)
        if length is None:
            raise MediaError("audio_clip_failed", "没能截取这段音乐", 500)
        if length < start + CLIP_MIN_S:
            raise MediaError("invalid_params", f"这首歌从第 {start:g} 秒起不足 {CLIP_MIN_S} 秒", 400)
        ffmpeg = compose.ffmpeg_path()
        if ffmpeg is None:
            raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
        return self._run_to_input(lambda wav: compose.audio_clip_command(ffmpeg, song, start, seconds, wav), ".wav",
                                  "audio_clip_failed", "没能截取这段音乐")

    def start_video_job(self, *, prompt, width, height, frames, steps,
                        mode="text", first_frame=None, last_frame=None, ref_video=None, ref_image=None,
                        audio_start=0, use_audio=True, seed=None, session_id=None, continues=None, refs=None,
                        force=False) -> dict:
        _nonempty("prompt", prompt, code="prompt_required", message="请填写视频提示词")
        for name, value in (("width", width), ("height", height), ("frames", frames), ("steps", steps)):
            _positive_int(name, value)
        _validate_seed(seed)
        _check_force(force)
        ref_names = set(refs) if isinstance(refs, dict) else set()
        if mode == "music_ref":
            self._check_music_ref(ref_image, audio_start, ref_names,
                                  conflicts=(continues is not None, first_frame, last_frame, ref_video))
        if continues is not None and (mode not in ("text", "image") or first_frame or last_frame or ref_video):
            raise MediaError("invalid_params", CONTINUE_CONFLICT, 400)
        wants_ref_frame = "first_frame" in ref_names
        if wants_ref_frame and continues is not None:
            raise MediaError("invalid_params", CONTINUE_CONFLICT, 400)
        if wants_ref_frame and (mode != "image" or first_frame):
            raise MediaError("invalid_params", "首帧只能从上传或图片会话二选一", 400)
        if mode not in VIDEO_REF_NAMES or mode == "soundtrack" or not isinstance(use_audio, bool):
            raise MediaError("invalid_params", "生成模式或音轨选项无效", 400)
        from_ref = (mode == "image" and wants_ref_frame) or (mode == "music_ref" and "ref_image" in ref_names)
        if any(value and key not in _video_assets(mode, first_frame, last_frame, ref_video, ref_image, first_from_ref=from_ref)
               for key, value in (("first_frame", first_frame), ("last_frame", last_frame),
                                  ("ref_video", ref_video), ("ref_image", ref_image))):
            raise MediaError("invalid_params", "素材与生成模式不匹配", 400)
        session_id = self._check_session("video", session_id, required=True)
        _check_ref_names(refs, VIDEO_REF_NAMES[mode])   # B-32: refs are checked after the session
        join, made = None, []   # made: files this request extracted, removed again on any refusal (B-37)
        root = Path(self._resolve_paths().outputs_root)
        if continues is not None:
            source = self._segment("video", session_id, continues)
            join = self._join_plan("video", session_id, continues)
            joined = source.get("joined_output")
            self._check_idle()   # cheap pre-check; `_start` still decides under its lock
            frame = self._extract_last_frame(root / (joined if joined and not source.get("joined_missing") else source["output"]))
            made.append(root / ".inputs" / frame)
            mode, first_frame = "image", frame
        clip_path = None
        try:
            stored_refs, ref_paths = self._resolve_refs("video", refs)
            assets = _video_assets(mode, first_frame, last_frame, ref_video, ref_image, first_from_ref=from_ref)
            try:
                for asset_id, kind in assets.values():
                    resolve_input(root, asset_id, kind)
            except ValueError as exc:
                raise MediaError("invalid_input", str(exc), 400) from exc
            params = {"prompt": prompt, "width": width, "height": height, "frames": frames, "steps": steps,
                      "seed": _check_seed(seed)}
            if mode == "music_ref":
                self._check_idle()
                clip = self._clip_audio(ref_paths["ref_audio"], audio_start,
                                        max(CLIP_MIN_S, min(CLIP_MAX_S, frames / compose.FPS)))
                made.append(clip)
                ref_paths["ref_audio"] = clip
                clip_path = clip   # nothing else ever references this clip; the job deletes it when it finalizes
                params.update(audio_start=audio_start, ref_image=None)
            if mode != "text":
                params.update(mode=mode, use_audio=use_audio, **{key: value[0] for key, value in assets.items()})
            return self._start("video", params, force=force, session_id=session_id,
                               attempt_extra={"refs": stored_refs, "continues": continues}, join=join,
                               ref_paths=ref_paths, clip_path=clip_path)
        except Exception:
            for path in made:
                path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _check_music_ref(ref_image, audio_start, ref_names: set, *, conflicts) -> None:
        """The music_ref request's own rules (S-10/S-11), before anything touches a session."""
        if any(conflicts) or "first_frame" in ref_names:
            raise MediaError("invalid_params", MUSIC_REF_CONFLICT, 400)
        if ref_image and "ref_image" in ref_names:
            raise MediaError("invalid_params", "参考图只能从上传或图片会话二选一", 400)
        if not ref_image and "ref_image" not in ref_names:
            raise MediaError("invalid_params", "请先选择参考图", 400)
        if "ref_audio" not in ref_names:
            raise MediaError("invalid_params", "请先选择一首歌", 400)
        if isinstance(audio_start, bool) or not isinstance(audio_start, (int, float)) \
                or not math.isfinite(audio_start) or audio_start < 0:
            raise MediaError("invalid_params", "起始秒数须为不小于 0 的数", 400)

    def start_music_job(self, *, caption, lyrics, duration, seed=None, session_id=None, continues=None,
                        refs=None, force=False) -> dict:
        _nonempty("caption", caption, code="caption_required", message="请填写风格描述")
        if not isinstance(lyrics, str) or isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise MediaError("invalid_params", "lyrics must be a string and duration must be positive", 400)
        if not lyrics.strip():
            raise MediaError("lyrics_required", "请填写歌词：Music 3 需要歌词才能生成", 400)
        _validate_seed(seed)
        _check_force(force)
        session_id = self._check_session("music", session_id, required=True)
        join = None
        if continues is not None:
            self._segment("music", session_id, continues)
            join = self._join_plan("music", session_id, continues)
        stored_refs, _ref_paths = self._resolve_refs("music", refs)
        return self._start("music", {"caption": caption, "lyrics": lyrics, "duration": duration, "seed": _check_seed(seed)},
                           force=force, session_id=session_id,
                           attempt_extra={"refs": stored_refs, "continues": continues}, join=join)

    def start_image_job(self, *, session_id=None, prompt, width=1024, height=1024, steps=40,
                        seed=None, force=False, base=None, continues=None, refs=None) -> dict:
        """Start an image job inside a session.

        Order (design D-20): parameters → session → the shared `_start` gates.
        A running attempt is appended only once the job really runs; any refusal
        before that leaves the session file untouched (D-21). `seed=None` means
        "pick one": the value actually used is what the attempt records (D-19)."""
        if continues is not None or refs is not None:
            raise MediaError("invalid_params", "图片不支持续写或引用", 400)   # B-00b
        _nonempty("prompt", prompt, code="prompt_required", message="请填写图片提示词")
        for name, value in (("width", width), ("height", height)):
            _positive_int(name, value)
            if not 256 <= value <= 2048 or value % 16:
                raise MediaError("invalid_params", "宽高须为 256–2048 范围内的 16 的倍数", 400)
        if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 100:
            raise MediaError("invalid_params", "步数须为 1–100 的整数", 400)
        _validate_seed(seed)
        _check_force(force)
        session_id = self._check_session("image", session_id, required=True)
        params = dict(prompt=prompt, width=width, height=height, steps=steps)
        if base is not None:
            source = self._base_attempt(session_id, base)
            # The base image fixes the canvas: img2img redraws it, so its size wins.
            params.update(width=source["params"]["width"], height=source["params"]["height"],
                          base={"attempt_id": source["id"], "strength": base["strength"], "output": source["output"]})
        params["seed"] = _check_seed(seed)
        extra = {"base": {"attempt_id": params["base"]["attempt_id"], "strength": params["base"]["strength"]}} \
            if params.get("base") else {}
        return self._start("image", params, force=force, session_id=session_id, attempt_extra=extra)

    def start_compose_job(self, *, kind, session_id, parts, force=False) -> dict:
        """Join chosen segments into one file (B-44–B-48): ffmpeg only, no arbiter, no memory check.

        `force` is accepted and ignored so the page can resend every job the same way (B-45)."""
        if kind not in ("video", "music"):
            raise MediaError("invalid_params", "只有视频和音乐可以合成成片", 400)
        if not isinstance(parts, list) or len(parts) < 2 or not all(isinstance(p, str) for p in parts):
            raise MediaError("invalid_params", "至少选两段来合成", 400)
        if not isinstance(force, bool):
            raise MediaError("invalid_params", "force 必须为布尔值", 400)
        session_id = self._check_session(kind, session_id, required=True)
        items = [self._segment(kind, session_id, part) for part in parts]
        root = Path(self._resolve_paths().outputs_root)
        paths = [root / item["output"] for item in items]   # each segment's own file, never its joined one (B-48)
        joined = list(zip(paths, _drop_flags(items)))
        # Inputs are read here, outside the lock `_start` holds (a probe may take up to 30 s), and a bad
        # one refuses the job before anything is written (B-33).
        self._check_idle()
        if compose.ffmpeg_path() is None or (kind == "video" and compose.ffprobe_path() is None):
            raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)   # before any probing
        if kind == "video":
            try:
                size = compose.probe_size(compose.ffprobe_path(), paths[0])
            except ValueError:
                raise MediaError("join_failed", "读不出第一段的画面尺寸", 500) from None
            command = lambda ffmpeg, output: self._join_command("video", joined, output, ffmpeg, size)
        else:
            try:
                timed = _timed_parts(joined)
            except JoinInputError as exc:
                raise MediaError("join_failed", str(exc), 500) from None
            command = lambda ffmpeg, output: compose.crossfade_audio_command(ffmpeg, timed, output)
        return self._start(kind, {"op": "compose", "parts": list(parts)}, session_id=session_id,
                           attempt_extra={"op": "compose", "params": {"parts": list(parts)}},
                           compose_command=command,
                           output_prefix="h3-compose" if kind == "video" else "music3-compose")

    def start_soundtrack_job(self, *, session_id, source, refs, force=False) -> dict:
        """Replace a video attempt's audio with a music-session song (S-01–S-05): ffmpeg only, like compose.

        `force` is accepted and ignored, as for compose (B-45)."""
        if not isinstance(source, str) or not isinstance(refs, dict) or set(refs) != VIDEO_REF_NAMES["soundtrack"] \
                or not isinstance(refs["soundtrack"], dict):
            raise MediaError("invalid_params", "配乐参数有误：需要一段视频和一首歌", 400)
        if not isinstance(force, bool):
            raise MediaError("invalid_params", "force 必须为布尔值", 400)
        session_id = self._check_session("video", session_id, required=True)
        segment = self._segment("video", session_id, source)
        stored_refs, ref_paths = self._resolve_refs("video", refs)
        joined = segment.get("joined_output")
        root = Path(self._resolve_paths().outputs_root)
        video = root / (joined if joined and not segment.get("joined_missing") else segment["output"])   # S-03
        audio = ref_paths["soundtrack"]
        return self._start("video", {"op": "soundtrack", "source": source}, session_id=session_id,
                           attempt_extra={"op": "soundtrack", "refs": stored_refs},
                           compose_command=lambda ffmpeg, output: compose.soundtrack_command(ffmpeg, video, audio, output),
                           output_prefix="h3-soundtrack")

    def _base_attempt(self, session_id: str, base) -> dict:
        """The done attempt of this session an img2img job redraws from (its file must still exist)."""
        if (not isinstance(base, dict) or not isinstance(base.get("attempt_id"), str)
                or base.get("strength") not in BASE_STRENGTHS or isinstance(base.get("strength"), bool)):
            raise MediaError("invalid_params", "底稿参数有误：需要尝试 id 和预设的变化幅度", 400)
        session = self._sessions["image"].get(session_id)
        source = next((a for a in session.get("attempts", [])
                       if isinstance(a, dict) and a.get("id") == base["attempt_id"]), None)
        if source is None:
            raise MediaError("base_not_found", "找不到作为底稿的那一次生成", 404)
        if source.get("status") != "done" or source.get("output_missing") or not source.get("output"):
            raise MediaError("base_missing", "底稿图片已不在，无法以它为底稿重绘", 404)
        return source

    def _estimate(self, kind: str, params: dict) -> tuple[int, str]:
        """(bytes, source) —— 按作业参数估算的峰值。

        作业峰值是**作业本身的属性**（模型 + 分辨率 × 帧数），不是机器的属性：
        同样的参数在任何机器上要的内存都一样。所以这里只有按参数算的一条路。

        曾经还有一条「用运行时 available_bytes 的基线减最低点来标定」的路，已删除：
        后来量到 available_bytes 对常驻内存只捕捉 51–73%，那样记下的峰值系统性偏低，
        而 measured 优先于 predicted —— 预算会以为视频只要 14 GiB（实际 27），
        放行装不下的组合。偏低的方向正是会 OOM 的那一侧。
        """
        from .memory_estimate import estimate_bytes
        return estimate_bytes(kind, params), "predicted"

    def _start(self, kind: str, params: dict, *, force: bool = False, session_id: str | None = None,
              attempt_extra: dict | None = None, join: dict | None = None,
              compose_command: Callable[[str, Path], list[str]] | None = None, output_prefix: str | None = None,
              ref_paths: dict | None = None, clip_path: Path | None = None) -> dict:
        """`join` (from `_join_plan`) makes the job join the chain into a finished file after the model (B-38).

        `compose_command(ffmpeg, output) -> argv` makes it an ffmpeg-only job instead (compose B-45,
        soundtrack S-02): arbiter, capability/model checks and the memory estimate are skipped, and
        the output is `<output_prefix>-<stamp>-<8hex>` with the kind's suffix."""
        heavy = compose_command is None
        with self._lock:
            self._refuse_if_busy()
            roots = self._resolve_paths()
            job_id = self._state["job_id"] + 1
            if heavy:
                model_root, permit = self._admit_heavy(kind, params, force, join, roots, job_id)
            else:
                ffmpeg = compose.ffmpeg_path()
                if ffmpeg is None:
                    raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
                model_root, permit = None, None
            now = self._clock()
            # Per-job state: a later `_start` must never change what this job's finalize releases or records.
            job = {"permit": permit, "released": False, "join": join, "compose": not heavy,
                   "joined": {"joined_output": None, "joined_error": None}, "clip_path": clip_path}
            try:
                stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
                root = Path(roots.outputs_root); root.mkdir(parents=True, exist_ok=True)
                if not heavy:
                    suffix = ".mp4" if kind == "video" else ".wav"
                    output = root / f"{output_prefix}-{stamp}-{uuid.uuid4().hex[:8]}{suffix}"
                    command = compose_command(ffmpeg, output)
                    extra_env = {}
                elif kind == "video":
                    output = root / f"h3-{stamp}-{uuid.uuid4().hex[:8]}.mp4"
                    command_params = dict(params)
                    command_params.pop("mode", None)
                    command_params.pop("audio_start", None)
                    for key in ("first_frame", "last_frame", "ref_video", "ref_image"):
                        if command_params.get(key):
                            command_params[key] = resolve_input(root, command_params[key], "video" if key == "ref_video" else "image")
                    for key in ("first_frame", "ref_image", "ref_audio"):
                        if ref_paths and ref_paths.get(key):
                            command_params[key] = ref_paths[key]
                    command = build_h3_command(tuple(roots.mlx_h3_cmd), model_root, output=output, **command_params)
                    extra_env = dict(roots.mlx_h3_env)
                elif kind == "music":
                    output = root / f"music3-{stamp}-{uuid.uuid4().hex[:8]}.wav"
                    command = build_music_command(Path(roots.music_python), Path(roots.media_cli_dir) / "music3_cli.py", model_root, output=output, **params)
                    extra_env = dict(roots.music_env)
                else:
                    output = root / f"qwen-image-{stamp}-{uuid.uuid4().hex[:8]}.png"
                    command_params = {key: params[key] for key in ("prompt", "width", "height", "steps", "seed")}
                    if params.get("base"):
                        command_params.update(init_image=root / params["base"]["output"],
                                              image_strength=params["base"]["strength"])
                    command = build_image_command(Path(roots.image_python), Path(roots.media_cli_dir) / "image_cli.py", model_root, output=output, **command_params)
                    extra_env = dict(roots.image_env)
                handle = self._executor.spawn(command, extra_env=extra_env)
            except Exception as exc:
                self._state = {"job_id": job_id, "status": "error", "kind": kind, "params": dict(params), "output": None,
                    "error": {"code": "spawn_failed", "message": str(exc)}, "started_at": now, "finished_at": self._clock(),
                    "session_id": None, "attempt_id": None, "refs": None}
                self._reset_log(); self._finalize(job, self._final_snapshot(job))
                raise MediaError("spawn_failed", str(exc), 500) from exc
            self._state = {"job_id": job_id, "status": "running", "kind": kind, "params": dict(params), "output": None,
                "error": None, "started_at": now, "finished_at": None, "session_id": None, "attempt_id": None,
                "refs": (attempt_extra or {}).get("refs") or None}
            self._reset_log(); self._cancel_requested = False; self._cancel_origin = "user"; self._handle = handle
            if session_id is not None:
                self._begin_attempt(kind, session_id, job_id, params, attempt_extra or {})
            self._worker_thread = threading.Thread(target=self._worker, args=(handle, job, output, kind), daemon=True)
            self._worker_thread.start()
            return self.job_status()

    def _admit_heavy(self, kind: str, params: dict, force: bool, join: dict | None, roots, job_id: int):
        """Capability, model, memory and arbiter gates for a model job; returns (model_root, permit)."""
        cap_key = {"video": "mlx_h3", "music": "music_runtime", "image": "image_runtime"}[kind]
        cap = self._probe_capabilities().get(cap_key)
        if cap is None or not cap.present:
            raise MediaError("capability_missing", f"{cap_key} is unavailable: {getattr(cap, 'detail', '')}", 503)

        catalog_key = {"video": "h3", "music": "music3", "image": "qwen-image"}[kind]
        catalog = list(self._list_catalog())
        model_root = Path(roots.models_root) / {e.key: e.relpath for e in catalog}[catalog_key]
        if kind == "image":
            from .image_model import validate_model
            try:
                validate_model(model_root)
            except (OSError, ValueError) as exc:
                raise MediaError("model_incomplete", str(exc), 409) from exc
        estimated, source = self._estimate(kind, params)
        # 预算按作业参数算峰值（memory_estimate 就是这么设计的：分辨率×帧数决定体积项）。
        # 只从 legacy 的 estimated_bytes 通道递过去，预算路径读不到，会退回草稿档默认值——
        # 和 llm 侧「不传 config 就把聊天算成 0 字节」是同一类漏。
        pre = self._arbiter.can_start_heavy(kind, params=params, key=catalog_key,
                                            estimated_bytes=estimated)
        if not pre.get("ok"):
            reason = pre.get("reason") or {}
            raise MediaError(reason.get("code", "refused"), reason.get("message", "arbiter refused"), 409, reason)
        warning = pre.get("memory_warning")
        if warning and not force:
            required = warning["required_bytes"] / 1024 ** 3
            available = warning["available_bytes"] / 1024 ** 3
            label = "已实测" if source == "measured" else "估算"
            raise MediaError("insufficient_memory",
                              f"生成约需 {required:.1f} GiB 内存（{label}），当前可用 {available:.1f} GiB，可能失败或拖慢整机",
                              409, {**warning, "source": source})
        if join and "parts" in join and compose.ffmpeg_path() is None:
            raise MediaError("capability_missing", compose.FFMPEG_MISSING, 503)
        display = {"video": "视频生成中", "music": "音乐生成中", "image": "图片生成中"}[kind]
        grant = self._arbiter.acquire_heavy(kind, f"job-{job_id}", display,
                                            params=params, key=catalog_key)
        if not grant.get("ok"):
            reason = grant.get("reason") or {}
            raise MediaError(reason.get("code", "acquire_refused"), reason.get("message", "arbiter refused"), 409, reason)
        return model_root, grant["token"]

    def _begin_attempt(self, kind: str, session_id: str, job_id: int, params: dict, extra: dict) -> None:
        """Attach the now-running job to its session (IS D-20 step 5, B-32).

        A session deleted since the check, or a store failure, leaves the job
        running unattached (IS D-23): the output still reaches outputs and history."""
        attempt_id = uuid.uuid4().hex
        try:
            attached = self._sessions[kind].begin_attempt(session_id, {
                "id": attempt_id, "job_id": job_id, "params": dict(extra.get("params", params)),
                "op": extra.get("op", "generate"), "continues": extra.get("continues"),
                "refs": extra.get("refs") or {}, "base": extra.get("base")})
        except Exception:
            log.exception("begin_attempt failed; %s job runs without a session", kind)
            attached = False
        if attached:
            self._state.update(session_id=session_id, attempt_id=attempt_id)

    def _worker(self, handle, job: dict, output: Path, kind: str) -> None:
        final = None
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
                if job["compose"] and status == "error":   # B-47/S-05: an ffmpeg-only job fails as a join
                    error = {"code": "join_failed", "message": "拼接成片失败", "log_tail": self._log_tail(5)}
                if job["compose"] and status != "done":   # B-45/S-05: no half-written output left behind
                    output.unlink(missing_ok=True)
                join = job["join"] if status == "done" else None
                session_id, attempt_id = self._state["session_id"], self._state["attempt_id"]
                if join is None:
                    self._state.update(status=status, output=output.name if status == "done" else None,
                                       error=error, finished_at=self._clock())
                    self._handle = None
                    final = self._final_snapshot(job)
            if join is not None:
                self._release_permit(job)   # the model has exited; joining only needs ffmpeg (B-38b)
                if session_id:
                    try:
                        self._sessions[kind].record_output(session_id, attempt_id, output.name)   # B-38a
                    except Exception:
                        log.exception("record_output failed")
                job["joined"] = self._run_join(kind, join, output)
                with self._lock:
                    self._state.update(status="done", output=output.name, error=None, finished_at=self._clock())
                    self._handle = None
                    final = self._final_snapshot(job)
        finally:
            if final is None:   # the worker itself failed before the job reached a terminal state
                with self._lock: final = self._final_snapshot(job)
            self._finalize(job, final)

    def _final_snapshot(self, job: dict) -> tuple:
        """What finalize reports, taken (under the lock) in the same step that ends the job:
        once the status is terminal a new `_start` may run and replace the service's state."""
        return self.job_status(), list(self._callbacks), self._cancel_origin, dict(job["joined"])

    def _release_permit(self, job: dict) -> None:
        """Release this job's heavy permit at most once (B-38b)."""
        with self._lock:
            if job["permit"] is None or job["released"]:
                return
            job["released"] = True
        try: self._arbiter.release_heavy(job["permit"])
        except Exception: log.exception("release_heavy failed")

    def _run_join(self, kind: str, join: dict, segment: Path) -> dict:
        """Join the chain plus the new segment (B-38–B-42); never raises, never fails the segment.

        Relies on `_state["status"]` staying "running" for the whole join (the worker only
        sets it terminal afterwards): no other job can start meanwhile, so the service-wide
        `_cancel_requested` belongs to this job alone."""
        if "error" in join:
            return {"joined_output": None, "joined_error": dict(join["error"])}
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self._clock()))
        suffix, prefix = (".mp4", "h3") if kind == "video" else (".wav", "music3")
        target = segment.parent / f"{prefix}-joined-{stamp}-{uuid.uuid4().hex[:8]}{suffix}"
        try:
            ffmpeg = compose.ffmpeg_path()
            if ffmpeg is None:
                raise RuntimeError(compose.FFMPEG_MISSING)
            command = self._join_command(kind, [*join["parts"], (segment, True)], target, ffmpeg)
            with self._lock:
                if self._cancel_requested:
                    return {"joined_output": None, "joined_error": dict(JOIN_CANCELLED)}
                handle = self._executor.spawn(command)
                self._handle = handle
            self._append_log("[join] 正在拼接成片…")
            for line in handle.iter_output(): self._append_log(line)
            code = handle.wait()
        except JoinInputError as exc:   # refused before spawning: nothing to clean up
            return {"joined_output": None, "joined_error": {"code": "join_failed", "message": str(exc)}}
        except Exception as exc:
            target.unlink(missing_ok=True)
            with self._lock:
                cancelled = self._cancel_requested
            if cancelled:   # a cancelled ffmpeg may surface as an exception rather than an exit code
                return {"joined_output": None, "joined_error": dict(JOIN_CANCELLED)}
            return {"joined_output": None,
                    "joined_error": {"code": "join_failed", "message": "拼接成片失败", "log_tail": str(exc)}}
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

    @staticmethod
    def _join_command(kind: str, parts: list, target: Path, ffmpeg: str,
                      size: tuple[int, int] | None = None) -> list[str]:
        """ffmpeg argv joining [(path, drop_first_frame)] into `target` (B-50 video / B-51 music).

        Video uses `size` when given (compose reads it outside the lock); probing it here is only
        for `_run_join`, which builds its command before taking the lock. Raises `JoinInputError(n)`
        when music segment n's (1-based) duration cannot be read."""
        if kind == "video":
            if size is None:
                ffprobe = compose.ffprobe_path()
                if ffprobe is None:   # never fall back to a bare name (#17 drift); _run_join reports this as join_failed
                    raise RuntimeError("需要 ffprobe 才能拼接成片")
                size = compose.probe_size(ffprobe, parts[0][0])
            return compose.concat_video_command(ffmpeg, parts, size, target)
        return compose.crossfade_audio_command(ffmpeg, _timed_parts(parts), target)

    def _finalize(self, job: dict, final: tuple) -> None:
        snap, callbacks, origin, joined = final
        self._release_permit(job)
        if job.get("clip_path") is not None:   # music_ref's cut clip is referenced by nothing after the job (whatever the outcome)
            try: job["clip_path"].unlink(missing_ok=True)
            except Exception: log.exception("clip_path cleanup failed")
        try: self._append_history(self._history_entry(snap, joined))
        except Exception as exc: self._append_log(f"[media] append_history failed: {exc}")
        self._settle_attempt(snap, origin, joined)
        for callback in callbacks:
            try: callback(snap)
            except Exception: log.exception("jobFinished subscriber failed")

    def _settle_attempt(self, snap: dict, cancel_origin: str, joined: dict) -> None:
        """Write the job's outcome into its session attempt (D-24); never raises."""
        if not snap.get("attempt_id"):
            return
        status = {"done": "done", "error": "failed", "cancelled": "cancelled"}[snap["status"]]
        error = None
        if status == "failed":
            error = snap["error"]
        elif status == "cancelled":
            error = dict(CANCEL_ERRORS[cancel_origin])
        try:
            settled = self._sessions[snap["kind"]].settle_attempt(
                snap["session_id"], snap["attempt_id"], status, snap["output"], error,
                joined_output=joined["joined_output"], joined_error=joined["joined_error"])
            if not settled:
                log.info("%s attempt %s not settled: its session is gone", snap["kind"], snap["attempt_id"])
        except Exception:
            log.exception("settle_attempt failed")

    def _history_entry(self, snap: dict, joined: dict) -> dict:
        error = snap["error"]
        entry = {"kind": snap["kind"], "status": {"done": "done", "error": "failed", "cancelled": "cancelled"}[snap["status"]],
            "params": snap["params"], "output": snap["output"], "duration_s": snap["finished_at"] - snap["started_at"],
            "error": f"{error['code']}: {error['message']}" if error else None}
        entry.update(session_id=snap.get("session_id"), attempt_id=snap.get("attempt_id"))
        if snap.get("refs"):
            entry["refs"] = snap["refs"]
        if joined.get("joined_output"):
            entry["joined_output"] = joined["joined_output"]
        if snap["kind"] == "music" and snap["status"] == "done" and snap["output"]:
            entry["audio_seconds"] = wav_seconds(Path(self._resolve_paths().outputs_root) / snap["output"])
        return entry

    def cancel_job(self) -> dict:
        return self._cancel("user")

    def _cancel(self, origin: str) -> dict:
        with self._lock:
            if self._state["status"] != "running": raise MediaError("no_running_job", "no media job is running", 409)
            if not self._cancel_requested: self._cancel_origin = origin
            self._cancel_requested = True; handle = self._handle
        handle.terminate()
        deadline = time.monotonic() + self._term_grace_s
        while handle.poll() is None and time.monotonic() < deadline: time.sleep(.02)
        if handle.poll() is None: handle.kill()
        return self.job_status()

    def close(self) -> None:
        """Cancel any running job on shutdown so its worker never outlives the service.

        Waits for the worker's finalize too, not just the status flip: the
        session attempt is settled there (as `cancelled_on_quit`), and returning
        earlier would let the process exit with the attempt still running."""
        with self._lock:
            running = self._state["status"] == "running"
            worker = self._worker_thread
        if running:
            try:
                self._cancel("quit")
            except MediaError:
                pass  # finished between the check and the cancel
        if worker is not None and worker is not threading.current_thread():
            worker.join(self._term_grace_s + 2.0)

    def job_status(self, *, log_from: int = 0, job_id: int | None = None) -> dict:
        with self._lock:
            state = dict(self._state); state["params"] = dict(self._state["params"]) if self._state["params"] else None
            state["error"] = dict(self._state["error"]) if self._state["error"] else None
            if job_id is not None and job_id != state["job_id"]: log_from = 0
            state.update(log=self._log[max(log_from - self._log_dropped, 0):], next_log_from=self._log_dropped + len(self._log), log_len=self._log_dropped + len(self._log), log_truncated=self._log_truncated)
            state["elapsed_s"] = self._clock() - state["started_at"] if state["status"] == "running" else None
            return state

    def on_job_finished(self, callback: Callable[[dict], None]) -> Callable[[], None]:
        """Test seam: production code never calls this (census 2026-09-08, F13)."""
        with self._lock: self._callbacks.append(callback)
        def unsubscribe() -> None:
            with self._lock:
                if callback in self._callbacks: self._callbacks.remove(callback)
        return unsubscribe

    def _log_tail(self, n: int) -> str:
        lines = [line for line in self._log.splitlines() if line.strip()]
        return "\n".join(lines[-n:])

    def _reset_log(self) -> None: self._log = ""; self._log_dropped = 0; self._log_truncated = False
    def _append_log(self, line: str) -> None:
        with self._lock:
            self._log += line if line.endswith("\n") else line + "\n"
            overflow = len(self._log) - self._log_limit
            if overflow > 0: self._log = self._log[overflow:]; self._log_dropped += overflow; self._log_truncated = True
