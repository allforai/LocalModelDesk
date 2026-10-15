"""Image sessions for agents: sessions/new/show/gen/wait/rename (A-10/A-11/A-14..A-16/A-25..A-27)."""
from __future__ import annotations

import re
import shutil
import signal
from pathlib import Path

from .chat import AGENT, snapshot
from .client import DeskClient, HttpError, Unreachable
from .decide import RETRY_CODES, decide
from .errors import (CliError, EXIT_ERROR, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_TIMEOUT, EXIT_USAGE, Interrupted)
from .waiter import Waiter

KIND = "image"
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_SIZE = re.compile(r"^(\d+)x(\d+)$")


def add_parsers(sub, common) -> None:
    image = sub.add_parser("image", help="本地生图与图片会话")
    isub = image.add_subparsers(dest="image_command", required=True)
    isub.add_parser("sessions", parents=[common], help="列出图片会话")
    new = isub.add_parser("new", parents=[common], help="新建图片会话")
    new.add_argument("name")
    show = isub.add_parser("show", parents=[common], help="查看会话里的尝试")
    show.add_argument("session")
    gen = isub.add_parser("gen", parents=[common], help="在会话里生成一张图")
    gen.add_argument("session")
    gen.add_argument("prompt")
    gen.add_argument("--size", default="1024x1024")
    gen.add_argument("--steps", type=int, default=40)
    gen.add_argument("--seed", type=int)
    gen.add_argument("--from", dest="base")
    gen.add_argument("--strength", type=float, default=0.6)
    gen.add_argument("--out")
    gen.add_argument("--force", action="store_true")
    gen.add_argument("--no-wait", action="store_true")
    wait = isub.add_parser("wait", parents=[common], help="等待某次尝试的结果")
    wait.add_argument("session")
    wait.add_argument("attempt")
    wait.add_argument("--out")
    rename = isub.add_parser("rename", parents=[common], help="重命名会话")
    rename.add_argument("session")
    rename.add_argument("name")


def _sessions(client: DeskClient) -> list[dict]:
    return [s for s in client.get(f"/api/media-sessions/{KIND}") if not s.get("corrupt")]


def resolve_session(client: DeskClient, ref: str) -> dict:
    ref = ref.strip()
    sessions = _sessions(client)
    if _HEX32.match(ref):
        match = [s for s in sessions if s["id"] == ref]
    else:
        match = [s for s in sessions if (s.get("title") or "").strip() == ref]
    if not match:
        raise CliError(EXIT_NOT_FOUND, "session_not_found", f"没有这个图片会话：{ref}。用 lmdesk image sessions 查看")
    if len(match) > 1:
        lines = "\n".join(f"  {s['id']}  {s.get('title')}  {s.get('updated')}" for s in match)
        raise CliError(EXIT_USAGE, "session_ambiguous", f"有多个会话叫「{ref}」，请改用 id：\n{lines}")
    return match[0]


def _outputs_root(client: DeskClient) -> Path:
    return Path(client.get("/api/config")["outputs_root"])


def _attempt_view(attempt: dict, root: Path) -> dict:
    output = attempt.get("joined_output") or attempt.get("output")
    return {"id": attempt.get("id"), "status": attempt.get("status"), "prompt": (attempt.get("params") or {}).get("prompt"),
            "params": attempt.get("params"), "base": attempt.get("base"),
            "path": str(root / output) if output else None, "error": attempt.get("error")}


def _session(client: DeskClient, session_id: str) -> dict:
    return client.get(f"/api/media-sessions/{KIND}/{session_id}")


def _copy_out(src: Path, out: str | None, err) -> Path:
    if not out:
        return src
    target = Path(out)
    if target.is_dir():
        target = target / src.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"已覆盖：{target}", file=err)
    shutil.copyfile(src, target)
    return target.resolve()


def _resume_hint(session_id: str, attempt_id: str) -> str:
    return (f"已提交：会话 {session_id} 尝试 {attempt_id}"
            f"（中断后可用 lmdesk image wait {session_id} {attempt_id} 继续等待）")


def wait_attempt(client: DeskClient, session_id: str, attempt_id: str, job_id: int | None, waiter: Waiter,
                 err, out: str | None = None) -> dict:
    root = _outputs_root(client)
    log_from = 0
    while True:
        attempt = next((a for a in _session(client, session_id).get("attempts") or [] if a.get("id") == attempt_id), None)
        if attempt is None:
            raise CliError(EXIT_NOT_FOUND, "attempt_not_found", f"会话里没有这次尝试：{attempt_id}")
        status = attempt.get("status")
        if status == "done":
            view = _attempt_view(attempt, root)
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
        waiter.pause("图片生成中")


