# lmdesk / 本机 agent：cross-exam 缺口修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉 2026-10-16 cross-exam 在 `feat/agent-skill` 上实测出的 12 条缺口和 1 条旅程缺口，重点是「换模型后对话一直被当成已收回」（G6/G7）。

**Architecture:**
- 根因修复在服务端：arbiter 增加 `retarget_heavy`，`LlmService.load` 换模型时用它把同一张 llm 令牌改记成新模型，不再沿用旧模型的标签和预算开销。
- 命令行（`desk/agent_cli/`，只用标准库）补几处：
  - 连续被拒时不原地打转；
  - 心跳线程保证每 15s 一行；
  - stdin 读取不挂死；
  - `--file` 非 UTF-8 时给出明确报错；
  - Ctrl-C 后如实报告结果；
  - 拉起台面时带「后台」参数。
- Swift 外壳按这个参数决定启动时不弹主窗口。
- 设置页的「应用」按钮把命令行链接也算进去；说明文字和 SKILL.md 跟上第二期。

**Tech Stack:** Python 3.13 标准库 · pytest · 原生 ES modules + `node --test` · Playwright e2e（`tests/e2e`）· Swift / AppKit，用 `macos/harness/ShellHarness.swift` 测纯逻辑。

**Spec:**
- 缺口来源：`docs/cross-exam/2026-10-16-agent-skill/completion-report.md`（§缺口清单、§缺陷模式），证据在同目录 `evidence/qNN/`。
- 需求基准：`docs/superpowers/specs/2026-10-16-agent-skill-design.md`（A-xx）和 `docs/superpowers/specs/2026-10-16-agent-media-design.md`（B-xx）。
- 本计划改动的 A 条目（A-12、A-23、A-25、A-31、A-61、A-64、A-67）在各自任务里同步改 spec 原文。

## Global Constraints

