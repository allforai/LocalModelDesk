# 代码摘录：spawn 若抛异常（真正的"解释器不存在"分支）未被捕获

本次实测中 venv_python 实际存在（dev 模式 = sys.executable），因此没能触发
`subprocess.Popen` 因可执行文件不存在而抛 `FileNotFoundError` 的分支；实测改为
观察到"解释器存在但 mlx_lm 模块不存在"的相邻分支（见 q09-04/q09-05/q09-06）。

以下为静态代码摘录，说明若 spawn 本身抛异常（例如 python 可执行文件真的不存在），
控制流会怎样——仅代码阅读，未在本次实测中触发验证。

## desk/llm/service.py 第 200-206 行（`_load_worker`）

```
200	        proc = self._backend.spawn(python, model_dir, self._port, log_path)
201	        with self._lock:
202	            if generation != self._load_generation:
203	                proc.terminate()
204	                return
205	            self._proc = proc
206	        deadline = time.monotonic() + self._load_timeout_s
```

第 200 行 `self._backend.spawn(...)` 调用外层没有 try/except。`_load_worker` 由
`load()`（第 156-162 行）以 `threading.Thread(..., daemon=True)` 启动：

```
154	        with self._lock:
155	            self._token = acquired.get("token")
156	            self._load_thread = threading.Thread(
157	                target=self._load_worker,
158	                args=(entry, model_dir, Path(roots.venv_python), self._log_path(roots), generation),
159	                daemon=True,
160	                name="llm-load",
161	            )
162	            self._load_thread.start()
163	            return self._state.to_dict()
```

`self._token`（重活令牌，来自 `self._arbiter.acquire_heavy(...)`，第 144 行）在启动线程
*之前* 已经写入 `self._token`；`self._state` 在 `load()` 第 131 行已经设为
`LlmState(status=STATUS_LOADING, ...)`。若第 200 行的 `spawn()` 抛出异常（未被任何
try/except 捕获），该守护线程会带着未处理异常终止（异常经由
`threading.excepthook` 打到 stderr），既不会走到第 217 行的 `STATUS_ERROR` 赋值，
也不会走到 `self._arbiter.release_heavy(token)`。`self._state` 与 `self._token`
将保持在线程启动前的值——即 `status=loading`、`self._token` 非空——没有其他代码路径
会在此后主动把它们改回来。

## desk/llm/backend.py 第 46-56 行（`MlxLmBackend.spawn`）

```
46	    def spawn(
47	        self, python: Path, model_path: Path, port: int, log_path: Path
48	    ) -> BackendProcess:
49	        log_path.parent.mkdir(parents=True, exist_ok=True)
50	        argv = [
51	            str(python), "-s", "-m", "mlx_lm", "server",
52	            "--model", str(model_path), "--host", "127.0.0.1",
53	            "--port", str(port),
54	        ]
55	        with log_path.open("ab") as log_file:
56	            return subprocess.Popen(argv, stdout=log_file, stderr=log_file)
```

`subprocess.Popen(argv, ...)`：若 `argv[0]`（解释器路径）在文件系统上不存在，
Python 标准库在此处同步抛出 `FileNotFoundError`（不是子进程以非零码退出，是
`Popen()` 调用本身失败），该异常沿调用栈从 `spawn()` 传到 `_load_worker()`，如上一节所述，无人捕获。