def _submit(client: DeskClient, args, session_id: str, width: int, height: int) -> dict:
    body = {"session_id": session_id, "prompt": args.prompt, "width": width, "height": height, "steps": args.steps,
            "force": bool(args.force), **AGENT}
    if args.seed is not None:
        body["seed"] = args.seed
    if args.base:
        body["base"] = {"attempt_id": args.base, "strength": args.strength}
    return client.post("/api/media/image", body)


def run_gen(client: DeskClient, args, waiter: Waiter, err) -> dict:
    match = _SIZE.match(args.size or "")
    if not match:
        raise CliError(EXIT_USAGE, "invalid_size", "--size 须形如 1024x1024")
    width, height = int(match.group(1)), int(match.group(2))
    session_id = resolve_session(client, args.session)["id"]
    query = {"op": "image", "width": width, "height": height, "steps": args.steps}
    while True:
        decision = decide("image", None, snapshot(client, "image", None, query))
        if decision.action == "wait":
            waiter.pause(decision.reason)
            continue
        try:
            job = _submit(client, args, session_id, width, height)
            break
        except HttpError as exc:
            if exc.code in RETRY_CODES:
                waiter.pause("图片任务槽位被占用")
                continue
            if exc.code == "insufficient_memory":
                raise CliError(EXIT_MEMORY, exc.code, f"{exc.message}。确认后可加 --force 重试") from None
            if exc.code == "session_not_found" or exc.status == 404:
                raise CliError(EXIT_NOT_FOUND, exc.code, exc.message) from None
            if exc.status == 400:
                raise CliError(EXIT_USAGE, exc.code, exc.message) from None
            raise CliError(EXIT_ERROR, exc.code, exc.message) from None
    job_id, attempt_id = job.get("job_id"), job.get("attempt_id")
    if job.get("status") != "running" or not attempt_id:
        error = job.get("error") or {}
        raise CliError(EXIT_ERROR, error.get("code") or "start_failed", f"生图没能开始：{error.get('message')}")
    hint = _resume_hint(session_id, attempt_id)
    print(hint, file=err, flush=True)
    if args.no_wait:
        return {"text": attempt_id, "session_id": session_id, "attempt_id": attempt_id}
    try:
        return wait_attempt(client, session_id, attempt_id, job_id, waiter, err, args.out)
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


def dispatch(args, client: DeskClient, waiter: Waiter, err) -> dict:
    cmd = args.image_command
    if cmd == "sessions":
        sessions = _sessions(client)
        text = "\n".join(f"{s['id']}\t{s.get('title')}\t{s.get('updated')}" for s in sessions) or "（还没有图片会话）"
        return {"text": text, "sessions": sessions}
    if cmd == "new":
        created = client.post(f"/api/media-sessions/{KIND}", {})
        named = client.patch(f"/api/media-sessions/{KIND}/{created['id']}", {"title": args.name})
        return {"text": named["id"], "id": named["id"], "title": named.get("title")}
    if cmd == "rename":
        session_id = resolve_session(client, args.session)["id"]
        named = client.patch(f"/api/media-sessions/{KIND}/{session_id}", {"title": args.name})
        return {"text": named.get("title"), "id": session_id, "title": named.get("title")}
    if cmd == "show":
        summary = resolve_session(client, args.session)
        root = _outputs_root(client)
        attempts = [_attempt_view(a, root) for a in _session(client, summary["id"]).get("attempts") or []]
        text = "\n".join(f"{a['id']}\t{a['status']}\t{a['path'] or ''}\t{a['prompt'] or ''}" for a in attempts) or "（这个会话还没有尝试）"
        return {"text": text, "id": summary["id"], "title": summary.get("title"), "attempts": attempts}
    if cmd == "gen":
        return run_gen(client, args, waiter, err)
    if cmd == "wait":
        session_id = resolve_session(client, args.session)["id"]
        try:
            return wait_attempt(client, session_id, args.attempt, None, waiter, err, args.out)
        except Unreachable:
            raise CliError(EXIT_ERROR, "desk_gone", "台面已退出", hint=_resume_hint(session_id, args.attempt)) from None
    raise CliError(EXIT_USAGE, "unknown_command", cmd)
