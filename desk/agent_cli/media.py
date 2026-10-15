"""Image/video/music sessions for agents: sessions/new/show/gen/wait/rename/join (A-10..A-27, B-01..B-32)."""
from __future__ import annotations

import base64
import os
import re
import shutil
import signal
from pathlib import Path

from .chat import AGENT, _llm, snapshot
from .client import DeskClient, HttpError, Unreachable
from .decide import RETRY_CODES, Snapshot, decide
from .errors import (CliError, EXIT_ERROR, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_TIMEOUT, EXIT_USAGE, Interrupted)
from .waiter import Waiter

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_SIZE = re.compile(r"^(\d+)x(\d+)$")

# UI defaults: desk/static/js/pure/video_session.js (DURATIONS, DEFAULT_FRAMES, DEFAULT_STEPS),
# desk/static/index.html (data-video-steps, data-music-duration, data-image-steps).
VIDEO_DURATIONS = {49: "约 2 秒", 73: "约 3 秒", 124: "约 5 秒", 192: "约 8 秒", 243: "约 10 秒", 362: "约 15 秒"}
VIDEO_DEFAULT_SIZE = "768x448"
VIDEO_DEFAULT_FRAMES = 124
VIDEO_DEFAULT_STEPS = 16
IMAGE_DEFAULT_SIZE = "1024x1024"
IMAGE_DEFAULT_STEPS = 40
MUSIC_DEFAULT_DURATION = 60
FIRST_FRAME_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
MAX_INPUT_BYTES = 32 * 1024 * 1024
LABELS = {"image": "图片", "video": "视频", "music": "音乐"}
ENDPOINTS = {"image": "/api/media/image", "video": "/api/media/video", "music": "/api/media/music"}


def add_parsers(sub, common) -> None:
    for kind, label in LABELS.items():
        top = sub.add_parser(kind, help={"image": "本地生图与图片会话", "video": "本地生成视频与视频会话",
                                         "music": "本地生成音乐与音乐会话"}[kind])
        msub = top.add_subparsers(dest="media_command", required=True)
        msub.add_parser("sessions", parents=[common], help=f"列出{label}会话")
        new = msub.add_parser("new", parents=[common], help=f"新建{label}会话")
        new.add_argument("name")
        show = msub.add_parser("show", parents=[common], help="查看会话里的尝试")
        show.add_argument("session")
        gen = msub.add_parser("gen", parents=[common], help=f"在会话里生成{label}")
        gen.add_argument("session")
        gen.add_argument("prompt")
        gen.add_argument("--seed", type=int)
        gen.add_argument("--out")
        gen.add_argument("--force", action="store_true")
        gen.add_argument("--no-wait", action="store_true")
        if kind == "image":
            gen.add_argument("--size", default=IMAGE_DEFAULT_SIZE)
            gen.add_argument("--steps", type=int, default=IMAGE_DEFAULT_STEPS)
            gen.add_argument("--from", dest="base")
            gen.add_argument("--strength", type=float, default=0.6)
        elif kind == "video":
            gen.add_argument("--size", default=VIDEO_DEFAULT_SIZE)
            gen.add_argument("--frames", type=int, default=VIDEO_DEFAULT_FRAMES)
            gen.add_argument("--steps", type=int, default=VIDEO_DEFAULT_STEPS)
            gen.add_argument("--continue", dest="continues")
            gen.add_argument("--first-frame", dest="first_frame")
        else:
            gen.add_argument("--lyrics")
            gen.add_argument("--lyrics-file", dest="lyrics_file")
            gen.add_argument("--duration", type=int, default=MUSIC_DEFAULT_DURATION)
            gen.add_argument("--continue", dest="continues")
        wait = msub.add_parser("wait", parents=[common], help="等待某次尝试的结果")
        wait.add_argument("session")
        wait.add_argument("attempt")
        wait.add_argument("--out")
        rename = msub.add_parser("rename", parents=[common], help="重命名会话")
        rename.add_argument("session")
        rename.add_argument("name")
        if kind != "image":
            join = msub.add_parser("join", parents=[common], help="把几段合成成片")
            join.add_argument("session")
            join.add_argument("parts", nargs="+")
            join.add_argument("--out")
            join.add_argument("--no-wait", action="store_true")


def _sessions(client: DeskClient, kind: str) -> list[dict]:
    return [s for s in client.get(f"/api/media-sessions/{kind}") if not s.get("corrupt")]


