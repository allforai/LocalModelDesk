"""lmdesk entry: argument parsing, output (text or --json), signals, exit codes (A-11/A-13/A-25)."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path

from . import chat
from .client import HttpError, Unreachable
from .discovery import SANDBOX_MESSAGE, connect
from .errors import CliError, EXIT_ERROR, EXIT_OK, EXIT_SANDBOX, EXIT_TIMEOUT, EXIT_USAGE, Interrupted
from .waiter import Waiter


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lmdesk", description="本机模型台面（LocalModelDesk）的命令行")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="stdout 输出单个 JSON 对象")
    common.add_argument("--timeout", type=float, default=1800.0, help="总等待秒数，默认 1800")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status", parents=[common], help="台面状态")
    sub.add_parser("models", parents=[common], help="本机对话模型")
    ask = sub.add_parser("ask", parents=[common], help="问本地对话模型（一次性）")
    ask.add_argument("question")
    ask.add_argument("--model")
    ask.add_argument("--system")
    ask.add_argument("--file", action="append", default=[])
    ask.add_argument("--max-tokens", type=int)
    from . import images
    images.add_parsers(sub, common)
    return p


def _emit(result, args, out) -> None:
    if args.json:
        if isinstance(result, dict) and "text" in result:
            result = {k: v for k, v in result.items() if k != "text"}
        print(json.dumps(result, ensure_ascii=False), file=out)
        return
    if isinstance(result, dict) and "text" in result:
        print(result["text"], file=out)
        return
    if args.command == "ask":
        print(result["content"], file=out)
    elif args.command == "status":
        llm, media, version = result["llm"], result["media"], result["version"]
        print(f"台面：{result['desk']['url']}\n对话模型：{llm['status']} {llm['model'] or ''}\n"
              f"媒体任务：{'进行中' if media['running'] else '空闲'}\n版本：lmdesk {version['cli']} / 台面 {version['desk']}", file=out)
    elif args.command == "models":
        for m in result:
            mark = "\t已加载" if m["loaded"] else ""
            print(f"{m['key']}\t{m['name']}\t{m['gb']} GB{mark}", file=out)
    else:
        print(json.dumps(result, ensure_ascii=False), file=out)


def _fail(exc: CliError, args, out, err) -> int:
    if exc.hint:
        print(exc.hint, file=err)
    print(exc.message, file=err)
    if getattr(args, "json", False):
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}, ensure_ascii=False), file=out)
    return exc.exit_code


def main(argv=None, *, env=os.environ, stdin=sys.stdin, out=sys.stdout, err=sys.stderr, here: Path | None = None,
         connect_fn=None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return EXIT_OK
        if "--json" in (argv if argv is not None else sys.argv[1:]):
            print(json.dumps({"error": {"code": "usage", "message": "参数错误，见 stderr"}}, ensure_ascii=False), file=out)
        return EXIT_USAGE

    def on_signal(signum, _frame):
        raise Interrupted(signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, on_signal)
    try:
        client = (connect_fn or connect)(env, here=here or Path(__file__))
        desk_version = client.get("/api/state").get("version")
        cli_version = chat.cli_version()
        if desk_version and desk_version != cli_version:
            print(f"注意：版本不一致（lmdesk {cli_version}，台面 {desk_version}）", file=err)
        waiter = Waiter(args.timeout, err=err)
        result = _dispatch(args, client, waiter, stdin, err)
        _emit(result, args, out)
        return EXIT_OK
    except CliError as exc:
        return _fail(exc, args, out, err)
    except Interrupted:
        return _fail(CliError(EXIT_TIMEOUT, "interrupted", "已中断"), args, out, err)
    except Unreachable as exc:
        if exc.kind == "sandbox":
            return _fail(CliError(EXIT_SANDBOX, "sandboxed", SANDBOX_MESSAGE), args, out, err)
        return _fail(CliError(EXIT_ERROR, "desk_gone", f"台面连接中断：{exc.detail}"), args, out, err)
    except HttpError as exc:
        return _fail(CliError(EXIT_ERROR, exc.code, exc.message), args, out, err)


def _read_stdin(stdin) -> str:
    try:
        if stdin is None or stdin.isatty():
            return ""
    except (AttributeError, ValueError):
        return ""
    return stdin.read()


def _dispatch(args, client, waiter, stdin, err):
    if args.command == "status":
        return chat.run_status(client)
    if args.command == "models":
        return chat.run_models(client) if not args.json else {"models": chat.run_models(client)}
    if args.command == "ask":
        return chat.run_ask(client, question=args.question, model=args.model, system=args.system, files=args.file,
                            stdin_text=_read_stdin(stdin), max_tokens=args.max_tokens, waiter=waiter)
    from . import images
    return images.dispatch(args, client, waiter, err)
