"""status / models / ask (A-12, A-21, A-22)."""
from __future__ import annotations

import os
from pathlib import Path

from .client import DeskClient, HttpError
from .decide import RETRY_CODES, Snapshot, decide
from .errors import CliError, EXIT_ERROR, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_USAGE
from .version import read_version, resources_root
from .waiter import Waiter

AGENT = {"origin": "agent"}
# 模型已加载、要的就是它，对话却连续被拒这么多次：说明台面那边卡住了，重试改变不了什么（P2）。
STUCK_LIMIT = 3


def _llm(client: DeskClient) -> dict:
    return client.get("/api/llm/status")


def snapshot(client: DeskClient, op: str, want_model: str | None, precheck_query: dict) -> Snapshot:
    llm = _llm(client)
    state = llm.get("state") or {}
    job = client.get("/api/media/job")
    try:
        precheck = client.get("/api/agent/precheck", precheck_query)
    except HttpError as exc:
        if exc.status == 404:
            raise CliError(EXIT_NOT_FOUND, exc.code, exc.message) from None
        raise
    return Snapshot(
        llm_status=state.get("status") or "idle",
        llm_model=state.get("model_key") if state.get("status") == "loaded" else None,
        active_chats=int(llm.get("active_chats") or 0),
        ui_chat_recent=bool(llm.get("ui_chat_recent")),
        media_running=job.get("status") == "running",
        precheck=precheck,
    )


def chat_models(client: DeskClient) -> list[dict]:
    return [m for m in client.get("/api/resources/catalog") if m.get("group") == "chat"]


def run_status(client: DeskClient) -> dict:
    llm = _llm(client)
    state, job, desk = llm.get("state") or {}, client.get("/api/media/job"), client.get("/api/state")
    return {
        "desk": {"reachable": True, "url": client.base_url},
        "llm": {"status": state.get("status"), "model": state.get("model_key"),
                "loaded_by": llm.get("loaded_by"), "active_chats": llm.get("active_chats", 0)},
        "media": {"running": job.get("status") == "running", "kind": job.get("kind")},
        "version": {"cli": cli_version(), "desk": desk.get("version")},
    }


def cli_version() -> str:
    return os.environ.get("LMDESK_FAKE_VERSION") or read_version(resources_root())


def run_models(client: DeskClient) -> list[dict]:
    loaded = (_llm(client).get("state") or {})
    resident = loaded.get("model_key") if loaded.get("status") == "loaded" else None
    return [{"key": m["key"], "name": m.get("name"), "gb": m.get("gb"), "group": m.get("group"),
             "loaded": m["key"] == resident, "fit": (m.get("fit") or {}).get("level")} for m in chat_models(client)]


def _message(question: str, files: list[str], stdin_text: str) -> str:
    parts = [question]
    if stdin_text and stdin_text.strip():
        parts.append(stdin_text)
    for name in files:
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(EXIT_USAGE, "file_unreadable", f"读不了文件 {name}：{exc.strerror}") from None
        parts.append(f"--- {path.name} ---\n{text}")
    return "\n\n".join(parts)


def _pick_model(client: DeskClient, model: str | None) -> str:
    keys = [m["key"] for m in chat_models(client)]
    if model:
        if model not in keys:
            raise CliError(EXIT_NOT_FOUND, "model_not_found", f"没有这个对话模型：{model}。可用：{', '.join(keys)}")
        return model
    state = _llm(client).get("state") or {}
    if state.get("status") == "loaded" and state.get("model_key"):
        return state["model_key"]
    raise CliError(EXIT_NOT_FOUND, "no_model_selected",
                   f"没有指定模型，台面当前也没有加载。请用 --model 指定，可用：{', '.join(keys)}")


def _swap(client: DeskClient, key: str, waiter: Waiter) -> None:
    try:
        client.post("/api/llm/load", {"key": key, **AGENT})
    except HttpError as exc:
        if exc.code in RETRY_CODES or exc.code == "insufficient_budget":
            waiter.pause("等待加载模型")
            return
        raise CliError(EXIT_ERROR, exc.code, f"加载模型失败：{exc.message}") from None
    waiter.reset()
    while True:
        state = _llm(client).get("state") or {}
        if state.get("status") == "loaded":
            return
        if state.get("status") == "error":
            error = state.get("error") or {}
            raise CliError(EXIT_ERROR, error.get("code") or "load_failed", f"加载模型失败：{error.get('message')}")
        if state.get("status") != "loading":
            return
        waiter.pause(f"正在加载 {key}")


def run_ask(client: DeskClient, *, question: str, model: str | None, system: str | None, files: list[str],
            stdin_text: str, max_tokens: int | None, waiter: Waiter) -> dict:
    content = _message(question, files, stdin_text)
    want = _pick_model(client, model)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    refused = 0
    while True:
        decision = decide("chat", want, snapshot(client, "chat", want, {"op": "chat", "model": want}))
        if decision.action == "wait":
            refused = 0
            waiter.pause(decision.reason)
            continue
        if decision.action == "fail":
            raise CliError(decision.exit_code or EXIT_MEMORY, "insufficient_budget", decision.reason)
        if decision.action == "swap":
            refused = 0
            _swap(client, want, waiter)
            continue
        body = {"messages": messages, "model": want, **AGENT}
        if max_tokens:
            body["max_tokens"] = max_tokens
        try:
            waiter.note("模型正在回答")
            # 非流式对话要等整段回答生成完，本地模型常常超过客户端默认的 30s；用剩余的 --timeout 兜住。
            result = client.post("/api/llm/chat", body, timeout=max(30.0, waiter.remaining()))
        except HttpError as exc:
            if exc.code in RETRY_CODES:
                refused += 1
                if refused >= STUCK_LIMIT:
                    raise CliError(EXIT_ERROR, exc.code, f"台面连续 {refused} 次拒绝对话：{exc.message}") from None
                waiter.pause("模型被换走了，重新排队")
                continue
            raise CliError(EXIT_ERROR, exc.code, exc.message) from None
        return {"content": result.get("content") or "", "model": result.get("model"), "usage": result.get("usage")}
