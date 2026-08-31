# 实施计划：media（H3 视频 + Music 3 歌曲作业运行器）

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-media-spec.md`
**design** `docs/superpowers/specs/2026-08-31-media-design.md`
**覆盖需求** R-media-01 … R-media-07
**方法** 严格 TDD：每个任务 先写失败测试 → 跑一遍确认失败 → 实现 → 跑通 → commit。

## 交付物

```
desk/media/
  __init__.py       # 导出 MediaService / MediaError
  commands.py       # H3 / Music 命令行构造唯一定义点（纯函数，零 IO）
  music3_cli.py     # Music 3 管线子进程入口（取代根目录 run-music3.py）
  executor.py       # 可替换子进程执行器接口 + SubprocessExecutor 真实现
  service.py        # MediaService：状态机、作业线程、取消、历史、事件
  routes.py         # HTTP 适配：路由表交装配点挂载
tests/
  media_fakes.py            # FakeExecutor / FakeArbiter / FakeHistory / 固定 clock
  test_media_commands.py
  test_media_executor.py
  test_media_music3_cli.py
  test_media_service.py
  test_media_routes.py
```

## 消费的兄弟合同（全部构造注入，测试用假件）

| 接口 | 形状（来自兄弟设计，Phase 1.2 已对齐） |
|---|---|
| `api:resolvePaths` / `data:pathRoots` | 对象属性：`outputs_root`、`models_root`、`mlx_h3_cmd`（argv 前缀 tuple）、`mlx_h3_env`、`music_python`、`music_env`、`media_cli_dir` |
| foundation `probe_capabilities` | dict：键 `mlx_h3` / `music_runtime`，值有 `.present` / `.detail` |
| `api:listCatalog` | 条目有 `.key`（`h3`/`music3`）与 `.relpath`；模型根 = `models_root / relpath` |
| `api:canStartHeavy(kind)` | `{"ok": bool, "reason": {"code","message"} \| None}` |
| `api:acquireHeavy(kind, label)` | 成功 `{"ok": True, "token": str}`；失败 `{"ok": False, "reason": {...}}` |
| `api:releaseHeavy(token)` | `{"ok": bool}`；异常只记日志 |
| `api:appendHistory` / `data:historyEntry` | library 的 `HistoryStore.append(entry)`；media 传 `kind/status/params/output/duration_s/error`，`id`/`ts` 由 library 补；作业 `error` 终态映射为历史 `failed` |

单测不 import 任何兄弟包：假件按上表形状构造（`types.SimpleNamespace` 足够），
所以 media 全部单测在兄弟模块尚未落地时也能跑。跨模块排期由 `requires` 字段驱动。

## 运行前提

- 验收统一 `cd /Users/aa/LocalModelDesk && python3 -m pytest <file> -q`。
  `python3 -m pytest` 把仓库根放进 `sys.path`，`desk` 以（命名空间或常规）包解析，
  不依赖 foundation 是否已创建 `desk/__init__.py`。
- 不触碰真实权重、真实 outputs、8767 端口；一切文件 IO 用 `tmp_path`。
- `desk/` 内不出现 `raise SystemExit` / `sys.exit(`（foundation 仓库级静态断言）。

---

## T-media-01 H3 命令构造唯一定义点

**需求** R-media-01（census A03/A04 的替代物）
**文件** `desk/media/__init__.py`（新建，空壳）、`desk/media/commands.py`、`tests/test_media_commands.py`

失败测试（先写，先跑红）——逐参数全等比对，参数值实证自 `run-h3.sh` 与 `server.py:_run_h3`：

```python
# tests/test_media_commands.py
"""H3 / Music 命令构造：逐参数全等断言，防两处漂移复发（census A03/A04/A05）。"""
from pathlib import Path

from desk.media.commands import H3_BUDGET_GB, build_h3_command


def test_h3_budget_constant():
    assert H3_BUDGET_GB == 70


def test_build_h3_command_full_argv_equality():
    argv = build_h3_command(
        ("/opt/py/bin/python3.13", "-s", "-c", "from mlx_h3.cli import main; main()"),
        Path("/m/minimax-h3"),
        prompt="rain on a quiet street",
        width=512, height=288, frames=73, steps=10,
        output=Path("/out/h3-20260831-101500.mp4"))
    assert argv == [
        "/opt/py/bin/python3.13", "-s", "-c", "from mlx_h3.cli import main; main()",
        "rain on a quiet street",
        "--tokenizer", "/m/minimax-h3/tokenizer/tokenizer.json",
        "--text-encoder", "/m/minimax-h3/mlx-8bit/te_qwen3vl_a8g32.safetensors",
        "--dit", "/m/minimax-h3/mlx-8bit/dit_fl2va_a8g32.safetensors",
        "--ref-dit", "/m/minimax-h3/mlx-8bit/dit_ref2va_a8g32.safetensors",
        "--video-vae", "/m/minimax-h3/bf16/vae/minimax_h3_video_vae_fp16.safetensors",
        "--audio-vae", "/m/minimax-h3/bf16/vae/minimax_h3_audio_vae_fp32.safetensors",
        "--width", "512",
        "--height", "288",
        "--frames", "73",
        "--steps", "10",
        "--budget", "70",
        "--output", "/out/h3-20260831-101500.mp4",
    ]


def test_build_h3_command_single_element_dev_prefix():
    argv = build_h3_command(("/Users/x/.local/bin/mlx-h3",), Path("/m/minimax-h3"),
                            prompt="p", width=1024, height=576, frames=124, steps=20,
                            output=Path("/out/v.mp4"))
    assert argv[0] == "/Users/x/.local/bin/mlx-h3"
    assert argv[1] == "p"
    assert argv[argv.index("--frames") + 1] == "124"
```

实现：

```python
# desk/media/commands.py
"""H3 / Music 3 命令行构造的唯一定义点（census A03/A04/A05 的替代物）。

纯函数，零 IO，不做存在性检查——只负责「参数怎么拼」，方便逐参数断言。
H3 的六个模型文件相对路径与 --budget 只允许出现在本文件。
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

H3_BUDGET_GB = 70  # mlx-h3 --budget 显存预算；仓库内仅此一处


def build_h3_command(mlx_h3_cmd: Sequence[str], h3_root: Path, *, prompt: str,
                     width: int, height: int, frames: int, steps: int,
                     output: Path) -> list[str]:
    """mlx_h3_cmd 为 foundation data:pathRoots.mlx_h3_cmd 的 argv 前缀
    （dev：单元素可执行；bundle：内嵌解释器 + mlx_h3.cli 入口）。"""
    return [
        *mlx_h3_cmd,
        prompt,
        "--tokenizer", str(h3_root / "tokenizer" / "tokenizer.json"),
        "--text-encoder", str(h3_root / "mlx-8bit" / "te_qwen3vl_a8g32.safetensors"),
        "--dit", str(h3_root / "mlx-8bit" / "dit_fl2va_a8g32.safetensors"),
        "--ref-dit", str(h3_root / "mlx-8bit" / "dit_ref2va_a8g32.safetensors"),
        "--video-vae", str(h3_root / "bf16" / "vae" / "minimax_h3_video_vae_fp16.safetensors"),
        "--audio-vae", str(h3_root / "bf16" / "vae" / "minimax_h3_audio_vae_fp32.safetensors"),
        "--width", str(width),
        "--height", str(height),
        "--frames", str(frames),
        "--steps", str(steps),
        "--budget", str(H3_BUDGET_GB),
        "--output", str(output),
    ]
```

`desk/media/__init__.py` 本任务先落空壳（T-media-05 改为导出 MediaService）：

```python
# desk/media/__init__.py
"""H3 文生视频与 Music 3 文生歌曲的作业运行器。"""
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_commands.py -q`

---

## T-media-02 Music 命令构造 + 单点定义守卫

**需求** R-media-02；census A03/A04 守卫
**文件** `desk/media/commands.py`、`tests/test_media_commands.py`（追加）

失败测试：

```python
# tests/test_media_commands.py 追加
from desk.media.commands import build_music_command

REPO = Path(__file__).resolve().parent.parent


def test_build_music_command_full_argv_equality():
    argv = build_music_command(
        Path("/opt/py/bin/python3.13"),
        Path("/res/desk/media/music3_cli.py"),
        Path("/m/minimax-music3"),
        caption="synthwave night drive", lyrics="la la la", duration=30.0,
        output=Path("/out/music3-20260831-101500.wav"))
    assert argv == [
        "/opt/py/bin/python3.13", "/res/desk/media/music3_cli.py",
        "--root", "/m/minimax-music3",
        "--caption", "synthwave night drive",
        "--lyrics", "la la la",
        "--duration", "30.0",
        "--output", "/out/music3-20260831-101500.wav",
    ]


def test_h3_params_single_definition_point_within_desk():
    """census A03/A04 守卫：desk/ 内 H3 固定参数只允许出现在 desk/media/。
    （根目录旧脚本的删除属清理阶段，由 census 重跑命令另行把守。）"""
    needles = ("--ref-dit", "--video-vae", "--audio-vae",
               "te_qwen3vl", "dit_fl2va", "dit_ref2va", "--budget")
    media_dir = REPO / "desk" / "media"
    hits = []
    for py in (REPO / "desk").rglob("*.py"):
        if media_dir in py.parents:
            continue
        text = py.read_text(encoding="utf-8")
        hits += [(str(py), n) for n in needles if n in text]
    assert hits == []
```

实现（追加到 `commands.py`）：

```python
def build_music_command(music_python: Path, music3_cli: Path, music3_root: Path, *,
                        caption: str, lyrics: str, duration: float,
                        output: Path) -> list[str]:
    """music_python/music3_cli 来自 data:pathRoots（music_python、media_cli_dir）。"""
    return [
        str(music_python), str(music3_cli),
        "--root", str(music3_root),
        "--caption", caption,
        "--lyrics", lyrics,
        "--duration", str(duration),
        "--output", str(output),
    ]
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_commands.py -q`

---

## T-media-03 可替换执行器（真子进程实现）

**需求** R-media-03/07 的基座；spec「子进程执行走可替换的执行器接口」
**文件** `desk/media/executor.py`、`tests/test_media_executor.py`

失败测试（真起秒级 `python -c` 微进程，不碰任何权重/端口）：

```python
# tests/test_media_executor.py
"""SubprocessExecutor：真子进程（python -c 微进程），验证合并输出、退出码、进程组信号。"""
import os
import signal
import sys
import time

from desk.media.executor import SubprocessExecutor


def _wait_dead(pid: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"pid {pid} still alive")


def test_iter_output_merges_stdout_stderr_line_by_line():
    h = SubprocessExecutor().spawn([
        sys.executable, "-u", "-c",
        "import sys; print('out-1'); print('err-1', file=sys.stderr); print('out-2')"])
    lines = list(h.iter_output())
    assert h.wait() == 0
    assert sorted(lines) == ["err-1", "out-1", "out-2"]  # 合并流；顺序内核态可交错


def test_nonzero_exit_code_is_reported():
    h = SubprocessExecutor().spawn([sys.executable, "-c", "import os; os._exit(3)"])
    list(h.iter_output())
    assert h.wait() == 3
    assert h.poll() == 3


def test_extra_env_overlays_inherited_environment():
    h = SubprocessExecutor().spawn(
        [sys.executable, "-u", "-c",
         "import os; print(os.environ['LMD_PROBE']); print('PATH' in os.environ)"],
        extra_env={"LMD_PROBE": "42"})
    assert list(h.iter_output()) == ["42", "True"]
    assert h.wait() == 0


def test_terminate_signals_the_whole_process_group():
    # 父进程再 spawn 一个孙进程（mlx-h3 可能有子进程），terminate 必须整组消灭
    prog = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "print('pids', os.getpid(), child.pid, flush=True)\n"
        "time.sleep(60)\n")
    h = SubprocessExecutor().spawn([sys.executable, "-u", "-c", prog])
    line = next(h.iter_output())
    _, parent_pid, child_pid = line.split()
    h.terminate()
    assert h.wait() == -signal.SIGTERM
    _wait_dead(int(parent_pid))
    _wait_dead(int(child_pid))


def test_kill_after_ignored_terminate():
    prog = ("import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n")
    h = SubprocessExecutor().spawn([sys.executable, "-u", "-c", prog])
    assert next(h.iter_output()) == "ready"
    h.terminate()
    time.sleep(0.3)
    assert h.poll() is None          # SIGTERM 被忽略，还活着
    h.kill()
    assert h.wait() == -signal.SIGKILL
```

实现：

```python
# desk/media/executor.py
"""可替换的子进程执行器接口 + 真实现。

单测注入 FakeExecutor（tests/media_fakes.py），任何 MediaService 单测不起真进程；
本文件的真实现由 tests/test_media_executor.py 用秒级 python -c 微进程验证。
"""
from __future__ import annotations

import os
import signal
import subprocess
from typing import Iterator, Protocol


class ProcessHandle(Protocol):
    def iter_output(self) -> Iterator[str]: ...   # 合并 stdout/stderr，逐行（不含换行符）
    def wait(self) -> int: ...                    # 退出码（信号死亡为负值）
    def terminate(self) -> None: ...              # SIGTERM，发给整个进程组
    def kill(self) -> None: ...                   # SIGKILL，发给整个进程组
    def poll(self) -> int | None: ...


class Executor(Protocol):
    def spawn(self, cmd: list[str], *,
              extra_env: dict[str, str] | None = None) -> ProcessHandle: ...
        # extra_env 叠加在继承环境之上（bundle 态 H3/Music 需 PYTHONPATH，
        # 取自 pathRoots 的 mlx_h3_env / music_env；dev 态为空 dict）


class SubprocessHandle:
    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc

    def iter_output(self) -> Iterator[str]:
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            yield line.rstrip("\n")

    def wait(self) -> int:
        return self._proc.wait()

    def poll(self) -> int | None:
        return self._proc.poll()

    def _signal_group(self, sig: int) -> None:
        try:
            os.killpg(os.getpgid(self._proc.pid), sig)
        except ProcessLookupError:
            pass  # 已死：信号无处可发不是错误

    def terminate(self) -> None:
        self._signal_group(signal.SIGTERM)

    def kill(self) -> None:
        self._signal_group(signal.SIGKILL)


class SubprocessExecutor:
    """真实现：start_new_session=True 使取消可对整个进程组发信号。"""

    def spawn(self, cmd: list[str], *,
              extra_env: dict[str, str] | None = None) -> SubprocessHandle:
        env = {**os.environ, **extra_env} if extra_env else None
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, start_new_session=True, env=env)
        return SubprocessHandle(proc)
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_executor.py -q`

---

## T-media-04 Music 3 管线入口脚本

**需求** R-media-02（census A05 的替代物）
**文件** `desk/media/music3_cli.py`、`tests/test_media_music3_cli.py`

失败测试：

```python
# tests/test_media_music3_cli.py
"""music3_cli 冒烟：--help 在未装 mlx 管线的环境（desk 测试 venv）必须能跑。
真实生成不进自动验收（reality gate，见计划 runbook）。"""
import ast
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "desk" / "media" / "music3_cli.py"


def test_help_runs_without_mlx_pipeline():
    res = subprocess.run([sys.executable, str(CLI), "--help"],
                         capture_output=True, text=True, timeout=30)
    assert res.returncode == 0
    for flag in ("--root", "--caption", "--lyrics", "--duration", "--output"):
        assert flag in res.stdout


def test_missing_required_args_fail_nonzero():
    res = subprocess.run([sys.executable, str(CLI), "--caption", "x"],
                         capture_output=True, text=True, timeout=30)
    assert res.returncode != 0


def test_module_top_imports_only_argparse():
    """mlx import 必须延迟到 main() 内（设计 §2）；顶层只允许 argparse。"""
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    assert names <= {"argparse"}


def test_never_calls_unload_or_imports_desk():
    src = CLI.read_text(encoding="utf-8")
    assert "unload-llm" not in src          # 卸 LLM 归 arbiter（A06/A07）
    assert "import desk" not in src         # music venv 无需安装 desk 包
    assert "sys.exit(" not in src           # foundation 静态不变量
    assert "SystemExit" not in src
```

实现（Pipeline 调用逐参照抄根目录 `run-music3.py` 的实测形态：
`GenerationRequest(caption, lyrics, audio_duration, seed)` + `generate(req, output=..., overwrite=True)`）：

```python
# desk/media/music3_cli.py
"""Music 3 管线调用的唯一定义点（census A05：取代根目录 run-music3.py）。

以文件路径方式被 music 解释器执行：
    <music_python> music3_cli.py --root <music3_root> --caption ... --lyrics ...
                                 --duration 30 --output <path>.wav

- 顶层只 import argparse：--help 在未安装 mlx 管线的环境也能运行；
- --root 必传：模型根由调用方解析注入，本脚本零路径拼接；
- 不调用 unload-llm.sh：卸 LLM 是 arbiter 在 acquire 时做的；
- 生成结束把输出路径打到 stdout；失败以未捕获异常报非零退出码。
"""
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music3_cli",
        description="Generate a song with MiniMax Music 3 (MLX)")
    parser.add_argument("--root", required=True, help="music3 model root directory")
    parser.add_argument("--caption", required=True, help="style description")
    parser.add_argument("--lyrics", required=True, help="lyrics text (may be empty)")
    parser.add_argument("--duration", required=True, type=float, help="target seconds")
    parser.add_argument("--output", required=True, help="output .wav path")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    # 延迟 import：参数解析成功之后才碰 mlx 管线
    from mlx_minimax_music3 import GenerationRequest, Music3Pipeline
    pipeline = Music3Pipeline(args.root)
    pipeline.generate(
        GenerationRequest(
            caption=args.caption,
            lyrics=args.lyrics,
            audio_duration=args.duration,
            seed=0,
        ),
        output=args.output,
        overwrite=True,
    )
    print(args.output, flush=True)


if __name__ == "__main__":
    main()
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_music3_cli.py -q`

---

## T-media-05 MediaService：视频作业成功路径（data:jobState + api:startVideoJob）

**需求** R-media-01/03/04（成功分支）
**文件** `desk/media/service.py`、`desk/media/__init__.py`（改导出）、
`tests/media_fakes.py`、`tests/test_media_service.py`

先落假件（测试基础设施，不算实现——它编码的是兄弟合同的形状）：

```python
# tests/media_fakes.py
"""media 单测注入件：不起真进程、不碰真权重、固定 clock。

FakeHandle 四种剧本（spec 验收取向的四种执行剧本）：
  success   — 写出产出文件后退出 0
  no_output — 退出 0 但不写产出文件
  fail      — 退出 3
  block     — 阻塞直到 terminate()/kill()；terminate 后退出码 0
              （被取消的作业即使退出码 0 也必须是 cancelled）
"""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from desk.media.service import MediaService

FIXED_TIME = 1756600000.0
STAMP = time.strftime("%Y%m%d-%H%M%S", time.localtime(FIXED_TIME))


class FakeHandle:
    def __init__(self, script: str, output: Path, lines, *, ignore_term: bool):
        assert script in ("success", "no_output", "fail", "block")
        self.script = script
        self.lines = list(lines)
        self.ignore_term = ignore_term
        self.terminated = False
        self.killed = False
        self._queue: queue.Queue[str] = queue.Queue()
        self._exited = threading.Event()
        self._code: int | None = None
        if script == "success":
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"fake-media-bytes")
        if script != "block":
            self._exit(3 if script == "fail" else 0)

    def emit(self, line: str) -> None:      # block 剧本：测试分批喂日志行
        self._queue.put(line)

    def _exit(self, code: int) -> None:
        self._code = code
        self._exited.set()

    def iter_output(self):
        yield from self.lines
        while self.script == "block":
            try:
                yield self._queue.get(timeout=0.02)
            except queue.Empty:
                if self._exited.is_set():
                    return

    def wait(self) -> int:
        assert self._exited.wait(10.0), "FakeHandle never exited"
        assert self._code is not None
        return self._code

    def poll(self) -> int | None:
        return self._code if self._exited.is_set() else None

    def terminate(self) -> None:
        self.terminated = True
        if self.script == "block" and not self.ignore_term:
            self._exit(0)

    def kill(self) -> None:
        self.killed = True
        if not self._exited.is_set():
            self._exit(-9)


class FakeExecutor:
    def __init__(self, script: str = "success", lines=("line-1", "line-2"), *,
                 ignore_term: bool = False, spawn_error: Exception | None = None):
        self.script = script
        self.lines = lines
        self.ignore_term = ignore_term
        self.spawn_error = spawn_error
        self.spawned: list[dict] = []
        self.handles: list[FakeHandle] = []

    def spawn(self, cmd, *, extra_env=None):
        if self.spawn_error is not None:
            raise self.spawn_error
        self.spawned.append({"cmd": list(cmd), "extra_env": dict(extra_env or {})})
        handle = FakeHandle(self.script, Path(cmd[-1]), self.lines,
                            ignore_term=self.ignore_term)
        self.handles.append(handle)
        return handle


class FakeArbiter:
    def __init__(self, *, can_start_ok: bool = True, acquire_ok: bool = True,
                 refuse=("media_busy", "another heavy task is running")):
        self.can_start_ok = can_start_ok
        self.acquire_ok = acquire_ok
        self.refuse = refuse
        self.acquired: list[tuple] = []
        self.released: list[str] = []
        self.release_error: Exception | None = None
        self._seq = 0

    def can_start_heavy(self, kind):
        if self.can_start_ok:
            return {"ok": True, "reason": None}
        code, message = self.refuse
        return {"ok": False, "reason": {"code": code, "message": message}}

    def acquire_heavy(self, kind, label):
        if not self.acquire_ok:
            code, message = self.refuse
            return {"ok": False, "reason": {"code": code, "message": message}}
        self._seq += 1
        token = f"permit-{self._seq}"
        self.acquired.append((kind, label, token))
        return {"ok": True, "token": token}

    def release_heavy(self, token):
        if self.release_error is not None:
            raise self.release_error
        self.released.append(token)
        return {"ok": True}


class FakeHistory:
    def __init__(self):
        self.entries: list[dict] = []
        self.error: Exception | None = None

    def append(self, entry: dict) -> dict:
        if self.error is not None:
            raise self.error
        self.entries.append(entry)
        return {**entry, "id": "f" * 32, "ts": "2026-08-31T10:00:00"}


def make_caps(*, mlx_h3: bool = True, music_runtime: bool = True):
    def cap(present, why):
        return SimpleNamespace(present=present, path="", detail="" if present else why)
    return {"mlx_h3": cap(mlx_h3, "mlx-h3 not found"),
            "music_runtime": cap(music_runtime, "mlx_minimax_music3 missing")}


CATALOG = (
    SimpleNamespace(key="h3", relpath="minimax-h3"),
    SimpleNamespace(key="music3", relpath="minimax-music3"),
    SimpleNamespace(key="glm", relpath="llms/zai-org/GLM-4.5-Air-mlx-4bit"),
)


def make_roots(tmp_path: Path):
    return SimpleNamespace(
        outputs_root=tmp_path / "outputs",
        models_root=tmp_path / "models",
        mlx_h3_cmd=("/fake/bin/mlx-h3",),
        mlx_h3_env={"PYTHONPATH": "/fake/pylibs/h3"},
        music_python=Path("/fake/bin/python3"),
        music_env={"PYTHONPATH": "/fake/pylibs/music"},
        media_cli_dir=Path("/fake/res/desk/media"),
    )


def make_service(tmp_path: Path, *, executor=None, arbiter=None, history=None,
                 caps=None, term_grace_s: float = 0.2, log_limit: int = 1024 * 1024):
    executor = executor if executor is not None else FakeExecutor()
    arbiter = arbiter if arbiter is not None else FakeArbiter()
    history = history if history is not None else FakeHistory()
    caps = caps if caps is not None else make_caps()
    roots = make_roots(tmp_path)
    service = MediaService(
        resolve_paths=lambda: roots,
        probe_capabilities=lambda: caps,
        arbiter=arbiter,
        list_catalog=lambda: list(CATALOG),
        append_history=history.append,
        executor=executor,
        clock=lambda: FIXED_TIME,
        term_grace_s=term_grace_s,
        log_limit=log_limit,
    )
    deps = SimpleNamespace(executor=executor, arbiter=arbiter,
                           history=history, roots=roots)
    return service, deps


def finished_snapshot(service, start_fn, timeout: float = 5.0) -> dict:
    """启动并等 event:jobFinished（它在 release+history 之后派发，等到即断言安全）。"""
    done = threading.Event()
    box: dict = {}
    service.on_job_finished(lambda snap: (box.update(snap), done.set()))
    start_fn()
    assert done.wait(timeout), "job never finished"
    return box


def wait_for(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not met in time")
```

失败测试：

```python
# tests/test_media_service.py
"""MediaService：注入假件，不起真进程、不碰真权重，秒级跑完。"""
import threading

import pytest

from desk.media.service import MediaError
from media_fakes import (CATALOG, FIXED_TIME, STAMP, FakeArbiter, FakeExecutor,
                         FakeHistory, finished_snapshot, make_caps, make_service,
                         wait_for)


class TestInitialState:
    def test_initial_job_state_shape(self, tmp_path):
        service, _ = make_service(tmp_path)
        state = service.job_status()
        assert state["job_id"] == 0
        assert state["status"] == "idle"
        assert state["kind"] is None
        assert state["params"] is None
        assert state["output"] is None
        assert state["error"] is None
        assert state["started_at"] is None
        assert state["finished_at"] is None
        assert state["log"] == ""
        assert state["next_log_from"] == 0
        assert state["log_len"] == 0
        assert state["log_truncated"] is False


class TestVideoHappyPath:
    def _start(self, service):
        return service.start_video_job(prompt="rain on a quiet street",
                                       width=512, height=288, frames=73, steps=10)

    def test_start_returns_running_state(self, tmp_path):
        service, _ = make_service(tmp_path, executor=FakeExecutor("block"))
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        state = self._start(service)
        assert state["status"] == "running"
        assert state["job_id"] == 1
        assert state["kind"] == "video"
        assert state["started_at"] == FIXED_TIME
        service.cancel_job()
        assert done.wait(5.0)

    def test_video_job_done_end_to_end(self, tmp_path):
        service, deps = make_service(tmp_path)
        snap = finished_snapshot(service, lambda: self._start(service))
        assert snap["status"] == "done"
        assert snap["output"] == f"h3-{STAMP}.mp4"
        assert snap["error"] is None
        assert snap["finished_at"] == FIXED_TIME
        assert (tmp_path / "outputs" / f"h3-{STAMP}.mp4").is_file()
        assert snap["params"] == {"prompt": "rain on a quiet street", "width": 512,
                                  "height": 288, "frames": 73, "steps": 10}
        assert "line-1" in snap["log"] and "line-2" in snap["log"]

    def test_spawned_argv_is_exactly_the_h3_command(self, tmp_path):
        from desk.media.commands import build_h3_command
        service, deps = make_service(tmp_path)
        finished_snapshot(service, lambda: self._start(service))
        expected = build_h3_command(
            ("/fake/bin/mlx-h3",), tmp_path / "models" / "minimax-h3",
            prompt="rain on a quiet street", width=512, height=288,
            frames=73, steps=10,
            output=tmp_path / "outputs" / f"h3-{STAMP}.mp4")
        assert deps.executor.spawned == [
            {"cmd": expected, "extra_env": {"PYTHONPATH": "/fake/pylibs/h3"}}]

    def test_permit_acquired_and_released_exactly_once(self, tmp_path):
        service, deps = make_service(tmp_path)
        finished_snapshot(service, lambda: self._start(service))
        assert [(k, l) for k, l, _ in deps.arbiter.acquired] == [("video", "job-1")]
        assert deps.arbiter.released == ["permit-1"]

    def test_history_entry_has_full_params(self, tmp_path):
        service, deps = make_service(tmp_path)
        finished_snapshot(service, lambda: self._start(service))
        assert len(deps.history.entries) == 1
        entry = deps.history.entries[0]
        assert entry == {
            "kind": "video", "status": "done",
            "params": {"prompt": "rain on a quiet street", "width": 512,
                       "height": 288, "frames": 73, "steps": 10},
            "output": f"h3-{STAMP}.mp4",
            "duration_s": 0.0,      # 固定 clock：finished - started == 0
            "error": None,
        }
```

实现：

```python
# desk/media/service.py
"""MediaService：H3 视频 / Music 3 歌曲作业运行器（一次至多一个作业）。

启动前必须取得 arbiter 重活许可（其副作用是卸 LLM）；产出落 outputs 根，
文件名带时间戳；任何终态（done/error/cancelled）都：释放许可 → 写一条历史 →
派发 event:jobFinished。错误保持是错误：退出码 0 但产出文件不存在 = no_output 失败。
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .commands import build_h3_command, build_music_command

log = logging.getLogger(__name__)

DEFAULT_LOG_LIMIT = 1024 * 1024   # 内存日志上限（字符），超限丢最旧并记截断标记
DEFAULT_TERM_GRACE_S = 5.0        # 取消：SIGTERM → 宽限 → SIGKILL

_HISTORY_STATUS = {"done": "done", "error": "failed", "cancelled": "cancelled"}


class MediaError(Exception):
    """机器可读的拒绝/失败；code 进 HTTP 错误信封。"""

    def __init__(self, code: str, message: str, http_status: int,
                 detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.detail = detail or {}


def _require_nonempty_str(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MediaError("invalid_params", f"{name} must be a non-empty string", 400)


def _require_pos_int(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MediaError("invalid_params", f"{name} must be a positive integer", 400)


def _require_pos_number(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise MediaError("invalid_params", f"{name} must be a positive number", 400)


class MediaService:
    def __init__(self, *, resolve_paths, probe_capabilities, arbiter,
                 list_catalog, append_history, executor,
                 clock: Callable[[], float] = time.time,
                 term_grace_s: float = DEFAULT_TERM_GRACE_S,
                 log_limit: int = DEFAULT_LOG_LIMIT):
        self._resolve_paths = resolve_paths
        self._probe_capabilities = probe_capabilities
        self._arbiter = arbiter
        self._list_catalog = list_catalog
        self._append_history = append_history
        self._executor = executor
        self._clock = clock
        self._term_grace_s = term_grace_s
        self._log_limit = log_limit

        self._lock = threading.RLock()
        self._state: dict[str, Any] = {
            "job_id": 0, "status": "idle", "kind": None, "params": None,
            "output": None, "error": None, "started_at": None, "finished_at": None,
        }
        self._log = ""
        self._log_dropped = 0
        self._log_truncated = False
        self._cancel_requested = False
        self._handle = None
        self._callbacks: list[Callable[[dict], None]] = []

    # ---- api:startVideoJob ----
    def start_video_job(self, *, prompt, width, height, frames, steps) -> dict:
        _require_nonempty_str("prompt", prompt)
        for name, value in (("width", width), ("height", height),
                            ("frames", frames), ("steps", steps)):
            _require_pos_int(name, value)
        return self._start("video", {"prompt": prompt, "width": width,
                                     "height": height, "frames": frames,
                                     "steps": steps})

    # ---- api:startMusicJob ----
    def start_music_job(self, *, caption, lyrics, duration) -> dict:
        _require_nonempty_str("caption", caption)
        if not isinstance(lyrics, str):
            raise MediaError("invalid_params", "lyrics must be a string", 400)
        _require_pos_number("duration", duration)
        return self._start("music", {"caption": caption, "lyrics": lyrics,
                                     "duration": duration})

    def _start(self, kind: str, params: dict) -> dict:
        cap_key = "mlx_h3" if kind == "video" else "music_runtime"
        with self._lock:
            # 2) 自身互斥
            if self._state["status"] == "running":
                raise MediaError("media_busy", "a media job is already running", 409)
            # 3) 能力预检（此时尚未触碰 arbiter：二进制缺失不会白卸 LLM）
            caps = self._probe_capabilities()
            cap = caps.get(cap_key)
            if cap is None or not cap.present:
                detail = cap.detail if cap is not None else "capability not probed"
                raise MediaError("capability_missing",
                                 f"{cap_key} is unavailable: {detail}", 503)
            # 路径与模型根（零硬编码：pathRoots + catalog relpath）
            roots = self._resolve_paths()
            catalog_key = "h3" if kind == "video" else "music3"
            relpath = {e.key: e.relpath for e in self._list_catalog()}[catalog_key]
            model_root = Path(roots.models_root) / relpath
            # 4) 无副作用预检：拒绝原因透传 arbiter 词汇
            pre = self._arbiter.can_start_heavy(kind)
            if not pre.get("ok"):
                reason = pre.get("reason") or {}
                raise MediaError(reason.get("code", "refused"),
                                 reason.get("message", "arbiter refused"), 409)
            # 5) 权威一步：acquire（副作用 = arbiter 按端口卸 LLM）；失败即启动失败
            job_id = self._state["job_id"] + 1
            grant = self._arbiter.acquire_heavy(kind, f"job-{job_id}")
            if not grant.get("ok"):
                reason = grant.get("reason") or {}
                raise MediaError(reason.get("code", "acquire_refused"),
                                 reason.get("message", "arbiter refused"), 409)
            permit = grant["token"]
            # 6) 拿到许可后才拼命令、spawn；此段失败由本路径收尾（worker 尚不存在）
            now = self._clock()
            try:
                stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
                outputs_root = Path(roots.outputs_root)
                if kind == "video":
                    output = outputs_root / f"h3-{stamp}.mp4"
                    cmd = build_h3_command(
                        tuple(roots.mlx_h3_cmd), model_root,
                        prompt=params["prompt"], width=params["width"],
                        height=params["height"], frames=params["frames"],
                        steps=params["steps"], output=output)
                    extra_env = dict(roots.mlx_h3_env)
                else:
                    output = outputs_root / f"music3-{stamp}.wav"
                    cmd = build_music_command(
                        Path(roots.music_python),
                        Path(roots.media_cli_dir) / "music3_cli.py",
                        model_root, caption=params["caption"],
                        lyrics=params["lyrics"], duration=params["duration"],
                        output=output)
                    extra_env = dict(roots.music_env)
                outputs_root.mkdir(parents=True, exist_ok=True)
                handle = self._executor.spawn(cmd, extra_env=extra_env)
            except Exception as exc:
                self._state = {
                    "job_id": job_id, "status": "error", "kind": kind,
                    "params": dict(params), "output": None,
                    "error": {"code": "spawn_failed", "message": str(exc)},
                    "started_at": now, "finished_at": self._clock(),
                }
                self._reset_log()
                self._finalize(permit)   # 与 worker finally 同语义：释放+历史+事件
                raise MediaError("spawn_failed", str(exc), 500) from exc
            # 置 running 与 handle 赋值在同一次持锁内完成：
            # cancel_job 不可能看到「running 但 handle 为空」
            self._state = {
                "job_id": job_id, "status": "running", "kind": kind,
                "params": dict(params), "output": None, "error": None,
                "started_at": now, "finished_at": None,
            }
            self._reset_log()
            self._cancel_requested = False
            self._handle = handle
            threading.Thread(target=self._worker, args=(handle, permit, output),
                             name=f"media-job-{job_id}", daemon=True).start()
            return self.job_status()

    def _worker(self, handle, permit: str, output: Path) -> None:
        try:
            code: int | None = None
            failure: str | None = None
            try:
                for line in handle.iter_output():
                    self._append_log(line)
                code = handle.wait()
            except Exception as exc:   # 执行器异常也是作业失败，不是崩
                log.exception("media worker failed")
                failure = str(exc)
            with self._lock:
                if self._cancel_requested:          # 优先级最高：退出码 0 也不改判
                    status, error = "cancelled", None
                elif failure is not None:
                    status, error = "error", {"code": "worker_failed",
                                              "message": failure}
                elif code == 0 and output.is_file():
                    status, error = "done", None
                elif code == 0:                     # R-media-06：绝不报成功
                    status, error = "error", {
                        "code": "no_output",
                        "message": "exit 0 but output file missing"}
                else:
                    status, error = "error", {"code": "exit_nonzero",
                                              "message": f"exit {code}"}
                self._state.update(
                    status=status,
                    output=output.name if status == "done" else None,
                    error=error, finished_at=self._clock())
                self._handle = None
        finally:
            self._finalize(permit)   # 无论终态如何必然释放（R-media-05/07）

    def _finalize(self, permit: str) -> None:
        """终态尾声：释放许可 → 写历史 → 派发事件。此处失败大声记日志，
        但绝不改写作业终态（已成功的生成不因记账失败改判）。"""
        with self._lock:
            snap = self.job_status()
            callbacks = list(self._callbacks)
        try:
            self._arbiter.release_heavy(permit)
        except Exception:
            log.exception("release_heavy failed (job %s)", snap["job_id"])
        try:
            self._append_history(self._history_entry(snap))
        except Exception as exc:
            log.exception("append_history failed (job %s)", snap["job_id"])
            self._append_log(f"[media] append_history failed: {exc}")
        for cb in callbacks:
            try:
                cb(snap)
            except Exception:
                log.exception("jobFinished subscriber failed (job %s)",
                              snap["job_id"])

    def _history_entry(self, snap: dict) -> dict:
        error = snap["error"]
        duration = None
        if snap["started_at"] is not None and snap["finished_at"] is not None:
            duration = snap["finished_at"] - snap["started_at"]
        return {
            "kind": snap["kind"],
            "status": _HISTORY_STATUS[snap["status"]],   # error → failed
            "params": snap["params"],
            "output": snap["output"],
            "duration_s": duration,
            "error": f"{error['code']}: {error['message']}" if error else None,
        }

    # ---- api:cancelJob（T-media-09 完成实现）----
    def cancel_job(self) -> dict:
        with self._lock:
            if self._state["status"] != "running":
                raise MediaError("no_running_job", "no media job is running", 409)
            self._cancel_requested = True
            handle = self._handle
        handle.terminate()
        deadline = time.monotonic() + self._term_grace_s
        while handle.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if handle.poll() is None:
            handle.kill()
        with self._lock:
            return self.job_status()

    # ---- api:jobStatus / data:jobState ----
    def job_status(self, *, log_from: int = 0, job_id: int | None = None) -> dict:
        with self._lock:
            state = dict(self._state)
            state["params"] = dict(self._state["params"]) if self._state["params"] else None
            state["error"] = dict(self._state["error"]) if self._state["error"] else None
            if job_id is not None and job_id != state["job_id"]:
                log_from = 0             # 旧作业的游标：从头重发
            start = max(log_from - self._log_dropped, 0)
            state["log"] = self._log[start:]
            state["next_log_from"] = self._log_dropped + len(self._log)
            state["log_len"] = self._log_dropped + len(self._log)
            state["log_truncated"] = self._log_truncated
            return state

    # ---- event:jobFinished ----
    def on_job_finished(self, callback: Callable[[dict], None]) -> Callable[[], None]:
        with self._lock:
            self._callbacks.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)
        return unsubscribe

    def _reset_log(self) -> None:
        self._log = ""
        self._log_dropped = 0
        self._log_truncated = False

    def _append_log(self, line: str) -> None:
        with self._lock:
            self._log += line if line.endswith("\n") else line + "\n"
            overflow = len(self._log) - self._log_limit
            if overflow > 0:
                self._log = self._log[overflow:]
                self._log_dropped += overflow
                self._log_truncated = True
```

`desk/media/__init__.py` 改为：

```python
"""H3 文生视频与 Music 3 文生歌曲的作业运行器。"""
from .service import MediaError, MediaService

__all__ = ["MediaError", "MediaService"]
```

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-06 启动纪律：校验、能力、许可（拒绝路径）

**需求** R-media-05；错误处理表 `invalid_params` / `media_busy` / `capability_missing` / arbiter 码透传
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestStartDiscipline:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    @pytest.mark.parametrize("bad", [
        dict(prompt=""), dict(prompt="   "), dict(prompt=None),
        dict(width=0), dict(width=-1), dict(width="512"), dict(width=True),
        dict(height=0), dict(frames=0), dict(steps=0),
    ])
    def test_invalid_video_params_never_touch_arbiter_or_spawn(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**{**self.VALID, **bad})
        assert err.value.code == "invalid_params"
        assert err.value.http_status == 400
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []
        assert service.job_status()["status"] == "idle"

    @pytest.mark.parametrize("bad", [
        dict(caption=""), dict(caption=None), dict(lyrics=None),
        dict(duration=0), dict(duration=-3.0), dict(duration="30"),
    ])
    def test_invalid_music_params(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        valid = dict(caption="c", lyrics="l", duration=30.0)
        with pytest.raises(MediaError) as err:
            service.start_music_job(**{**valid, **bad})
        assert err.value.code == "invalid_params"
        assert deps.executor.spawned == []

    def test_missing_mlx_h3_is_503_and_arbiter_untouched(self, tmp_path):
        service, deps = make_service(tmp_path, caps=make_caps(mlx_h3=False))
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "capability_missing"
        assert err.value.http_status == 503
        assert deps.arbiter.acquired == []   # 不会为一次注定失败的启动白卸 LLM
        assert deps.executor.spawned == []

    def test_can_start_refusal_passes_arbiter_code_through(self, tmp_path):
        arbiter = FakeArbiter(can_start_ok=False,
                              refuse=("transition_in_progress", "evicting now"))
        service, deps = make_service(tmp_path, arbiter=arbiter)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "transition_in_progress"
        assert err.value.http_status == 409
        assert arbiter.acquired == []
        assert deps.executor.spawned == []

    def test_acquire_refusal_never_spawns_and_state_unchanged(self, tmp_path):
        arbiter = FakeArbiter(acquire_ok=False,
                              refuse=("evict_failed",
                                      "pids [4242] still listening after SIGKILL"))
        service, deps = make_service(tmp_path, arbiter=arbiter)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "evict_failed"          # 让出失败即启动失败
        assert deps.executor.spawned == []
        assert arbiter.released == []
        assert service.job_status()["status"] == "idle"
```

实现：T-media-05 的 `_start` 已按此纪律写就；本任务跑测试暴露任何缺口并修正
（例如 `width=True` 的 bool 拦截、`duration="30"` 的类型拦截）。红→绿后提交。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-07 音乐作业路径（api:startMusicJob）

**需求** R-media-02/04（音乐分支与视频同构，唯二差别：命令与产出名）
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestMusicJob:
    def test_music_job_done_end_to_end(self, tmp_path):
        service, deps = make_service(tmp_path)
        snap = finished_snapshot(service, lambda: service.start_music_job(
            caption="synthwave night drive", lyrics="la la", duration=30.0))
        assert snap["status"] == "done"
        assert snap["kind"] == "music"
        assert snap["output"] == f"music3-{STAMP}.wav"
        assert (tmp_path / "outputs" / f"music3-{STAMP}.wav").is_file()
        assert deps.history.entries[0]["kind"] == "music"
        assert deps.history.entries[0]["params"] == {
            "caption": "synthwave night drive", "lyrics": "la la", "duration": 30.0}

    def test_spawned_argv_is_exactly_the_music_command(self, tmp_path):
        from pathlib import Path
        from desk.media.commands import build_music_command
        service, deps = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_music_job(
            caption="c", lyrics="l", duration=30.0))
        expected = build_music_command(
            Path("/fake/bin/python3"), Path("/fake/res/desk/media/music3_cli.py"),
            tmp_path / "models" / "minimax-music3",
            caption="c", lyrics="l", duration=30.0,
            output=tmp_path / "outputs" / f"music3-{STAMP}.wav")
        assert deps.executor.spawned == [
            {"cmd": expected, "extra_env": {"PYTHONPATH": "/fake/pylibs/music"}}]

    def test_music_acquires_music_kind_and_allows_empty_lyrics(self, tmp_path):
        service, deps = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_music_job(
            caption="c", lyrics="", duration=1.5))    # 纯器乐：空歌词合法
        assert deps.arbiter.acquired[0][0] == "music"

    def test_missing_music_runtime_is_503(self, tmp_path):
        service, deps = make_service(tmp_path, caps=make_caps(music_runtime=False))
        with pytest.raises(MediaError) as err:
            service.start_music_job(caption="c", lyrics="l", duration=30.0)
        assert err.value.code == "capability_missing"
        assert deps.arbiter.acquired == []
```

实现：T-media-05 的 `_start` 音乐分支即为实现；红→绿补漏（如空歌词必须放行：
校验只拦「非字符串」，不拦空串）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-08 失败终态：no_output / exit_nonzero / spawn_failed / 记账失败

**需求** R-media-06；错误处理表 `spawn_failed` / `appendHistory 抛异常` / `releaseHeavy 抛异常` 三行
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestFailureStates:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def test_exit_zero_without_output_is_error_not_success(self, tmp_path):
        service, deps = make_service(tmp_path, executor=FakeExecutor("no_output"))
        snap = finished_snapshot(service,
                                 lambda: service.start_video_job(**self.VALID))
        assert snap["status"] == "error"              # R-media-06：绝不报成功
        assert snap["error"]["code"] == "no_output"
        assert snap["output"] is None
        assert deps.history.entries[0]["status"] == "failed"
        assert "no_output" in deps.history.entries[0]["error"]
        assert deps.arbiter.released == ["permit-1"]

    def test_nonzero_exit_is_error_with_code(self, tmp_path):
        service, deps = make_service(tmp_path, executor=FakeExecutor("fail"))
        snap = finished_snapshot(service,
                                 lambda: service.start_video_job(**self.VALID))
        assert snap["status"] == "error"
        assert snap["error"]["code"] == "exit_nonzero"
        assert "3" in snap["error"]["message"]
        assert deps.history.entries[0]["status"] == "failed"
        assert deps.arbiter.released == ["permit-1"]

    def test_spawn_exception_still_releases_and_records(self, tmp_path):
        executor = FakeExecutor(spawn_error=RuntimeError("boom"))
        service, deps = make_service(tmp_path, executor=executor)
        events = []
        service.on_job_finished(events.append)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "spawn_failed"
        assert err.value.http_status == 500
        assert deps.arbiter.released == ["permit-1"]        # 无泄漏路径
        assert deps.history.entries[0]["status"] == "failed"
        assert "spawn_failed" in deps.history.entries[0]["error"]
        assert len(events) == 1 and events[0]["status"] == "error"
        assert service.job_status()["status"] == "error"

    def test_history_failure_does_not_rewrite_terminal_state(self, tmp_path):
        history = FakeHistory()
        history.error = RuntimeError("disk full")
        service, deps = make_service(tmp_path, history=history)
        snap = finished_snapshot(service,
                                 lambda: service.start_video_job(**self.VALID))
        assert snap["status"] == "done"                    # 成功不因记账失败改判
        assert deps.arbiter.released == ["permit-1"]
        assert "append_history failed" in service.job_status()["log"]

    def test_release_failure_is_logged_history_still_written(self, tmp_path):
        arbiter = FakeArbiter()
        arbiter.release_error = RuntimeError("arbiter down")
        service, deps = make_service(tmp_path, arbiter=arbiter)
        snap = finished_snapshot(service,
                                 lambda: service.start_video_job(**self.VALID))
        assert snap["status"] == "done"
        assert deps.history.entries[0]["status"] == "done"  # 尾声继续走完
```

实现：T-media-05 的 `_worker` 终态判定、`_finalize` 尾声与 `_start` 的
spawn_failed 收尾即为实现；红→绿补漏。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-09 取消（api:cancelJob）

**需求** R-media-07；错误处理表 `no_running_job`；TERM→宽限→KILL
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestCancel:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def _start_blocking(self, tmp_path, **executor_kwargs):
        executor = FakeExecutor("block", **executor_kwargs)
        service, deps = make_service(tmp_path, executor=executor)
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        service.start_video_job(**self.VALID)
        return service, deps, done

    def test_cancel_running_job_exit_zero_stays_cancelled(self, tmp_path):
        service, deps, done = self._start_blocking(tmp_path)
        assert service.job_status()["status"] == "running"
        service.cancel_job()
        assert done.wait(5.0)
        handle = deps.executor.handles[0]
        assert handle.terminated                    # SIGTERM 确实发出
        snap = service.job_status()
        assert snap["status"] == "cancelled"        # 退出码 0 也不会被改写成 done
        assert snap["error"] is None
        assert deps.arbiter.released == ["permit-1"]
        assert deps.history.entries[0]["status"] == "cancelled"   # 取消也写历史

    def test_kill_after_ignored_terminate(self, tmp_path):
        service, deps, done = self._start_blocking(tmp_path, ignore_term=True)
        service.cancel_job()                        # 宽限 0.2s 后升级 KILL
        assert done.wait(5.0)
        handle = deps.executor.handles[0]
        assert handle.terminated and handle.killed
        assert service.job_status()["status"] == "cancelled"

    def test_cancel_without_running_job_is_409(self, tmp_path):
        service, _ = make_service(tmp_path)
        with pytest.raises(MediaError) as err:
            service.cancel_job()
        assert err.value.code == "no_running_job"
        assert err.value.http_status == 409

    def test_cancel_after_done_is_409(self, tmp_path):
        service, _ = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        with pytest.raises(MediaError) as err:
            service.cancel_job()
        assert err.value.code == "no_running_job"
```

实现：T-media-05 已落 `cancel_job` 骨架；红→绿补漏（宽限轮询步长、
`cancel_requested` 在 worker 判定里的最高优先级）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-10 互斥与并发

**需求** R-media-05（media_busy）；设计测试第 4 项
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestMutex:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def test_second_start_while_running_is_media_busy(self, tmp_path):
        service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        service.start_video_job(**self.VALID)
        with pytest.raises(MediaError) as err:
            service.start_music_job(caption="c", lyrics="l", duration=5.0)
        assert err.value.code == "media_busy"
        snap = service.job_status()
        assert snap["status"] == "running" and snap["job_id"] == 1   # 原作业无恙
        assert len(deps.executor.spawned) == 1
        assert len(deps.arbiter.acquired) == 1     # busy 拒绝不触碰 arbiter
        service.cancel_job()
        assert done.wait(5.0)

    def test_parallel_starts_exactly_one_wins(self, tmp_path):
        service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        barrier = threading.Barrier(2)
        results: list[str] = []

        def attempt():
            barrier.wait()
            try:
                service.start_video_job(**self.VALID)
                results.append("ok")
            except MediaError as exc:
                results.append(exc.code)

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5.0)
        assert sorted(results) == ["media_busy", "ok"]   # 恰一个成功（服务内锁）
        assert len(deps.executor.spawned) == 1
        assert len(deps.arbiter.acquired) == 1
        service.cancel_job()
        assert done.wait(5.0)

    def test_release_called_exactly_once_per_terminal_state(self, tmp_path):
        for script in ("success", "no_output", "fail"):
            service, deps = make_service(tmp_path / script,
                                         executor=FakeExecutor(script))
            finished_snapshot(service,
                              lambda: service.start_video_job(**self.VALID))
            assert deps.arbiter.released == ["permit-1"], script
```

实现：`_start` 全程持 `RLock` 已保证；红→绿补漏。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-11 进度流式读取：增量日志游标（api:jobStatus）

**需求** R-media-03；设计「日志累积 + 增量游标 + 截断标记」
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestLogCursor:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def test_incremental_cursor(self, tmp_path):
        service, deps = make_service(tmp_path,
                                     executor=FakeExecutor("block", lines=()))
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        service.start_video_job(**self.VALID)
        handle = deps.executor.handles[0]
        handle.emit("alpha")
        wait_for(lambda: "alpha" in service.job_status()["log"])
        first = service.job_status()
        assert first["log"] == "alpha\n"
        cursor = first["next_log_from"]
        handle.emit("beta")
        wait_for(lambda: service.job_status()["next_log_from"] > cursor)
        second = service.job_status(log_from=cursor, job_id=first["job_id"])
        assert second["log"] == "beta\n"           # 只有增量
        assert second["next_log_from"] == cursor + len("beta\n")
        service.cancel_job()
        assert done.wait(5.0)

    def test_stale_job_id_resets_cursor_to_zero(self, tmp_path):
        service, _ = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        full = service.job_status()["log"]
        assert full == "line-1\nline-2\n"
        replay = service.job_status(log_from=len(full), job_id=999)
        assert replay["log"] == full               # job_id 不符：从头重发

    def test_truncation_keeps_absolute_cursor_and_flags(self, tmp_path):
        service, deps = make_service(tmp_path, log_limit=32,
                                     executor=FakeExecutor("block", lines=()))
        done = threading.Event()
        service.on_job_finished(lambda s: done.set())
        service.start_video_job(**self.VALID)
        handle = deps.executor.handles[0]
        for i in range(10):
            handle.emit(f"line-{i:04d}")           # 10 行 × 10 字符 > 32
        wait_for(lambda: service.job_status()["log_truncated"])
        state = service.job_status()
        assert state["log_truncated"] is True
        assert len(state["log"]) <= 32             # 只留最新
        assert state["log_len"] > 32               # 绝对长度保留（游标不回跳）
        assert state["next_log_from"] == state["log_len"]
        assert service.job_status(log_from=state["next_log_from"])["log"] == ""
        service.cancel_job()
        assert done.wait(5.0)

    def test_new_job_resets_log(self, tmp_path):
        service, _ = make_service(tmp_path)
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        state = service.job_status()
        assert state["job_id"] == 2
        assert state["log"] == "line-1\nline-2\n"  # 第二单的日志，不是累积
```

实现：T-media-05 已落 `job_status` / `_append_log` / `_reset_log`；红→绿补漏
（截断用绝对游标 `_log_dropped`，防止旧游标在截断后读串位）。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-12 event:jobFinished 订阅语义

**需求** R-media-04 的事件出口；设计「回调异常被捕获不影响作业终态」
**文件** `tests/test_media_service.py`（追加）；`desk/media/service.py`（按测试修缺）

追加失败测试：

```python
class TestJobFinishedEvent:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    def test_payload_is_terminal_snapshot(self, tmp_path):
        service, _ = make_service(tmp_path)
        events: list[dict] = []
        service.on_job_finished(events.append)
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        assert len(events) == 1
        snap = events[0]
        assert snap["status"] == "done"
        assert snap["output"] == f"h3-{STAMP}.mp4"
        assert snap["params"]["prompt"] == "p"

    def test_broken_subscriber_does_not_break_others_or_job(self, tmp_path):
        service, deps = make_service(tmp_path)
        seen: list[dict] = []

        def bad(_snap):
            raise RuntimeError("subscriber bug")

        service.on_job_finished(bad)               # 先注册的坏订阅者
        service.on_job_finished(seen.append)
        snap = finished_snapshot(service,
                                 lambda: service.start_video_job(**self.VALID))
        assert snap["status"] == "done"            # 作业终态不受影响
        assert len(seen) == 1
        assert deps.history.entries[0]["status"] == "done"

    def test_unsubscribe_stops_delivery(self, tmp_path):
        service, _ = make_service(tmp_path)
        seen: list[dict] = []
        unsubscribe = service.on_job_finished(seen.append)
        unsubscribe()
        finished_snapshot(service, lambda: service.start_video_job(**self.VALID))
        assert seen == []

    def test_event_fires_for_every_terminal_state(self, tmp_path):
        for script, status in (("success", "done"), ("no_output", "error"),
                               ("fail", "error")):
            service, _ = make_service(tmp_path / script,
                                      executor=FakeExecutor(script))
            snap = finished_snapshot(service,
                                     lambda: service.start_video_job(**self.VALID))
            assert snap["status"] == status, script
```

实现：T-media-05 已落 `on_job_finished` 与 `_finalize` 派发；红→绿补漏。

**验收** `cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_service.py -q`

---

## T-media-13 HTTP 适配层：路由表

**需求** 设计 §5「HTTP 挂载」；错误信封 `{"error": {"code", "message", "detail"}}`
**文件** `desk/media/routes.py`、`tests/test_media_routes.py`

失败测试：

```python
# tests/test_media_routes.py
"""路由表适配层：handler 是纯 (body, query) -> (status, payload)，装配点一行转发。"""
import threading

from desk.media.routes import build_routes
from media_fakes import make_caps, make_service


def route_map(service):
    return {(method, path): handler
            for method, path, handler in build_routes(service)}


def test_route_table_shape(tmp_path):
    service, _ = make_service(tmp_path)
    assert [(m, p) for m, p, _ in build_routes(service)] == [
        ("POST", "/api/media/video"),
        ("POST", "/api/media/music"),
        ("POST", "/api/media/cancel"),
        ("GET", "/api/media/job"),
    ]


def test_start_video_route_success_returns_running_state(tmp_path):
    service, _ = make_service(tmp_path)
    done = threading.Event()
    service.on_job_finished(lambda s: done.set())
    status, payload = route_map(service)[("POST", "/api/media/video")](
        {"prompt": "p", "width": 512, "height": 288, "frames": 73, "steps": 10}, {})
    assert status == 200
    assert payload["status"] == "running"
    assert done.wait(5.0)


def test_invalid_params_envelope_400(tmp_path):
    service, _ = make_service(tmp_path)
    status, payload = route_map(service)[("POST", "/api/media/video")](
        {"prompt": ""}, {})
    assert status == 400
    assert payload["error"]["code"] == "invalid_params"
    assert "message" in payload["error"]


def test_missing_capability_envelope_503(tmp_path):
    service, _ = make_service(tmp_path, caps=make_caps(mlx_h3=False))
    status, payload = route_map(service)[("POST", "/api/media/video")](
        {"prompt": "p", "width": 512, "height": 288, "frames": 73, "steps": 10}, {})
    assert status == 503
    assert payload["error"]["code"] == "capability_missing"


def test_cancel_without_job_envelope_409(tmp_path):
    service, _ = make_service(tmp_path)
    status, payload = route_map(service)[("POST", "/api/media/cancel")](None, {})
    assert status == 409
    assert payload["error"]["code"] == "no_running_job"


def test_status_route_parses_query_and_rejects_garbage(tmp_path):
    service, _ = make_service(tmp_path)
    handler = route_map(service)[("GET", "/api/media/job")]
    status, payload = handler(None, {"log_from": "0", "job_id": "0"})
    assert status == 200
    assert payload["status"] == "idle"
    status, payload = handler(None, {"log_from": "abc"})
    assert status == 400
    assert payload["error"]["code"] == "invalid_params"


def test_start_music_route(tmp_path):
    service, _ = make_service(tmp_path)
    done = threading.Event()
    service.on_job_finished(lambda s: done.set())
    status, payload = route_map(service)[("POST", "/api/media/music")](
        {"caption": "c", "lyrics": "l", "duration": 30.0}, {})
    assert status == 200 and payload["kind"] == "music"
    assert done.wait(5.0)
```

实现：

```python
# desk/media/routes.py
"""HTTP 适配：MediaService -> 路由表，交台面服务器装配点挂载。

handler 签名 (body, query) -> (http_status, payload)：body 为已解析 JSON
（dict | None），query 为查询参数 dict[str, str]。零业务逻辑，只做参数
解析 + 调服务方法 + 异常映射为错误信封。
"""
from __future__ import annotations

from typing import Callable

from .service import MediaError, MediaService

Handler = Callable[[dict | None, dict], tuple[int, dict]]


def _envelope(exc: MediaError) -> dict:
    return {"error": {"code": exc.code, "message": exc.message,
                      "detail": exc.detail}}


def _run(fn: Callable[[], dict]) -> tuple[int, dict]:
    try:
        return 200, fn()
    except MediaError as exc:
        return exc.http_status, _envelope(exc)


def _int_param(query: dict, name: str, default: int | None) -> int | None:
    raw = query.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise MediaError("invalid_params", f"{name} must be an integer", 400)


def build_routes(service: MediaService) -> list[tuple[str, str, Handler]]:
    def start_video(body, query):
        payload = body or {}
        return _run(lambda: service.start_video_job(
            prompt=payload.get("prompt"), width=payload.get("width"),
            height=payload.get("height"), frames=payload.get("frames"),
            steps=payload.get("steps")))

    def start_music(body, query):
        payload = body or {}
        return _run(lambda: service.start_music_job(
            caption=payload.get("caption"), lyrics=payload.get("lyrics"),
            duration=payload.get("duration")))

    def cancel(body, query):
        return _run(service.cancel_job)

    def status(body, query):
        def call():
            return service.job_status(
                log_from=_int_param(query, "log_from", 0) or 0,
                job_id=_int_param(query, "job_id", None))
        return _run(call)

    return [
        ("POST", "/api/media/video", start_video),   # api:startVideoJob
        ("POST", "/api/media/music", start_music),   # api:startMusicJob
        ("POST", "/api/media/cancel", cancel),       # api:cancelJob
        ("GET", "/api/media/job", status),           # api:jobStatus
    ]
```

**验收（全模块回归）**
`cd /Users/aa/LocalModelDesk && python3 -m pytest tests/test_media_commands.py tests/test_media_executor.py tests/test_media_music3_cli.py tests/test_media_service.py tests/test_media_routes.py -q`

---

## T-media-14 reality gate：真出一条视频、一首歌、一次取消（人工 runbook）

**需求** spec 验收第 7 项。真实 H3 / Music 3 生成以分钟计并独占 128GB 统一内存，
环境测定为 NOT AVAILABLE 的自动验收项——**不进自动验收，不伪造证据**。

本任务先把下述步骤固化到
`docs/superpowers/runbooks/2026-08-31-media-reality-runbook.md`；该文件是 agent 可提交的
运行说明，不是验收证据。签核路径不在任务 artifact contract 内，agent 无权代写。

### 人工验收 runbook（RG-media）

前置：全模块装配完成（foundation/arbiter/resources/library/media 真实现在跑），
真权重齐备，台面服务已启动（dev 态 `python -m desk` 即可）。

1. **真出一条 5 秒视频**
   - 任一 HTTP 客户端（或 UI 视频面板）：
     `curl -sS -X POST http://127.0.0.1:8766/api/media/video -H 'Content-Type: application/json' -d '{"prompt":"A cinematic shot of rain on a quiet city street at night, neon reflections, stereo ambience.","width":512,"height":288,"frames":73,"steps":10}'`
   - 观察：响应 200 且 `status:"running"`；
     轮询 `GET /api/media/job?log_from=0` 日志持续增长；
   - 生成期间尝试加载聊天模型（UI 或 `POST /api/llm/load`）：**必须被拒**，
     机器可读码 `media_busy`；
   - 结束后：`~/Library/Application Support/LocalModelDesk/outputs/h3-<stamp>.mp4`
     存在，QuickTime 可播且有环境声；`GET /api/history` 新增一条 `kind:"video"`、
     `status:"done"`、params 含完整 prompt/width/height/frames/steps；
     `GET /api/desk-state` holder 回到空闲。
2. **真出一首 30 秒歌**
   - `curl -sS -X POST http://127.0.0.1:8766/api/media/music -H 'Content-Type: application/json' -d '{"caption":"synthwave night drive","lyrics":"city lights fading","duration":30}'`
   - 观察：`music3-<stamp>.wav` 存在且可听；历史新增 `kind:"music"` 一条。
3. **生成中途取消**
   - 再发起一条视频作业；日志开始滚动后
     `curl -sS -X POST http://127.0.0.1:8766/api/media/cancel`；
   - 观察：约 5 秒内 `pgrep -f mlx-h3` 为空（进程组整组消失）；
     `GET /api/media/job` 终态 `cancelled`；历史新增 `status:"cancelled"` 一条；
     arbiter 回到空闲（可立即成功加载一个聊天模型）。

**通过标准**：三步全部符合观察项，且期间无任何「exit 0 无文件却报成功」类假成功。
**签核**：人工通过后，把观察记录（日期、三步各自的输出文件名/历史 id）写入
`docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/media-reality.md`，并单独写一行
`VERDICT: PASS`。验收命令检查 runbook、非空签核及该标记——**由人写，不得由 agent 代写**。

**验收** `test -s /Users/aa/LocalModelDesk/docs/superpowers/runs/2026-08-31-localmodeldesk-app/signoffs/media-reality.md`

---

## 需求覆盖矩阵

| 需求 | 任务 |
|---|---|
| R-media-01（视频参数、H3 单点） | T-01、T-02（守卫）、T-05 |
| R-media-02（歌曲参数、Music 单点） | T-02、T-04、T-07 |
| R-media-03（流式进度） | T-03、T-11 |
| R-media-04（时间戳产出 + 历史） | T-05、T-07、T-09（取消也写历史）、T-12 |
| R-media-05（许可纪律） | T-06、T-08（无泄漏）、T-10 |
| R-media-06（exit 0 无文件 = 失败） | T-08 |
| R-media-07（取消） | T-03（进程组信号）、T-09 |
| 真实生成 | T-14（reality gate + runbook） |

## 计划内决定（备查）

1. **executor.spawn 不带 log_path 形参**（对设计 §3 的微缩）：日志累积在服务内存，
   没有任何消费者需要执行器落盘日志——YAGNI；接口收窄为 `spawn(cmd, extra_env)`。
2. **worker 内执行器异常映射为 `error/worker_failed`**：设计错误处理表未列此行，
   但「worker 内异常也必须走 finally 尾声」是设计原文；错误如实上报，不吞不装死。
3. **日志游标是绝对偏移**（含已截断部分）：截断后旧游标不会读串位，
   `next_log_from` 单调不减。
4. **测试态 `term_grace_s=0.2`**：TERM→KILL 宽限经构造注入，生产默认 5.0 秒。
5. **单点守卫的范围是 `desk/` 树**：根目录旧脚本（run-h3.sh 等）的删除属清理阶段，
   由 census 重跑命令把守；media 的静态测试只保证 desk/ 内不出现第二份 H3 参数。
6. **签核文件即 reality-gate 验收**：命令要求人工签核与 `VERDICT: PASS`，且签核路径不在
   agent 的 artifact contract 内，机械阻止伪造生成证据。
