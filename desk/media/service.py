"""H3 video and Music 3 job runner."""
from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .audio import wav_seconds
from .commands import build_h3_command, build_music_command, build_image_command
from .inputs import save_input, resolve_input

log = logging.getLogger(__name__)
DEFAULT_LOG_LIMIT = 1024 * 1024


class MediaError(Exception):
    def __init__(self, code: str, message: str, http_status: int, detail: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.http_status, self.detail = code, message, http_status, detail or {}


def _nonempty(name: str, value: Any, *, code: str = "invalid_params", message: str | None = None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MediaError(code, message or f"{name} must be a non-empty string", 400)


def _positive_int(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MediaError("invalid_params", f"{name} must be a positive integer", 400)


class MediaService:
    def __init__(self, *, resolve_paths, probe_capabilities, arbiter, list_catalog,
                 append_history, executor, clock: Callable[[], float] = time.time,
                 term_grace_s: float = 5.0, log_limit: int = DEFAULT_LOG_LIMIT):
        """`measurements`/`measurements_path`/`available_bytes` are Task 7's media
        calibration seam (R-budget-06): optional, off by default. When all three
        are wired, a job's peak resident bytes (baseline available_bytes right
        before start, minus the lowest point sampled every `mem_sample_interval_s`
        while it runs) is recorded via `Measurements.record_media` and persisted,
        so the next job of that kind gets a `measured` estimate instead of the
        parameter-based `predicted` one. With none wired (the production default
        today — see Task 7 deviations, desk/runtime.py has not been updated to
        build and pass these in), behaviour is unchanged from before this task."""
        self._resolve_paths, self._probe_capabilities, self._arbiter = resolve_paths, probe_capabilities, arbiter
        self._list_catalog, self._append_history, self._executor = list_catalog, append_history, executor
        self._clock, self._term_grace_s, self._log_limit = clock, term_grace_s, log_limit
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {"job_id": 0, "status": "idle", "kind": None, "params": None,
            "output": None, "error": None, "started_at": None, "finished_at": None}
        self._log = ""; self._log_dropped = 0; self._log_truncated = False
        self._cancel_requested = False; self._handle = None; self._callbacks: list[Callable[[dict], None]] = []

    def upload_input(self, *, name=None, data=None) -> dict:
        try:
            return save_input(self._resolve_paths().outputs_root, name, data)
        except ValueError as exc:
            raise MediaError("invalid_input", str(exc), 400) from exc

    def start_video_job(self, *, prompt, width, height, frames, steps,
                        mode="text", first_frame=None, last_frame=None, ref_video=None,
                        use_audio=True, force=False) -> dict:
        _nonempty("prompt", prompt, code="prompt_required", message="请填写视频提示词")
        for name, value in (("width", width), ("height", height), ("frames", frames), ("steps", steps)):
            _positive_int(name, value)
        if mode not in ("text", "image", "reference") or not isinstance(use_audio, bool):
            raise MediaError("invalid_params", "生成模式或音轨选项无效", 400)
        assets = {}
        if mode == "image":
            assets = {"first_frame": (first_frame, "image")}
            if last_frame: assets["last_frame"] = (last_frame, "image")
        elif mode == "reference":
            assets = {"ref_video": (ref_video, "video")}
        expected = set(assets)
        if any(value and key not in expected for key, value in
               (("first_frame", first_frame), ("last_frame", last_frame), ("ref_video", ref_video))):
            raise MediaError("invalid_params", "素材与生成模式不匹配", 400)
        try:
            for asset_id, kind in assets.values():
                resolve_input(self._resolve_paths().outputs_root, asset_id, kind)
        except ValueError as exc:
            raise MediaError("invalid_input", str(exc), 400) from exc
        params = {"prompt": prompt, "width": width, "height": height, "frames": frames, "steps": steps}
        if mode != "text":
            params.update(mode=mode, use_audio=use_audio, **{key: value[0] for key, value in assets.items()})
        return self._start("video", params, force=force)

    def start_music_job(self, *, caption, lyrics, duration, force=False) -> dict:
        _nonempty("caption", caption, code="caption_required", message="请填写风格描述")
        if not isinstance(lyrics, str) or isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise MediaError("invalid_params", "lyrics must be a string and duration must be positive", 400)
        if not lyrics.strip():
            raise MediaError("lyrics_required", "请填写歌词：Music 3 需要歌词才能生成", 400)
        return self._start("music", {"caption": caption, "lyrics": lyrics, "duration": duration}, force=force)

    def start_image_job(self, *, prompt, width=1024, height=1024, steps=40, seed=42, force=False) -> dict:
        _nonempty("prompt", prompt, code="prompt_required", message="请填写图片提示词")
        for name, value in (("width", width), ("height", height)):
            _positive_int(name, value)
            if not 256 <= value <= 2048 or value % 16:
                raise MediaError("invalid_params", "宽高须为 256–2048 范围内的 16 的倍数", 400)
        if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 100:
            raise MediaError("invalid_params", "步数须为 1–100 的整数", 400)
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
            raise MediaError("invalid_params", "种子须为 0–4294967295 的整数", 400)
        if not isinstance(force, bool):
            raise MediaError("invalid_params", "force 必须为布尔值", 400)
        return self._start("image", dict(prompt=prompt, width=width, height=height, steps=steps, seed=seed), force=force)

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

    def _start(self, kind: str, params: dict, *, force: bool = False) -> dict:
        with self._lock:
            if self._state["status"] == "running":
                raise MediaError("media_busy", "a media job is already running", 409)
            cap_key = {"video": "mlx_h3", "music": "music_runtime", "image": "image_runtime"}[kind]
            cap = self._probe_capabilities().get(cap_key)
            if cap is None or not cap.present:
                raise MediaError("capability_missing", f"{cap_key} is unavailable: {getattr(cap, 'detail', '')}", 503)
            roots = self._resolve_paths()

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
            job_id = self._state["job_id"] + 1
            display = {"video": "视频生成中", "music": "音乐生成中", "image": "图片生成中"}[kind]
            grant = self._arbiter.acquire_heavy(kind, f"job-{job_id}", display,
                                                params=params, key=catalog_key)
            if not grant.get("ok"):
                reason = grant.get("reason") or {}
                raise MediaError(reason.get("code", "acquire_refused"), reason.get("message", "arbiter refused"), 409, reason)
            permit, now = grant["token"], self._clock()
            try:
                stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
                root = Path(roots.outputs_root); root.mkdir(parents=True, exist_ok=True)
                if kind == "video":
                    output = root / f"h3-{stamp}.mp4"
                    command_params = dict(params)
                    command_params.pop("mode", None)
                    for key in ("first_frame", "last_frame", "ref_video"):
                        if key in command_params:
                            command_params[key] = resolve_input(root, command_params[key], "video" if key == "ref_video" else "image")
                    command = build_h3_command(tuple(roots.mlx_h3_cmd), model_root, output=output, **command_params)
                    extra_env = dict(roots.mlx_h3_env)
                elif kind == "music":
                    output = root / f"music3-{stamp}.wav"
                    command = build_music_command(Path(roots.music_python), Path(roots.media_cli_dir) / "music3_cli.py", model_root, output=output, **params)
                    extra_env = dict(roots.music_env)
                else:
                    output = root / f"qwen-image-{stamp}-{uuid.uuid4().hex[:8]}.png"
                    command = build_image_command(Path(roots.image_python), Path(roots.media_cli_dir) / "image_cli.py", model_root, output=output, **params)
                    extra_env = dict(roots.image_env)
                handle = self._executor.spawn(command, extra_env=extra_env)
            except Exception as exc:
                self._state = {"job_id": job_id, "status": "error", "kind": kind, "params": dict(params), "output": None,
                    "error": {"code": "spawn_failed", "message": str(exc)}, "started_at": now, "finished_at": self._clock()}
                self._reset_log(); self._finalize(permit)
                raise MediaError("spawn_failed", str(exc), 500) from exc
            self._state = {"job_id": job_id, "status": "running", "kind": kind, "params": dict(params), "output": None,
                "error": None, "started_at": now, "finished_at": None}
            self._reset_log(); self._cancel_requested = False; self._handle = handle
            threading.Thread(target=self._worker, args=(handle, permit, output, kind), daemon=True).start()
            return self.job_status()

    def _worker(self, handle, permit: str, output: Path, kind: str) -> None:
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
                self._state.update(status=status, output=output.name if status == "done" else None, error=error, finished_at=self._clock())
                self._handle = None
        finally:
            self._finalize(permit)

    def _finalize(self, permit: str) -> None:
        with self._lock: snap, callbacks = self.job_status(), list(self._callbacks)
        try: self._arbiter.release_heavy(permit)
        except Exception: log.exception("release_heavy failed")
        try: self._append_history(self._history_entry(snap))
        except Exception as exc: self._append_log(f"[media] append_history failed: {exc}")
        for callback in callbacks:
            try: callback(snap)
            except Exception: log.exception("jobFinished subscriber failed")

    def _history_entry(self, snap: dict) -> dict:
        error = snap["error"]
        entry = {"kind": snap["kind"], "status": {"done": "done", "error": "failed", "cancelled": "cancelled"}[snap["status"]],
            "params": snap["params"], "output": snap["output"], "duration_s": snap["finished_at"] - snap["started_at"],
            "error": f"{error['code']}: {error['message']}" if error else None}
        if snap["kind"] == "music" and snap["status"] == "done" and snap["output"]:
            entry["audio_seconds"] = wav_seconds(Path(self._resolve_paths().outputs_root) / snap["output"])
        return entry

    def cancel_job(self) -> dict:
        with self._lock:
            if self._state["status"] != "running": raise MediaError("no_running_job", "no media job is running", 409)
            self._cancel_requested = True; handle = self._handle
        handle.terminate()
        deadline = time.monotonic() + self._term_grace_s
        while handle.poll() is None and time.monotonic() < deadline: time.sleep(.02)
        if handle.poll() is None: handle.kill()
        return self.job_status()

    def close(self) -> None:
        """Cancel any running job on shutdown so its worker never outlives the service."""
        with self._lock:
            running = self._state["status"] == "running"
        if not running:
            return
        try:
            self.cancel_job()
        except MediaError:
            return  # finished between the check and the cancel
        deadline = time.monotonic() + self._term_grace_s + 2.0
        while time.monotonic() < deadline:
            with self._lock:
                if self._state["status"] != "running":
                    return
            time.sleep(0.02)

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
