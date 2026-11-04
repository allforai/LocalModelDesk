# grep memory_warning in agent_cli
exit=1

# grep memory|warn
/Users/aa/LocalModelDesk/desk/agent_cli/media.py:320:            if exc.code == "insufficient_memory":

## chat.py:20-37
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
## decide.py:33-72
def _releasable(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and bool(precheck.get("release"))


def _too_big(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and not precheck.get("release")


def _evicts_llm(precheck: dict | None) -> bool:
    return bool(precheck) and any(item.get("kind") == "llm" for item in precheck.get("release") or [])


def decide(op: str, want_model: str | None, snap: Snapshot) -> Decision:
    if op == "compose":
        # ffmpeg only, no arbiter (B-02): only a running media job makes it wait; no precheck is read.
        return _wait("媒体任务进行中") if snap.media_running else Decision("submit", "")
    if snap.llm_status == "loading":
        return _wait("正在加载模型")
    if op == "chat":
        if snap.llm_status == "loaded" and snap.llm_model == want_model:
            return Decision("submit", "")
        if snap.media_running:
            return _wait("媒体任务进行中")
        if snap.active_chats > 0:
            return _wait("有对话正在进行")
        if snap.ui_chat_recent and snap.llm_status == "loaded":
            return _wait("台面里最近在用当前模型对话")
        if _releasable(snap.precheck):
            return _wait("内存被占用，等待释放")
        if _too_big(snap.precheck):
            message = (snap.precheck.get("reason") or {}).get("message") or "内存不足"
            return Decision("fail", f"{message}。对话模型不能强制加载，请换一个更小的模型", EXIT_MEMORY)
        return Decision("swap", "")
    if snap.media_running:
        return _wait("媒体任务进行中")
    if snap.active_chats > 0:
        return _wait("有对话正在进行")
    if _evicts_llm(snap.precheck) and snap.ui_chat_recent:
        return _wait("生成需要卸掉对话模型，但台面里最近在用它")
    if _releasable(snap.precheck):
## media.py:310-330
            uploaded.append(_upload_first_frame(client, upload))  # once, only when about to submit
            body["mode"], body["first_frame"] = "image", uploaded[0]
        _hold_signals()
        try:
            return client.post(path, body)
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