def resolve_session(client: DeskClient, kind: str, ref: str) -> dict:
    ref = ref.strip()
    sessions = _sessions(client, kind)
    if _HEX32.match(ref):
        match = [s for s in sessions if s["id"] == ref]
    else:
        match = [s for s in sessions if (s.get("title") or "").strip() == ref]
    if not match:
        raise CliError(EXIT_NOT_FOUND, "session_not_found",
                       f"没有这个{LABELS[kind]}会话：{ref}。用 lmdesk {kind} sessions 查看")
    if len(match) > 1:
        lines = "\n".join(f"  {s['id']}  {s.get('title')}  {s.get('updated')}" for s in match)
        raise CliError(EXIT_USAGE, "session_ambiguous", f"有多个会话叫「{ref}」，请改用 id：\n{lines}")
    return match[0]


def _outputs_root(client: DeskClient) -> Path:
    return Path(client.get("/api/config")["outputs_root"])


def _prompt_of(kind: str, attempt: dict) -> str | None:
    params = attempt.get("params") or {}
    if attempt.get("op") == "compose":
        return "合成：" + " ".join(params.get("parts") or [])
    return params.get("caption") if kind == "music" else params.get("prompt")


def _attempt_view(kind: str, attempt: dict, root: Path) -> dict:
    output = attempt.get("joined_output") or attempt.get("output")
    return {"id": attempt.get("id"), "status": attempt.get("status"), "prompt": _prompt_of(kind, attempt),
            "params": attempt.get("params"), "base": attempt.get("base"),
            "path": str(root / output) if output else None, "error": attempt.get("error")}


def _session(client: DeskClient, kind: str, session_id: str) -> dict:
    return client.get(f"/api/media-sessions/{kind}/{session_id}")


def _copy_out(src: Path, out: str | None, err) -> Path:
    if not out:
        return src
    target = Path(out)
    if out.endswith(("/", os.sep)) or target.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        target = target / src.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"已覆盖：{target}", file=err)
    shutil.copyfile(src, target)
    return target.resolve()


def _resume_hint(kind: str, session_id: str, attempt_id: str) -> str:
    return (f"已提交：会话 {session_id} 尝试 {attempt_id}"
            f"（中断后可用 lmdesk {kind} wait {session_id} {attempt_id} 继续等待）")


def wait_attempt(client: DeskClient, kind: str, session_id: str, attempt_id: str, job_id: int | None,
                 waiter: Waiter, err, out: str | None = None) -> dict:
    root = _outputs_root(client)
    log_from = 0
    while True:
        attempt = next((a for a in _session(client, kind, session_id).get("attempts") or [] if a.get("id") == attempt_id), None)
        if attempt is None:
            raise CliError(EXIT_NOT_FOUND, "attempt_not_found", f"会话里没有这次尝试：{attempt_id}")
        status = attempt.get("status")
        if status == "done":
            view = _attempt_view(kind, attempt, root)
            if not view["path"]:
                raise CliError(EXIT_ERROR, "output_missing", "尝试已完成但没有输出文件")
            final = _copy_out(Path(view["path"]), out, err)
            params = attempt.get("params") or {}
            return {"text": str(final), "session_id": session_id, "attempt_id": attempt_id, "path": str(final),
                    "seed": params.get("seed"), "params": params}
        if status in ("failed", "cancelled"):
            error = attempt.get("error") or {}
            raise CliError(EXIT_ERROR, f"attempt_{status}", f"生成{'失败' if status == 'failed' else '已取消'}：{error.get('message') or status}")
        if job_id is not None:
            job = client.get("/api/media/job", {"job_id": job_id, "log_from": log_from})
            if job.get("job_id") == job_id:
                log_from = job.get("next_log_from", log_from)
        waiter.pause(f"{LABELS[kind]}生成中")


_GUARDED_SIGNALS = {signal.SIGINT, signal.SIGTERM}


def _hold_signals() -> None:
    # 提交请求在途时到达的信号无法判断作业是否已开始；先挂起，进入续等/取消的处理区再放行（A-25）。
    signal.pthread_sigmask(signal.SIG_BLOCK, _GUARDED_SIGNALS)


def _release_signals() -> None:
    signal.pthread_sigmask(signal.SIG_UNBLOCK, _GUARDED_SIGNALS)


# ---- per-kind request building: `check` is pure argument validation (exit 2), `build` may touch the desk ----

def _parse_size(text: str) -> tuple[int, int]:
    match = _SIZE.match(text or "")
    if not match:
        raise CliError(EXIT_USAGE, "invalid_size", "--size 须形如 1024x1024")
    return int(match.group(1)), int(match.group(2))


def _check_image(args) -> dict:
    width, height = _parse_size(args.size)
    return {"width": width, "height": height}


def _build_image(client, args, checked, session_id):
    body = {"prompt": args.prompt, "width": checked["width"], "height": checked["height"], "steps": args.steps}
    if args.base:
        body["base"] = {"attempt_id": args.base, "strength": args.strength}
    query = {"op": "image", "width": checked["width"], "height": checked["height"], "steps": args.steps}
    return query, body


