"""ask 读管道输入：不在没人写的管道上一直等下去（A-12，cross-exam G8）。"""
from __future__ import annotations

import os
import select
import time

from .errors import CliError, EXIT_TIMEOUT, EXIT_USAGE

IDLE_S = 5.0


def read_piped(stdin, *, deadline_s: float, err, idle_s: float = IDLE_S, clock=time.monotonic) -> str:
    """stdin 不是终端时读完它。

    - idle_s 内既没有数据也没有结束：按没有输入处理，并在 stderr 说一句。agent 的执行器有时把一个
      不关闭的管道接在 stdin 上，直接 read() 会永远等下去，连 --timeout 都管不到。
    - 开始有数据后读到结束为止，但不超过 deadline_s（剩余的 --timeout）。
    """
    if stdin is None:
        return ""
    try:
        if stdin.isatty():
            return ""
        fd = stdin.fileno()
    except (AttributeError, ValueError, OSError):
        # 没有文件描述符（测试里的 StringIO 之类）：不会阻塞，直接读。
        return stdin.read() if hasattr(stdin, "read") else ""
    if not select.select([fd], [], [], idle_s)[0]:
        print(f"stdin {idle_s:g} 秒内没有数据，按没有输入处理", file=err, flush=True)
        return ""
    end = clock() + deadline_s
    chunks: list[bytes] = []
    while True:
        data = os.read(fd, 65536)
        if not data:
            break
        chunks.append(data)
        left = end - clock()
        if left <= 0 or not select.select([fd], [], [], left)[0]:
            raise CliError(EXIT_TIMEOUT, "stdin_timeout", "stdin 一直没有结束，等待超时")
    try:
        return b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError:
        raise CliError(EXIT_USAGE, "stdin_not_utf8", "stdin 不是 UTF-8 文本，请先转成 UTF-8") from None
