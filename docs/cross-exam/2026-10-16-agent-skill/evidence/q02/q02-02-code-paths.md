# 四种情况代码路径（desk/agent_cli/）
errors.py:4 EXIT_TIMEOUT=3
cli.py:60-66 _fail: 若 exc.hint 则先 print(hint) 到 stderr，再 print(exc.message) 到 stderr
waiter.py:35,43 pause 超时 -> CliError(3,"timeout",f"等待超时（{reason}）")
media.py:140-142 _resume_hint = "已提交：会话 {sid} 尝试 {aid}（中断后可用 lmdesk {kind} wait {sid} {aid} 继续等待）"; 348 提交后即打印到 stderr
(1) 生成超时: media.py:169 waiter.pause(f"{LABELS[kind]}生成中") -> 363-365 CliError(3, "timeout", "等待超时（<标签>生成中），生成仍在台面继续", hint=hint) -> cli.py _fail: stderr 先 hint 行(含 lmdesk <kind> wait) 再 message。台面任务继续(未发 cancel)。
(2) SIGINT: cli.py:81-85 handler raise Interrupted; media.py:355-361 signum==SIGINT -> post /api/media/cancel(吞 HttpError/Unreachable) -> CliError(3,"interrupted","已中断并取消这次生成") 无 hint；stderr 只有该句(此前提交时已打印过一次续等提示 media.py:348)。任务被取消。
(3) SIGTERM: media.py:362 CliError(3,"interrupted","已中断，生成仍在台面继续",hint=hint) -> stderr: 续等提示行 + "已中断，生成仍在台面继续"。任务继续。
(4) ask 排不上队: chat.py:123 waiter.pause(decision.reason)（或 chat.py:99/112/138 其他 pause）-> waiter.py:35/43 CliError(3,"timeout","等待超时（<decision.reason>）")，无 hint，无「wait」提示；chat.py 无 cancel/任务概念。stderr 另可有 waiter.py:41 每15s「等待中：<reason>（已等 Ns）」。
补充: ask 等待中收到信号（非题问）: cli.py:98-99 -> exit 3 "已中断"，无 hint。ask 发出 /api/llm/chat 后超时由 client.post timeout=max(30,remaining) 控制(chat.py:135)，超时表现未读 client.py 全文确认。
补充: 媒体提交阶段(_submit)超时(媒体排不上队) 走 waiter.pause 抛 timeout，media.py:338-340 仅 discard，无 hint(此时尚无 attempt)。