def _check_video(args) -> dict:
    width, height = _parse_size(args.size)
    if args.frames not in VIDEO_DURATIONS:
        options = "、".join(f"{frames}（{label}）" for frames, label in VIDEO_DURATIONS.items())
        raise CliError(EXIT_USAGE, "invalid_frames", f"--frames 只能取：{options}")
    checked = {"width": width, "height": height, "first_frame": None}
    if args.continues and args.first_frame:
        raise CliError(EXIT_USAGE, "continue_conflict", "--continue 与 --first-frame 不能同时使用")
    spec = args.first_frame
    if spec is None:
        return checked
    if spec.startswith("image:"):
        session, _, attempt = spec[len("image:"):].rpartition(":")
        if not session.strip() or not attempt.strip():
            raise CliError(EXIT_USAGE, "invalid_first_frame", "--first-frame 引用须形如 image:<图片会话>:<尝试id>")
        checked["first_frame"] = ("ref", session, attempt.strip())
        return checked
    path = Path(spec)
    if not path.is_file():
        raise CliError(EXIT_USAGE, "invalid_first_frame", f"首帧文件不存在：{spec}")
    if path.suffix.lower() not in FIRST_FRAME_EXTENSIONS:
        raise CliError(EXIT_USAGE, "invalid_first_frame", "首帧只支持 png、jpg、jpeg、webp")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise CliError(EXIT_USAGE, "invalid_first_frame", "首帧文件不能超过 32 MB")
    checked["first_frame"] = ("file", path)
    return checked


def _build_video(client, args, checked, session_id):
    body = {"prompt": args.prompt, "width": checked["width"], "height": checked["height"],
            "frames": args.frames, "steps": args.steps}
    if args.continues:
        body["continues"] = args.continues
    first = checked["first_frame"]
    if first and first[0] == "file":
        try:
            uploaded = client.post("/api/media/inputs", {"name": first[1].name,
                                                          "data": base64.b64encode(first[1].read_bytes()).decode("ascii")})
        except HttpError as exc:
            raise CliError(EXIT_USAGE if exc.status == 400 else EXIT_ERROR, exc.code, exc.message) from None
        body.update(mode="image", first_frame=uploaded["id"])
    elif first:
        image = resolve_session(client, "image", first[1])
        body.update(mode="image", refs={"first_frame": {"kind": "image", "session_id": image["id"], "attempt_id": first[2]}})
    query = {"op": "video", "width": checked["width"], "height": checked["height"],
             "frames": args.frames, "steps": args.steps}
    return query, body


def _check_music(args) -> dict:
    if bool(args.lyrics) == bool(args.lyrics_file):
        raise CliError(EXIT_USAGE, "lyrics_required", "Music 3 必须有歌词：--lyrics 与 --lyrics-file 二选一")
    lyrics = args.lyrics
    if args.lyrics_file:
        try:
            lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CliError(EXIT_USAGE, "invalid_lyrics_file", f"读不了歌词文件：{args.lyrics_file}（{exc}）") from None
    return {"lyrics": lyrics}


def _build_music(client, args, checked, session_id):
    body = {"caption": args.prompt, "lyrics": checked["lyrics"], "duration": args.duration}
    if args.continues:
        body["continues"] = args.continues
    return {"op": "music", "duration": args.duration}, body


_CHECK = {"image": _check_image, "video": _check_video, "music": _check_music}
_BUILD = {"image": _build_image, "video": _build_video, "music": _build_music}


def _compose_snapshot(client: DeskClient) -> Snapshot:
    # compose is ffmpeg only and skips the arbiter, so there is no precheck to ask for (B-02).
    llm = _llm(client)
    state = llm.get("state") or {}
    return Snapshot(llm_status=state.get("status") or "idle",
                    llm_model=state.get("model_key") if state.get("status") == "loaded" else None,
                    active_chats=int(llm.get("active_chats") or 0), ui_chat_recent=bool(llm.get("ui_chat_recent")),
                    media_running=client.get("/api/media/job").get("status") == "running", precheck=None)


