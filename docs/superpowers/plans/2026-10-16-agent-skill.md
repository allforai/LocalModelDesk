# 本机 agent 能力（lmdesk + skill + 多选安装）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Claude Code、Codex、pi、DeepSeek Harness 通过 `lmdesk` 命令使用台面的本地对话模型和图片生成（含图片会话管理），并在设置页由用户多选安装 skill。

**Architecture:**
- `lmdesk` 是一个只用标准库的 Python 命令行（`desk/agent_cli/`），通过 HTTP 调用台面内部的 `/api`。
- 排队等待、按需换模型、续等都在命令行进程内完成，服务端不加队列。
- 服务端只补几处小改动：对话计数、模型来源、带 id 的取消、预检接口、版本号、安装接口。
- 安装方式是软链接：把 app 包（或仓库）里的 skill 和命令行链接到各 agent 的 skill 目录和 `~/.local/bin`。

**Tech Stack:**
- Python 3.13 标准库（命令行与服务端）、pytest；
- 原生 ES modules，用 `node --test` 测纯函数；
- Playwright e2e（`tests/e2e`）；
- Swift（菜单栏）及 `macos/harness/ShellHarness.swift`；
- bash（打包与卸载脚本）。

**Spec:** `docs/superpowers/specs/2026-10-16-agent-skill-design.md`（条目编号 A-xx，下文直接引用）

## Global Constraints

- skill 名称和目录名都是 `local-model-desk`；`description` ≤ 1024 字符；SKILL.md 第一行是 `---`（A-80）。
- 退出码：0 成功；1 其他错误；2 参数错误或会话名歧义；3 等待超时；4 内存不足；5 模型、会话或尝试不存在；6 被沙箱拦截（A-13）。
- `--timeout` 默认 1800 秒。轮询间隔从 2s 起，每次 ×1.5，最长 5s；等待提示每 15s 一行（A-23）。
- 界面最近对话保护的窗口是 300 秒（A-40），写成常量 `UI_CHAT_RECENT_S = 300`。
- 命令行改变状态的请求一律带 `"origin": "agent"`（A-05）。
- `desk/agent_cli/` 只 import 标准库和 `desk.agent_cli.*`，不 import `desk` 的其他模块（A-01）。
- 端口取 `LMD_SHELL_PORT`，不合法或未设置时用 8766（A-30）。
- 安装位置（A-50）：
  - `~/.claude/skills/local-model-desk`
  - `~/.codex/skills/local-model-desk`（以 Task 1 的实测结论为准）
  - `~/.pi/agent/skills/local-model-desk`
  - `~/.dsh/skills/local-model-desk`
  - 命令行：`~/.local/bin/lmdesk`
- 卸载与安装都绝不删除真实的文件或目录，也绝不删除指向别处的链接（A-55）。
- 台面不会自己安装任何一项（A-56）；也不会自动改链接（A-72）。
- 新增的 HTTP 路由必须同时挂在 `desk/runtime.py` 和 `desk/testing/harness.py`，并加进 `tests/test_e2e_harness_assembly.py::production_route_table`。
- 只构建到 `dist/`，不装到 `/Applications`。
- 台面未发布：不写兼容或迁移代码。
- 每个任务都按 TDD 走：先写测试、看它失败，再写实现、看它通过，最后提交。提交信息结尾加：
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

## Review Focus

1. **会话名是中文、带空格，或者和另一个会话的 id 前缀相同**：按名字匹配要精确相等（去掉首尾空白），id 要精确等于 32 位 hex。不能做前缀匹配，否则会生成到错的会话里。（测试在 Task 9）
2. **`--out` 指向不存在的目录，或者指向一个目录**：
   - 目录不存在：自动创建上级目录。
   - 指向已存在的目录：在其中用原文件名保存。
   - 目标文件已存在：直接覆盖，并在 stderr 提示「已覆盖」。
   （测试在 Task 9）
3. **用户的 HOME 里 `~/.claude/skills` 本身就是一个软链接**（比如同步工具建的）：安装时要跟随它写进链接目标里，不能把它替换掉。（测试在 Task 10）
4. **台面在命令行等待途中被用户退出**：轮询时出现连接被拒绝，不能当作沙箱拦截（6），也不能卡到超时；要按「台面已退出」以退出码 1 报错，并保留续等提示。（测试在 Task 9）
5. **`ask` 的 stdin 不是终端但内容为空**（agent 环境里很常见，stdin 是 `/dev/null`）：不能把空内容拼进消息，也不能因为等待 stdin 而卡住。（测试在 Task 8）

---

## File Structure

**新建：**
- 命令行包 `desk/agent_cli/`：
  - `__init__.py`：包说明。
  - `__main__.py`：`python -m desk.agent_cli` 入口。
  - `errors.py`：退出码常量和 `CliError`。
  - `version.py`：解析 resources root，读版本号。
  - `client.py`：HTTP JSON 客户端，以及连接失败分类。
  - `discovery.py`：端口、所在 app 包、后台拉起 app。
  - `decide.py`：纯函数 `decide()` 与 `Snapshot`、`Decision`。
  - `waiter.py`：退避等待与进度输出。
  - `chat.py`：`status`、`models`、`ask`。
  - `images.py`：`image sessions|new|show|gen|wait|rename`。
  - `cli.py`：argparse、输出格式、信号处理、退出码。
- 安装模块包 `desk/agent_skill/`：
  - `__init__.py`
  - `bundled/local-model-desk/SKILL.md`
  - `targets.py`：安装目标表与检测。
  - `installer.py`：链接状态判定、安装与卸载。
  - `service.py`：`AgentSkillService`，负责状态、应用、检查、预检。
  - `routes.py`：`/api/agent-skill*` 和 `/api/agent/precheck`。
- `scripts/lmdesk`：开发态入口脚本。
- 前端：
  - `desk/static/js/pure/agent_skill.js`：设置页纯逻辑。
  - `desk/static/js/pure/agent_switch.js`：聊天页切换提示的纯逻辑。
  - `desk/static/js/panes/agent_skill.js`：设置页「本机 agent」区域。
- 测试：
  - `tests/agent_cli/__init__.py`
  - `tests/agent_cli/test_decide.py`
  - `tests/agent_cli/test_waiter.py`
  - `tests/agent_cli/test_client.py`
  - `tests/agent_cli/test_discovery.py`
  - `tests/agent_cli/test_chat_cli.py`
  - `tests/agent_cli/test_image_cli.py`
  - `tests/agent_cli/cli_helpers.py`
  - `tests/test_agent_skill_installer.py`
  - `tests/test_agent_skill_routes.py`
  - `tests/test_agent_skill_md.py`
  - `tests/test_llm_agent_signals.py`
  - `tests/test_media_cancel_job_id.py`
  - `tests/test_uninstall_agent_links.py`
  - `tests/js/agent_skill.test.js`
  - `tests/js/agent_switch.test.js`
  - `tests/e2e/test_agent_skill_settings.py`
  - `tests/e2e/test_agent_switch_notice.py`

**修改：**
- 服务端：
  - `desk/llm/service.py`：对话计数、界面最近对话、模型来源、预检。
  - `desk/llm/routes.py`：把 `origin` 透传给 load。
  - `desk/media/service.py`：带 `job_id` 的取消，图片预检。
  - `desk/media/routes.py`：取消接口接受 `job_id`。
  - `desk/runtime.py`：挂新路由；`/api/state` 增加 `version` 和 `agent_skill_stale`。
  - `desk/testing/harness.py`：同上。
  - `tests/test_e2e_harness_assembly.py`：路由表。
- 前端：
  - `desk/static/index.html`：设置区域和聊天提示的标记。
  - `desk/static/js/api.js`：新路由。
  - `desk/static/js/panes/settings.js`：挂载新区域。
  - `desk/static/js/panes/chat.js`：切换提示。
  - `desk/static/js/main.js`：把 settings 的 ctx 透传给新区域。
  - 样式文件：在 `desk/static/` 下用 `ls desk/static/*.css desk/static/css 2>/dev/null` 找到放 `.settings-section` 的那个文件。
- Swift：
  - `macos/ShellStatus.swift`
  - `macos/StatusItemController.swift`
  - `macos/harness/ShellHarness.swift`
  - `tests/test_shell_status.py`
- 脚本：
  - `scripts/build-app.sh`
  - `scripts/uninstall-app.sh`

---

### Task 1: 实测 Codex 读不读 `~/.codex/skills`（A-51）

这是一个 spike，不写产品代码。结论决定 Task 10 里 `codex` 那一行的链接位置。

**Files:**
- Modify: `docs/superpowers/specs/2026-10-16-agent-skill-design.md`（只改 A-51，写入结论）

- [ ] **Step 1: 放一个探针 skill**

```bash
mkdir -p ~/.codex/skills/lmd-probe-7f3a
cat > ~/.codex/skills/lmd-probe-7f3a/SKILL.md <<'EOF'
---
name: lmd-probe-7f3a
description: Probe skill. When the user says "probe 7f3a", reply exactly "PROBE-7F3A-SEEN".
---
Reply exactly "PROBE-7F3A-SEEN".
EOF
```

- [ ] **Step 2: 让 Codex 列出它看到的 skill**

```bash
cd "$(mktemp -d)" && codex exec --skip-git-repo-check "List the names of every skill available to you, one per line, nothing else." 2>&1 | tail -40
```

预期结果有两种：输出里出现 `lmd-probe-7f3a`，说明 Codex 读这个目录；没出现，说明不读。

- [ ] **Step 3: 换到 `~/.agents/skills` 做对照**

```bash
mv ~/.codex/skills/lmd-probe-7f3a ~/.agents/skills/lmd-probe-7f3a
cd "$(mktemp -d)" && codex exec --skip-git-repo-check "List the names of every skill available to you, one per line, nothing else." 2>&1 | tail -40
```

预期：输出里出现 `lmd-probe-7f3a`。这一步用来确认 Step 2 的方法本身有效。如果这里也没出现，说明 `codex exec` 列不出 skill，要改用交互式 `codex` 输入同样的提问再试一次。

- [ ] **Step 4: 清理探针**

```bash
rm -rf ~/.agents/skills/lmd-probe-7f3a ~/.codex/skills/lmd-probe-7f3a
ls ~/.agents/skills ~/.codex/skills
```

预期：两处都不再有 `lmd-probe-7f3a`，其他 skill 原样都在。

- [ ] **Step 5: 把结论写回 A-51 并提交**

在 A-51 末尾追加一行，二选一：
- `- **实测（2026-10-16，codex-cli 0.160.1）**：读取 ~/.codex/skills，codex 行用 ~/.codex/skills。`
- `- **实测（…）**：不读 ~/.codex/skills，codex 行用 ~/.agents/skills，并显示「同时对 pi、DeepSeek Harness 生效」。`

```bash
git add docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "docs(spec): A-51 实测 Codex skill 目录

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**后续影响**：如果结论是 `~/.agents/skills`，Task 10 的 `TARGETS` 里 codex 行改为 `Path(".agents/skills/local-model-desk")`，并把 `shared_note` 设为 `"同时对 pi、DeepSeek Harness 生效"`。Task 13 会把它显示出来。

---

### Task 2: LlmService 记录对话计数、界面最近对话和模型来源（A-40、A-43）

**Files:**
- Modify: `desk/llm/service.py`
- Modify: `desk/llm/routes.py`（`_load`）
- Test: `tests/test_llm_agent_signals.py`

**Interfaces:**
- 产出：
  - `LlmService(..., clock: Callable[[], float] = time.monotonic)`
  - `LlmService.load(key, origin: str = "ui")`
  - `LlmService.status()` 额外返回顶层键 `active_chats: int`、`ui_chat_recent: bool`、`loaded_by: "agent" | "ui" | None`
  - 模块常量 `UI_CHAT_RECENT_S = 300.0`
- 约定：`chat_completion(request)` 和 `chat_stream(request)` 通过 `request.get("origin") == "agent"` 判断请求是否来自 agent。

- [ ] **Step 1: 写失败的测试**

```python
"""A-40/A-43: chat counting, recent UI chat, and who loaded the model."""
from desk.llm.backend import BackendHttpError
from tests.llm.llm_fakes import make_loaded, make_service