- 退出码不变：0 成功；1 其他错误；2 参数错误或会话名有歧义；3 等待超时或中断；4 内存不足；5 不存在；6 被沙箱拦截（A-13）。
- `--timeout` 默认 1800 秒；轮询间隔从 2s 起，每次 ×1.5，最长 5s；等待提示每 15s 一行（A-23）。
- `desk/agent_cli/` 只 import 标准库和 `desk.agent_cli.*`（A-01）。
- 命令行改变状态的请求一律带 `"origin": "agent"`（A-05）。
- 面向用户和 agent 的文字一律简体中文；stdout 只放结果，进度和提示走 stderr（A-11）。
- 前端无构建步骤、无依赖；DOM 只用 `createElement` / `textContent`。
- 只构建到 `dist/`，绝不装到 `/Applications`。
- 台面未发布：不写兼容层或迁移代码。
- 每个任务按 TDD 走：先写测试、看它失败，再写实现、看它通过，最后提交。
- 只 `git add` 本任务列出的文件。`docs/cross-exam/`、`.allforai/`、`.claude/` 不进提交。
- 提交信息结尾加：
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```
- 测试命令：
  - Python：`python3 -m pytest <路径> -q`
  - 前端：`node --test tests/js`
  - Swift 纯逻辑：`python3 -m pytest tests/test_shell_status.py -q`（会用 `xcrun swiftc` 编译 harness）

## 本计划替用户做的决定（都按推荐项；评审时请逐条确认）

- **D1 换模型怎么记账**
  - 同一张 llm 令牌原地改记成新模型，不走「先释放再申请」。先释放会留出空档，媒体作业可能插进来。
  - 预算模式下按「去掉旧模型、加上新模型」重算一次。装不下就拒绝，并且**旧模型原样留着、照常可用**；先问 arbiter，问过才停旧进程。
- **D2 进度行用心跳线程**：每 15s 一行，从命令开始计时，不管主线程卡在哪（排队、HTTP 请求、等模型回答）。q14 里那 60 秒的空白是主线程卡在请求里造成的，在轮询里打点覆盖不到这种情况。
- **D3 stdin**：不是终端时，最多等 5 秒等第一个字节或结束。5 秒内什么都没有，就按没有输入处理，并在 stderr 说一句。一旦开始有数据，就读到结束为止，但受剩余 `--timeout` 约束。
- **D4 Ctrl-C 时作业已经做完**：仍然退出码 3，最后一行写「已中断。这次生成在中断前已经完成，没有取消」，前面保留 `wait` 续等提示。
- **D5 后台拉起**
  - lmdesk 用 `open -gj <app> --args --lmdesk-background` 拉起台面。
  - app 带这个参数启动时不显示主窗口；之后点 Dock 图标，照常打开窗口。
  - 菜单栏和 Dock 图标不变。
- **D6 J3（续写后不 join）**：续写得到的就是完整成片。SKILL.md 写明两种情况：
  - 续写的几段不需要再 join；
  - 用户说要「合成」「拼接」，或者几段是各自单独生成的，用 join，台面会留下合成记录。

  q40 已实测：续写的几段 join 出来，和续写成片的内容相同。
- **D7 防原地打转（缺陷模式 P2）**：`ask` 在模型已加载、要的就是它的情况下，对话请求连续 3 次被可重试的错误码拒绝，就不再排队，以退出码 1 报出台面给的原因。

## Review Focus

1. **换模型时，新模型和正在跑的媒体任务一起装不下**：换模型被拒，旧模型照常加载并能对话。agent 侧收到 `insufficient_budget` 后回到等待，不报错退出。（测试在 Task 2）
2. **换模型过程中送达一条台面状态，里面还是旧模型的标签**：不能被读成「已被收回」把加载作废。（测试在 Task 2）
3. **管道上游很慢，1 秒后才吐出第一段数据**（例如 `curl … | lmdesk ask`）：要照常读入，不能当成空输入。（测试在 Task 5）
4. **按 Ctrl-C 时台面已经退出**：不能说「已取消」，要保留续等提示。（测试在 Task 6）
5. **设置页一个 agent 都不勾，而命令行链接还在**：「应用」能点，点了卸掉链接。（测试在 Task 8）

---

## File Structure

| 文件 | 本计划里的职责 |
|---|---|
| `desk/arbiter/core.py` | 新增 `Arbiter.retarget_heavy` |
| `desk/llm/service.py` | `load` 换模型走 `retarget_heavy`；`_on_desk_state` 在换模型期间认旧标签 |
| `tests/test_arbiter_retarget.py`（新） | retarget 的台账、预算、拒绝 |
| `tests/llm/llm_fakes.py` | `FakeArbiter.retarget_heavy` |
| `tests/llm/test_llm_switch_evict.py` | 换模型的服务层测试 |
| `desk/agent_cli/chat.py` | 连续被拒退出；`--file` 解码报错；等回答时给心跳设原因 |
| `desk/agent_cli/waiter.py` | 心跳线程，`note()` |
| `desk/agent_cli/stdin_reader.py`（新） | 读管道输入，带空闲窗口和总时限 |
| `desk/agent_cli/cli.py` | 接上心跳与 `read_piped` |
| `desk/agent_cli/media.py` | `_interrupted`：信号后如实报告 |
| `desk/agent_cli/discovery.py` | 拉起时带 `--lmdesk-background`；不在 app 包内时说明原因 |
| `macos/ShellStatus.swift` | `backgroundLaunchArgument`、`showsWindowAtLaunch` |
| `macos/AppDelegate.swift` | 启动时按参数决定是否显示主窗口 |
| `macos/harness/ShellHarness.swift` | `window-at-launch` 命令 |
| `desk/static/js/pure/agent_skill.js` | `applyEnabled` 把命令行链接算进去 |
| `desk/static/js/panes/agent_skill.js` | 传入 cli；「检查」后刷新各行 |
| `desk/static/index.html` | 说明文字加上视频、音乐 |
| `desk/agent_skill/bundled/local-model-desk/SKILL.md` | 退出码 3、退出码 6、join 的说明 |
| `docs/superpowers/specs/2026-10-16-agent-skill-design.md` | 同步 A-12、A-23、A-25、A-31、A-61、A-64、A-67 |
| 测试：`tests/agent_cli/*`、`tests/js/agent_skill.test.js`、`tests/e2e/test_agent_skill_settings.py`、`tests/test_shell_status.py`、`tests/test_agent_skill_md.py` | 各任务的测试 |

---

### Task 1: arbiter 原地改记聊天模型（`retarget_heavy`）

**Files:**
- Modify: `desk/arbiter/core.py`（在 `release_heavy`，约 475 行之前，新增方法）
- Test: `tests/test_arbiter_retarget.py`（新建）

**Interfaces:**
- Produces: `Arbiter.retarget_heavy(token: str, label: str, display: str | None = None, *, params: dict | None = None, key: str | None = None) -> dict`
  - 成功：`{"ok": True, "token": token, "state": <desk_state>}`，并通知订阅者一次。
  - 失败：`{"ok": False, "reason": {"code", "message"}}`，台账不动。`code` 为以下之一：
    - `not_holder`：令牌不存在，或不是 llm；
    - `capacity_unknown`：预算模式下没给 params 和 key；
    - `insufficient_budget`：装不下。

- [ ] **Step 1: 写失败的测试**

`tests/test_arbiter_retarget.py`：

```python
"""换聊天模型时，同一张 llm 令牌改记成新模型（cross-exam G6/G7）。"""
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult
from desk.arbiter.state import still_holds
from desk.budget.budget import Workload

GB = 1_000_000_000


class KeyedBudget:
    """按 (kind, key) 给开销：换模型要两个大小不同的聊天模型，按 kind 给定值的 FakeBudget 分不出来。"""

    def __init__(self, costs):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[(kind, key)]


def _arbiter(budget=None, available=100 * GB):
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=available))
    return Arbiter(llm_port=43123, memory=memory, budget=budget,
                   reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]))


def _costs():
    table = {("llm", "small"): 20, ("llm", "big"): 60, ("video", None): 50}
    return KeyedBudget({k: Workload(k[0], k[1], v * GB, "measured") for k, v in table.items()})


def test_retarget_relabels_the_llm_holder_and_notifies_subscribers():
    arbiter = _arbiter()
    token = arbiter.acquire_heavy("llm", "glm", "GLM")["token"]
    seen = []
    arbiter.subscribe(seen.append)

    result = arbiter.retarget_heavy(token, "qwen", "Qwen", params={}, key="qwen")

    assert result["ok"] is True and result["token"] == token
    state = arbiter.desk_state()
    assert still_holds(state, "llm", "qwen") and not still_holds(state, "llm", "glm")
    assert state["holder"]["display"] == "Qwen"
    assert len(seen) == 1 and still_holds(seen[0], "llm", "qwen")
    assert arbiter.release_heavy(token) == {"ok": True}


def test_retarget_counts_the_new_model_and_drops_the_old_one():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]

    assert arbiter.retarget_heavy(token, "big", params={}, key="big")["ok"] is True

    # big 60 + video 50 > 100：开视频要先让出聊天模型，让出的应是 big。
    # 台账若还按 small 20 记，20 + 50 装得下，release 会是空的。
    answer = arbiter.can_start_heavy("video", params={}, key=None)
    assert [w["key"] for w in answer["release"]] == ["big"]


def test_retarget_refuses_when_the_new_model_does_not_fit_beside_running_media():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]
    assert arbiter.acquire_heavy("video", "job-1", params={}, key=None)["ok"] is True

    result = arbiter.retarget_heavy(token, "big", params={}, key="big")

    assert result["ok"] is False and result["reason"]["code"] == "insufficient_budget"
    assert still_holds(arbiter.desk_state(), "llm", "small")


def test_retarget_only_accepts_a_live_llm_token():
    arbiter = _arbiter()
    media = arbiter.acquire_heavy("video", "job-1")["token"]
    assert arbiter.retarget_heavy("nope", "qwen")["reason"]["code"] == "not_holder"
    assert arbiter.retarget_heavy(media, "qwen")["reason"]["code"] == "not_holder"


def test_budget_mode_retarget_needs_capacity_inputs():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]
    assert arbiter.retarget_heavy(token, "big")["reason"]["code"] == "capacity_unknown"
    assert still_holds(arbiter.desk_state(), "llm", "small")
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/test_arbiter_retarget.py -q`
Expected: FAIL，`AttributeError: 'Arbiter' object has no attribute 'retarget_heavy'`

- [ ] **Step 3: 实现**

在 `desk/arbiter/core.py` 的 `release_heavy` 之前加入（`fits`、`plan_acquire`、`replace` 在文件顶部已经 import 过）：

```python
    def retarget_heavy(self, token: str, label: str, display: str | None = None,
                       *, params: dict | None = None, key: str | None = None) -> dict:
        """换聊天模型：把这张 llm 令牌改记成新模型（label、display、预算开销一起换）。

        不走「先释放再申请」：中间会有一段谁都不持有的空档，媒体作业会插进来。
        也不能只换进程不换台账：台账还记着旧模型时，对话闸 `still_holds` 认不出
        新模型，每次对话都被当成「已被收回」拒掉（cross-exam G6/G7）。
        预算模式下按「去掉旧模型、加上新模型」重算一次；装不下就拒绝，台账不动。
        """
        with self._transition_lock:
            with self._state_lock:
                holder = self._holders.get(token)
                others = [w for t, w in self._workloads.items() if t != token]
            if holder is None or holder.kind != "llm":
                return {"ok": False, "reason": self._reason("not_holder", "这张令牌不是当前的聊天模型持有者")}
            workload = None
            if self._budget is not None:
                if params is None and key is None:
                    return {"ok": False, "reason": self._reason(
                        "capacity_unknown", "换模型需要模型参数才算得出内存开销；这次调用没有给出，不予更换")}
                workload = self._cost("llm", params, key)
                verdict = fits(others + [workload], self._capacity_bytes())
                if not verdict.ok:
                    refused = plan_acquire((), "llm", verdict)
                    return {"ok": False, "reason": self._reason(refused.reason_code, refused.reason_message)}
            with self._state_lock:
                self._holders[token] = replace(holder, label=label, display=display, since=self._clock())
                if workload is not None:
                    self._workloads[token] = workload
                holders = tuple(self._holders.values())
            state = self._state_for(holders)
        self._dispatch([state])
        return {"ok": True, "token": token, "state": state}
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/test_arbiter_retarget.py tests/test_arbiter_core.py tests/test_arbiter_state.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add desk/arbiter/core.py tests/test_arbiter_retarget.py
git commit -m "feat(arbiter): retarget_heavy relabels the chat-model lease in place

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 换模型用 `retarget_heavy`，换完能对话（G6、G7 根因）

**Files:**
- Modify: `desk/llm/service.py`
  - `__init__`（约 102 行附近加字段）
  - `load`（153–218 行整段替换）
  - `_on_desk_state`（331 行的 `still_held` 判断）
- Modify: `tests/llm/llm_fakes.py`（`FakeArbiter`）
- Modify: `tests/llm/test_llm_switch_evict.py`
- Modify: `tests/agent_cli/test_chat_cli.py`

**Interfaces:**
- Consumes: Task 1 的 `Arbiter.retarget_heavy(token, label, display, *, params, key)`。
- Produces:
  - `LlmService.load(key, origin)` 的签名不变；
  - 换模型被拒时抛 `LlmRejected(code, message)`，`code` 取 arbiter 给的值，比如 `insufficient_budget`。路由照旧映射成 409，命令行 `_swap` 已经会对它 `pause`。

- [ ] **Step 1: 给 FakeArbiter 加 `retarget_heavy`**

在 `tests/llm/llm_fakes.py` 的 `FakeArbiter.__init__` 参数表末尾加 `retarget_result: dict | None = None`，在方法体末尾加：

```python
        self.retarget_result = retarget_result
        self.on_retarget = None   # 测试可设：retarget 返回前调用，模拟这期间送达的台面状态
        self.last_retarget: dict | None = None
```

在 `release_heavy` 前加：

```python
    def retarget_heavy(self, token: str, label: str, display: str | None = None,
                       *, params: dict | None = None, key: str | None = None) -> dict:
        self.last_retarget = {"token": token, "label": label, "display": display, "params": params, "key": key}
        _record(self.calls, "retarget", token, label)
        if self.on_retarget is not None:
            self.on_retarget()
        return self.retarget_result or {"ok": True, "token": token}
```

- [ ] **Step 2: 写失败的测试**

在 `tests/llm/test_llm_switch_evict.py` 里，把 `test_switch_model_reuses_existing_llm_permit` 整个替换成下面三条，并在文件末尾追加第四条。文件顶部补上 `import pytest` 和 `from desk.llm.state import LlmRejected`。

```python
def test_switch_model_retargets_the_same_permit(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    testbed = make_loaded(tmp_path, entries=[glm, qwen])
    testbed.calls.clear()

    state = testbed.service.load("qwen")

    assert state["status"] == "loading"
    assert testbed.service.wait_settled()["status"] == "loaded"
    names = [call[0] for call in testbed.calls]
    assert "acquire" not in names and "release" not in names
    assert names[:4] == ["retarget", "terminate", "wait", "reap"]   # 先问 arbiter，再停旧进程
    assert testbed.calls[0] == ("retarget", "tok-1", "qwen")
    assert testbed.arbiter.last_retarget["key"] == "qwen"
    assert ("spawn", str(testbed.paths.venv_python),
            str(testbed.paths.models_root / qwen.relpath), 8767,
            str(testbed.paths.logs_dir / "mlx-lm.log")) in testbed.calls


def test_switch_refused_keeps_the_old_model_loaded(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    refusal = {"ok": False, "reason": {"code": "insufficient_budget", "message": "装不下"}}
    testbed = make_loaded(tmp_path, entries=[glm, qwen], arbiter_kw={"retarget_result": refusal})
    testbed.calls.clear()

    with pytest.raises(LlmRejected) as exc:
        testbed.service.load("qwen")

    assert exc.value.code == "insufficient_budget"
    status = testbed.service.status()
    assert status["state"]["status"] == "loaded" and status["state"]["model_key"] == "glm"
    assert "terminate" not in [call[0] for call in testbed.calls]


def test_state_with_the_old_label_during_a_switch_is_not_an_eviction(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    testbed = make_loaded(tmp_path, entries=[glm, qwen])
    old = {"kind": "llm", "label": "glm", "phase": "held"}
    testbed.arbiter.on_retarget = lambda: testbed.arbiter.emit(
        {"holder": old, "holders": [old], "media_busy": False})

    testbed.service.load("qwen")

    assert testbed.service.wait_settled()["status"] == "loaded"
```

文件末尾追加，用真 arbiter 复现 q41：

```python
def test_chat_after_a_switch_is_answered_not_refused_as_evicted(tmp_path):
    glm, qwen = make_entry(key="glm"), make_entry(key="qwen")
    paths = FakePaths(tmp_path)
    for entry in (glm, qwen):
        (paths.models_root / entry.relpath).mkdir(parents=True)
    port = _free_port()
    backend = FakeBackend(chat_result={"choices": [{"message": {"content": "好"}, "finish_reason": "stop"}],
                                       "usage": {"total_tokens": 1}})
    service = LlmService(
        backend=backend,
        arbiter=Arbiter(llm_port=port, reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[])),
        catalog=FakeCatalog([glm, qwen]), paths=paths, port=port, poll_interval_s=0.001,
    )
    service.load("glm")
    assert service.wait_settled()["status"] == "loaded"
    service.load("qwen")
    assert service.wait_settled()["status"] == "loaded"

    answer = service.chat_completion({"messages": [{"role": "user", "content": "hi"}], "model": "qwen"})

    assert answer["content"] == "好" and answer["model"] == "qwen"
    assert service.status()["state"]["status"] == "loaded"
```

在 `tests/agent_cli/test_chat_cli.py` 末尾追加命令行层的复现：

```python
def test_ask_switches_from_a_ui_loaded_model_and_both_can_chat(tmp_path):
    turn = [Delta(content="你好，世界"), Done(usage={"total_tokens": 1})]
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"},
                             chat_script=ChatScript(turn + turn)) as h:
        h.llm.load(CHAT); h.llm.wait_settled()

        r = run_cli(h, "ask", "你好", "--model", OTHER, "--timeout", "30")

        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "你好，世界"
        assert h.llm.status()["state"]["model_key"] == OTHER
        ui = h.llm.chat_completion({"messages": [{"role": "user", "content": "hi"}], "model": OTHER})
        assert ui["model"] == OTHER   # 界面身份的对话也不再被当成「已收回」
```

- [ ] **Step 3: 运行，确认失败**

Run: `python3 -m pytest tests/llm/test_llm_switch_evict.py tests/agent_cli/test_chat_cli.py::test_ask_switches_from_a_ui_loaded_model_and_both_can_chat -q`
Expected: FAIL
- 服务层：`"retarget"` 不在调用记录里；真 arbiter 那条抛 `LlmRejected: 模型已被台面收回`。
- 命令行那条：退出码 3，stderr 里反复出现「模型被换走了，重新排队」。

- [ ] **Step 4: 实现**

`desk/llm/service.py`：

① 在 `__init__` 最后一行 `self._loaded_by: str | None = None` 之后加：

```python
        # 换模型期间台面上记的还是旧模型；这段时间送达的状态不能被读成「被收回了」。
        self._swapping_from: str | None = None
```

② 把整个 `load` 方法（从 `def load(` 到 fresh 路径 `return self._state.to_dict()` 结束）替换为下面三个方法：

```python
    def load(self, key: Any, origin: str = "ui") -> dict[str, Any]:
        """Start loading *key* and immediately return its loading state."""
        if not isinstance(key, str) or not key.strip():
            raise LlmRejected(ERR_KEY_REQUIRED, "缺少 key 参数")
        with self._lock:
            if self._state.status == STATUS_LOADING:
                raise LlmRejected(ERR_LOAD_IN_PROGRESS, "已有模型正在加载")
            entry = self._find_entry(key)
            if entry is None:
                raise LlmRejected(ERR_MODEL_NOT_FOUND, f"未找到模型: {key}")
            roots = self._paths.resolve_paths()
            model_dir = Path(roots.models_root) / entry.relpath
            if not model_dir.is_dir():
                raise LlmRejected(ERR_MODEL_DIR_MISSING, f"模型目录不存在: {model_dir}")
            previous = (self._state, self._entry, self._loaded_by)
            swap_token = self._token if self._state.status == STATUS_LOADED else None
            if swap_token is not None:
                self._swapping_from = self._state.model_key
            self._entry = None
            self._state = LlmState(status=STATUS_LOADING, model_key=entry.key)
            self._load_generation += 1
            generation = self._load_generation
        if swap_token is not None:
            return self._swap(entry, model_dir, roots, origin, generation, swap_token, previous)

        # 预算要靠 config 与权重才算得出这个模型的真实开销；不传的话 budget.cost
        # 会把聊天算成 0 字节，于是预算对任何组合都说「装得下」（Task 9）。
        acquired = self._arbiter.acquire_heavy(
            "llm", entry.key, getattr(entry, "name", None),
            params=self._heavy_request(entry), key=entry.key,
        )
        if not acquired.get("ok"):
            reason = acquired.get("reason") or {}
            code = reason.get("code") if isinstance(reason, dict) else None
            message = reason.get("message") if isinstance(reason, dict) else None
            with self._lock:
                if generation == self._load_generation:
                    self._state = previous[0]
            raise LlmRejected(code or ERR_MEDIA_BUSY, message or "媒体任务正在运行")

        with self._lock:
            self._token = acquired.get("token")
            return self._start_load_locked(entry, model_dir, roots, origin, generation)

    def _swap(self, entry: Any, model_dir: Path, roots: Any, origin: str, generation: int,
              token: str, previous: tuple) -> dict[str, Any]:
        """换模型：同一张令牌改记成新模型，再停旧进程、起新进程（cross-exam G6/G7）。

        先问 arbiter 再停旧进程：新模型装不下时旧模型原样留着，不会两头落空。
        """
        answer = self._arbiter.retarget_heavy(token, entry.key, getattr(entry, "name", None),
                                              params=self._heavy_request(entry), key=entry.key)
        with self._lock:
            self._swapping_from = None
            if generation != self._load_generation:
                return self._state.to_dict()
            if not answer.get("ok"):
                self._state, self._entry, self._loaded_by = previous
                reason = answer.get("reason") or {}
                raise LlmRejected(reason.get("code") or ERR_MEDIA_BUSY, reason.get("message") or "换模型失败")
            if not self._teardown_proc_locked():
                self._state = LlmState(
                    status=STATUS_ERROR, model_key=entry.key,
                    error=LlmError(ERR_PORT_NOT_RELEASED, f"切换后端口 {self._port} 仍被占用"),
                )
                return self._state.to_dict()
            return self._start_load_locked(entry, model_dir, roots, origin, generation)

    def _start_load_locked(self, entry: Any, model_dir: Path, roots: Any, origin: str,
                           generation: int) -> dict[str, Any]:
        self._loaded_by = "agent" if origin == "agent" else "ui"
        self._load_thread = threading.Thread(
            target=self._load_worker,
            args=(entry, model_dir, Path(roots.venv_python), self._log_path(roots), generation),
            daemon=True,
            name="llm-load",
        )
        self._load_thread.start()
        return self._state.to_dict()
```

③ `_on_desk_state` 里，把

```python
            still_held = any(
                isinstance(h, dict)
                and h.get("kind") == "llm"
                and h.get("label") == self._state.model_key
                for h in holders
            )
```

改为

```python
            labels = {self._state.model_key, self._swapping_from} - {None}
            still_held = any(
                isinstance(h, dict)
                and h.get("kind") == "llm"
                and h.get("label") in labels
                for h in holders
            )
```

- [ ] **Step 5: 运行，确认通过**

Run: `python3 -m pytest tests/llm tests/test_arbiter_retarget.py tests/test_llm_agent_signals.py tests/test_llm_budget_wiring.py tests/agent_cli/test_chat_cli.py -q`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add desk/llm/service.py tests/llm/llm_fakes.py tests/llm/test_llm_switch_evict.py tests/agent_cli/test_chat_cli.py
git commit -m "fix(llm): switching chat models retargets the arbiter lease so chat is not refused as evicted

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `ask` 不在原地打转（缺陷模式 P2）

**Files:**
- Modify: `desk/agent_cli/chat.py`（`run_ask`，115 行起）
- Test: `tests/agent_cli/test_chat_retry.py`（新建）

**Interfaces:**
- Produces: `chat.STUCK_LIMIT = 3`。`run_ask` 的签名不变。

- [ ] **Step 1: 写失败的测试**

`tests/agent_cli/test_chat_retry.py`：

```python
"""模型已加载、要的就是它，对话却一直被拒：重试改变不了什么，不能等到超时（P2）。"""
import io

import pytest

from desk.agent_cli.chat import run_ask
from desk.agent_cli.client import HttpError
from desk.agent_cli.errors import CliError, EXIT_ERROR
from desk.agent_cli.waiter import Waiter


class Desk:
    def __init__(self, refusals):
        self.refusals = refusals
        self.chats = 0

    def get(self, path, query=None):
        if path == "/api/llm/status":
            return {"state": {"status": "loaded", "model_key": "glm"}, "active_chats": 0, "ui_chat_recent": False}
        if path == "/api/media/job":
            return {"status": "idle"}
        if path == "/api/agent/precheck":
            return {"ok": True, "release": []}
        if path == "/api/resources/catalog":
            return [{"key": "glm", "group": "chat"}]
        raise AssertionError(path)

    def post(self, path, body=None, timeout=None):
        assert path == "/api/llm/chat"
        self.chats += 1
        if self.chats <= self.refusals:
            raise HttpError(409, "evicted", "模型已被台面收回", {})
        return {"content": "好", "model": "glm"}


def _waiter():
    now = [0.0]
    return Waiter(600, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), err=io.StringIO())


def _ask(desk):
    return run_ask(desk, question="hi", model="glm", system=None, files=[], stdin_text="",
                   max_tokens=None, waiter=_waiter())


def test_three_refusals_of_a_loaded_model_end_with_the_desks_reason():
    desk = Desk(refusals=99)
    with pytest.raises(CliError) as exc:
        _ask(desk)
    assert exc.value.exit_code == EXIT_ERROR
    assert "模型已被台面收回" in exc.value.message
    assert desk.chats == 3


def test_a_single_refusal_is_still_retried():
    desk = Desk(refusals=1)
    assert _ask(desk)["content"] == "好"
    assert desk.chats == 2
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/agent_cli/test_chat_retry.py -q`
Expected: 第一条 FAIL。抛出的是退出码 3 的超时，不是退出码 1；`chats` 远大于 3。

- [ ] **Step 3: 实现**

在 `desk/agent_cli/chat.py` 的 `AGENT = {...}` 下面加：

```python
# 模型已加载、要的就是它，对话却连续被拒这么多次：说明台面那边卡住了，重试改变不了什么（P2）。
STUCK_LIMIT = 3
```

把 `run_ask` 的循环体改成下面这样，只动计数相关的几行：

```python
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
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/agent_cli -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/chat.py tests/agent_cli/test_chat_retry.py
git commit -m "fix(agent): ask stops after three refusals of an already-loaded model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 心跳线程，每 15s 一行（G4）

**Files:**
- Modify: `desk/agent_cli/waiter.py`（整份替换）
- Modify: `desk/agent_cli/cli.py`（93 行 `result = _dispatch(...)`）
- Modify: `desk/agent_cli/chat.py`（`run_ask` 里对话请求之前）
- Modify: `tests/agent_cli/test_waiter.py`
- Modify: `docs/superpowers/specs/2026-10-16-agent-skill-design.md`（A-23）

**Interfaces:**
- Produces:
  - `Waiter.note(reason: str) -> None`；
  - `Waiter.heartbeat()`：上下文管理器，进入时起线程，退出时停下并 join；
  - `waiter.DEFAULT_REASON = "等待台面响应"`；
  - `pause()` 不再打印，只记原因、退避、判超时。

- [ ] **Step 1: 写失败的测试**

在 `tests/agent_cli/test_waiter.py` 顶部加 `import time`。把 `test_reports_every_15_seconds_with_reason_and_elapsed` 整条替换为下面三条：

```python
def test_pause_only_records_the_reason_and_never_prints():
    t, err = T(), io.StringIO()
    w = Waiter(1000, clock=t.clock, sleep=t.sleep, err=err)
    for _ in range(8):
        w.pause("图片任务进行中")
    assert err.getvalue() == ""


def test_heartbeat_prints_every_interval_with_the_latest_reason():
    err = io.StringIO()
    w = Waiter(100, err=err, report_every=0.05)
    with w.heartbeat():
        w.note("图片任务进行中")
        time.sleep(0.18)
    lines = err.getvalue().splitlines()
    assert len(lines) >= 2
    assert all(line.startswith("等待中：图片任务进行中（已等 ") for line in lines)


def test_heartbeat_runs_while_the_main_thread_is_blocked_and_stops_on_exit():
    err = io.StringIO()
    w = Waiter(100, err=err, report_every=0.05)
    with w.heartbeat():
        time.sleep(0.12)   # 主线程卡在一次阻塞调用里，从不调 pause（q14 的情形）
    count = len(err.getvalue().splitlines())
    assert count >= 1 and err.getvalue().startswith("等待中：等待台面响应（已等 ")
    time.sleep(0.12)
    assert len(err.getvalue().splitlines()) == count
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/agent_cli/test_waiter.py -q`
Expected: FAIL
- `pause` 打出了行；
- `Waiter` 没有 `heartbeat`、`note`。

- [ ] **Step 3: 实现**

`desk/agent_cli/waiter.py` 整份替换为：

```python
"""Backoff between polls, a heartbeat line every 15 s on stderr, and the overall deadline (A-23/A-25)."""
from __future__ import annotations

import contextlib
import sys
import threading
import time

from .errors import CliError, EXIT_TIMEOUT

DEFAULT_REASON = "等待台面响应"


class Waiter:
    def __init__(self, timeout_s: float, *, clock=time.monotonic, sleep=time.sleep, err=sys.stderr,
                 initial: float = 2.0, factor: float = 1.5, cap: float = 5.0, report_every: float = 15.0):
        self._clock, self._sleep, self._err = clock, sleep, err
        self._initial, self._factor, self._cap, self._report_every = initial, factor, cap, report_every
        self._start = clock()
        self._deadline = self._start + timeout_s
        self._interval = initial
        self._reason = DEFAULT_REASON

    def elapsed(self) -> float:
        return self._clock() - self._start

    def remaining(self) -> float:
        return max(0.0, self._deadline - self._clock())

    def expired(self) -> bool:
        return self._clock() >= self._deadline

    def reset(self) -> None:
        self._interval = self._initial

    def note(self, reason: str) -> None:
        """记下此刻在等什么，心跳行会用它。"""
        self._reason = reason

    def pause(self, reason: str) -> None:
        self._reason = reason
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")
        self._sleep(min(self._interval, remaining))
        self._interval = min(self._interval * self._factor, self._cap)
        if self._clock() >= self._deadline:
            raise CliError(EXIT_TIMEOUT, "timeout", f"等待超时（{reason}）")

    @contextlib.contextmanager
    def heartbeat(self):
        """命令运行期间每 15s 在 stderr 打一行，不管主线程卡在哪（排队、HTTP 请求、等模型回答）。

        q14：主线程卡在一次慢请求里时，在轮询里打点的写法整整 60s 一行都没有。
        退出时先停线程再返回，保证报错时 stderr 最后一行是原因，不是心跳。
        """
        stop = threading.Event()

        def beat() -> None:
            while not stop.wait(self._report_every):
                print(f"等待中：{self._reason}（已等 {int(self.elapsed())}s）", file=self._err, flush=True)

        thread = threading.Thread(target=beat, name="lmdesk-heartbeat", daemon=True)
        thread.start()
        try:
            yield self
        finally:
            stop.set()
            thread.join()
```

`desk/agent_cli/cli.py` 第 93 行：

```python
        result = _dispatch(args, client, waiter, stdin, err)
```

改为

```python
        with waiter.heartbeat():
            result = _dispatch(args, client, waiter, stdin, err)
```

`desk/agent_cli/chat.py` 的 `run_ask` 里，在 `try:` 和 `result = client.post("/api/llm/chat", …)` 之间加一行：

```python
            waiter.note("模型正在回答")
```

spec `docs/superpowers/specs/2026-10-16-agent-skill-design.md` 的 A-23，把

```
- [A-23] 轮询间隔从 2s 开始，每次 ×1.5，最长 5s。等待期间，stderr 每 15s 打一行，例如「等待中：图片任务进行中（已等 45s）」。
```

改为

```
- [A-23] 轮询间隔从 2s 开始，每次 ×1.5，最长 5s。命令运行期间，stderr 每 15s 打一行，例如「等待中：图片任务进行中（已等 45s）」。从命令开始计时，由独立线程打印：卡在排队、卡在一次 HTTP 请求里、等模型回答，都照样打。
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/agent_cli -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/waiter.py desk/agent_cli/cli.py desk/agent_cli/chat.py tests/agent_cli/test_waiter.py docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "fix(agent): progress line every 15s from a heartbeat thread, even while a request blocks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: stdin 不挂死，非 UTF-8 输入报参数错误（G8、G2）

**Files:**
- Create: `desk/agent_cli/stdin_reader.py`
- Modify: `desk/agent_cli/cli.py`（删掉 `_read_stdin`，108–114 行；`_dispatch` 里 ask 的调用）
- Modify: `desk/agent_cli/chat.py`（`_message`，67 行起）
- Modify: `tests/agent_cli/cli_helpers.py`（`popen_cli` 加 `stdin` 参数）
- Test: `tests/agent_cli/test_stdin_reader.py`（新建）、`tests/agent_cli/test_chat_cli.py`
- Modify: spec A-12

**Interfaces:**
- Produces: `stdin_reader.read_piped(stdin, *, deadline_s: float, err, idle_s: float = IDLE_S, clock=time.monotonic) -> str`，其中 `IDLE_S = 5.0`。
  - 空闲窗口内没有数据：返回 `""`，并在 stderr 打一行含「没有数据」的提示。
  - 有数据但超过 `deadline_s` 还没结束：抛 `CliError(EXIT_TIMEOUT, "stdin_timeout", …)`。
  - 不是 UTF-8：抛 `CliError(EXIT_USAGE, "stdin_not_utf8", …)`。
- Produces: `popen_cli(harness, *args, stdin=subprocess.DEVNULL)`

- [ ] **Step 1: 写失败的测试**

`tests/agent_cli/test_stdin_reader.py`：

```python
"""ask 读管道输入（A-12，G8）：没人写的管道不能把命令挂死。"""
import io
import os
import threading
import time

import pytest

from desk.agent_cli.errors import CliError, EXIT_TIMEOUT, EXIT_USAGE
from desk.agent_cli.stdin_reader import read_piped


def _pipe():
    r, w = os.pipe()
    return os.fdopen(r, "r"), w


def test_open_pipe_without_data_is_ignored_after_the_idle_window():
    reader, w = _pipe()
    err = io.StringIO()
    start = time.monotonic()
    try:
        assert read_piped(reader, deadline_s=60, idle_s=0.2, err=err) == ""
    finally:
        os.close(w)
        reader.close()
    assert time.monotonic() - start < 2
    assert "没有数据" in err.getvalue()


def test_closed_pipe_with_data_is_read_whole():
    reader, w = _pipe()
    os.write(w, "管道内容".encode())
    os.close(w)
    assert read_piped(reader, deadline_s=60, idle_s=0.2, err=io.StringIO()) == "管道内容"
    reader.close()


def test_slow_producer_that_starts_inside_the_window_is_read():
    reader, w = _pipe()

    def produce():
        time.sleep(0.1); os.write(w, b"late "); time.sleep(0.1); os.write(w, b"data"); os.close(w)

    threading.Thread(target=produce).start()
    assert read_piped(reader, deadline_s=60, idle_s=1.0, err=io.StringIO()) == "late data"
    reader.close()


def test_data_that_never_ends_times_out_with_exit_3():
    reader, w = _pipe()
    os.write(w, b"partial")
    with pytest.raises(CliError) as exc:
        read_piped(reader, deadline_s=0.3, idle_s=0.2, err=io.StringIO())
    assert exc.value.exit_code == EXIT_TIMEOUT
    os.close(w)
    reader.close()


def test_non_utf8_input_is_exit_2():
    reader, w = _pipe()
    os.write(w, "中文".encode("gbk"))
    os.close(w)
    with pytest.raises(CliError) as exc:
        read_piped(reader, deadline_s=60, idle_s=0.2, err=io.StringIO())
    assert exc.value.exit_code == EXIT_USAGE
    reader.close()


def test_dev_null_and_in_memory_text():
    with open(os.devnull) as devnull:
        assert read_piped(devnull, deadline_s=60, idle_s=0.2, err=io.StringIO()) == ""
    assert read_piped(io.StringIO("内存里的"), deadline_s=60, idle_s=0.2, err=io.StringIO()) == "内存里的"
    assert read_piped(None, deadline_s=60, err=io.StringIO()) == ""
```

`tests/agent_cli/cli_helpers.py`：把 `popen_cli` 改成可以指定 stdin。

```python
def popen_cli(harness, *args, stdin=subprocess.DEVNULL):
    env = {**os.environ, "LMD_SHELL_PORT": harness_port(harness), "PYTHONPATH": str(ROOT),
           "LMDESK_FAKE_VERSION": "e2e"}  # the fake bundle reports version "e2e"
    return subprocess.Popen([sys.executable, "-m", "desk.agent_cli", *args], stdin=stdin,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=str(ROOT))
```

`tests/agent_cli/test_chat_cli.py`：顶部加 `import subprocess`；import 行改成 `from tests.agent_cli.cli_helpers import popen_cli, run_cli`；文件末尾追加两条：

```python
def test_non_utf8_file_is_exit_2_without_a_traceback(tmp_path):
    gbk = tmp_path / "gbk.txt"
    gbk.write_bytes("中文内容".encode("gbk"))
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "x", "--file", str(gbk))
        assert r.returncode == 2
        assert "Traceback" not in r.stderr and "UTF-8" in r.stderr


def test_ask_with_an_open_silent_stdin_pipe_answers_instead_of_hanging(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        p = popen_cli(h, "ask", "你好", "--model", CHAT, stdin=subprocess.PIPE)   # 不写、不关
        try:
            assert p.wait(timeout=60) == 0
            assert p.stdout.read().strip() == "你好，世界"
            assert "没有数据" in p.stderr.read()
        finally:
            p.stdin.close()
            if p.poll() is None:
                p.kill()
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/agent_cli/test_stdin_reader.py tests/agent_cli/test_chat_cli.py -q`
Expected: FAIL
- `ModuleNotFoundError: desk.agent_cli.stdin_reader`；
- GBK 那条退出码是 1，stderr 带 Traceback；
- 管道那条 `subprocess.TimeoutExpired`。

- [ ] **Step 3: 实现**

`desk/agent_cli/stdin_reader.py`：

```python
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
```

`desk/agent_cli/cli.py`：
- 删除整个 `_read_stdin` 函数；
- 顶部 import 区加 `from .stdin_reader import read_piped`；
- `_dispatch` 里 ask 那一行的 `stdin_text=_read_stdin(stdin)` 改为 `stdin_text=read_piped(stdin, deadline_s=waiter.remaining(), err=err)`。

`desk/agent_cli/chat.py` 的 `_message` 里，把

```python
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(EXIT_USAGE, "file_unreadable", f"读不了文件 {name}：{exc.strerror}") from None
```

改为

```python
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(EXIT_USAGE, "file_unreadable", f"读不了文件 {name}：{exc.strerror}") from None
        except UnicodeDecodeError:
            raise CliError(EXIT_USAGE, "file_not_utf8", f"文件 {name} 不是 UTF-8 文本，请先转成 UTF-8") from None
```

spec A-12，把

```
- [A-12] `ask` 的 stdin 不是终端时，读入 stdin 内容，接在问题后面。`--file` 可以重复，每个文件以「文件名 + 内容」的块拼进用户消息。
```

改为

```
- [A-12] `ask` 的 stdin 不是终端时，读入 stdin 内容，接在问题后面。`--file` 可以重复，每个文件以「文件名 + 内容」的块拼进用户消息。
  - stdin 在 5 秒内既没有数据也没有结束：按没有输入处理，stderr 提示一行（agent 执行器有时接一个不关闭的管道）。开始有数据后读到结束为止，受剩余 `--timeout` 约束，超时退出码 3。
  - stdin 或 `--file` 不是 UTF-8：退出码 2，提示先转成 UTF-8。
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/agent_cli -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/stdin_reader.py desk/agent_cli/cli.py desk/agent_cli/chat.py tests/agent_cli/cli_helpers.py tests/agent_cli/test_stdin_reader.py tests/agent_cli/test_chat_cli.py docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "fix(agent): ask no longer hangs on an open silent stdin; non-UTF-8 input is a usage error

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Ctrl-C 之后如实报告（G5）

**Files:**
- Modify: `desk/agent_cli/media.py`（新增 `_interrupted`；替换 `_run_job` 里 355–362 行的 `except Interrupted` 块）
- Test: `tests/agent_cli/test_video_cli.py`（末尾追加）
- Modify: spec A-25

**Interfaces:**
- Produces: `media._interrupted(client, kind, session_id, attempt_id, job_id, signum, hint) -> CliError`。退出码一律 3，最后一行措辞固定。Task 9 的 SKILL.md 依赖这些关键词：

| 情况 | 最后一行 | 续等提示 |
|---|---|---|
| SIGTERM | 已中断，生成仍在台面继续 | 有 |
| SIGINT，取消成功 | 已中断并取消这次生成 | 无 |
| SIGINT，作业已结束且尝试 done | 已中断。这次生成在中断前已经完成，没有取消 | 有 |
| SIGINT，作业已结束且尝试 failed / cancelled | 已中断。这次生成在中断前已经结束，没有成片 | 无 |
| SIGINT，连不上台面，或者读不到尝试状态 | 已中断，生成可能仍在台面继续 | 有 |

- [ ] **Step 1: 写失败的测试**

`tests/agent_cli/test_video_cli.py` 末尾追加：

```python
def _interrupt_desk(cancel, attempts):
    class Desk:
        posts = []

        def post(self, path, body=None, **_):
            Desk.posts.append(path)
            if isinstance(cancel, Exception):
                raise cancel
            return cancel

        def get(self, path, query=None):
            if isinstance(attempts, Exception):
                raise attempts
            return {"attempts": attempts}

    Desk.posts = []
    return Desk()


def _interrupt(desk, signum):
    from desk.agent_cli.media import _interrupted
    return _interrupted(desk, "video", "s1", "a1", 7, signum, "已提交：…（中断后可用 lmdesk video wait s1 a1 继续等待）")


def test_sigint_cancel_succeeds():
    error = _interrupt(_interrupt_desk({"status": "cancelled"}, []), signal.SIGINT)
    assert error.exit_code == 3 and error.message == "已中断并取消这次生成" and error.hint is None


def test_sigint_after_the_job_already_finished_says_so_and_keeps_the_wait_hint():
    from desk.agent_cli.client import HttpError
    desk = _interrupt_desk(HttpError(409, "job_not_running", "作业 7 不在运行", {}), [{"id": "a1", "status": "done"}])
    error = _interrupt(desk, signal.SIGINT)
    assert error.exit_code == 3 and "中断前已经完成" in error.message and "取消这次" not in error.message
    assert "lmdesk video wait s1 a1" in error.hint


def test_sigint_after_the_job_already_failed_has_no_result():
    from desk.agent_cli.client import HttpError
    desk = _interrupt_desk(HttpError(409, "job_not_running", "x", {}), [{"id": "a1", "status": "failed"}])
    error = _interrupt(desk, signal.SIGINT)
    assert "已经结束" in error.message and error.hint is None


def test_sigint_with_the_desk_gone_never_claims_cancelled():
    from desk.agent_cli.client import Unreachable
    error = _interrupt(_interrupt_desk(Unreachable("refused", "x"), Unreachable("refused", "x")), signal.SIGINT)
    assert "取消" not in error.message and "仍在台面继续" in error.message and error.hint


def test_sigterm_never_cancels():
    desk = _interrupt_desk({"status": "cancelled"}, [])
    error = _interrupt(desk, signal.SIGTERM)
    assert error.message == "已中断，生成仍在台面继续" and error.hint and desk.posts == []
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/agent_cli/test_video_cli.py -q -k "sigint_ or sigterm_never"`
Expected: FAIL，`ImportError: cannot import name '_interrupted'`

- [ ] **Step 3: 实现**

在 `desk/agent_cli/media.py` 的 `_run_job` 定义之前加：

```python
def _interrupted(client: DeskClient, kind: str, session_id: str, attempt_id: str, job_id,
                 signum: int, hint: str) -> CliError:
    """收到信号之后如实说结果（A-25）。

    SIGTERM 不取消。SIGINT 去取消，但作业可能在这之前已经做完了（合成常常不到一秒，G5），
    这时取消会得到 job_not_running，要看会话里的记录再说话，不能一律说「已取消」。
    措辞里的「仍在台面继续」「已经完成」「取消」「已经结束」是 SKILL.md 退出码 3 的判断依据。
    """
    if signum != signal.SIGINT:
        return CliError(EXIT_TIMEOUT, "interrupted", "已中断，生成仍在台面继续", hint=hint)
    try:
        client.post("/api/media/cancel", {"job_id": job_id, **AGENT})
        return CliError(EXIT_TIMEOUT, "interrupted", "已中断并取消这次生成")
    except Unreachable:
        return CliError(EXIT_TIMEOUT, "interrupted", "已中断，生成可能仍在台面继续", hint=hint)
    except HttpError:
        pass   # job_not_running：作业在中断前就结束了
    try:
        attempts = _session(client, kind, session_id).get("attempts") or []
    except (HttpError, Unreachable):
        attempts = []
    status = next((a.get("status") for a in attempts if a.get("id") == attempt_id), None)
    if status == "done":
        return CliError(EXIT_TIMEOUT, "interrupted_after_done", "已中断。这次生成在中断前已经完成，没有取消", hint=hint)
    if status in ("failed", "cancelled"):
        return CliError(EXIT_TIMEOUT, "interrupted", "已中断。这次生成在中断前已经结束，没有成片")
    return CliError(EXIT_TIMEOUT, "interrupted", "已中断，生成可能仍在台面继续", hint=hint)
```

把 `_run_job` 里的

```python
    except Interrupted as exc:
        if exc.signum == signal.SIGINT:
            try:
                client.post("/api/media/cancel", {"job_id": job_id, **AGENT})
            except (HttpError, Unreachable):
                pass
            raise CliError(EXIT_TIMEOUT, "interrupted", "已中断并取消这次生成") from None
        raise CliError(EXIT_TIMEOUT, "interrupted", "已中断，生成仍在台面继续", hint=hint) from None
```

改为

```python
    except Interrupted as exc:
        raise _interrupted(client, kind, session_id, attempt_id, job_id, exc.signum, hint) from None
```

spec A-25 的 SIGINT 行，把

```
    - **SIGINT（用户在终端按 Ctrl-C）：取消任务**。调用 `POST /api/media/cancel`，带上自己的 `job_id`（A-42），然后以退出码 3 退出。
```

改为

```
    - **SIGINT（用户在终端按 Ctrl-C）：取消任务**。调用 `POST /api/media/cancel`，带上自己的 `job_id`（A-42），然后以退出码 3 退出。
      - 取消返回 `job_not_running`（作业在中断前已结束）时，按会话里这次尝试的状态说明：已完成则写「已中断。这次生成在中断前已经完成，没有取消」并保留续等提示；失败或已取消则写「已中断。这次生成在中断前已经结束，没有成片」。
      - 连不上台面时不说「已取消」，写「已中断，生成可能仍在台面继续」并保留续等提示。
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/agent_cli/test_video_cli.py tests/agent_cli/test_image_cli.py tests/agent_cli/test_music_cli.py -q`
Expected: PASS（包括原有的 `test_sigint_after_submit_cancels_only_own_job`）

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/media.py tests/agent_cli/test_video_cli.py docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "fix(agent): Ctrl-C after the job already finished no longer claims it was cancelled

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 后台拉起不弹主窗口（G12；G11 报错说明原因）

**Files:**
- Modify: `desk/agent_cli/discovery.py`（61–62 行）
- Modify: `macos/ShellStatus.swift`（文件末尾追加）
- Modify: `macos/AppDelegate.swift`（47 行）
- Modify: `macos/harness/ShellHarness.swift`（14 行附近加一个 case）
- Test: `tests/agent_cli/test_discovery.py`、`tests/test_shell_status.py`
- Modify: spec A-31

**Interfaces:**
- Produces:
  - Python `discovery.BACKGROUND_ARG = "--lmdesk-background"`；
  - Swift `let backgroundLaunchArgument = "--lmdesk-background"` 和 `func showsWindowAtLaunch(arguments: [String]) -> Bool`；
  - harness 命令 `window-at-launch [args…]`，打印 `show` 或 `hidden`。

- [ ] **Step 1: 写失败的测试**

`tests/agent_cli/test_discovery.py`：

把 `test_refused_in_bundle_launches_hidden_then_connects` 的断言改为：

```python
    assert calls == [["open", "-gj", str(tmp_path / "LocalModelDesk.app"), "--args", "--lmdesk-background"]]
```

在 `test_refused_outside_bundle_does_not_launch` 的 `assert exc.value.exit_code == EXIT_ERROR` 后加：

```python
    assert "不在 app 包里" in exc.value.message
```

文件末尾追加：

```python
def test_background_argument_matches_the_swift_shell():
    from pathlib import Path
    from desk.agent_cli.discovery import BACKGROUND_ARG
    swift = (Path(__file__).resolve().parents[2] / "macos" / "ShellStatus.swift").read_text(encoding="utf-8")
    assert f'"{BACKGROUND_ARG}"' in swift
```

`tests/test_shell_status.py` 末尾追加（文件已 import `subprocess` 和 `harness_path`）：

```python
def test_lmdesk_background_launch_keeps_the_main_window_hidden():
    plain = subprocess.run([harness_path(), "window-at-launch"], capture_output=True, text=True)
    assert plain.stdout.strip() == "show"
    hidden = subprocess.run([harness_path(), "window-at-launch", "--lmdesk-background"],
                            capture_output=True, text=True)
    assert hidden.stdout.strip() == "hidden"
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/agent_cli/test_discovery.py tests/test_shell_status.py -q`
Expected: FAIL
- `calls` 少了 `--args`；
- 提示里没有原因；
- `ImportError: BACKGROUND_ARG`；
- harness 对 `window-at-launch` 不认识（空输出或 exit 64）。

- [ ] **Step 3: 实现**

`desk/agent_cli/discovery.py`：在 `SANDBOX_MESSAGE` 下面加

```python
# 与 macos/ShellStatus.swift 的 backgroundLaunchArgument 一致：带它启动的台面不显示主窗口（A-31）。
BACKGROUND_ARG = "--lmdesk-background"
```

把

```python
    if app is None:
        raise CliError(EXIT_ERROR, "desk_not_running", "台面没有运行。请先打开 LocalModelDesk。")
    rc = launcher(["open", "-gj", str(app)])
```

改为

```python
    if app is None:
        raise CliError(EXIT_ERROR, "desk_not_running",
                       "台面没有运行。请先打开 LocalModelDesk。（这个 lmdesk 不在 app 包里，不会自动启动台面）")
    rc = launcher(["open", "-gj", str(app), "--args", BACKGROUND_ARG])
```

`macos/ShellStatus.swift` 末尾追加：

```swift
/// lmdesk 在后台拉起台面时带上的参数（A-31）：这次启动不显示主窗口。
let backgroundLaunchArgument = "--lmdesk-background"

/// 启动时要不要显示主窗口。用户自己打开台面时显示；lmdesk 用 `open -gj … --args --lmdesk-background`
/// 拉起时不显示。之后点 Dock 图标，照常由 applicationShouldHandleReopen 打开窗口。
func showsWindowAtLaunch(arguments: [String]) -> Bool {
  !arguments.contains(backgroundLaunchArgument)
}
```

`macos/harness/ShellHarness.swift` 在 `case "agent-skill-note": …` 下一行加：

```swift
    case "window-at-launch": print(showsWindowAtLaunch(arguments: Array(args.dropFirst())) ? "show" : "hidden")
```

`macos/AppDelegate.swift` 第 47 行：

```swift
    windowController.showWindow()
```

改为

```swift
    if showsWindowAtLaunch(arguments: CommandLine.arguments) { windowController.showWindow() }
```

spec A-31 的第一条子项，把

```
  - 如果命令行位于某个 app 包内，就执行 `open -gj <该 app>`，然后每 1s 探测一次 `/api/state`，最多 60s。超时以退出码 1 退出，提示「台面未能启动」。
  - 从源码运行（不在 app 包内）时，不自动启动，直接以退出码 1 提示。
```

改为

```
  - 如果命令行位于某个 app 包内，就执行 `open -gj <该 app> --args --lmdesk-background`，然后每 1s 探测一次 `/api/state`，最多 60s。超时以退出码 1 退出，提示「台面未能启动」。
    - app 带 `--lmdesk-background` 启动时不显示主窗口；之后用户点 Dock 图标，照常打开窗口。
  - 从源码运行（不在 app 包内）时，不自动启动，直接以退出码 1 提示，并说明「这个 lmdesk 不在 app 包里，不会自动启动台面」。
```

- [ ] **Step 4: 运行，确认通过，并确认整个外壳能编译**

Run: `python3 -m pytest tests/agent_cli/test_discovery.py tests/test_shell_status.py -q && scripts/build-shell-app.sh "$(mktemp -d)" >/dev/null && echo shell-ok`
Expected: PASS，最后打印 `shell-ok`

- [ ] **Step 5: 提交**

```bash
git add desk/agent_cli/discovery.py macos/ShellStatus.swift macos/AppDelegate.swift macos/harness/ShellHarness.swift tests/agent_cli/test_discovery.py tests/test_shell_status.py docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "fix(shell): a desk launched by lmdesk starts without showing its main window

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 设置页：命令行链接失效时能点「应用」；说明文字补上视频、音乐（G9、G3）

**Files:**
- Modify: `desk/static/js/pure/agent_skill.js`（`applyEnabled`）
- Modify: `desk/static/js/panes/agent_skill.js`
- Modify: `desk/static/index.html`（148 行的说明文字）
- Test: `tests/js/agent_skill.test.js`、`tests/e2e/test_agent_skill_settings.py`
- Modify: spec A-61、A-64、A-67

**Interfaces:**
- Produces: `applyEnabled(rows, checked, cli = null) -> boolean`。不传 `cli` 时，行为和原来一样。

- [ ] **Step 1: 写失败的测试**

`tests/js/agent_skill.test.js` 末尾追加：

```js
test("命令行链接失效或缺失时，应用按钮可点（G9）", () => {
  const rows = [row("claude", "installed"), row("pi", "absent")];
  const checked = new Set(["claude"]);
  assert.equal(applyEnabled(rows, checked, { state: "stale" }), true);
  assert.equal(applyEnabled(rows, checked, { state: "absent" }), true);
  assert.equal(applyEnabled(rows, checked, { state: "installed" }), false);
  assert.equal(applyEnabled(rows, checked, { state: "occupied" }), false, "被占用的位置点了也修不好");
});

test("一个 agent 都不装、命令行链接还在：应用可点，点了卸掉它", () => {
  const rows = [row("claude", "absent")];
  assert.equal(applyEnabled(rows, new Set(), { state: "installed" }), true);
  assert.equal(applyEnabled(rows, new Set(), { state: "stale" }), true);
  assert.equal(applyEnabled(rows, new Set(), { state: "absent" }), false);
});
```

`tests/e2e/test_agent_skill_settings.py`：顶部加 `import os`，末尾追加：

```python
def test_stale_cli_link_enables_apply_and_apply_fixes_it(page, tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with launch_test_harness(tmp_path) as h:
        section = _open(page, h)
        expect(section.locator("p.hint").first).to_contain_text("视频、音乐")
        section.locator(".agent-skill-row[data-key=claude] input").check()
        apply = section.locator("[data-agent-skill-apply]")
        apply.click()
        expect(section.locator(".agent-skill-row[data-key=claude] [data-agent-skill-status]")).to_have_text("已安装")
        cli = home / ".local/bin/lmdesk"
        good = os.readlink(cli)
        cli.unlink()
        cli.symlink_to("/gone/Old.app/Contents/Resources/bin/lmdesk")

        section.locator("[data-agent-skill-check]").click()   # 检查时顺手刷新各行

        expect(section.locator("[data-agent-skill-cli]")).to_contain_text("已失效，点应用更新")
        expect(apply).to_be_enabled()
        apply.click()
        expect(section.locator("[data-agent-skill-cli]")).to_contain_text("已安装")
        assert os.readlink(cli) == good
```

- [ ] **Step 2: 运行，确认失败**

Run: `node --test tests/js/agent_skill.test.js; python3 -m pytest tests/e2e/test_agent_skill_settings.py -q -k stale_cli`
Expected: 两条 node 测试 FAIL（cli 失效时返回 false）；e2e FAIL，说明文字里没有「视频、音乐」。

- [ ] **Step 3: 实现**

`desk/static/js/pure/agent_skill.js`，把 `applyEnabled` 替换为：

```js
// cli 是命令行链接那一行（payload.cli）。它跟着 agent 行走：应用后只要有一行装上，它就该在；
// 一行都不装，它就该被卸掉（installer.apply）。它失效或缺失时也要能点应用，点了才会修好（A-64，G9）。
export function applyEnabled(rows, checked, cli = null) {
  const rowsChange = rows.some((r) => {
    const want = checked.has(r.key);
    // 勾上被占用的行也算变化：点了应用，这一行才会报出装不上的原因（A-54/A-64）。
    if (want) return r.state !== "installed";
    return r.state === "installed" || r.state === "stale";
  });
  if (rowsChange || !cli) return rowsChange;
  if (rows.some((r) => checked.has(r.key))) return cli.state === "stale" || cli.state === "absent";
  return cli.state === "installed" || cli.state === "stale";
}
```

`desk/static/js/panes/agent_skill.js`：

① `let rows = [];` 下面加一行 `let cli = {};`；

② `refreshApply` 改为：

```js
  const refreshApply = () => { els.apply.disabled = !applyEnabled(rows, checked, cli); };
```

③ `render` 里把 `const cli = payload.cli ?? {};` 改为 `cli = payload.cli ?? {};`；

④ 「检查」的点击处理改为：

```js
  els.check.addEventListener("click", async () => {
    els.checkResult.textContent = "检查中…";
    try {
      const result = await api.agentSkillCheck();
      els.checkResult.textContent = result.ok ? "lmdesk 能连上台面 ✓" : result.message;
      render(await api.agentSkillStatus());   // 链接可能在台面外被改过：检查时顺手刷新各行，保留当前勾选（G9）
    } catch (error) { els.checkResult.textContent = error.message; }
  });
```

`desk/static/index.html` 148 行，把 `让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）。` 改为 `让选中的 agent 通过 lmdesk 命令使用本机模型（对话、图片、视频、音乐，以及它们的会话）。`

spec 同步：
- A-61 的说明文字改成同一句：「让选中的 agent 通过 lmdesk 命令使用本机模型（对话、图片、视频、音乐，以及它们的会话）」。
- A-64 第一条子项后加一条：

  ```
  - 各行都没有变化时，再看命令行链接：有勾选的行，而链接是 `stale` 或 `absent`；或者一行都不勾，而链接是 `installed` 或 `stale`：可以点。
  ```

- A-67 第一条子项末尾加：「检查完同时刷新各行和命令行链接的状态，保留当前勾选。」

- [ ] **Step 4: 运行，确认通过**

Run: `node --test tests/js && python3 -m pytest tests/e2e/test_agent_skill_settings.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add desk/static/js/pure/agent_skill.js desk/static/js/panes/agent_skill.js desk/static/index.html tests/js/agent_skill.test.js tests/e2e/test_agent_skill_settings.py docs/superpowers/specs/2026-10-16-agent-skill-design.md
git commit -m "fix(settings): Apply is enabled when the lmdesk link is stale or missing; copy mentions video and music

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: SKILL.md：退出码 3、退出码 6、join 什么时候用（G1、G10、J3）

**Files:**
- Modify: `desk/agent_skill/bundled/local-model-desk/SKILL.md`（61、83、88–90 行）
- Test: `tests/test_agent_skill_md.py`

**Interfaces:**
- Consumes: Task 6 的固定措辞（「仍在台面继续」「已经完成」「取消」「已经结束」），以及 Task 4 原有的超时文案：提交后超时写「…，生成仍在台面继续」。

- [ ] **Step 1: 写失败的测试**

`tests/test_agent_skill_md.py` 末尾追加：

```python
def test_exit_3_sandbox_and_join_guidance():
    """G1：退出码 3 按 stderr 最后一行分情况；G10：放行方法原样转述、不冒充；J3：续写不必再 join。"""
    _, body = _frontmatter(SKILL.read_text(encoding="utf-8"))
    for needle in ("stderr 最后一行", "仍在台面继续", "已经完成", "已经结束", "原样", "冒充本地模型",
                   "不需要再 join", "合成记录", "network_access = true"):
        assert needle in body, needle
```

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -m pytest tests/test_agent_skill_md.py -q`
Expected: FAIL，提示缺 `stderr 最后一行`

- [ ] **Step 3: 改 SKILL.md**

第 61 行

```
- 把几段合成成片：`lmdesk video join "产品演示" <尝试id> <尝试id> [...]`，至少两段。续写后 `wait` 输出的是到当前这段为止的完整成片。
```

替换为

```
- 把几段做成一个成片：
  - 续写的几段：`wait` 拿到的已经是从第一段到这一段的完整成片，不需要再 join 就能用。
  - 用户说要「合成」「拼接」，或者几段是各自单独生成的：用 `lmdesk video join "产品演示" <尝试id> <尝试id> [...]`，至少两段，台面会留下一条合成记录。续写的几段 join 出来，和续写成片的内容相同。
```

第 83 行

```
- 退出码 3：等待超时，台面一直在忙。告诉用户。如果是生图、视频或音乐，稍后可以用对应的 `wait` 命令（如 `lmdesk video wait`）取结果。
```

替换为

```
- 退出码 3：没等到结果。看 stderr 最后一行：
  - 含「仍在台面继续」或「已经完成」：用 stderr 前面那行 `lmdesk <image|video|music> wait <会话> <尝试id>` 取结果，不要重新 gen。
  - 含「取消」或「已经结束」：这次生成没有结果（通常是用户按了 Ctrl-C）。需要的话重新 gen。
  - 其他（`ask`，或者生成还没提交）：台面一直在忙，没排上队。告诉用户，稍后再试。
```

第 88–90 行（退出码 6 及其两条子项）替换为

```
- 退出码 6：被沙箱拦截，访问不了本机网络（127.0.0.1）。先请求提升权限；拿不到权限时，把下面对应的放行方法**原样**告诉用户，然后停下：
  - Codex：默认的 workspace-write 沙箱关闭了网络。在 `~/.codex/config.toml` 里加上 `[sandbox_workspace_write]` 和 `network_access = true`，或者用 `codex -s workspace-write -c sandbox_workspace_write.network_access=true` 启动。
  - Claude Code 开启了沙箱时：把 `127.0.0.1` 加进沙箱的网络白名单。
  - 不要改用别的办法（自己翻译、自己写代码画图、联网下载）冒充本地模型的结果：用户要的就是本地模型。
```

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -m pytest tests/test_agent_skill_md.py -q`
Expected: PASS（description 长度仍 ≤ 1024，原有关键词都还在）

- [ ] **Step 5: 提交**

```bash
git add desk/agent_skill/bundled/local-model-desk/SKILL.md tests/test_agent_skill_md.py
git commit -m "docs(skill): exit 3 by the last stderr line, relay sandbox fixes verbatim, when join is needed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 全量回归、构建 dist、在真实例上复核

**Files:** 不改代码。若这一步发现问题，退回对应任务修，并重新提交。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest -q && node --test tests/js`
Expected: 全部 PASS。有失败就停下，按失败所属的任务修，不要跳过。

- [ ] **Step 2: 构建 dist**

先退出正在运行的 dist 台面：

```bash
osascript -e "tell application \"$PWD/dist/LocalModelDesk.app\" to quit"
```

30 秒后 `lsof -nP -iTCP:8766 -sTCP:LISTEN` 仍有监听时，**停下来问用户**，不要 kill。

确认端口已空后：

```bash
scripts/build-app.sh --output dist
test -x dist/LocalModelDesk.app/Contents/Resources/bin/lmdesk && echo built
```

Expected: 打印 `built`。不要装到 `/Applications`。

- [ ] **Step 3: 后台拉起不弹窗（G12）**

台面此时没有运行。准备一个查窗口的脚本：

```bash
T=$(mktemp -d)
cat > "$T/windows.swift" <<'EOF'
import CoreGraphics
let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] ?? []
for w in info where (w[kCGWindowOwnerName as String] as? String) == "LocalModelDesk"
                   && (w[kCGWindowLayer as String] as? Int) == 0 {
  print("window", w[kCGWindowBounds as String] ?? "")
}
EOF
~/.local/bin/lmdesk status --json; echo "exit=$?"
sleep 3; xcrun swift "$T/windows.swift"
```

Expected:
- `exit=0`，输出状态 JSON；
- 查窗口脚本**没有输出**（没有可见主窗口）。

再模拟用户自己打开：

```bash
open dist/LocalModelDesk.app; sleep 2; xcrun swift "$T/windows.swift"
```

Expected: 打印一行 `window …`。

- [ ] **Step 4: 换模型后能对话（G6、G7）**

用 `~/.local/bin/lmdesk models` 挑两个本机都放得下的对话模型，记作 A、B（本机此前用的是 `superqwen` 和 `qwen27`）。

```bash
A=superqwen; B=qwen27
curl -s -X POST localhost:8766/api/llm/load -H 'Content-Type: application/json' -d "{\"key\":\"$A\"}"
until curl -s localhost:8766/api/llm/status | grep -q '"status": *"loaded"'; do sleep 3; done
~/.local/bin/lmdesk ask "只回一个字：白" --model "$B" --timeout 600; echo "exit=$?"
curl -s localhost:8766/api/state | python3 -c 'import json,sys; print([h["label"] for h in json.load(sys.stdin)["holders"]])'
curl -s -X POST localhost:8766/api/llm/chat -H 'Content-Type: application/json' \
  -d "{\"model\":\"$B\",\"messages\":[{\"role\":\"user\",\"content\":\"只回一个字：好\"}]}" | head -c 300; echo
```

Expected:
- `ask` 输出回答，`exit=0`；
- holders 里是 `B`；
- 最后那次界面身份的对话返回回答，不是 `evicted`。

再反向换一次：用 `/api/llm/load` 载入 `A`，等 loaded，然后用 `/api/llm/chat` 对 `A` 说一句。Expected: 返回回答，不是 409。

- [ ] **Step 5: 生图期间 ask 每 15s 有一行（G4）**

```bash
~/.local/bin/lmdesk image new "修复验证-心跳"
~/.local/bin/lmdesk image gen "修复验证-心跳" "雪山日出" --size 1024x1024 --no-wait
date +%s; ~/.local/bin/lmdesk ask "只回一个字：白" --model "$B" --timeout 900 2>&1 \
  | while IFS= read -r l; do printf '%s %s\n' "$(date +%s)" "$l"; done
```

Expected: 第一行「等待中：…」的时间戳与开头的 `date +%s` 相差 ≤ 16 秒，之后约每 15 秒一行，最后输出回答。

- [ ] **Step 6: 不关闭的 stdin 管道（G8）**

```bash
time (sleep 600 | ~/.local/bin/lmdesk ask "只回一个字：白" --model "$B" --timeout 120); echo "exit=$?"
```

Expected:
- 约 5 秒后 stderr 出现「stdin 5 秒内没有数据，按没有输入处理」；
- 随后输出回答，`exit=0`；
- 总耗时远小于 120 秒。

- [ ] **Step 7: 收尾**

- 把本任务里创建的「修复验证-心跳」会话告诉用户，请用户在台面里删除（命令行不提供删除）。
- 汇报：每一步的实际输出（成功和失败都写），以及每条缺口对应的提交。
- 不 push、不合并，等用户决定。

---

## 不在本计划内

- **G11**（q11 的「没有拉起」）后续 6 组实测都没复现。本计划只让「不在 app 包里」这种情况报出原因（Task 7），如果再出现，从报错就能看出是不是这一种。
- **q24 纯音乐有没有人声**：需要人耳听 `docs/cross-exam/2026-10-16-agent-skill/evidence/q24/music3-20261019-190645-c2c3561a.wav`。
- **J1 的窗口条款**：这次没有专门复核 J1 那次运行。G12 修好后，由 Task 10 Step 3 复核同一条件。
- **缺陷模式 P1**：本计划改了其中的 SKILL.md 退出码与视频节、设置页说明文字、媒体中断文案、Waiter 文案。其余位点（argparse 帮助、菜单栏文案、卸载脚本输出等）没有逐条复核。
- **报告「未拉的线」**：空 `--lyrics-file`、`--steps 99999`、desk.log 451MB、重名会话不警告等，都不在本计划内。
- 修完之后，可以对这些缺口续盘 `/superstorm:cross-exam`，由独立实测官重新取证。