def _run_job(client: DeskClient, kind: str, args, waiter: Waiter, err, session_id: str, op: str,
             query: dict | None, path: str, body: dict) -> dict:
    label = LABELS[kind]
    while True:
        snap = _compose_snapshot(client) if query is None else snapshot(client, op, None, query)
        decision = decide(op, None, snap)
        if decision.action == "wait":
            waiter.pause(decision.reason)
            continue
        _hold_signals()
        try:
            job = client.post(path, body)
            break
        except HttpError as exc:
            _release_signals()
            if exc.code in RETRY_CODES:
                waiter.pause(f"{label}任务槽位被占用")
                continue
            if exc.code == "insufficient_memory":
                raise CliError(EXIT_MEMORY, exc.code, f"{exc.message}。确认后可加 --force 重试") from None
            if exc.code == "session_not_found" or exc.status == 404:
                raise CliError(EXIT_NOT_FOUND, exc.code, exc.message) from None
            if exc.status == 400:
                raise CliError(EXIT_USAGE, exc.code, exc.message) from None
            raise CliError(EXIT_ERROR, exc.code, exc.message) from None
        except BaseException:
            _release_signals()
            raise
    job_id, attempt_id = job.get("job_id"), job.get("attempt_id")
    if job.get("status") != "running" or not attempt_id:
        _release_signals()
        error = job.get("error") or {}
        raise CliError(EXIT_ERROR, error.get("code") or "start_failed", f"{label}任务没能开始：{error.get('message')}")
    hint = _resume_hint(kind, session_id, attempt_id)
    print(hint, file=err, flush=True)
    if args.no_wait:
        _release_signals()
        return {"text": attempt_id, "session_id": session_id, "attempt_id": attempt_id}
    try:
        _release_signals()
        return wait_attempt(client, kind, session_id, attempt_id, job_id, waiter, err, args.out)
    except Interrupted as exc:
        if exc.signum == signal.SIGINT:
            try:
                client.post("/api/media/cancel", {"job_id": job_id, **AGENT})
            except (HttpError, Unreachable):
                pass
            raise CliError(EXIT_TIMEOUT, "interrupted", "已中断并取消这次生成") from None
        raise CliError(EXIT_TIMEOUT, "interrupted", "已中断，生成仍在台面继续", hint=hint) from None
    except CliError as exc:
        if exc.exit_code == EXIT_TIMEOUT:
            raise CliError(EXIT_TIMEOUT, exc.code, exc.message + "，生成仍在台面继续", hint=hint) from None
        raise
    except Unreachable:
        raise CliError(EXIT_ERROR, "desk_gone", "台面已退出，生成结果可能未完成", hint=hint) from None


def run_gen(client: DeskClient, kind: str, args, waiter: Waiter, err) -> dict:
    checked = _CHECK[kind](args)
    session_id = resolve_session(client, kind, args.session)["id"]
    query, body = _BUILD[kind](client, args, checked, session_id)
    if args.seed is not None:
        body["seed"] = args.seed
    body.update(session_id=session_id, force=bool(args.force), **AGENT)
    return _run_job(client, kind, args, waiter, err, session_id, kind, query, ENDPOINTS[kind], body)


def run_join(client: DeskClient, kind: str, args, waiter: Waiter, err) -> dict:
    if len(args.parts) < 2:
        raise CliError(EXIT_USAGE, "join_needs_two", "至少要两段才能合成")
    session_id = resolve_session(client, kind, args.session)["id"]
    body = {"kind": kind, "session_id": session_id, "parts": list(args.parts), **AGENT}
    return _run_job(client, kind, args, waiter, err, session_id, "compose", None, "/api/media/compose", body)


def dispatch(args, client: DeskClient, waiter: Waiter, err) -> dict:
    kind, cmd = args.command, args.media_command
    label = LABELS[kind]
    if cmd == "sessions":
        sessions = _sessions(client, kind)
        text = "\n".join(f"{s['id']}\t{s.get('title')}\t{s.get('updated')}" for s in sessions) or f"（还没有{label}会话）"
        return {"text": text, "sessions": sessions}
    if cmd == "new":
        created = client.post(f"/api/media-sessions/{kind}", {})
        named = client.patch(f"/api/media-sessions/{kind}/{created['id']}", {"title": args.name})
        return {"text": named["id"], "id": named["id"], "title": named.get("title")}
    if cmd == "rename":
        session_id = resolve_session(client, kind, args.session)["id"]
        named = client.patch(f"/api/media-sessions/{kind}/{session_id}", {"title": args.name})
        return {"text": named.get("title"), "id": session_id, "title": named.get("title")}
    if cmd == "show":
        summary = resolve_session(client, kind, args.session)
        root = _outputs_root(client)
        attempts = [_attempt_view(kind, a, root) for a in _session(client, kind, summary["id"]).get("attempts") or []]
        text = "\n".join(f"{a['id']}\t{a['status']}\t{a['path'] or ''}\t{a['prompt'] or ''}" for a in attempts) or "（这个会话还没有尝试）"
        return {"text": text, "id": summary["id"], "title": summary.get("title"), "attempts": attempts}
    if cmd == "gen":
        return run_gen(client, kind, args, waiter, err)
    if cmd == "join":
        return run_join(client, kind, args, waiter, err)
    if cmd == "wait":
        session_id = resolve_session(client, kind, args.session)["id"]
        try:
            return wait_attempt(client, kind, session_id, args.attempt, None, waiter, err, args.out)
        except Unreachable:
            raise CliError(EXIT_ERROR, "desk_gone", "台面已退出", hint=_resume_hint(kind, session_id, args.attempt)) from None
    raise CliError(EXIT_USAGE, "unknown_command", cmd)