OK = {
    "choices": [{"message": {"content": "答"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}
STREAM = [
    {"choices": [{"delta": {"content": "答"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}],
     "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_status_reports_zero_chats_and_no_recent_ui_chat_initially(tmp_path):
    testbed = make_service(tmp_path)
    status = testbed.service.status()
    assert status["active_chats"] == 0
    assert status["ui_chat_recent"] is False
    assert status["loaded_by"] is None


def test_loaded_by_follows_the_load_origin(tmp_path):
    testbed = make_service(tmp_path)
    testbed.service.load("glm", origin="agent")
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "agent"
    testbed.service.load("glm")
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "ui"


def test_unload_clears_loaded_by(tmp_path):
    testbed = make_loaded(tmp_path)
    testbed.service.unload()
    assert testbed.service.status()["loaded_by"] is None


def test_ui_chat_marks_recent_for_300_seconds_and_agent_chat_does_not(tmp_path):
    clock = Clock()
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK}, clock=clock)
    testbed.service.chat_completion({"messages": [], "origin": "agent"})
    assert testbed.service.status()["ui_chat_recent"] is False
    testbed.service.chat_completion({"messages": []})
    assert testbed.service.status()["ui_chat_recent"] is True
    clock.now += 299
    assert testbed.service.status()["ui_chat_recent"] is True
    clock.now += 2
    assert testbed.service.status()["ui_chat_recent"] is False


def test_stream_counts_while_open_and_decrements_once_on_finish(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    first = next(events)
    assert first is not None
    assert testbed.service.status()["active_chats"] == 1
    list(events)
    assert testbed.service.status()["active_chats"] == 0


def test_stream_closed_midway_decrements_exactly_once(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    next(events)
    events.close()
    events.close()
    assert testbed.service.status()["active_chats"] == 0


def test_stream_never_iterated_does_not_leak_a_count(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    del events
    assert testbed.service.status()["active_chats"] == 0


def test_completion_error_decrements(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_error": BackendHttpError("boom")})
    try:
        testbed.service.chat_completion({"messages": []})
    except Exception:
        pass
    assert testbed.service.status()["active_chats"] == 0


def test_load_route_passes_origin(tmp_path):
    from desk.llm.routes import build_routes

    testbed = make_service(tmp_path)
    load = next(r for r in build_routes(testbed.service) if r.path == "/api/llm/load")
    result = load.handler({"key": "glm", "origin": "agent"})
    assert result.status == 202
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "agent"
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_llm_agent_signals.py -v`
预期：FAIL，报 `KeyError: 'active_chats'`，或者 `load() got an unexpected keyword argument 'origin'`。

- [ ] **Step 3: 实现**

在 `desk/llm/service.py` 的 import 区后加常量：

```python
# A-40：界面最近这么多秒内对话过，agent 就不换模型、也不让生图卸掉对话模型。
UI_CHAT_RECENT_S = 300.0
```

`__init__` 签名加 `clock: Any = time.monotonic`，在函数体末尾（`self._closed = False` 之后）加：

```python
        self._clock = clock
        self._active_chats = 0
        self._last_ui_chat: float | None = None
        self._loaded_by: str | None = None
```

`load` 改签名，并在启动加载线程前记下来源：

```python
    def load(self, key: Any, origin: str = "ui") -> dict[str, Any]:
```

在 `self._token = acquired.get("token")` 这一行之前加：

```python
            self._loaded_by = "agent" if origin == "agent" else "ui"
```

`close()`、`unload()`，以及 `status()` 里把状态置回 IDLE 或 ERROR 的每个分支，都在赋值 `self._state = LlmState(status=STATUS_IDLE)`（或 ERROR）的同一处，加上 `self._loaded_by = None`。用 `grep -n "LlmState(status=STATUS_IDLE)\|status=STATUS_ERROR" desk/llm/service.py` 逐个定位。`_on_desk_state` 里驱逐导致的 ERROR 分支也要加。

在 `_chat_precheck` 前加计数辅助：

```python
    def _chat_begin(self, request: dict[str, Any]) -> None:
        with self._lock:
            self._active_chats += 1
            if request.get("origin") != "agent":
                self._last_ui_chat = self._clock()

    def _chat_end(self, request: dict[str, Any]) -> None:
        with self._lock:
            self._active_chats = max(0, self._active_chats - 1)
            if request.get("origin") != "agent":
                self._last_ui_chat = self._clock()
```

`chat_completion` 在 precheck 通过后包上计数：

```python
    def chat_completion(self, request: dict[str, Any]) -> dict[str, Any]:
        """Forward a non-streaming chat request without fabricating response data."""
        entry = self._chat_precheck(request)
        self._chat_begin(request)
        try:
            return self._chat_completion(request, entry)
        finally:
            self._chat_end(request)
```

把原来 `chat_completion` 里从 `payload = self._upstream_payload(request, entry)` 开始的函数体，原样移到新方法 `def _chat_completion(self, request, entry)` 中。

`chat_stream` 改成在生成器真正开始时计数：用 `try/finally` 包住，生成器被关闭或被回收时也会走到 finally。

```python
    def chat_stream(self, request: dict[str, Any]):
        """Yield separated chat deltas and one terminal event from the resident model."""
        entry = self._chat_precheck(request)
        payload = self._upstream_payload(request, entry)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        return self._counted_stream(request, payload, entry)

    def _counted_stream(self, request, payload, entry):
        self._chat_begin(request)
        try:
            yield from self._stream_events(payload, entry)
        finally:
            self._chat_end(request)
```

说明：生成器只有在第一次 `next()` 时才会执行到 `_chat_begin`，所以一次都没迭代过的流不计数，满足 `test_stream_never_iterated_does_not_leak_a_count`。`close()` 会触发 `GeneratorExit` 走到 finally，第二次 `close()` 不会再执行 finally。

`status()` 的返回值：先看现有 `return` 返回的字典（键有 `state`、`loaded_model`），在构造它的地方合并新键：

```python
            recent = self._last_ui_chat is not None and self._clock() - self._last_ui_chat < UI_CHAT_RECENT_S
            result = {..., "active_chats": self._active_chats, "ui_chat_recent": recent,
                      "loaded_by": self._loaded_by if self._state.status == STATUS_LOADED else None}
```

这里的 `...` 是现有的两个键，原样保留，只追加三个新键。

`desk/llm/routes.py` 的 `_load`：

```python
        state = service.load(body.get("key"), origin=body.get("origin") or "ui")
```

- [ ] **Step 4: 运行新测试和全部 LLM 测试**

运行：`python -m pytest tests/test_llm_agent_signals.py tests/llm tests/test_llm_budget_wiring.py -q`
预期：全部 PASS。如果有现有测试断言 `status()` 字典完全相等而失败，就把那个断言改成只比较 `state` 和 `loaded_model` 两个键，不要删掉新键。

- [ ] **Step 5: 提交**

```bash
git add desk/llm/service.py desk/llm/routes.py tests/test_llm_agent_signals.py tests/llm
git commit -m "feat(llm): 对话计数、界面最近对话与模型来源（A-40/A-43）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 媒体取消接受 `job_id`（A-42）

**Files:**
- Modify: `desk/media/service.py`（`cancel_job`）
- Modify: `desk/media/routes.py`（`cancel`）
- Test: `tests/test_media_cancel_job_id.py`

**Interfaces:**
- 产出：
  - `MediaService.cancel_job(job_id: int | None = None) -> dict`。`job_id` 不是当前正在跑的任务时，抛出 `MediaError("job_not_running", …, 409)`。
  - `POST /api/media/cancel` 的请求体可以带 `{"job_id": N}`。

- [ ] **Step 1: 写失败的测试**

先看 `tests/media_fakes.py` 里有没有能直接构造「正在运行的媒体服务」的工厂：`grep -n "^def " tests/media_fakes.py`。下面用 harness 写，最稳。

```python
"""A-42: cancel names its job, so an agent never cancels someone else's."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, cancellable_media_steps


def _post(url, body):
    req = Request(url, data=json.dumps(body).encode(), method="POST",
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def _start_image(h):
    _, session = _post(h.base_url + "/api/media-sessions/image", {})
    status, job = _post(h.base_url + "/api/media/image",
                        {"session_id": session["id"], "prompt": "猫", "width": 512, "height": 512, "steps": 4})
    assert status == 200, job
    return job


def test_cancel_with_a_stale_job_id_is_refused_and_leaves_the_running_job(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
                             media_script=script) as h:
        job = _start_image(h)
        status, body = _post(h.base_url + "/api/media/cancel", {"job_id": job["job_id"] - 1})
        assert status == 409
        assert body["error"]["code"] == "job_not_running"
        assert h.media.job_status()["status"] == "running"
        status, body = _post(h.base_url + "/api/media/cancel", {"job_id": job["job_id"]})
        assert status == 200


def test_cancel_without_job_id_keeps_todays_behavior(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True,
                             media_script=script) as h:
        _start_image(h)
        status, _ = _post(h.base_url + "/api/media/cancel", {})
        assert status == 200
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_media_cancel_job_id.py -v`
预期：第一个测试 FAIL。因为现在的取消接口不看 `job_id`，返回的是 200。

- [ ] **Step 3: 实现**

`desk/media/service.py`：

```python
    def cancel_job(self, job_id: int | None = None) -> dict:
        if job_id is not None:
            with self._lock:
                current, status = self._state["job_id"], self._state["status"]
            if current != job_id or status != "running":
                raise MediaError("job_not_running", f"作业 {job_id} 不在运行，未取消任何作业", 409)
        return self._cancel("user")
```

`desk/media/routes.py`：

```python
    def cancel(body, _query):
        job_id = (body or {}).get("job_id")
        if job_id is not None and (isinstance(job_id, bool) or not isinstance(job_id, int)):
            return 400, {"error": {"code": "invalid_params", "message": "job_id 须为整数", "detail": {}}}
        return _run(lambda: service.cancel_job(job_id))
```

- [ ] **Step 4: 运行这个测试和全部媒体测试**

运行：`python -m pytest tests/test_media_cancel_job_id.py tests -q -k "media or cancel"`
预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add desk/media/service.py desk/media/routes.py tests/test_media_cancel_job_id.py
git commit -m "feat(media): 取消接口接受 job_id，不误取消别人的作业（A-42）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 版本号、预检接口，以及路由在两边挂载（A-44、A-45、A-32 的服务端部分）

**Files:**
- Create: `desk/agent_cli/__init__.py`、`desk/agent_cli/version.py`
- Create: `desk/agent_skill/__init__.py`、`desk/agent_skill/routes.py`（这一步只放预检路由）
- Modify: `desk/llm/service.py`（`precheck_load`）
- Modify: `desk/media/service.py`（`precheck_image`）
- Modify: `desk/runtime.py`、`desk/testing/harness.py`
- Modify: `tests/test_e2e_harness_assembly.py`
- Test: `tests/test_agent_skill_routes.py`（新建，先写预检和版本两部分）

**Interfaces:**
- 产出：
  - `desk.agent_cli.version.resources_root() -> Path`：返回 `desk/agent_cli/version.py` 往上三级目录，即 `desk` 包的父目录。打包后是 `Contents/Resources`，开发时是仓库根目录。
  - `desk.agent_cli.version.read_version(root: Path) -> str`：优先读 `root/bundle.json` 的 `bundle_version`，其次读 `root/packaging/VERSION`，都没有时返回 `"unknown"`。
  - `LlmService.precheck_load(key: str) -> dict`：返回 `{ok, reason, release, memory_warning}`。key 不存在时抛 `LlmRejected(ERR_MODEL_NOT_FOUND)`。
  - `MediaService.precheck_image(width: int, height: int, steps: int) -> dict`：返回结构同上。
  - `desk.agent_skill.routes.build_precheck_routes(llm, media) -> list[tuple[method, path, handler(req) -> Response]]`
  - `/api/state` 返回 `arbiter.desk_state()` 的内容，外加 `version`；`agent_skill_stale` 在 Task 11 加。

- [ ] **Step 1: 写失败的测试**

```python
"""A-44/A-45: /api/state carries the version; precheck answers without changing state."""
import json
from urllib.request import urlopen
from urllib.error import HTTPError

from desk.agent_cli.version import read_version, resources_root
from desk.testing import launch_test_harness


def _get(url):
    try:
        with urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def test_read_version_prefers_bundle_json(tmp_path):
    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging" / "VERSION").write_text("1.2.3\n")
    assert read_version(tmp_path) == "1.2.3"
    (tmp_path / "bundle.json").write_text(json.dumps({"bundle_version": "9.9.9"}))
    assert read_version(tmp_path) == "9.9.9"


def test_read_version_unknown_when_nothing_found(tmp_path):
    assert read_version(tmp_path) == "unknown"


def test_resources_root_is_the_parent_of_the_desk_package():
    assert (resources_root() / "desk" / "agent_cli" / "version.py").is_file()


def test_state_reports_version(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, state = _get(h.base_url + "/api/state")
        assert status == 200
        assert state["version"] == read_version(resources_root())
        assert "holder" in state


def test_precheck_chat_for_an_idle_desk_is_ok(tmp_path):
    with launch_test_harness(tmp_path, model_states={"glm": "present"}) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=chat&model=glm")
        assert status == 200
        assert body["ok"] is True
        assert set(body) >= {"ok", "reason", "release", "memory_warning"}
        assert h.llm.status()["state"]["status"] == "idle"


def test_precheck_chat_unknown_model_is_404(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=chat&model=nope")
        assert status == 404
        assert body["error"]["code"] == "model_not_found"


def test_precheck_image_is_ok_when_idle(tmp_path):
    with launch_test_harness(tmp_path, model_states={"qwen-image": "present"}, image_runtime=True) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=image&width=512&height=512&steps=4")
        assert status == 200
        assert body["ok"] is True


def test_precheck_bad_op_is_400(tmp_path):
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent/precheck?op=video")
        assert status == 400
```

`model_states` 的 key 用 harness 目录里真实存在的对话模型。先运行 `python -c "from desk.resources.catalog import list_catalog; print([e.key for e in list_catalog() if e.group=='chat'])"` 确认 `glm` 在列表里；不在就换成列表里的第一个。

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_agent_skill_routes.py -v`
预期：FAIL，报 `ModuleNotFoundError: desk.agent_cli`。

- [ ] **Step 3: 实现 `desk/agent_cli/__init__.py` 与 `version.py`**

```python
"""lmdesk：给本机 agent 用的台面命令行。只用标准库，不 import desk 的其他模块（A-01）。"""
```

```python
"""Resources root and version, shared by the CLI and the desk's /api/state (A-32)."""
from __future__ import annotations

import json
from pathlib import Path


def resources_root() -> Path:
    """Contents/Resources inside the app bundle, or the repo root in development."""
    return Path(__file__).resolve().parents[2]


def read_version(root: Path) -> str:
    try:
        data = json.loads((root / "bundle.json").read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("bundle_version"), str):
            return data["bundle_version"]
    except (OSError, ValueError):
        pass
    try:
        text = (root / "packaging" / "VERSION").read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    return "unknown"
```

- [ ] **Step 4: 实现两个预检方法**

`desk/llm/service.py`：把 `load` 里组装 `acquire_heavy` 参数的那段代码抽成一个复用函数，再加 `precheck_load`。

```python
    def _heavy_request(self, entry: Any) -> dict[str, Any]:
        model_dir = Path(self._paths.resolve_paths().models_root) / entry.relpath
        return {"config": _read_model_config(model_dir), "weights_gb": getattr(entry, "gb", None)}

    def precheck_load(self, key: str) -> dict[str, Any]:
        """A-45: what acquire_heavy would answer for loading *key*, without acquiring."""
        entry = self._find_entry(key) if isinstance(key, str) else None
        if entry is None:
            raise LlmRejected(ERR_MODEL_NOT_FOUND, f"未找到模型: {key}")
        answer = self._arbiter.can_start_heavy("llm", params=self._heavy_request(entry), key=entry.key)
        return {"ok": bool(answer.get("ok")), "reason": answer.get("reason"),
                "release": list(answer.get("release") or []), "memory_warning": answer.get("memory_warning")}
```

然后把 `load` 里 `acquire_heavy(..., params={"config": ..., "weights_gb": ...}, ...)` 改为 `params=self._heavy_request(entry)`，保证两处用同一份参数。

`desk/media/service.py`（放在 `start_image_job` 之后）：

```python
    def precheck_image(self, width: int, height: int, steps: int) -> dict:
        """A-45: what the arbiter would answer for an image job of this size, without starting one."""
        params = {"prompt": "", "width": width, "height": height, "steps": steps}
        answer = self._arbiter.can_start_heavy("image", params=params, key="qwen-image")
        return {"ok": bool(answer.get("ok")), "reason": answer.get("reason"),
                "release": list(answer.get("release") or []), "memory_warning": answer.get("memory_warning")}
```

先用 `grep -n "def can_start_heavy" -A3 desk/arbiter/core.py` 确认 `can_start_heavy` 的 kind 用的是 `"image"`。`_admit_heavy` 里已经是 `can_start_heavy(kind, ...)`，其中 kind 为 `"image"`。

- [ ] **Step 5: 实现路由 `desk/agent_skill/__init__.py`、`routes.py`**

```python
"""本机 agent：skill 安装状态、安装/卸载、检查与预检接口。"""
```

```python
"""HTTP routes for the agent capability (A-41, A-45). Returns DeskApp-style (method, path, handler(req))."""
from __future__ import annotations

from desk.app import Response
from desk.llm.state import LlmRejected


def _error(status: int, code: str, message: str) -> Response:
    return Response(status, {"error": {"code": code, "message": message}})


def _int(query: dict, name: str):
    try:
        return int(query.get(name, ""))
    except ValueError:
        return None


def build_precheck_routes(llm, media) -> list:
    def precheck(req):
        op = req.query.get("op")
        if op == "chat":
            try:
                return Response(200, llm.precheck_load(req.query.get("model") or ""))
            except LlmRejected as exc:
                return _error(404 if exc.code == "model_not_found" else 409, exc.code, exc.message)
        if op == "image":
            width, height, steps = _int(req.query, "width"), _int(req.query, "height"), _int(req.query, "steps")
            if None in (width, height, steps):
                return _error(400, "invalid_params", "width/height/steps 须为整数")
            return Response(200, media.precheck_image(width, height, steps))
        return _error(400, "invalid_params", "op 只能是 chat 或 image")

    return [("GET", "/api/agent/precheck", precheck)]
```

- [ ] **Step 6: 挂进生产环境和测试台面，`/api/state` 加版本号**

`desk/runtime.py`：import `from .agent_cli.version import read_version` 和 `from .agent_skill.routes import build_precheck_routes`。在 `_mount_routes` 末尾的 `app.add_routes([...])` 之前加：

```python
    app.add_routes(build_precheck_routes(llm, media))
```

把 `("GET", "/api/state", lambda _req: arbiter.desk_state())` 改为：

```python
        ("GET", "/api/state", lambda _req: {**arbiter.desk_state(), "version": read_version(roots.resources_root)}),
```

`desk/testing/harness.py`：在 `_mount_routes` 的 `table` 列表里同样处理，改 `/api/state` 那一行，并在列表末尾加 `*build_precheck_routes(llm, media),`。import 方式与 runtime 相同，用绝对路径 `from desk.agent_skill.routes import build_precheck_routes`、`from desk.agent_cli.version import read_version`。

`tests/test_e2e_harness_assembly.py::production_route_table` 的 `table.update({...})` 里加入 `("GET", "/api/agent/precheck")`。

- [ ] **Step 7: 运行测试**

运行：`python -m pytest tests/test_agent_skill_routes.py tests/test_e2e_harness_assembly.py tests/llm -q`
预期：全部 PASS。

- [ ] **Step 8: 提交**

```bash
git add desk/agent_cli desk/agent_skill desk/llm/service.py desk/media/service.py desk/runtime.py desk/testing/harness.py tests/test_agent_skill_routes.py tests/test_e2e_harness_assembly.py
git commit -m "feat(agent): /api/state 带版本号，新增只读预检接口（A-44/A-45）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 命令行的基础：错误、HTTP 客户端、服务发现（A-13、A-30、A-31、A-33）

**Files:**
- Create: `desk/agent_cli/errors.py`、`desk/agent_cli/client.py`、`desk/agent_cli/discovery.py`
- Test: `tests/agent_cli/__init__.py`（空文件）、`tests/agent_cli/test_client.py`、`tests/agent_cli/test_discovery.py`

**Interfaces:**
- 产出：
  - `errors`：
    - 常量 `EXIT_OK=0, EXIT_ERROR=1, EXIT_USAGE=2, EXIT_TIMEOUT=3, EXIT_MEMORY=4, EXIT_NOT_FOUND=5, EXIT_SANDBOX=6`；
    - `class CliError(Exception)`，属性有 `exit_code: int`、`code: str`、`message: str`、`hint: str | None`。
  - `client`：
    - `class Unreachable(Exception)`，属性 `kind: Literal["refused", "sandbox", "other"]`、`detail: str`；
    - `class HttpError(Exception)`，属性 `status: int`、`code: str`、`message: str`、`detail: dict`；
    - `class DeskClient`：构造参数为 `(base_url: str, timeout: float = 30.0)`，方法有 `.get(path, query: dict | None = None)`、`.post(path, body: dict | None = None)`、`.patch(path, body)`，返回解析后的 JSON。
  - `discovery`：
    - `port_from_env(env: Mapping[str, str]) -> int`
    - `app_bundle_of(path: Path) -> Path | None`
    - `connect(env, *, here: Path, launcher, sleep, clock, start_timeout_s=60.0) -> DeskClient`

- [ ] **Step 1: 写失败的测试**

`tests/agent_cli/test_client.py`：

```python
import errno
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from desk.agent_cli.client import DeskClient, HttpError, Unreachable, classify_os_error


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/ok"):
            self._send(200, {"path": self.path})
        elif self.path == "/obj-error":
            self._send(409, {"error": {"code": "media_busy", "message": "忙", "detail": {"x": 1}}})
        else:
            self._send(404, {"error": "会话不存在"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self._send(200, {"echo": json.loads(self.rfile.read(n) or b"{}")})


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_get_with_query_and_post_body(server):
    c = DeskClient(server)
    assert c.get("/ok", {"a": "中 文"})["path"] == "/ok?a=%E4%B8%AD+%E6%96%87"
    assert c.post("/x", {"k": 1}) == {"echo": {"k": 1}}


def test_object_error_envelope(server):
    with pytest.raises(HttpError) as exc:
        DeskClient(server).get("/obj-error")
    assert (exc.value.status, exc.value.code, exc.value.message, exc.value.detail) == (409, "media_busy", "忙", {"x": 1})


def test_string_error_envelope(server):
    with pytest.raises(HttpError) as exc:
        DeskClient(server).get("/missing")
    assert (exc.value.status, exc.value.code, exc.value.message) == (404, "http_404", "会话不存在")


def test_refused_connection_is_classified_refused():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    with pytest.raises(Unreachable) as exc:
        DeskClient(f"http://127.0.0.1:{port}").get("/ok")
    assert exc.value.kind == "refused"


@pytest.mark.parametrize("err,kind", [
    (errno.ECONNREFUSED, "refused"), (errno.EPERM, "sandbox"), (errno.EACCES, "sandbox"),
    (errno.ETIMEDOUT, "other"),
])
def test_classify_os_error(err, kind):
    assert classify_os_error(OSError(err, "x")) == kind
```

`tests/agent_cli/test_discovery.py`：

```python
from pathlib import Path

import pytest

from desk.agent_cli.client import Unreachable
from desk.agent_cli.discovery import app_bundle_of, connect, port_from_env
from desk.agent_cli.errors import CliError, EXIT_ERROR, EXIT_SANDBOX


@pytest.mark.parametrize("env,port", [({}, 8766), ({"LMD_SHELL_PORT": "9001"}, 9001),
                                      ({"LMD_SHELL_PORT": "0"}, 8766), ({"LMD_SHELL_PORT": "x"}, 8766),
                                      ({"LMD_SHELL_PORT": "70000"}, 8766)])
def test_port_from_env(env, port):
    assert port_from_env(env) == port


def test_app_bundle_of_finds_the_enclosing_app(tmp_path):
    res = tmp_path / "LocalModelDesk.app" / "Contents" / "Resources"
    (res / "desk" / "agent_cli").mkdir(parents=True)
    (res / "bundle.json").write_text("{}")
    assert app_bundle_of(res / "desk" / "agent_cli" / "x.py") == tmp_path / "LocalModelDesk.app"
    assert app_bundle_of(tmp_path / "elsewhere.py") is None


class FakeProbe:
    """Stands in for DeskClient.get('/api/state'): raises the scripted outcomes in order."""
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def __call__(self, base_url):
        outcome = self.outcomes.pop(0) if self.outcomes else {"holder": None}
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _connect(tmp_path, probe, *, in_bundle=True, launch_rc=0):
    calls = []
    here = (tmp_path / "LocalModelDesk.app/Contents/Resources/desk/agent_cli/x.py") if in_bundle else tmp_path / "x.py"
    if in_bundle:
        (tmp_path / "LocalModelDesk.app/Contents/Resources").mkdir(parents=True)
        (tmp_path / "LocalModelDesk.app/Contents/Resources/bundle.json").write_text("{}")
    t = [0.0]
    client = connect({}, here=here, probe=probe,
                     launcher=lambda argv: (calls.append(argv), launch_rc)[1],
                     sleep=lambda s: t.__setitem__(0, t[0] + s), clock=lambda: t[0])
    return client, calls


def test_running_desk_connects_without_launching(tmp_path):
    client, calls = _connect(tmp_path, FakeProbe([{"holder": None}]))
    assert client.base_url == "http://127.0.0.1:8766" and calls == []


def test_refused_in_bundle_launches_hidden_then_connects(tmp_path):
    client, calls = _connect(tmp_path, FakeProbe([Unreachable("refused", "x"), Unreachable("refused", "x"), {"holder": None}]))
    assert calls == [["open", "-gj", str(tmp_path / "LocalModelDesk.app")]]


def test_refused_outside_bundle_does_not_launch(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")]), in_bundle=False)
    assert exc.value.exit_code == EXIT_ERROR


def test_sandbox_is_exit_6_and_never_launches(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("sandbox", "EPERM")]))
    assert exc.value.exit_code == EXIT_SANDBOX


def test_launch_permission_failure_is_exit_6(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")]), launch_rc=-13)
    assert exc.value.exit_code == EXIT_SANDBOX


def test_never_comes_up_is_exit_1_after_60s(tmp_path):
    with pytest.raises(CliError) as exc:
        _connect(tmp_path, FakeProbe([Unreachable("refused", "x")] * 100))
    assert exc.value.exit_code == EXIT_ERROR
    assert "台面未能启动" in exc.value.message
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/agent_cli -v`
预期：FAIL，报 `ModuleNotFoundError: desk.agent_cli.client`。

- [ ] **Step 3: 实现 `errors.py`**

```python
"""Exit codes (A-13) and the one exception every command raises to stop."""
from __future__ import annotations

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_TIMEOUT, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_SANDBOX = 0, 1, 2, 3, 4, 5, 6


class CliError(Exception):
    def __init__(self, exit_code: int, code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.exit_code, self.code, self.message, self.hint = exit_code, code, message, hint
```

- [ ] **Step 4: 实现 `client.py`**

```python
"""JSON over HTTP to the desk, with connection failures sorted into refused / sandbox / other (A-33)."""
from __future__ import annotations

import errno
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_SANDBOX_ERRNOS = {errno.EPERM, errno.EACCES}


class Unreachable(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind, self.detail = kind, detail


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str, detail: dict):
        super().__init__(message)
        self.status, self.code, self.message, self.detail = status, code, message, detail


def classify_os_error(exc: OSError) -> str:
    if exc.errno == errno.ECONNREFUSED:
        return "refused"
    if exc.errno in _SANDBOX_ERRNOS:
        return "sandbox"
    return "other"


def _http_error(exc: HTTPError) -> HttpError:
    code, message, detail = f"http_{exc.code}", f"HTTP {exc.code}", {}
    try:
        payload = json.loads(exc.read() or b"{}")
    except ValueError:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, str) and error:
        message = error
    elif isinstance(error, dict):
        code = error.get("code") or code
        message = error.get("message") or message
        detail = error.get("detail") if isinstance(error.get("detail"), dict) else {}
    return HttpError(exc.code, code, message, detail)


class DeskClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url, self.timeout = base_url.rstrip("/"), timeout

    def _send(self, method: str, path: str, body=None, query=None):
        url = self.base_url + path + (("?" + urlencode(query)) if query else "")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            raise _http_error(exc) from None
        except URLError as exc:
            reason = exc.reason
            kind = classify_os_error(reason) if isinstance(reason, OSError) else "other"
            raise Unreachable(kind, str(reason)) from None
        except OSError as exc:
            raise Unreachable(classify_os_error(exc), str(exc)) from None
        return json.loads(raw) if raw else None

    def get(self, path, query=None):
        return self._send("GET", path, query=query)

    def post(self, path, body=None):
        return self._send("POST", path, body if body is not None else {})

    def patch(self, path, body):
        return self._send("PATCH", path, body)
```

- [ ] **Step 5: 实现 `discovery.py`**

```python
"""Find the desk: port from env, the enclosing app bundle, and a hidden launch when it is down (A-30/A-31/A-33)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable, Mapping

from .client import DeskClient, Unreachable
from .errors import CliError, EXIT_ERROR, EXIT_SANDBOX

DEFAULT_PORT = 8766
SANDBOX_MESSAGE = "被沙箱拦截，需要允许访问本机网络（127.0.0.1）"


def port_from_env(env: Mapping[str, str]) -> int:
    try:
        port = int(env.get("LMD_SHELL_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


def app_bundle_of(path: Path) -> Path | None:
    for parent in Path(path).resolve().parents:
        if parent.suffix == ".app" and (parent / "Contents" / "Resources" / "bundle.json").is_file():
            return parent
    return None


def _default_probe(base_url: str):
    return DeskClient(base_url, timeout=3.0).get("/api/state")


def _default_launcher(argv: list[str]) -> int:
    try:
        return subprocess.run(argv, capture_output=True).returncode
    except PermissionError:
        return -13


def _sandbox() -> CliError:
    return CliError(EXIT_SANDBOX, "sandboxed", SANDBOX_MESSAGE)


def connect(env: Mapping[str, str], *, here: Path, probe: Callable = _default_probe,
            launcher: Callable[[list[str]], int] = _default_launcher,
            sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
            start_timeout_s: float = 60.0) -> DeskClient:
    base_url = f"http://127.0.0.1:{port_from_env(env)}"
    try:
        probe(base_url)
        return DeskClient(base_url)
    except Unreachable as exc:
        if exc.kind == "sandbox":
            raise _sandbox() from None
        if exc.kind != "refused":
            raise CliError(EXIT_ERROR, "unreachable", f"连不上台面：{exc.detail}") from None
    app = app_bundle_of(here)
    if app is None:
        raise CliError(EXIT_ERROR, "desk_not_running", "台面没有运行。请先打开 LocalModelDesk。")
    rc = launcher(["open", "-gj", str(app)])
    if rc in (-13, 13, 126):
        raise _sandbox()
    if rc != 0:
        raise CliError(EXIT_ERROR, "launch_failed", f"台面未能启动（open 退出码 {rc}）")
    deadline = clock() + start_timeout_s
    while clock() < deadline:
        sleep(1.0)
        try:
            probe(base_url)
            return DeskClient(base_url)
        except Unreachable as exc:
            if exc.kind == "sandbox":
                raise _sandbox() from None
    raise CliError(EXIT_ERROR, "launch_timeout", f"台面未能启动（{int(start_timeout_s)}s 内无响应）")
```

- [ ] **Step 6: 运行测试**

运行：`python -m pytest tests/agent_cli -v`
预期：全部 PASS。

- [ ] **Step 7: 提交**

```bash
git add desk/agent_cli tests/agent_cli
git commit -m "feat(lmdesk): 退出码、HTTP 客户端与服务发现（含沙箱分类）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 纯函数 `decide()`（A-20、A-24、A-26）

**Files:**
- Create: `desk/agent_cli/decide.py`
- Test: `tests/agent_cli/test_decide.py`

**Interfaces:**
- 产出：
  - `Snapshot`（frozen dataclass），字段如下：
    - `llm_status: str`（`idle`、`loading`、`loaded`、`error`）
    - `llm_model: str | None`（仅当 `loaded` 时有值）
    - `active_chats: int`
    - `ui_chat_recent: bool`
    - `media_running: bool`
    - `precheck: dict | None`
  - `Decision`（frozen dataclass），字段为 `action: str`（`wait`、`swap`、`submit`、`fail`）、`reason: str`、`exit_code: int | None = None`。
  - `decide(op: str, want_model: str | None, snap: Snapshot) -> Decision`，其中 op 为 `"chat"` 或 `"image"`。
  - `RETRY_CODES: frozenset[str]`：遇到就回到等待的错误码，包括 `media_busy`、`load_in_progress`、`model_mismatch`、`evicted`、`no_model_loaded`、`job_not_running`。

- [ ] **Step 1: 写失败的测试，按 A-20 表格逐格覆盖**

```python
import pytest

from desk.agent_cli.decide import RETRY_CODES, Snapshot, decide
from desk.agent_cli.errors import EXIT_MEMORY

OK = {"ok": True, "reason": None, "release": [], "memory_warning": None}
EVICTS_LLM = {"ok": True, "reason": None, "release": [{"kind": "llm", "key": "glm"}], "memory_warning": None}
WAIT_MEDIA = {"ok": False, "reason": {"code": "insufficient_budget", "message": "不够"},
              "release": [{"kind": "image", "key": "qwen-image"}], "memory_warning": None}
TOO_BIG = {"ok": False, "reason": {"code": "insufficient_budget", "message": "这台机器装不下"},
           "release": [], "memory_warning": None}


def snap(**kw):
    base = dict(llm_status="idle", llm_model=None, active_chats=0, ui_chat_recent=False,
                media_running=False, precheck=OK)
    base.update(kw)
    return Snapshot(**base)


def test_loading_waits_for_both_ops():
    assert decide("chat", "glm", snap(llm_status="loading")).action == "wait"
    assert decide("image", None, snap(llm_status="loading")).action == "wait"


def test_chat_with_the_resident_model_submits_even_when_busy():
    s = snap(llm_status="loaded", llm_model="glm", active_chats=3, media_running=True, ui_chat_recent=True)
    assert decide("chat", "glm", s).action == "submit"


@pytest.mark.parametrize("kw", [dict(media_running=True), dict(active_chats=1),
                                dict(ui_chat_recent=True, llm_status="loaded", llm_model="qwen27")])
def test_chat_needing_a_swap_waits_while_busy(kw):
    assert decide("chat", "glm", snap(**kw)).action == "wait"


def test_chat_swaps_when_idle_and_precheck_ok():
    assert decide("chat", "glm", snap()).action == "swap"
    assert decide("chat", "glm", snap(llm_status="loaded", llm_model="qwen27")).action == "swap"


def test_recent_ui_chat_without_a_loaded_model_does_not_block():
    assert decide("chat", "glm", snap(ui_chat_recent=True, llm_status="error")).action == "swap"


def test_chat_waits_when_memory_can_be_freed():
    assert decide("chat", "glm", snap(precheck=WAIT_MEDIA)).action == "wait"


def test_chat_fails_with_4_when_model_too_big():
    d = decide("chat", "glm", snap(precheck=TOO_BIG))
    assert (d.action, d.exit_code) == ("fail", EXIT_MEMORY)
    assert "这台机器装不下" in d.reason and "不能强制加载" in d.reason


@pytest.mark.parametrize("kw", [dict(media_running=True), dict(active_chats=1)])
def test_image_waits_while_media_or_chat_busy(kw):
    assert decide("image", None, snap(**kw)).action == "wait"


def test_image_submits_when_idle():
    assert decide("image", None, snap()).action == "submit"


def test_image_that_would_evict_llm_waits_if_ui_chatted_recently():
    s = snap(llm_status="loaded", llm_model="glm", ui_chat_recent=True, precheck=EVICTS_LLM)
    assert decide("image", None, s).action == "wait"
    s2 = snap(llm_status="loaded", llm_model="glm", ui_chat_recent=False, precheck=EVICTS_LLM)
    assert decide("image", None, s2).action == "submit"


def test_image_waits_when_memory_can_be_freed_and_submits_otherwise():
    assert decide("image", None, snap(precheck=WAIT_MEDIA)).action == "wait"
    # A non-releasable refusal is left to the server, whose error becomes the exit code.
    assert decide("image", None, snap(precheck=TOO_BIG)).action == "submit"


def test_retry_codes():
    assert {"media_busy", "load_in_progress", "model_mismatch", "evicted", "no_model_loaded"} <= RETRY_CODES
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/agent_cli/test_decide.py -v`
预期：FAIL，报 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
"""What to do next, given the desk's state: wait, swap the chat model, submit, or fail (A-20/A-24/A-26)."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import EXIT_MEMORY

RETRY_CODES = frozenset({"media_busy", "load_in_progress", "model_mismatch", "evicted",
                         "no_model_loaded", "job_not_running"})


@dataclass(frozen=True)
class Snapshot:
    llm_status: str
    llm_model: str | None
    active_chats: int
    ui_chat_recent: bool
    media_running: bool
    precheck: dict | None


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    exit_code: int | None = None


def _wait(reason: str) -> Decision:
    return Decision("wait", reason)


def _releasable(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and bool(precheck.get("release"))


def _too_big(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and not precheck.get("release")


def _evicts_llm(precheck: dict | None) -> bool:
    return bool(precheck) and any(item.get("kind") == "llm" for item in precheck.get("release") or [])


def decide(op: str, want_model: str | None, snap: Snapshot) -> Decision:
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
        return _wait("图片任务进行中")
    if snap.active_chats > 0:
        return _wait("有对话正在进行")
    if _evicts_llm(snap.precheck) and snap.ui_chat_recent:
        return _wait("生图需要卸掉对话模型，但台面里最近在用它")
    if _releasable(snap.precheck):
        return _wait("内存被占用，等待释放")
    return Decision("submit", "")
```

- [ ] **Step 4: 运行测试**

运行：`python -m pytest tests/agent_cli/test_decide.py -v`
预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/decide.py tests/agent_cli/test_decide.py
git commit -m "feat(lmdesk): 等待/换模型/提交的纯判定（A-20/A-24/A-26）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 退避等待器（A-23、A-25 的超时部分）

**Files:**
- Create: `desk/agent_cli/waiter.py`
- Test: `tests/agent_cli/test_waiter.py`

**Interfaces:**
- 产出：
  - `class Waiter`：构造参数为 `(timeout_s: float, *, clock=time.monotonic, sleep=time.sleep, err=sys.stderr, initial=2.0, factor=1.5, cap=5.0, report_every=15.0)`。
  - `.pause(reason: str) -> None`：睡一个退避间隔。超过总时限时抛出 `CliError(EXIT_TIMEOUT, "timeout", …)`。距上次报告满 `report_every` 秒时，往 err 写一行 `等待中：{reason}（已等 {n}s）`。
  - `.reset() -> None`：把退避间隔恢复到初始值。
  - `.expired() -> bool`
  - `.elapsed() -> float`

- [ ] **Step 1: 写失败的测试**

```python
import io

import pytest

from desk.agent_cli.errors import CliError, EXIT_TIMEOUT
from desk.agent_cli.waiter import Waiter


class T:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


def test_backoff_grows_by_1_5_and_caps_at_5():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(5):
        w.pause("x")
    assert t.sleeps == [2.0, 3.0, 4.5, 5.0, 5.0]


def test_reset_restarts_backoff():
    t = T()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=io.StringIO())
    w.pause("x"); w.pause("x"); w.reset(); w.pause("x")
    assert t.sleeps == [2.0, 3.0, 2.0]


def test_reports_every_15_seconds_with_reason_and_elapsed():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(8):
        w.pause("图片任务进行中")
    lines = err.getvalue().splitlines()
    assert lines and all(line.startswith("等待中：图片任务进行中（已等 ") for line in lines)
    assert len(lines) == 2


def test_timeout_raises_exit_3_and_never_oversleeps():
    t = T()
    w = Waiter(6, clock=t.clock, sleep=t.sleep, err=io.StringIO())
    with pytest.raises(CliError) as exc:
        for _ in range(10):
            w.pause("x")
    assert exc.value.exit_code == EXIT_TIMEOUT
    assert t.now <= 6.0
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/agent_cli/test_waiter.py -v`
预期：FAIL，报 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
"""Backoff between polls, a progress line every 15 s on stderr, and the overall deadline (A-23/A-25)."""
from __future__ import annotations

import sys
import time

from .errors import CliError, EXIT_TIMEOUT


class Waiter:
    def __init__(self, timeout_s: float, *, clock=time.monotonic, sleep=time.sleep, err=sys.stderr,
                 initial: float = 2.0, factor: float = 1.5, cap: float = 5.0, report_every: float = 15.0):
        self._clock, self._sleep, self._err = clock, sleep, err
        self._initial, self._factor, self._cap, self._report_every = initial, factor, cap, report_every
        self._start = clock()
        self._deadline = self._start + timeout_s
        self._interval = initial
        self._last_report = self._start

    def elapsed(self) -> float:
        return self._clock() - self._start

    def expired(self) -> bool:
        return self._clock() >= self._deadline

    def reset(self) -> None:
        self._interval = self._initial

    def pause(self, reason: str) -> None:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
        self._sleep(min(self._interval, remaining))
        self._interval = min(self._interval * self._factor, self._cap)
        now = self._clock()
        if now - self._last_report >= self._report_every:
            self._last_report = now
            print(f"等待中：{reason}（已等 {int(now - self._start)}s）", file=self._err, flush=True)
        if now >= self._deadline:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
```

- [ ] **Step 4: 运行测试**

运行：`python -m pytest tests/agent_cli/test_waiter.py -v`
预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/waiter.py tests/agent_cli/test_waiter.py
git commit -m "feat(lmdesk): 退避等待与进度提示（A-23）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: `status`、`models`、`ask`，以及命令行入口（A-10 至 A-13、A-21、A-22、A-32）

**Files:**
- Create: `desk/agent_cli/chat.py`、`desk/agent_cli/cli.py`、`desk/agent_cli/__main__.py`
- Create: `tests/agent_cli/cli_helpers.py`、`tests/agent_cli/test_chat_cli.py`

**Interfaces:**
- 消费：
  - `DeskClient`、`connect`（Task 5）
  - `decide`、`Snapshot`、`RETRY_CODES`（Task 6）
  - `Waiter`（Task 7）
  - `read_version`、`resources_root`（Task 4）
- 产出：
  - `chat.snapshot(client, op, want_model, precheck_query) -> Snapshot`
  - `chat.run_status(client) -> dict`
  - `chat.run_models(client) -> list[dict]`
  - `chat.run_ask(client, *, question, model, system, files, stdin_text, max_tokens, waiter) -> dict`，返回 `{"content", "model", "usage"}`
  - `cli.main(argv: list[str] | None = None, *, env=os.environ, stdin=sys.stdin, out=sys.stdout, err=sys.stderr, here: Path | None = None, connect_fn=None) -> int`
  - `cli_helpers.run_cli(harness, *args, stdin="", timeout=60) -> CompletedProcess`：在子进程里运行 `python -m desk.agent_cli`，并通过 `LMD_SHELL_PORT` 指向测试台面。

- [ ] **Step 1: 写测试辅助 `tests/agent_cli/cli_helpers.py`**

```python
"""Run lmdesk as a real subprocess against a launched test harness."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def harness_port(harness) -> str:
    return harness.base_url.rsplit(":", 1)[1]


def run_cli(harness, *args, stdin: str = "", timeout: float = 60, extra_env: dict | None = None):
    env = {**os.environ, "LMD_SHELL_PORT": harness_port(harness), "PYTHONPATH": str(ROOT)}
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "-m", "desk.agent_cli", *args], input=stdin,
                          capture_output=True, text=True, timeout=timeout, env=env, cwd=str(ROOT))


def popen_cli(harness, *args):
    env = {**os.environ, "LMD_SHELL_PORT": harness_port(harness), "PYTHONPATH": str(ROOT)}
    return subprocess.Popen([sys.executable, "-m", "desk.agent_cli", *args], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=str(ROOT))
```

- [ ] **Step 2: 写失败的测试 `tests/agent_cli/test_chat_cli.py`**

```python
import json

from desk.testing import launch_test_harness
from tests.agent_cli.cli_helpers import run_cli

CHAT = "glm"      # 与 Task 4 确认过的对话模型 key 一致
OTHER = "qwen27"  # 另一个对话模型；若目录里没有，换成目录中第二个 group=chat 的 key


def test_status_json_reports_desk_and_versions(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "status", "--json")
        assert r.returncode == 0, r.stderr
        body = json.loads(r.stdout)
        assert body["desk"]["reachable"] is True
        assert body["llm"]["status"] == "idle"
        assert body["media"]["running"] is False
        assert body["version"]["cli"] == body["version"]["desk"]


def test_models_lists_only_chat_models(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "models", "--json")
        assert r.returncode == 0, r.stderr
        models = json.loads(r.stdout)["models"]
        assert models and all(m["group"] == "chat" for m in models)
        assert {"key", "name", "gb", "loaded", "fit"} <= set(models[0])


def test_ask_without_model_and_nothing_loaded_is_exit_5_listing_models(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好")
        assert r.returncode == 5
        assert CHAT in r.stderr


def test_ask_unknown_model_is_exit_5(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "你好", "--model", "nope")
        assert r.returncode == 5


def test_ask_loads_on_demand_then_answers_and_marks_agent(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好", "--model", CHAT)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "你好，世界"
        status = h.llm.status()
        assert status["state"]["model_key"] == CHAT and status["loaded_by"] == "agent"
        assert status["ui_chat_recent"] is False
        assert h.chat_script.requests[-1].get("origin") is None  # origin never reaches the backend


def test_ask_uses_resident_model_when_none_given(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        r = run_cli(h, "ask", "你好")
        assert r.returncode == 0, r.stderr
        assert h.llm.status()["loaded_by"] == "ui"


def test_ask_waits_instead_of_swapping_while_ui_chatted_recently(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        h.llm.chat_completion({"messages": [{"role": "user", "content": "hi"}]})
        r = run_cli(h, "ask", "你好", "--model", OTHER, "--timeout", "3")
        assert r.returncode == 3
        assert h.llm.status()["state"]["model_key"] == CHAT


def test_ask_reads_stdin_and_files_and_ignores_empty_stdin(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("文件内容")
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "总结", "--model", CHAT, "--file", str(note), stdin="管道内容")
        assert r.returncode == 0, r.stderr
        sent = h.chat_script.requests[-1]["messages"][-1]["content"]
        assert "总结" in sent and "管道内容" in sent and "note.md" in sent and "文件内容" in sent
        r2 = run_cli(h, "ask", "只有问题", "--model", CHAT, stdin="")
        assert r2.returncode == 0
        assert h.chat_script.requests[-1]["messages"][-1]["content"] == "只有问题"


def test_ask_json_output(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好", "--model", CHAT, "--json")
        body = json.loads(r.stdout)
        assert body["content"] == "你好，世界" and body["model"] == CHAT


def test_missing_file_is_exit_2(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "x", "--file", str(tmp_path / "nope.md"))
        assert r.returncode == 2


def test_error_json_shape(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "x", "--model", "nope", "--json")
        assert json.loads(r.stdout)["error"]["code"] == "model_not_found"


def test_version_mismatch_only_warns(tmp_path, monkeypatch):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "status", extra_env={"LMDESK_FAKE_VERSION": "0.0.0-test"})
        assert r.returncode == 0
        assert "版本不一致" in r.stderr
```

`ChatScript.requests` 要求 fake 后端记录收到的 payload。如果 `FakeLlmBackend.chat` 还没有往 `script.requests` 里追加，就在 `desk/testing/fakes.py` 的 `chat` 和 `chat_stream` 开头加一行 `self._script.requests.append(payload)`。具体属性名以 fakes 里实际持有 ChatScript 的那个为准，用 `grep -n "requests" desk/testing/fakes.py` 确认。

`LMDESK_FAKE_VERSION` 是给测试用的覆盖开关：设置后，CLI 用它作为自己的版本号。

- [ ] **Step 3: 运行，确认失败**

运行：`python -m pytest tests/agent_cli/test_chat_cli.py -v`
预期：FAIL，报 `No module named desk.agent_cli.__main__`。

- [ ] **Step 4: 实现 `chat.py`**

```python
"""status / models / ask (A-12, A-21, A-22)."""
from __future__ import annotations

from pathlib import Path

from .client import DeskClient, HttpError
from .decide import RETRY_CODES, Snapshot, decide
from .errors import CliError, EXIT_ERROR, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_USAGE
from .version import read_version, resources_root
from .waiter import Waiter

AGENT = {"origin": "agent"}


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
    import os
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
    while True:
        decision = decide("chat", want, snapshot(client, "chat", want, {"op": "chat", "model": want}))
        if decision.action == "wait":
            waiter.pause(decision.reason)
            continue
        if decision.action == "fail":
            raise CliError(decision.exit_code or EXIT_MEMORY, "insufficient_budget", decision.reason)
        if decision.action == "swap":
            _swap(client, want, waiter)
            continue
        body = {"messages": messages, "model": want, **AGENT}
        if max_tokens:
            body["max_tokens"] = max_tokens
        try:
            result = client.post("/api/llm/chat", body)
        except HttpError as exc:
            if exc.code in RETRY_CODES:
                waiter.pause("模型被换走了，重新排队")
                continue
            raise CliError(EXIT_ERROR, exc.code, exc.message) from None
        return {"content": result.get("content") or "", "model": result.get("model"), "usage": result.get("usage")}
```

`/api/llm/chat` 透传请求体：`origin` 只被 `_chat_begin` 读取。`_upstream_payload` 只挑 `messages`、`temperature` 等字段，所以 `origin` 不会到达后端，测试 `test_ask_loads_on_demand_then_answers_and_marks_agent` 断言了这一点。

- [ ] **Step 5: 实现 `cli.py` 与 `__main__.py`**

```python
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
        print(json.dumps(result, ensure_ascii=False), file=out)
        return
    if isinstance(result, dict) and "text" in result:
        if args.json:
            print(json.dumps({k: v for k, v in result.items() if k != "text"}, ensure_ascii=False), file=out)
        else:
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
        return EXIT_OK if exc.code == 0 else EXIT_USAGE

    def on_signal(signum, _frame):
        raise Interrupted(signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, on_signal)
    try:
        client = (connect_fn or connect)(env, here=here or Path(__file__))
        desk_version = client.get("/api/state").get("version")
        cli_version = chat.cli_version()
        if desk_version and desk_version != cli_version:
            print(f"注意：lmdesk 版本 {cli_version} 与台面版本 {desk_version} 不一致", file=err)
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
```

```python
"""python -m desk.agent_cli"""
import sys

from .cli import main

sys.exit(main())
```

在 `errors.py` 末尾追加 `Interrupted`。信号处理函数抛出它；Task 9 的 `images.run_gen` 会自己捕获，按信号区分取消还是续等（A-25）。

```python
class Interrupted(Exception):
    """Raised from the SIGINT/SIGTERM handler; images decides cancel vs. keep-running by signum (A-25)."""
    def __init__(self, signum: int):
        super().__init__(signum)
        self.signum = signum
```

- [ ] **Step 6: 运行测试**

运行：`python -m pytest tests/agent_cli -v`
预期：全部 PASS。images 模块在 Task 9 才建，所以本任务要先放一个只含 `add_parsers(sub, common): pass` 和 `dispatch(...)` 的最小 `desk/agent_cli/images.py`，让 import 不报错。

- [ ] **Step 7: 提交**

```bash
git add desk/agent_cli tests/agent_cli desk/testing/fakes.py
git commit -m "feat(lmdesk): status/models/ask 与命令行入口（按需加载、排队、版本提示）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 图片会话命令 `sessions|new|show|gen|wait|rename`（A-10、A-11、A-14 至 A-16、A-25 至 A-27）

**Files:**
- Modify (实现完整内容): `desk/agent_cli/images.py`
- Test: `tests/agent_cli/test_image_cli.py`

**Interfaces:**
- 消费：
  - `snapshot`、`AGENT`（chat.py）
  - `decide`、`RETRY_CODES`
  - `Waiter`
  - `CliError`、`Interrupted`、各退出码常量
- 产出：
  - `images.add_parsers(sub, common) -> None`
  - `images.dispatch(args, client, waiter, err) -> dict`
  - `images.resolve_session(client, ref: str) -> dict`（返回会话摘要）
  - `images.run_gen(client, args, waiter, err) -> dict`、`images.wait_attempt(client, session_id, attempt_id, job_id, waiter, err) -> dict`
- 结果对象 `{"text": <stdout 文本>, ...json 字段}`：`_emit` 在非 `--json` 时打印 `text`，`--json` 时打印去掉 `text` 后的对象。

- [ ] **Step 1: 写失败的测试**

```python
import json
import signal
import time

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, cancellable_media_steps, default_media_steps, fast_media_steps
from tests.agent_cli.cli_helpers import popen_cli, run_cli

IMG = {"model_states": {"qwen-image": "present"}, "image_runtime": True}


def _new(h, name):
    r = run_cli(h, "image", "new", name, "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_new_sessions_rename_show(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        created = _new(h, "首页 banner")
        assert created["title"] == "首页 banner"
        listed = json.loads(run_cli(h, "image", "sessions", "--json").stdout)["sessions"]
        assert any(s["id"] == created["id"] and s["title"] == "首页 banner" for s in listed)
        r = run_cli(h, "image", "rename", "首页 banner", "首页大图", "--json")
        assert json.loads(r.stdout)["title"] == "首页大图"
        shown = json.loads(run_cli(h, "image", "show", created["id"], "--json").stdout)
        assert shown["attempts"] == []


def test_session_name_ambiguous_is_exit_2_and_prefix_never_matches(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        a = _new(h, "图标")
        _new(h, "图标")
        assert run_cli(h, "image", "show", "图标").returncode == 2
        assert run_cli(h, "image", "show", a["id"][:8]).returncode == 5
        assert run_cli(h, "image", "show", " 不存在 ").returncode == 5


def test_gen_writes_an_attempt_and_prints_absolute_path(tmp_path):
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        s = _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "一只橘猫", "--size", "512x512", "--steps", "4", "--json")
        assert r.returncode == 0, r.stderr
        body = json.loads(r.stdout)
        assert body["session_id"] == s["id"] and body["path"].startswith("/") and body["path"].endswith(".png")
        assert "已提交：会话" in r.stderr and "lmdesk image wait" in r.stderr
        shown = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)
        assert shown["attempts"][0]["id"] == body["attempt_id"]
        assert shown["attempts"][0]["path"] == body["path"]


def test_gen_out_copies_creates_dirs_and_handles_existing(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        target = tmp_path / "proj" / "assets" / "hero.png"
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--out", str(target))
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == str(target) and target.is_file()
        r2 = run_cli(h, "image", "gen", "猫", "y", "--size", "512x512", "--steps", "4", "--out", str(target))
        assert "已覆盖" in r2.stderr
        folder = tmp_path / "proj" / "assets"
        r3 = run_cli(h, "image", "wait", "猫", json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)["attempts"][0]["id"],
                     "--out", str(folder))
        assert r3.returncode == 0 and r3.stdout.strip().startswith(str(folder) + "/")


def test_gen_from_passes_base(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        first = json.loads(run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json").stdout)
        r = run_cli(h, "image", "gen", "猫", "改成蓝色", "--from", first["attempt_id"], "--strength", "0.6", "--json")
        assert r.returncode == 0, r.stderr
        shown = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)
        assert shown["attempts"][-1]["base"]["attempt_id"] == first["attempt_id"]


def test_no_wait_then_wait(tmp_path):
    script = MediaScript([default_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--no-wait", "--json")
        assert r.returncode == 0, r.stderr
        sub = json.loads(r.stdout)
        script.step(); script.step()
        r2 = run_cli(h, "image", "wait", "猫", sub["attempt_id"], "--json")
        assert r2.returncode == 0, r2.stderr
        assert json.loads(r2.stdout)["attempt_id"] == sub["attempt_id"]


def test_wait_unknown_attempt_is_5(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        _new(h, "猫")
        assert run_cli(h, "image", "wait", "猫", "f" * 32).returncode == 5


def test_sigterm_after_submit_keeps_job_and_wait_recovers(tmp_path):
    script = MediaScript([default_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        _wait_running(h)
        time.sleep(0.5)
        p.send_signal(signal.SIGTERM)
        _, stderr = p.communicate(timeout=20)
        assert p.returncode == 3
        assert "lmdesk image wait" in stderr
        assert h.media.job_status()["status"] == "running"
        script.step(); script.step()
        attempt = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)["attempts"][0]["id"]
        assert run_cli(h, "image", "wait", "猫", attempt).returncode == 0


def test_sigint_after_submit_cancels_only_own_job(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        _wait_running(h)
        time.sleep(0.5)
        p.send_signal(signal.SIGINT)
        p.communicate(timeout=20)
        assert p.returncode == 3
        assert h.media.job_status()["status"] == "cancelled"


def test_slot_reused_by_another_job_still_reads_result_from_session(tmp_path):
    script = MediaScript([default_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫"); _new(h, "狗")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json")
        _wait_running(h)
        script.step(); script.step()
        _wait_idle(h)
        h.media.start_image_job(session_id=_id(h, "狗"), prompt="y", width=512, height=512, steps=4)
        out, err = p.communicate(timeout=30)
        assert p.returncode == 0, err
        assert json.loads(out)["session_id"] == _id(h, "猫")


def test_memory_warning_is_4_then_force_succeeds(tmp_path):
    from desk.testing.scripts import MemoryScript
    from desk.testing.fakes import DEFAULT_SNAPSHOT_A
    # 可用内存设得很小，让图片估算超过它。具体字段以 DEFAULT_SNAPSHOT_A 的实际结构为准。
    low = {**DEFAULT_SNAPSHOT_A, "available_bytes": 1_000_000_000}
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, memory_script=MemoryScript([low]), **IMG) as h:
        _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        assert r.returncode == 4 and "GiB" in r.stderr
        r2 = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--force")
        assert r2.returncode == 0, r2.stderr


def test_busy_desk_then_free_retries_without_failing(tmp_path):
    script = MediaScript([default_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫"); _new(h, "狗")
        h.media.start_image_job(session_id=_id(h, "狗"), prompt="先占着", width=512, height=512, steps=4)
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json")
        time.sleep(1.0)
        script.step(); script.step()
        out, err = p.communicate(timeout=40)
        assert p.returncode == 0, err


def test_desk_quitting_midwait_is_exit_1_with_resume_hint(tmp_path):
    script = MediaScript([default_media_steps()])
    h = launch_test_harness(tmp_path, media_script=script, **IMG)
    _new(h, "猫")
    p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
    _wait_running(h)
    h.close()
    _, err = p.communicate(timeout=30)
    assert p.returncode == 1
    assert "lmdesk image wait" in err


def _id(h, title):
    return next(s["id"] for s in h.library.media_sessions["image"].list() if s.get("title") == title)


def _wait_running(h, timeout=10):
    deadline = time.time() + timeout
    while h.media.job_status()["status"] != "running":
        assert time.time() < deadline
        time.sleep(0.05)


def _wait_idle(h, timeout=10):
    deadline = time.time() + timeout
    while h.media.job_status()["status"] == "running":
        assert time.time() < deadline
        time.sleep(0.05)
```

执行前先确认以下几点，与实际不符就改测试里的写法，不要改产品语义：

- `h.library.media_sessions["image"]` 的访问方式：用 `grep -n "media_sessions" desk/library/__init__.py` 看实际属性名。
- `MemoryScript` 和 `DEFAULT_SNAPSHOT_A` 的字段名。
- `h.close()` 之后，进程能否被干净回收。

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/agent_cli/test_image_cli.py -v`
预期：FAIL，`image` 子命令不存在。

- [ ] **Step 3: 实现 `images.py`**

```python
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
    target = Path(out).expanduser()
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
```

`cli._emit`（Task 8）已经处理带 `text` 的结果：`--json` 时去掉 `text` 后输出，否则只打印 `text`。`args.json` 和 `args.timeout` 来自 `common` 父解析器，image 子命令同样继承。

- [ ] **Step 4: 运行测试**

运行：`python -m pytest tests/agent_cli -v`
预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli tests/agent_cli
git commit -m "feat(lmdesk): 图片会话命令，结果以会话尝试为准，被打断可续等（A-15/A-16/A-25/A-27）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 安装模块：目标、链接状态、安装与卸载（A-50 至 A-55）

**Files:**
- Create: `desk/agent_skill/targets.py`、`desk/agent_skill/installer.py`
- Test: `tests/test_agent_skill_installer.py`

**Interfaces:**
- 产出：
  - `targets.Target`（frozen dataclass），字段为：
    - `key: str`
    - `name: str`
    - `link: Path`（相对 HOME 的路径）
    - `detect_cmds: tuple[str, ...]`
    - `detect_paths: tuple[Path, ...]`（相对 HOME 的路径，以 `/` 开头的视为绝对路径）
    - `shared_note: str | None`
  - `targets.TARGETS: tuple[Target, ...]`：按 claude、codex、pi、dsh 的顺序排列。
  - `targets.CLI_LINK = Path(".local/bin/lmdesk")`
  - `targets.SKILL_SUFFIX = ("agent_skill", "bundled", "local-model-desk")`
  - `targets.CLI_SUFFIXES = (("Contents", "Resources", "bin", "lmdesk"), ("scripts", "lmdesk"))`
  - `installer.link_state(link: Path, current: Path, suffixes) -> dict`：返回 `{"state": "installed" | "absent" | "stale" | "occupied" | "error", "target": str | None, "message": str | None}`
  - `installer.detect(target, home, which) -> bool`
  - `installer.status(home: Path, skill_dir: Path, cli_path: Path, which=shutil.which) -> dict`：返回 `{"targets": [{key, name, path, detected, shared_note, state, target, message}], "cli": {path, state, target, message}}`
  - `installer.apply(home, skill_dir, cli_path, wanted: set[str], which=shutil.which) -> dict`：返回结构同 `status`，每一行再多一个 `result: "ok" | "error"`。
  - `installer.any_stale(home, skill_dir, cli_path) -> bool`

- [ ] **Step 1: 写失败的测试**

```python
"""A-50..A-55: link states and apply, all inside a temporary HOME."""
import os
from pathlib import Path

import pytest

from desk.agent_skill import installer
from desk.agent_skill.targets import TARGETS


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    res = tmp_path / "A.app" / "Contents" / "Resources"
    skill = res / "desk" / "agent_skill" / "bundled" / "local-model-desk"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: local-model-desk\n---\n")
    cli = res / "bin" / "lmdesk"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n")
    other = tmp_path / "B.app" / "Contents" / "Resources" / "desk" / "agent_skill" / "bundled" / "local-model-desk"
    other.mkdir(parents=True)
    return home, skill, cli, other


def _row(result, key):
    return next(r for r in result["targets"] if r["key"] == key)


def test_fresh_home_everything_absent(env):
    home, skill, cli, _ = env
    s = installer.status(home, skill, cli, which=lambda _c: None)
    assert [r["key"] for r in s["targets"]] == ["claude", "codex", "pi", "dsh"]
    assert all(r["state"] == "absent" for r in s["targets"]) and s["cli"]["state"] == "absent"


def test_apply_installs_only_selected_and_cli_follows(env):
    home, skill, cli, _ = env
    r = installer.apply(home, skill, cli, {"claude", "pi"}, which=lambda _c: None)
    assert _row(r, "claude")["state"] == "installed" and _row(r, "pi")["state"] == "installed"
    assert _row(r, "codex")["state"] == "absent" and _row(r, "dsh")["state"] == "absent"
    assert os.readlink(home / ".claude/skills/local-model-desk") == str(skill)
    assert (home / ".pi/agent/skills/local-model-desk").is_symlink()
    assert r["cli"]["state"] == "installed" and os.readlink(home / ".local/bin/lmdesk") == str(cli)
    r2 = installer.apply(home, skill, cli, set(), which=lambda _c: None)
    assert all(row["state"] == "absent" for row in r2["targets"]) and r2["cli"]["state"] == "absent"


def test_stale_link_to_other_app_is_detected_and_replaced(env):
    home, skill, cli, other = env
    link = home / ".claude/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(other)
    assert _row(installer.status(home, skill, cli), "claude")["state"] == "stale"
    assert installer.any_stale(home, skill, cli) is True
    installer.apply(home, skill, cli, {"claude"})
    assert os.readlink(link) == str(skill)


def test_dangling_link_with_our_suffix_is_stale(env):
    home, skill, cli, _ = env
    link = home / ".dsh/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(Path("/nonexistent/x/desk/agent_skill/bundled/local-model-desk"))
    assert _row(installer.status(home, skill, cli), "dsh")["state"] == "stale"


def test_occupied_by_real_dir_is_untouched_and_others_proceed(env):
    home, skill, cli, _ = env
    real = home / ".claude/skills/local-model-desk"
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text("mine")
    r = installer.apply(home, skill, cli, {"claude", "pi"})
    row = _row(r, "claude")
    assert row["state"] == "occupied" and row["result"] == "error"
    assert (real / "SKILL.md").read_text() == "mine"
    assert _row(r, "pi")["state"] == "installed"
    installer.apply(home, skill, cli, set())
    assert (real / "SKILL.md").read_text() == "mine"


def test_link_to_elsewhere_is_occupied_and_never_removed(env, tmp_path):
    home, skill, cli, _ = env
    elsewhere = tmp_path / "someone-else"
    elsewhere.mkdir()
    link = home / ".pi/agent/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere)
    assert _row(installer.status(home, skill, cli), "pi")["state"] == "occupied"
    installer.apply(home, skill, cli, set())
    assert link.is_symlink() and os.readlink(link) == str(elsewhere)


def test_cli_link_occupied_does_not_block_skill(env):
    home, skill, cli, _ = env
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/lmdesk").write_text("other tool")
    r = installer.apply(home, skill, cli, {"claude"})
    assert _row(r, "claude")["state"] == "installed"
    assert r["cli"]["state"] == "occupied"
    assert (home / ".local/bin/lmdesk").read_text() == "other tool"


def test_skills_dir_that_is_itself_a_symlink_is_followed_not_replaced(env, tmp_path):
    home, skill, cli, _ = env
    synced = tmp_path / "synced-skills"
    synced.mkdir()
    (home / ".claude").mkdir()
    (home / ".claude/skills").symlink_to(synced)
    installer.apply(home, skill, cli, {"claude"})
    assert (home / ".claude/skills").is_symlink()
    assert (synced / "local-model-desk").is_symlink()


def test_unwritable_parent_is_error_row(env):
    home, skill, cli, _ = env
    (home / ".pi/agent").mkdir(parents=True)
    os.chmod(home / ".pi/agent", 0o500)
    try:
        r = installer.apply(home, skill, cli, {"pi"})
        row = _row(r, "pi")
        assert row["result"] == "error" and row["message"]
    finally:
        os.chmod(home / ".pi/agent", 0o700)


def test_detect_uses_commands_or_paths(env):
    home, skill, cli, _ = env
    (home / ".dsh").mkdir()
    s = installer.status(home, skill, cli, which=lambda c: "/x/codex" if c == "codex" else None)
    assert _row(s, "codex")["detected"] and _row(s, "dsh")["detected"]
    assert not _row(s, "pi")["detected"]


def test_targets_table_matches_spec():
    links = {t.key: str(t.link) for t in TARGETS}
    assert links["claude"] == ".claude/skills/local-model-desk"
    assert links["pi"] == ".pi/agent/skills/local-model-desk"
    assert links["dsh"] == ".dsh/skills/local-model-desk"
    assert links["codex"] in (".codex/skills/local-model-desk", ".agents/skills/local-model-desk")
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_agent_skill_installer.py -v`
预期：FAIL，报 `ImportError`。

- [ ] **Step 3: 实现 `targets.py`**

codex 那一行按 Task 1 的结论填写。下面假设结论是读 `~/.codex/skills`。

```python
"""Where each agent reads user-level skills (A-50/A-51). Paths are relative to HOME unless they start with /."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SKILL_NAME = "local-model-desk"
SKILL_SUFFIX = ("agent_skill", "bundled", SKILL_NAME)
CLI_LINK = Path(".local/bin/lmdesk")
CLI_SUFFIXES = (("Contents", "Resources", "bin", "lmdesk"), ("scripts", "lmdesk"))


@dataclass(frozen=True)
class Target:
    key: str
    name: str
    link: Path
    detect_cmds: tuple[str, ...]
    detect_paths: tuple[Path, ...]
    shared_note: str | None = None


TARGETS = (
    Target("claude", "Claude Code", Path(".claude/skills") / SKILL_NAME, ("claude",),
           (Path(".claude"), Path(".local/bin/claude"))),
    Target("codex", "Codex", Path(".codex/skills") / SKILL_NAME, ("codex",), (Path(".codex"),)),
    Target("pi", "pi", Path(".pi/agent/skills") / SKILL_NAME, ("pi",), (Path(".pi"),)),
    Target("dsh", "DeepSeek Harness", Path(".dsh/skills") / SKILL_NAME, (),
           (Path("/Applications/DeepSeek Harness.app"), Path("Applications/DeepSeek Harness.app"), Path(".dsh"))),
)
```

- [ ] **Step 4: 实现 `installer.py`**

```python
"""Symlink states and apply for the agent skill and the lmdesk link (A-52..A-55). Never deletes real files."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .targets import CLI_LINK, CLI_SUFFIXES, SKILL_SUFFIX, TARGETS


def _ours(target: str, suffixes) -> bool:
    parts = Path(target).parts
    return any(tuple(parts[-len(s):]) == tuple(s) for s in suffixes)


def link_state(link: Path, current: Path, suffixes) -> dict:
    try:
        if link.is_symlink():
            target = os.readlink(link)
            if Path(target) == current:
                return {"state": "installed", "target": target, "message": None}
            if _ours(target, suffixes):
                return {"state": "stale", "target": target, "message": "指向旧位置，点应用更新"}
            return {"state": "occupied", "target": target, "message": f"这里已有指向 {target} 的链接，台面不会改动"}
        if link.exists():
            return {"state": "occupied", "target": None, "message": "这里已有同名文件或目录，台面不会改动"}
        return {"state": "absent", "target": None, "message": None}
    except OSError as exc:
        return {"state": "error", "target": None, "message": exc.strerror or str(exc)}


def _abs(home: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else home / rel


def detect(target, home: Path, which) -> bool:
    return any(which(cmd) for cmd in target.detect_cmds) or any(_abs(home, p).exists() for p in target.detect_paths)


def _install(link: Path, current: Path, state: dict) -> dict:
    if state["state"] == "installed":
        return {**state, "result": "ok"}
    if state["state"] in ("occupied", "error"):
        return {**state, "result": "error"}
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        if state["state"] == "stale":
            link.unlink()
        link.symlink_to(current)
    except OSError as exc:
        return {"state": "error", "target": None, "message": exc.strerror or str(exc), "result": "error"}
    return {"state": "installed", "target": str(current), "message": None, "result": "ok"}


def _uninstall(link: Path, state: dict) -> dict:
    if state["state"] not in ("installed", "stale"):
        return {**state, "result": "ok" if state["state"] in ("absent", "occupied") else "error"}
    try:
        if link.is_symlink():
            link.unlink()
    except OSError as exc:
        return {**state, "state": "error", "message": exc.strerror or str(exc), "result": "error"}
    return {"state": "absent", "target": None, "message": None, "result": "ok"}


def _row(target, home, which, state) -> dict:
    return {"key": target.key, "name": target.name, "path": str(_abs(home, target.link)),
            "detected": detect(target, home, which), "shared_note": target.shared_note, **state}


def status(home: Path, skill_dir: Path, cli_path: Path, which=shutil.which) -> dict:
    rows = [_row(t, home, which, link_state(_abs(home, t.link), skill_dir, (SKILL_SUFFIX,))) for t in TARGETS]
    cli = {"path": str(home / CLI_LINK), **link_state(home / CLI_LINK, cli_path, CLI_SUFFIXES)}
    return {"targets": rows, "cli": cli}


def apply(home: Path, skill_dir: Path, cli_path: Path, wanted: set[str], which=shutil.which) -> dict:
    rows = []
    for target in TARGETS:
        link = _abs(home, target.link)
        state = link_state(link, skill_dir, (SKILL_SUFFIX,))
        state = _install(link, skill_dir, state) if target.key in wanted else _uninstall(link, state)
        rows.append(_row(target, home, which, state))
    cli_link = home / CLI_LINK
    cli_state = link_state(cli_link, cli_path, CLI_SUFFIXES)
    any_installed = any(r["state"] == "installed" for r in rows)
    cli_state = _install(cli_link, cli_path, cli_state) if any_installed else _uninstall(cli_link, cli_state)
    return {"targets": rows, "cli": {"path": str(cli_link), **cli_state}}


def any_stale(home: Path, skill_dir: Path, cli_path: Path) -> bool:
    s = status(home, skill_dir, cli_path, which=lambda _c: None)
    return any(r["state"] == "stale" for r in s["targets"]) or s["cli"]["state"] == "stale"
```

关于 `mkdir(parents=True, exist_ok=True)`：当上级目录（比如 `~/.claude/skills`）本身是指向一个已存在目录的软链接时，`exist_ok` 会让它直接通过，后面的 `symlink_to` 会写进链接的目标目录里。这正是 Review Focus 第 3 条要求的行为。

- [ ] **Step 5: 运行测试**

运行：`python -m pytest tests/test_agent_skill_installer.py -v`
预期：全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add desk/agent_skill/targets.py desk/agent_skill/installer.py tests/test_agent_skill_installer.py
git commit -m "feat(agent-skill): 链接状态判定与按勾选安装/卸载（A-50..A-55）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 安装接口、检查接口，以及 `/api/state` 的失效标记（A-41、A-67、A-71 的服务端部分）

**Files:**
- Create: `desk/agent_skill/service.py`
- Modify: `desk/agent_skill/routes.py`（加 `build_routes(service)`）
- Modify: `desk/runtime.py`、`desk/testing/harness.py`、`tests/test_e2e_harness_assembly.py`
- Test: `tests/test_agent_skill_routes.py`（追加）

**Interfaces:**
- 消费：`installer.status`、`installer.apply`、`installer.any_stale`（Task 10）
- 产出：
  - `AgentSkillService(resources_root: Path, mode: str, home: Path, which=shutil.which, run=subprocess.run)`
  - `.skill_dir` 属性：`resources_root/desk/agent_skill/bundled/local-model-desk`
  - `.cli_path` 属性：bundle 模式下是 `resources_root/bin/lmdesk`，dev 模式下是 `resources_root/scripts/lmdesk`
  - `.status() -> dict`
  - `.apply(targets: list[str]) -> dict`：未知的 key 抛出 `ValueError`
  - `.check() -> {"ok": bool, "message": str, "output": str}`
  - `.stale() -> bool`：结果缓存，台面启动时算一次，之后每次 apply 后重算（A-71）
  - 路由：
    - `GET /api/agent-skill`
    - `POST /api/agent-skill` 请求体 `{"targets": [...]}`
    - `POST /api/agent-skill/check`
  - `/api/state` 增加 `agent_skill_stale: bool`

- [ ] **Step 1: 写失败的测试（追加到 `tests/test_agent_skill_routes.py`）**

```python
import shutil
from pathlib import Path
from urllib.request import Request

from desk.agent_skill.service import AgentSkillService


def _post(url, body):
    req = Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def test_service_paths_dev_vs_bundle(tmp_path):
    dev = AgentSkillService(tmp_path, "dev", tmp_path / "home")
    assert dev.cli_path == tmp_path / "scripts" / "lmdesk"
    bundle = AgentSkillService(tmp_path, "bundle", tmp_path / "home")
    assert bundle.cli_path == tmp_path / "bin" / "lmdesk"
    assert dev.skill_dir == tmp_path / "desk" / "agent_skill" / "bundled" / "local-model-desk"


def test_apply_rejects_unknown_target(tmp_path):
    svc = AgentSkillService(tmp_path, "dev", tmp_path / "home")
    with pytest.raises(ValueError):
        svc.apply(["claude", "vim"])


def test_check_reports_cli_outcome(tmp_path):
    class Done:
        def __init__(self, rc, out, err):
            self.returncode, self.stdout, self.stderr = rc, out, err
    ok = AgentSkillService(tmp_path, "dev", tmp_path / "home",
                           run=lambda *a, **k: Done(0, '{"desk": {"reachable": true}}', ""))
    assert ok.check()["ok"] is True
    bad = AgentSkillService(tmp_path, "dev", tmp_path / "home", run=lambda *a, **k: Done(6, "", "被沙箱拦截"))
    result = bad.check()
    assert result["ok"] is False and "沙箱" in result["message"]


def test_routes_status_apply_and_state_flag(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        status, body = _get(h.base_url + "/api/agent-skill")
        assert status == 200 and [r["key"] for r in body["targets"]] == ["claude", "codex", "pi", "dsh"]
        status, body = _post(h.base_url + "/api/agent-skill", {"targets": ["claude"]})
        assert status == 200
        assert next(r for r in body["targets"] if r["key"] == "claude")["state"] == "installed"
        assert (home / ".claude/skills/local-model-desk").is_symlink()
        status, body = _post(h.base_url + "/api/agent-skill", {"targets": ["nope"]})
        assert status == 400
        _, state = _get(h.base_url + "/api/state")
        assert state["agent_skill_stale"] is False
        _post(h.base_url + "/api/agent-skill", {"targets": []})
```

harness 里的服务通过 `Path.home()` 读取 HOME，测试用 `monkeypatch.setenv("HOME", …)` 隔离。所以 runtime 和 harness 都要在构造服务时传 `home=Path.home()`，而且这一句必须在 monkeypatch 之后才执行。harness 是在 `launch_test_harness` 内部构造服务的，满足这个时序。

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_agent_skill_routes.py -v`
预期：新增的测试 FAIL，报 `ImportError: desk.agent_skill.service`。

- [ ] **Step 3: 实现 `service.py`**

```python
"""AgentSkillService: status, apply, check and the cached stale flag (A-41/A-67/A-71)."""
from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

from . import installer
from .targets import SKILL_NAME, TARGETS


class AgentSkillService:
    def __init__(self, resources_root: Path, mode: str, home: Path, which=shutil.which, run=subprocess.run):
        self._resources_root, self._mode, self._home = Path(resources_root), mode, Path(home)
        self._which, self._run = which, run
        self._lock = threading.Lock()
        self._stale = installer.any_stale(self._home, self.skill_dir, self.cli_path)

    @property
    def skill_dir(self) -> Path:
        return self._resources_root / "desk" / "agent_skill" / "bundled" / SKILL_NAME

    @property
    def cli_path(self) -> Path:
        return self._resources_root / ("bin" if self._mode == "bundle" else "scripts") / "lmdesk"

    def status(self) -> dict:
        return installer.status(self._home, self.skill_dir, self.cli_path, which=self._which)

    def apply(self, targets: list[str]) -> dict:
        known = {t.key for t in TARGETS}
        wanted = set(targets)
        if not wanted <= known:
            raise ValueError(f"未知的 agent：{', '.join(sorted(wanted - known))}")
        with self._lock:
            result = installer.apply(self._home, self.skill_dir, self.cli_path, wanted, which=self._which)
            self._stale = installer.any_stale(self._home, self.skill_dir, self.cli_path)
        return result

    def stale(self) -> bool:
        return self._stale

    def check(self) -> dict:
        try:
            done = self._run([str(self.cli_path), "status", "--json", "--timeout", "10"],
                             capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "message": f"lmdesk 无法运行：{exc}", "output": ""}
        if done.returncode == 0:
            return {"ok": True, "message": "lmdesk 能连上台面", "output": done.stdout}
        lines = (done.stderr or "").strip().splitlines()
        return {"ok": False, "message": lines[-1] if lines else f"lmdesk 退出码 {done.returncode}", "output": done.stderr}
```

- [ ] **Step 4: 在 `routes.py` 里追加 `build_routes`**

```python
def build_routes(service) -> list:
    def get_status(_req):
        return Response(200, service.status())

    def post_apply(req):
        targets = (req.body or {}).get("targets")
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            return _error(400, "invalid_params", "targets 须为字符串数组")
        try:
            return Response(200, service.apply(targets))
        except ValueError as exc:
            return _error(400, "invalid_params", str(exc))

    def post_check(_req):
        return Response(200, service.check())

    return [("GET", "/api/agent-skill", get_status), ("POST", "/api/agent-skill", post_apply),
            ("POST", "/api/agent-skill/check", post_check)]
```

- [ ] **Step 5: 在 runtime 和 harness 里挂载**

`desk/runtime.py` 的 `_mount_routes` 中：

```python
    agent_skill = AgentSkillService(roots.resources_root, roots.mode, Path.home())
    app.add_routes(build_agent_skill_routes(agent_skill))
```

然后把 `/api/state` 的 lambda 改为：

```python
        ("GET", "/api/state", lambda _req: {**arbiter.desk_state(), "version": read_version(roots.resources_root),
                                            "agent_skill_stale": agent_skill.stale()}),
```

import 写法：`from .agent_skill.routes import build_routes as build_agent_skill_routes, build_precheck_routes`、`from .agent_skill.service import AgentSkillService`。

`desk/testing/harness.py` 的 `_mount_routes` 里同样处理：在 table 之前构造 `agent_skill = AgentSkillService(roots.resources_root, roots.mode, Path.home())`，并把 `*build_agent_skill_routes(agent_skill),` 加进 table，`/api/state` 也同步改。

`tests/test_e2e_harness_assembly.py::production_route_table` 加入三条路由：

```python
        ("GET", "/api/agent-skill"), ("POST", "/api/agent-skill"), ("POST", "/api/agent-skill/check"),
```

- [ ] **Step 6: 运行测试**

运行：`python -m pytest tests/test_agent_skill_routes.py tests/test_e2e_harness_assembly.py -v`
预期：全部 PASS。

- [ ] **Step 7: 提交**

```bash
git add desk/agent_skill desk/runtime.py desk/testing/harness.py tests/test_agent_skill_routes.py tests/test_e2e_harness_assembly.py
git commit -m "feat(agent-skill): 安装/检查接口与 /api/state 失效标记（A-41/A-67/A-71）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: SKILL.md 与开发态入口 `scripts/lmdesk`（A-04、A-80 至 A-82）

**Files:**
- Create: `desk/agent_skill/bundled/local-model-desk/SKILL.md`
- Create: `scripts/lmdesk`（可执行）
- Test: `tests/test_agent_skill_md.py`

- [ ] **Step 1: 写失败的测试**

```python
"""A-80/A-82: SKILL.md shape and the sections agents rely on; scripts/lmdesk runs."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "desk" / "agent_skill" / "bundled" / "local-model-desk" / "SKILL.md"


def _frontmatter(text):
    assert text.startswith("---\n")
    head, _, body = text[4:].partition("\n---\n")
    fields = {}
    for line in head.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body


def test_frontmatter_rules():
    fields, _ = _frontmatter(SKILL.read_text(encoding="utf-8"))
    assert fields["name"] == "local-model-desk" == SKILL.parent.name
    assert 0 < len(fields["description"]) <= 1024
    for word in ("本地模型", "台面", "本地生图"):
        assert word in fields["description"]


def test_body_covers_every_exit_code_and_resume():
    _, body = _frontmatter(SKILL.read_text(encoding="utf-8"))
    for needle in ("~/.local/bin/lmdesk", "lmdesk image wait", "--no-wait", "--force", "--from", "--out",
                   "image sessions", "退出码 3", "退出码 4", "退出码 5", "退出码 6", "不要重新 gen"):
        assert needle in body, needle


def test_dev_entry_script_runs_help():
    script = ROOT / "scripts" / "lmdesk"
    assert os.access(script, os.X_OK)
    r = subprocess.run([str(script), "--help"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and "lmdesk" in r.stdout
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_agent_skill_md.py -v`
预期：FAIL，提示文件不存在。

- [ ] **Step 3: 写 SKILL.md**

```markdown
---
name: local-model-desk
description: 本机的本地模型台面（LocalModelDesk）。需要用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务，或者用本地图片模型生成、迭代图片素材并按会话管理时使用。用户提到「本地模型」「台面」「本地生图」「用本机模型」时使用。通过 lmdesk 命令调用。
---

# 本机模型台面（lmdesk）

台面是这台 Mac 上的本地模型应用。`lmdesk` 命令让你使用它的对话模型和图片模型。台面会自己排队、按需加载模型。

## 调用

- 命令是 `lmdesk`。找不到时用 `~/.local/bin/lmdesk`。
- 加 `--json` 时，stdout 是单个 JSON 对象；进度和提示都在 stderr。
- **命令会自己排队等待**，生图或换模型可能要几分钟。把工具超时设得尽量长（至少 10 分钟），中途不要自己重试。

## 对话（一次性）

```bash
lmdesk models                                   # 本机有哪些对话模型、哪个已加载
lmdesk ask "把下面这段翻成英文" --model KEY --file draft.md
cat notes.txt | lmdesk ask "总结成三条要点"
```

- `ask` 不保留上下文。需要上下文时，用 `--file` 或 stdin 传入。
- 不写 `--model` 时，用台面当前已加载的模型。如果当前什么都没加载，会得到退出码 5，这时先运行 `lmdesk models`，按任务挑一个模型，再加 `--model` 重试。

## 生图与素材管理

```bash
lmdesk image sessions                            # 先看有没有合适的会话
lmdesk image new "首页 banner"                   # 没有就按用途新建，起有意义的名字
lmdesk image gen "首页 banner" "极简风格的山景插画" --size 1344x768 --out ./assets/hero.png
lmdesk image show "首页 banner"                  # 历史尝试：id、提示词、文件路径
lmdesk image gen "首页 banner" "改成黄昏色调" --from <尝试id> --strength 0.6 --out ./assets/hero.png
lmdesk image rename "首页 banner" "首页大图"
```

- 会话可以用名字或 id 指定。同名的有多个时，改用 id。
- 在满意的那张上继续改，用 `--from <尝试id>`；用 `--out` 把图放进项目。
- 不能删除会话。需要删的话，请用户在台面里删。
- 生图被你的工具超时打断时，stderr 里有一行 `lmdesk image wait <会话> <尝试id>`，**用它接着等，不要重新 gen**。生成会在台面继续进行。
- 能后台运行命令时，也可以先用 `lmdesk image gen … --no-wait` 提交，再用 `lmdesk image wait <会话> <尝试id>` 取结果。

## 退出码

- 退出码 0：成功。
- 退出码 1：其他错误，原因在 stderr 最后一行。
- 退出码 2：参数错误或会话名有歧义。按提示修正。
- 退出码 3：等待超时，台面一直在忙。告诉用户。如果是生图，稍后可以用 `lmdesk image wait` 取结果。
- 退出码 4：内存不足。
  - 生图：先问用户，用户同意后加 `--force` 重试。
  - 对话模型：不能强制加载。告诉用户，建议换一个更小的模型。
- 退出码 5：模型、会话或尝试不存在。用 `lmdesk models`、`lmdesk image sessions`、`lmdesk image show` 查清楚再调用。
- 退出码 6：被沙箱拦截，访问不了本机网络（127.0.0.1）。请求提升权限，或者告诉用户需要放行本机网络。

## 例子

1. 用户说「用本地模型把 README 翻成英文」：
   `lmdesk models`，选一个对话模型，然后 `lmdesk ask "翻译成英文，保留 Markdown 格式" --model KEY --file README.md`。
2. 用户说「本地生成一张 app 图标放到 ./tmp」：
   `lmdesk image sessions`，没有合适的会话就 `lmdesk image new "app 图标"`，然后 `lmdesk image gen "app 图标" "扁平风格的山形图标，蓝色" --size 1024x1024 --out ./tmp/icon.png`。
```

退出码 6 那一段的「具体放行方法」在 Task 17 实测后补充，这里先保留通用说法。

- [ ] **Step 4: 写 `scripts/lmdesk`**

```bash
#!/bin/bash
# Development entry for lmdesk: run the repo's desk.agent_cli with a Python that has only the stdlib needs.
set -euo pipefail
SELF="$(/usr/bin/python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$0")"
ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"
PY="${LMDESK_PYTHON:-$(command -v python3)}"
exec env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m desk.agent_cli "$@"
```

```bash
chmod +x scripts/lmdesk
```

- [ ] **Step 5: 运行测试**

运行：`python -m pytest tests/test_agent_skill_md.py -v`
预期：全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add desk/agent_skill/bundled scripts/lmdesk tests/test_agent_skill_md.py
git commit -m "feat(agent-skill): SKILL.md 与开发态 lmdesk 入口（A-04/A-80..A-82）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: 设置页「本机 agent」区域（A-60 至 A-65、A-67）

**Files:**
- Create: `desk/static/js/pure/agent_skill.js`、`desk/static/js/panes/agent_skill.js`
- Modify: `desk/static/index.html`（在「对外 API」那个 section 后面插入）
- Modify: `desk/static/js/api.js`
- Modify: `desk/static/js/panes/settings.js`（`init` 时同时初始化新区域）
- Modify: 设置页样式文件（先找到 `.settings-section` 所在的 css 文件）
- Test: `tests/js/agent_skill.test.js`、`tests/e2e/test_agent_skill_settings.py`

**Interfaces:**
- 消费：`GET/POST /api/agent-skill`、`POST /api/agent-skill/check`（Task 11）
- 产出：
  - `pure/agent_skill.js`：
    - `initialChecked(rows) -> Set<string>`：`installed` 或 `stale` 的行。
    - `applyEnabled(rows, checked: Set) -> boolean`：A-64。
    - `rowText(row) -> {status: string, tone: "ok" | "warn" | "none"}`
    - `TRY_PHRASE`
  - `api.js`：`agentSkillStatus()`、`agentSkillApply(targets)`、`agentSkillCheck()`
  - `panes/agent_skill.js`：`createAgentSkillSection(root, ctx) -> {init}`

- [ ] **Step 1: 写失败的 node 测试**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { applyEnabled, initialChecked, rowText, TRY_PHRASE } from "../../desk/static/js/pure/agent_skill.js";

const row = (key, state, extra = {}) => ({ key, name: key, state, detected: true, ...extra });

test("installed 与 stale 的行初始勾选，其余不勾", () => {
  const rows = [row("claude", "installed"), row("codex", "stale"), row("pi", "absent"), row("dsh", "occupied")];
  assert.deepEqual([...initialChecked(rows)].sort(), ["claude", "codex"]);
});

test("应用按钮：只有会产生变化时才可点（A-64）", () => {
  const rows = [row("claude", "installed"), row("codex", "stale"), row("pi", "absent")];
  assert.equal(applyEnabled(rows, new Set(["claude"])), true, "取消勾选 stale 行会卸掉它");
  assert.equal(applyEnabled(rows, new Set(["claude", "codex"])), true, "stale 勾着也要能点，点了才会更新");
  const clean = [row("claude", "installed"), row("pi", "absent")];
  assert.equal(applyEnabled(clean, new Set(["claude"])), false);
  assert.equal(applyEnabled(clean, new Set(["claude", "pi"])), true);
  assert.equal(applyEnabled(clean, new Set()), true);
});

test("勾选 occupied 的行不算变化：它装不上", () => {
  const rows = [row("claude", "occupied")];
  assert.equal(applyEnabled(rows, new Set(["claude"])), false);
});

test("状态文字", () => {
  assert.deepEqual(rowText(row("a", "installed")), { status: "已安装", tone: "ok" });
  assert.deepEqual(rowText(row("a", "absent")), { status: "未安装", tone: "none" });
  assert.equal(rowText(row("a", "stale")).status, "指向旧位置，点应用更新");
  assert.equal(rowText(row("a", "stale", { target: "/gone/x" , message: null })).tone, "warn");
  assert.equal(rowText(row("a", "occupied", { message: "这里已有同名文件或目录，台面不会改动" })).status,
    "这里已有同名文件或目录，台面不会改动");
  assert.equal(rowText(row("a", "error", { message: "Permission denied" })).status, "无法写入：Permission denied");
});

test("试用语", () => {
  assert.equal(TRY_PHRASE, "用本地模型把这句话翻成英文：今天天气很好");
});
```

- [ ] **Step 2: 运行，确认失败**

运行：`node --test tests/js/agent_skill.test.js`
预期：FAIL，报 `Cannot find module`。

- [ ] **Step 3: 实现 `pure/agent_skill.js`**

```js
// 设置页「本机 agent」的纯逻辑（A-62/A-64）。
export const TRY_PHRASE = "用本地模型把这句话翻成英文：今天天气很好";

export function initialChecked(rows) {
  return new Set(rows.filter((r) => r.state === "installed" || r.state === "stale").map((r) => r.key));
}

export function applyEnabled(rows, checked) {
  return rows.some((r) => {
    const want = checked.has(r.key);
    if (want) return r.state === "absent" || r.state === "stale" || r.state === "error";
    return r.state === "installed" || r.state === "stale";
  });
}

export function rowText(row) {
  switch (row.state) {
    case "installed": return { status: "已安装", tone: "ok" };
    case "absent": return { status: "未安装", tone: "none" };
    case "stale": return { status: "指向旧位置，点应用更新", tone: "warn" };
    case "occupied": return { status: row.message ?? "位置被占用，台面不会改动", tone: "warn" };
    default: return { status: `无法写入：${row.message ?? "未知原因"}`, tone: "warn" };
  }
}
```

- [ ] **Step 4: 运行 node 测试**

运行：`node --test tests/js/agent_skill.test.js`
预期：全部 PASS。

- [ ] **Step 5: 加 HTML 标记、API 和区域模块**

在 `desk/static/index.html` 中，「对外 API」那个 `</section>` 之后、`<p class="inline-error" data-settings-error>` 之前，插入：

```html
<section class="settings-section" data-agent-skill><h3>本机 agent</h3><p class="hint">让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）。</p><ul class="agent-skill-list" data-agent-skill-list></ul><div class="settings-actions"><button data-agent-skill-apply data-icon-name="check" class="btn-primary" disabled>应用</button><button data-agent-skill-check data-icon-name="refresh">检查</button><span class="hint" data-agent-skill-check-result></span></div><p class="hint" data-agent-skill-cli></p><div class="url-row"><code data-agent-skill-try></code><button data-agent-skill-copy data-icon-name="copy" class="btn-sm">复制</button></div><p class="inline-error" data-agent-skill-error></p></section>
```

在 `desk/static/js/api.js` 的 `ROUTES` 里加：

```js
  agentSkill: "/api/agent-skill", agentSkillCheck: "/api/agent-skill/check",
```

然后照着文件里现有的命名操作的写法（参考 `gatewayConfig`、`writeConfig` 的实现），导出三个函数：

```js
export const agentSkillStatus = () => getJson(ROUTES.agentSkill);
export const agentSkillApply = (targets) => postJson(ROUTES.agentSkill, { targets });
export const agentSkillCheck = () => postJson(ROUTES.agentSkillCheck, {});
```

`getJson` 和 `postJson` 换成 api.js 里实际的辅助函数名，先用 `grep -n "^async function\|^function\|^export" desk/static/js/api.js` 看清楚。

`desk/static/js/panes/agent_skill.js`：

```js
// ui:agentSkillSection —— 设置页「本机 agent」：多选安装、检查、试用语（A-60..A-67）。
import * as api from "../api.js";
import { applyEnabled, initialChecked, rowText, TRY_PHRASE } from "../pure/agent_skill.js";

export function createAgentSkillSection(root) {
  const els = {
    list: root.querySelector("[data-agent-skill-list]"),
    apply: root.querySelector("[data-agent-skill-apply]"),
    check: root.querySelector("[data-agent-skill-check]"),
    checkResult: root.querySelector("[data-agent-skill-check-result]"),
    cli: root.querySelector("[data-agent-skill-cli]"),
    tryText: root.querySelector("[data-agent-skill-try]"),
    copy: root.querySelector("[data-agent-skill-copy]"),
    error: root.querySelector("[data-agent-skill-error]"),
  };
  let rows = [];
  let checked = new Set();

  const refreshApply = () => { els.apply.disabled = !applyEnabled(rows, checked); };

  function render(payload) {
    rows = payload.targets ?? [];
    els.list.replaceChildren(...rows.map((row) => {
      const li = root.ownerDocument.createElement("li");
      li.className = "agent-skill-row";
      li.dataset.key = row.key;
      li.dataset.state = row.state;
      const label = root.ownerDocument.createElement("label");
      label.className = "check-row";
      const box = root.ownerDocument.createElement("input");
      box.type = "checkbox";
      box.checked = checked.has(row.key);
      box.addEventListener("change", () => { if (box.checked) checked.add(row.key); else checked.delete(row.key); refreshApply(); });
      const name = root.ownerDocument.createElement("span");
      name.textContent = row.name;
      label.append(box, name);
      const detected = root.ownerDocument.createElement("span");
      detected.className = "hint";
      detected.textContent = row.detected ? "已检测到" : "未检测到";
      const { status, tone } = rowText(row);
      const badge = root.ownerDocument.createElement("span");
      badge.className = `badge badge-${tone === "ok" ? "ok" : tone === "warn" ? "busy" : "none"}`;
      badge.dataset.agentSkillStatus = "";
      badge.textContent = status;
      li.append(label, detected, badge);
      if (row.shared_note) {
        const note = root.ownerDocument.createElement("span");
        note.className = "hint";
        note.textContent = row.shared_note;
        li.append(note);
      }
      return li;
    }));
    const cli = payload.cli ?? {};
    els.cli.textContent = `命令行 lmdesk：${cli.path ?? "~/.local/bin/lmdesk"} · ${rowText(cli).status}（至少勾选一个 agent 时自动安装）`;
    refreshApply();
  }

  async function load() {
    const payload = await api.agentSkillStatus();
    checked = initialChecked(payload.targets ?? []);
    render(payload);
  }

  els.apply.addEventListener("click", async () => {
    els.error.textContent = "";
    try {
      const payload = await api.agentSkillApply([...checked]);
      checked = initialChecked(payload.targets ?? []);
      render(payload);
      const failed = (payload.targets ?? []).filter((r) => r.result === "error");
      if (failed.length) els.error.textContent = failed.map((r) => `${r.name}：${rowText(r).status}`).join("；");
    } catch (error) { els.error.textContent = error.message; }
  });

  els.check.addEventListener("click", async () => {
    els.checkResult.textContent = "检查中…";
    try {
      const result = await api.agentSkillCheck();
      els.checkResult.textContent = result.ok ? "lmdesk 能连上台面 ✓" : result.message;
    } catch (error) { els.checkResult.textContent = error.message; }
  });

  els.tryText.textContent = TRY_PHRASE;
  els.copy.addEventListener("click", async () => {
    try { await globalThis.navigator.clipboard.writeText(TRY_PHRASE); }
    catch (error) { els.error.textContent = error.message; }
  });

  return { init: () => load().catch((error) => { els.error.textContent = error.message; }) };
}
```

`desk/static/js/panes/settings.js`：在文件顶部 import `createAgentSkillSection`；在 `createSettingsPane` 里构造 `const agentSkill = createAgentSkillSection(root.querySelector("[data-agent-skill]") ?? root);`，并在 `init()` 里加一行 `agentSkill.init();`。

样式：在 `.settings-section` 所在的 css 文件里加入下面的规则，保证窄窗口下自动换行、不出现横向滚动（A-65）。

```css
.agent-skill-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.agent-skill-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 0; }
.agent-skill-row .check-row { margin: 0; }
.agent-skill-row .badge { max-width: 100%; overflow-wrap: anywhere; }
[data-agent-skill] .url-row code { overflow-wrap: anywhere; min-width: 0; }
```

- [ ] **Step 6: 写 e2e 测试 `tests/e2e/test_agent_skill_settings.py`**

```python
"""A-T5: settings → 本机 agent: multi-select apply, stale row, check, copy, narrow window."""
import os
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness


def _open(page, h):
    page.goto(h.base_url)
    page.locator("[data-open-settings]").dispatch_event("click")
    section = page.locator("[data-agent-skill]")
    expect(section).to_be_visible()
    return section


def test_multi_select_apply_installs_only_checked(page, tmp_path, monkeypatch, audit_violations):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        rows = section.locator(".agent-skill-row")
        expect(rows).to_have_count(4)
        apply = section.locator("[data-agent-skill-apply]")
        expect(apply).to_be_disabled()
        section.locator(".agent-skill-row[data-key=pi] input").check()
        expect(apply).to_be_enabled()
        apply.click()
        expect(section.locator(".agent-skill-row[data-key=pi] [data-agent-skill-status]")).to_have_text("已安装")
        expect(section.locator(".agent-skill-row[data-key=claude] [data-agent-skill-status]")).to_have_text("未安装")
        assert (home / ".pi/agent/skills/local-model-desk").is_symlink()
        assert not (home / ".claude/skills/local-model-desk").exists()
        expect(apply).to_be_disabled()
    assert audit_violations == []


def test_stale_row_is_checked_and_apply_is_enabled(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    link = home / ".claude/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to("/gone/Old.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk")
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        row = section.locator(".agent-skill-row[data-key=claude]")
        expect(row.locator("input")).to_be_checked()
        expect(row.locator("[data-agent-skill-status]")).to_have_text("指向旧位置，点应用更新")
        expect(section.locator("[data-agent-skill-apply]")).to_be_enabled()


def test_occupied_row_shows_reason(page, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".dsh/skills/local-model-desk").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        expect(section.locator(".agent-skill-row[data-key=dsh] [data-agent-skill-status]")).to_contain_text("台面不会改动")


def test_check_and_copy(page, tmp_path, monkeypatch, context):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        section.locator("[data-agent-skill-check]").click()
        expect(section.locator("[data-agent-skill-check-result]")).not_to_have_text("检查中…")
        section.locator("[data-agent-skill-copy]").click()
        assert page.evaluate("navigator.clipboard.readText()") == "用本地模型把这句话翻成英文：今天天气很好"


def test_narrow_and_short_window_no_horizontal_scroll(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        page.set_viewport_size({"width": 720, "height": 520})
        _open(page, h)
        overflow = page.locator("#pane-settings").evaluate("el => el.scrollWidth - el.clientWidth")
        assert overflow <= 0
```

检查按钮在测试台面里运行的是 `scripts/lmdesk status`，这时 `LMD_SHELL_PORT` 没有指向测试台面，所以结果通常是「连不上」。测试只断言结果文字已经出现、并且不再是「检查中…」。剪贴板权限和 `context` fixture 的写法，参照 `tests/e2e/conftest.py` 里现有的写法；如果它不支持 clipboard，就去掉剪贴板断言，改为断言 `[data-agent-skill-try]` 的文本。

- [ ] **Step 7: 运行测试**

运行：`node --test tests/js && python -m pytest tests/e2e/test_agent_skill_settings.py tests/e2e/test_settings_api.py -v`
预期：全部 PASS。

- [ ] **Step 8: 提交**

```bash
git add desk/static tests/js/agent_skill.test.js tests/e2e/test_agent_skill_settings.py
git commit -m "feat(settings): 本机 agent 区域——多选安装、检查与试用语（A-60..A-67）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: 聊天页「模型已被 agent 切换」提示（A-66）

**Files:**
- Create: `desk/static/js/pure/agent_switch.js`
- Modify: `desk/static/index.html`（在聊天页 `.model-row` 后插入一行提示）
- Modify: `desk/static/js/panes/chat.js`（`renderLlm`）
- Test: `tests/js/agent_switch.test.js`、`tests/e2e/test_agent_switch_notice.py`

**Interfaces:**
- 产出：`agentSwitchNotice(prevKey: string | null, payload) -> string | null`。只有当 `payload.loaded_by === "agent"`、状态为 loaded、`model_key` 有值、并且和 `prevKey` 不同时，才返回文案 `模型已被 agent 切换为 ${name}`；`prevKey` 为 null（页面第一次看到模型）时不提示。

- [ ] **Step 1: 写失败的 node 测试**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { agentSwitchNotice } from "../../desk/static/js/pure/agent_switch.js";

const p = (key, by, name = key) => ({ state: { status: "loaded", model_key: key }, loaded_model: { name }, loaded_by: by });

test("agent 换了模型才提示", () => {
  assert.equal(agentSwitchNotice("glm", p("qwen27", "agent", "Qwen 27B")), "模型已被 agent 切换为 Qwen 27B");
  assert.equal(agentSwitchNotice("glm", p("qwen27", "ui")), null);
  assert.equal(agentSwitchNotice("glm", p("glm", "agent")), null);
  assert.equal(agentSwitchNotice(null, p("glm", "agent")), null);
  assert.equal(agentSwitchNotice("glm", { state: { status: "loading", model_key: "x" }, loaded_by: null }), null);
});
```

- [ ] **Step 2: 运行，确认失败**

运行：`node --test tests/js/agent_switch.test.js`
预期：FAIL。

- [ ] **Step 3: 实现**

```js
// 聊天页：驻留模型被 agent 换掉时给一条可关闭的提示（A-66）。
export function agentSwitchNotice(prevKey, payload) {
  const state = payload?.state ?? {};
  if (state.status !== "loaded" || !state.model_key || payload.loaded_by !== "agent") return null;
  if (prevKey === null || prevKey === state.model_key) return null;
  return `模型已被 agent 切换为 ${payload.loaded_model?.name ?? state.model_key}`;
}
```

`desk/static/index.html` 聊天页：在 `.model-row` 的 `</div>` 之后插入：

```html
<div class="agent-switch-notice" data-agent-switch hidden><span data-agent-switch-text></span><button class="btn-sm" data-agent-switch-close data-icon-name="x" aria-label="关闭提示">关闭</button></div>
```

`desk/static/js/panes/chat.js`：

- import `agentSwitchNotice`；
- 在 `els` 里加上 `agentSwitch`、`agentSwitchText`、`agentSwitchClose` 三个元素；
- 绑定关闭按钮：`els.agentSwitchClose.addEventListener("click", () => { els.agentSwitch.hidden = true; });`
- 在 `renderLlm` 的开头（在 `lastResidentModelKey` 被更新之前）加：

```js
    const notice = agentSwitchNotice(lastResidentModelKey, payload);
    if (notice) { els.agentSwitchText.textContent = notice; els.agentSwitch.hidden = false; }
```

`lastResidentModelKey` 就是这个函数末尾维护的「上次看到的驻留模型」，正好可以当作 `prevKey`。

样式（与 `.settings-section` 同一个 css 文件）：

```css
.agent-switch-notice { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 8px; background: var(--surface-2, #f3f4f6); }
.agent-switch-notice[hidden] { display: none; }
```

- [ ] **Step 4: 写 e2e 测试**

```python
"""A-66: the chat page says so when an agent swapped the resident model."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness

CHAT, OTHER = "glm", "qwen27"   # 同 Task 8


def test_notice_appears_after_agent_swap_and_closes(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        page.goto(h.base_url)
        expect(page.locator("[data-model-state]")).to_contain_text("已加载")
        notice = page.locator("[data-agent-switch]")
        expect(notice).to_be_hidden()
        h.llm.load(OTHER, origin="agent"); h.llm.wait_settled()
        expect(notice).to_be_visible(timeout=10_000)
        expect(notice).to_contain_text("模型已被 agent 切换为")
        page.locator("[data-agent-switch-close]").click()
        expect(notice).to_be_hidden()


def test_no_notice_when_the_user_switches(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        page.goto(h.base_url)
        expect(page.locator("[data-model-state]")).to_contain_text("已加载")
        h.llm.load(OTHER); h.llm.wait_settled()
        page.wait_for_timeout(4000)
        expect(page.locator("[data-agent-switch]")).to_be_hidden()
```

- [ ] **Step 5: 运行测试**

运行：`node --test tests/js && python -m pytest tests/e2e/test_agent_switch_notice.py tests/e2e/test_chat_layout.py -v`
预期：全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add desk/static tests/js/agent_switch.test.js tests/e2e/test_agent_switch_notice.py
git commit -m "feat(chat): agent 切换驻留模型时在聊天页提示（A-66）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: 菜单栏失效提示（A-71 的 Swift 部分）

**Files:**
- Modify: `macos/ShellStatus.swift`（`DeskStateSnapshot` 增加 `agentSkillStale`，新增 `agentSkillMenuNote(for:) -> String?`）
- Modify: `macos/StatusItemController.swift`（显示菜单项和提示点）
- Modify: `macos/harness/ShellHarness.swift`（新子命令 `agent-skill-note`）
- Modify: `tests/test_shell_status.py`

**Interfaces:**
- 产出：
  - `DeskStateSnapshot.agentSkillStale: Bool`：缺这个字段时为 false。
  - `func agentSkillMenuNote(for status: ShellStatus) -> String?`：stale 时返回 `"agent 链接指向旧位置，打开设置更新"`，否则返回 nil。
  - harness 子命令 `agent-skill-note`：从 stdin 读同样格式的 fixture，有提示时输出提示文字，没有时输出空行。

- [ ] **Step 1: 写失败的测试（追加到 `tests/test_shell_status.py`）**

```python
STALE = {**IDLE, "agent_skill_stale": True}


@pytest.mark.parametrize("desk_state,expected", [
    (IDLE, ""), (STALE, "agent 链接指向旧位置，打开设置更新"), ({**HELD_LLM, "agent_skill_stale": True},
                                                       "agent 链接指向旧位置，打开设置更新"),
])
def test_agent_skill_note(desk_state, expected):
    fixture = {"server": "owned", "needs_setup": False, "desk_state": desk_state}
    proc = subprocess.run([harness_path(), "agent-skill-note"], input=json.dumps(fixture),
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


def test_stale_flag_does_not_change_menu_title():
    fixture = {"server": "owned", "needs_setup": False, "desk_state": STALE}
    proc = subprocess.run([harness_path(), "map-status"], input=json.dumps(fixture),
                          capture_output=True, text=True, timeout=30)
    assert proc.stdout.strip() == "空闲"
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_shell_status.py -v -k agent_skill`
预期：FAIL，harness 不认识这个子命令（退出码非 0）。

- [ ] **Step 3: 实现**

`macos/ShellStatus.swift`：

```swift
struct DeskStateSnapshot: Equatable {
  var holderKind: String?
  var holderLabel: String?
  var holderDisplay: String?
  var agentSkillStale: Bool = false

  /// Ignores unknown fields, but rejects an absent or malformed `holder`.
  static func parse(_ object: Any) -> DeskStateSnapshot? {
    guard let dict = object as? [String: Any], let holderValue = dict["holder"] else {
      return nil
    }
    let stale = (dict["agent_skill_stale"] as? Bool) ?? false
    if holderValue is NSNull {
      return DeskStateSnapshot(holderKind: nil, holderLabel: nil, holderDisplay: nil, agentSkillStale: stale)
    }
    guard let holder = holderValue as? [String: Any], let kind = holder["kind"] as? String else {
      return nil
    }
    return DeskStateSnapshot(holderKind: kind, holderLabel: holder["label"] as? String,
                              holderDisplay: holder["display"] as? String, agentSkillStale: stale)
  }
}

/// A-71: a menu note when an installed agent link points at another copy of the app.
func agentSkillMenuNote(for status: ShellStatus) -> String? {
  guard status.desk?.agentSkillStale == true else { return nil }
  return "agent 链接指向旧位置，打开设置更新"
}
```

`macos/harness/ShellHarness.swift` 的 switch 里加一个分支：

```swift
    case "agent-skill-note": print(agentSkillMenuNote(for: parseStatusFixture()) ?? "")
```

`macos/StatusItemController.swift`：

- 在 `init` 里，仿照 `settingsItem` 的建法，新建 `agentSkillItem`（SF Symbol 用 `exclamationmark.circle`），action 与「设置」菜单项相同（打开设置），初始隐藏 `isHidden = true`，插在 `detailItem` 下面。
- 在 `render(_:)` 末尾加：

```swift
    let note = agentSkillMenuNote(for: status)
    agentSkillItem.isHidden = note == nil
    agentSkillItem.title = note ?? ""
```

- 提示点：在 `configureStatusButton` 画图标的闭包里，当 `agentSkillMenuNote(for: status) != nil` 时，在右上角画一个直径 5pt 的实心圆。图标是 template 图，这个点会跟随明暗模式一起着色。为此 `configureStatusButton` 要新增参数 `dot: Bool`，`render` 调用时传入 `note != nil`。

- [ ] **Step 4: 运行测试**

运行：`python -m pytest tests/test_shell_status.py tests/test_shell_static.py -v`
预期：全部 PASS。`test_shell_static.py` 会检查 Swift 能否编译。

- [ ] **Step 5: 提交**

```bash
git add macos tests/test_shell_status.py
git commit -m "feat(shell): agent 链接失效时菜单栏提示（A-71）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: 打包与卸载（A-57、A-90、A-91）

**Files:**
- Modify: `scripts/build-app.sh`（生成 `Contents/Resources/bin/lmdesk`）
- Modify: `scripts/uninstall-app.sh`（清理 agent 链接）
- Test: `tests/test_uninstall_agent_links.py`；`tests/test_e2e_scripts.py` 里如果已有 build-app 的结构检查，就在那里加断言

- [ ] **Step 1: 写失败的卸载测试**

```python
"""A-57: uninstall-app.sh removes only our agent links, honours --dry-run."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(home, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([str(ROOT / "scripts" / "uninstall-app.sh"), "--app-path", str(home / "nope.app"),
                           "--data-root", str(home / "data"), "--launch-agents-dir", str(home / "LA"), *args],
                          capture_output=True, text=True, env=env, timeout=60)


def _setup(tmp_path):
    home = tmp_path / "home"
    ours = home / ".claude/skills/local-model-desk"
    ours.parent.mkdir(parents=True)
    ours.symlink_to("/x/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk")
    cli = home / ".local/bin/lmdesk"
    cli.parent.mkdir(parents=True)
    cli.symlink_to("/x/LocalModelDesk.app/Contents/Resources/bin/lmdesk")
    theirs = home / ".pi/agent/skills/local-model-desk"
    theirs.mkdir(parents=True)
    (theirs / "SKILL.md").write_text("someone else")
    other_link = home / ".dsh/skills/local-model-desk"
    other_link.parent.mkdir(parents=True)
    other_link.symlink_to(tmp_path)
    return home, ours, cli, theirs, other_link


def test_dry_run_reports_and_keeps(tmp_path):
    home, ours, cli, *_ = _setup(tmp_path)
    r = _run(home, "--dry-run")
    assert str(ours) in r.stdout and str(cli) in r.stdout
    assert ours.is_symlink() and cli.is_symlink()


def test_removes_only_our_links(tmp_path):
    home, ours, cli, theirs, other_link = _setup(tmp_path)
    _run(home)
    assert not ours.is_symlink() and not cli.is_symlink()
    assert (theirs / "SKILL.md").read_text() == "someone else"
    assert other_link.is_symlink()
```

- [ ] **Step 2: 运行，确认失败**

运行：`python -m pytest tests/test_uninstall_agent_links.py -v`
预期：`test_removes_only_our_links` FAIL，因为链接还在。

- [ ] **Step 3: 在 `scripts/uninstall-app.sh` 里加函数并调用**

把下面的函数放在 `guarded_remove` 之后：

```bash
# A-57: remove agent skill / lmdesk links that point into a LocalModelDesk; never real files, never foreign links.
remove_agent_links() {
  local link target
  for link in "$HOME/.claude/skills/local-model-desk" "$HOME/.codex/skills/local-model-desk" \
              "$HOME/.agents/skills/local-model-desk" "$HOME/.pi/agent/skills/local-model-desk" \
              "$HOME/.dsh/skills/local-model-desk" "$HOME/.local/bin/lmdesk"; do
    [[ -L "$link" ]] || continue
    target="$(readlink "$link")"
    case "$target" in
      */agent_skill/bundled/local-model-desk|*/Contents/Resources/bin/lmdesk|*/scripts/lmdesk) ;;
      *) continue ;;
    esac
    if [[ "$DRY_RUN" == 1 ]]; then
      echo "[dry-run] rm '$link'"
    else
      rm -f -- "$link" || fail "failed to remove $link"
    fi
  done
}
```

在脚本主流程删除 app 包之前调用 `remove_agent_links`：先用 `grep -n "guarded_remove \"\$APP_PATH\"" scripts/uninstall-app.sh` 找到删 app 的那一行，在它前面一行插入。

- [ ] **Step 4: 在 `scripts/build-app.sh` 里生成 `bin/lmdesk`**

紧接在 `[2/9] Copy desk package` 的 rsync 之后加：

```bash
mkdir -p "$RES/bin"
cat > "$RES/bin/lmdesk" <<'SH'
#!/bin/bash
# lmdesk inside LocalModelDesk.app: the embedded Python runs desk.agent_cli (A-02).
SELF="$(/usr/bin/python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$0" 2>/dev/null || echo "$0")"
RES="$(cd "$(dirname "$SELF")/.." && pwd)"
exec env -u PYTHONHOME PYTHONPATH="$RES" PYTHONDONTWRITEBYTECODE=1 "$RES/python/bin/python3.13" -s -m desk.agent_cli "$@"
SH
chmod 755 "$RES/bin/lmdesk"
```

关于 `/usr/bin/python3`：它只用来解析软链接的真实路径，系统自带，不需要额外依赖。如果系统里没有，就退回用 `$0`，这时从软链接运行会解析错位置，但直接运行 app 里的这个脚本仍然正常。实现时可以改用 bash 的 `readlink` 循环，换掉这个依赖：

```bash
SELF="$0"; while [[ -L "$SELF" ]]; do t="$(readlink "$SELF")"; [[ "$t" = /* ]] && SELF="$t" || SELF="$(dirname "$SELF")/$t"; done
```

推荐用这个 readlink 循环；`scripts/lmdesk` 也同样改成这种写法。

- [ ] **Step 5: 构建并验证打包后的产物（A-91）**

```bash
python -m pytest tests/test_uninstall_agent_links.py -v
scripts/build-app.sh --output dist
test -x dist/LocalModelDesk.app/Contents/Resources/bin/lmdesk
test -f dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md
dist/LocalModelDesk.app/Contents/Resources/bin/lmdesk --help
```

预期：
- pytest 全部 PASS；
- 构建成功；
- 两个 `test` 检查都通过；
- `--help` 输出 lmdesk 的用法。

然后打开 `dist/LocalModelDesk.app`，等它就绪后运行：

```bash
dist/LocalModelDesk.app/Contents/Resources/bin/lmdesk status --json
```

预期：退出码 0，`version.cli` 等于 `version.desk`。

- [ ] **Step 6: 提交**

```bash
git add scripts/build-app.sh scripts/uninstall-app.sh scripts/lmdesk tests/test_uninstall_agent_links.py
git commit -m "build: app 包内置 lmdesk，卸载时清理 agent 链接（A-57/A-90/A-91）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: 全量回归与真实 agent 手动验收（A-T9）

**Files:**
- Create: `docs/superpowers/acceptance/2026-10-16-agent-skill.md`（验收记录）
- Modify: `desk/agent_skill/bundled/local-model-desk/SKILL.md`（写入沙箱放行方法）
- Modify: `docs/superpowers/specs/2026-10-16-agent-skill-design.md`（只在有新发现时修改）

- [ ] **Step 1: 全量自动测试**

运行：`python -m pytest -q && node --test tests/js && python -m pytest tests/e2e -q`
预期：全部 PASS。有失败就修，修完再继续。

- [ ] **Step 2: 用 dist 版本在设置页勾选四个 agent 并应用**

先运行 `scripts/build-app.sh --output dist`，再打开 `dist/LocalModelDesk.app`，在「设置 → 本机 agent」里勾选全部四个，点「应用」，再点「检查」。

预期：
- 四行都显示「已安装」；
- 命令行那一行显示「已安装」；
- 检查结果显示「lmdesk 能连上台面 ✓」。

- [ ] **Step 3: 在每个 agent 里试两句话，记录结果**

逐个在 Claude Code、Codex、pi、DeepSeek Harness 里，各开一个新会话，在一个临时目录里输入：

1. 「用本地模型把这句话翻成英文：今天天气很好」
2. 「本地生成一张猫的图片放进 ./tmp」

每次都记录以下内容：
- agent 有没有自己找到并调用 `lmdesk`；
- 退出码和最终结果；
- 有没有被沙箱拦截（退出码 6）；如果被拦了，具体是怎么放行的（配置项或者命令行参数）。

Codex 和 DeepSeek Harness 一定要在默认沙箱设置下试。

- [ ] **Step 4: 验证「被打断后续等」这条链路**

在 Claude Code 里说：「本地生成一张 2048x2048、50 步的图，然后告诉我路径」。观察：如果 Bash 工具超时（默认 2 分钟），agent 是否用 stderr 给出的 `lmdesk image wait …` 接着等，而不是重新 gen。在台面的图片页里确认只有一次尝试。

- [ ] **Step 5: 把沙箱放行方法写进 SKILL.md**

根据 Step 3 的实测结果，在 SKILL.md 退出码 6 那一条下面，按 agent 分条写出具体的放行方法。重新运行 `python -m pytest tests/test_agent_skill_md.py -q`，确认仍然 PASS。

- [ ] **Step 6: 写验收记录并提交**

`docs/superpowers/acceptance/2026-10-16-agent-skill.md` 用一张表，列出四个 agent 在两个场景下的结果（是否自己调用、退出码、是否被沙箱拦截、放行方法），再加上续等链路的结果，以及发现的问题。

```bash
git add docs/superpowers/acceptance/2026-10-16-agent-skill.md desk/agent_skill/bundled/local-model-desk/SKILL.md docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "docs(acceptance): 本机 agent 能力四个 agent 实测与沙箱放行说明（A-T9）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 规格覆盖对照

| 规格条目 | 任务 |
|---|---|
| A-00a 至 A-00d | 全局约束；不改 gateway（任何任务都不改 `desk/gateway/`） |
| A-01 至 A-04 | 4（version、包结构）、5、8、12（scripts/lmdesk）、16（bin/lmdesk） |
| A-05 | 8、9（`AGENT`）、2（服务端读取） |
| A-10 至 A-16 | 8、9 |
| A-20 至 A-28 | 6（判定）、7（等待）、8（ask、换模型）、9（生图、续等、取消）；A-28 不写代码，只是有意不做 |
| A-30 至 A-33 | 5、8（版本提示） |
| A-40、A-43 | 2 |
| A-41 | 11 |
| A-42 | 3 |
| A-44、A-45 | 4 |
| A-50 至 A-56 | 1（codex 目录实测）、10、11、13 |
| A-57 | 16 |
| A-60 至 A-65、A-67 | 13 |
| A-66 | 14 |
| A-70 至 A-72 | 10、11（失效判定和缓存）、15（菜单栏）；A-70 和 A-72 由软链接方案本身保证 |
| A-80 至 A-82 | 12、17（沙箱说明） |
| A-90、A-91 | 16 |
| A-T1 至 A-T9 | 6、7、8、9、2、3、10、13、14、12、16、15、17 |
