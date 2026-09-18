# 预算算术与查询分层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉 budget 模式的两个系统性错误——无参查询被迫做预算算术（导致换模型按钮灰掉、下载可能被误拒、网关错误码漂移），以及 `fits` 把已驻留的内存扣两遍（导致所有共存判定偏保守）。

**Architecture:** 两件事分开。第一件是**分层**：`can_start_heavy(kind)` 无参时只回答归属问题，不碰任何内存数字；容量判定另有入口，必须带参数。第二件是**算术**：`Workload` 增加 `bytes_resident`（授予前后 `available_bytes` 之差，实测得出），`fits` 对已驻留的重活只计 `bytes_needed - bytes_resident`。

**Tech Stack:** Python 3.13 标准库、pytest；不新增依赖。

**Spec:** `docs/superpowers/specs/2026-09-17-budget-spec.md`（R-budget-12、R-budget-13，以及既有的 R-budget-01/07/10）

## Global Constraints

- **零第三方依赖**，与仓库既有约定一致。
- **每个额度带 `source` ∈ `predicted` / `measured` / `unavailable`**（R-budget-01）。
- **一组的来源取最弱者**（R-budget-10）——这条不动，但它正是无参调用恒被拒的放大器，分层之后它只作用于**真正带参数**的容量判定。
- **测不到就退回保守**：`bytes_resident` 量不到时记 0，行为与今天一致（R-budget-12 末句）。绝不用估算值顶替。
- **测试必须验证「功能失效时会变红」**：每写完一个测试，短接被测实现跑一次，确认失败，再改回。**冗余守卫会让单点短接测不出来**——遇到「改了却不红」，先判断是守卫冗余还是测试是假的，两种处置不同：前者给每道守卫各补一条能独立打红的测试，后者按纪律修测试。这个仓库里已经出现过三次。
- **`__pycache__` 会造成假红**：短接验证前后若结果反常，先 `find desk -name __pycache__ -type d -exec rm -rf {} +` 再复跑。本仓库出现过一次。
- 中文标识符不进代码；面向用户的文案用中文。
- 不得写入 `~/LocalModelDesk/llms` 与 `~/Library/Application Support/LocalModelDesk`；测试一律用 `tmp_path` 或假件。

---

## 背景：两个错误的证据

**错误一（R-budget-13）**——已复现。六个调用点不传参数：

| 调用点 | 问的其实是 |
|---|---|
| `desk/runtime.py:180` 下载闸 | 有没有媒体作业在跑 |
| `desk/testing/harness.py:287` 同上（测试台面） | 同上 |
| `desk/gateway/guard.py:22` 网关守卫 | 现在能不能调模型 |
| `desk/gateway/desk_backend.py:24` | 同上 |
| `desk/testing/harness.py:60` | 同上（测试台面） |
| `desk/arbiter/core.py:158-159` 台面状态两个按钮 | 「加载」「生成」按钮该不该可点 |

它们问的都是归属，不是容量。无参进入预算路径后，`cost()` 拿不到 `config`/`params`，
产出 `bytes_needed=0` 且 `source="unavailable"` 的空壳 workload，与驻留的那件组成两件，
撞上 R-budget-10 → **恒为 `insufficient_budget`**。实测复现（驻留一个 30 GB 模型、可用 60 GiB）：

```
desk_state().can_start.llm
→ {'ok': False, 'reason': {'code': 'insufficient_budget',
   'message': '需要 61203087360 字节，可用 64424509440 字节（依据：unavailable）'}}
```

注意 **需要 61.2 G < 可用 64.4 G，数字上是够的**——被拒纯粹因为来源是 `unavailable`。
前端 `desk/static/js/main.js:90` 只对 `llm_already_held` 放行，`pure/desk_state.js` 的
`REASON_TEXT` 没有 `insufficient_budget` 条目 → 按钮灰掉并显示「暂不可用（insufficient_budget）」。

**错误二（R-budget-12）**——已实测。在子进程里真实占用 6 GiB：

```
占用前   available = 68.4 GiB
占 6 GiB 时        = 63.7 GiB   （降了 4.7）
释放后             = 68.4 GiB
```

`available_bytes` 确实随常驻占用下降，所以它**已经排除了常驻内存**。
而 `desk/arbiter/core.py` 的 `fits(list(resident) + [workload], available_bytes)`
把 resident 的 `bytes_needed` 整个加上去——已分配的那部分被扣了两遍。

**不能简单把 resident 整个排除**：mlx-lm 的 KV 是懒分配的，一个已驻留模型的权重已经占掉
（该排除），被授予的 KV 额度还没占（该保留为预留）。所以要区分「已分配」与「已承诺未分配」。

---

## File Structure

| 文件 | 改什么 |
|---|---|
| `desk/arbiter/core.py` | 无参走归属分支不碰预算；授予前后采样算 `bytes_resident`；`_decide_from` 传修正后的账 |
| `desk/budget/budget.py` | `Workload` 加 `bytes_resident`；`fits` 对 resident 只计未分配部分 |
| `desk/static/js/pure/desk_state.js` | `REASON_TEXT` 补 `insufficient_budget` 文案（分层之后按钮不该再撞上它，但兜底文案不能缺） |
| `tests/test_budget_fits.py` | resident 记账的新测试 |
| `tests/test_arbiter_core.py` | 无参归属查询、换模型可达性 |
| `tests/test_arbiter_resident_accounting.py` | 新建：授予前后采样与退化路径 |
| `tests/js/desk_state.test.js` | 文案兜底 |

---

### Task 1: Workload 记已分配字节，fits 只算未分配部分

**Files:**
- Modify: `desk/budget/budget.py`
- Test: `tests/test_budget_fits.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Workload(kind, key, bytes_needed, source, bytes_resident=0)` —— 新增第五个字段，**带默认值 0**，既有构造点一处都不用改
  - `fits(workloads, available_bytes)` 语义不变，但对 `bytes_resident > 0` 的 workload 只计 `bytes_needed - bytes_resident`

**背景（实现者必读）**：`Workload` 是 frozen dataclass，加字段必须给默认值，否则
`tests/test_arbiter_core.py` 与 `tests/test_budget_facade.py` 里几十处四参构造全会炸。

`bytes_resident` 的含义是「这件重活**已经占掉**、因而已经从 `available_bytes` 里扣除的字节数」。
它只在 workload 被授予并驻留之后才有值；未驻留的候选永远是 0（它还没占任何东西）。

**不要写成 `max(bytes_needed - bytes_resident, 0)` 之外的形式**：实测的 `bytes_resident`
可能因为采样噪声略大于 `bytes_needed`，负数会让一件重活反过来「贡献」额度。

- [ ] **Step 1: 写失败的测试**

```python
# 追加到 tests/test_budget_fits.py
def test_resident_bytes_are_not_counted_twice():
    """R-budget-12：available_bytes 已经排除了常驻内存，再整个加一遍就是扣两遍。

    实测（2026-09-18 本机）：子进程真实占用 6 GiB，available_bytes 降 4.7 GiB，
    释放后回升——它确实随常驻占用变化。
    """
    resident = Workload("chat", "m", int(80 * GIB), "measured", bytes_resident=int(80 * GIB))
    # 80 GiB 全部已分配 ⇒ 对剩余额度不再有任何占用
    assert fits([resident, w("video", 30)], 40 * GIB).ok


def test_the_unallocated_half_of_a_resident_still_counts():
    """懒分配是这条的理由：已驻留模型的权重占掉了，被授予的 KV 额度还没占，
    那部分仍是对内存的承诺，必须留着。"""
    resident = Workload("chat", "m", int(80 * GIB), "measured", bytes_resident=int(50 * GIB))
    # 未分配 30 GiB 仍要计 ⇒ 30 + 30 = 60 > 40
    assert not fits([resident, w("video", 30)], 40 * GIB).ok


def test_a_candidate_that_is_not_resident_counts_in_full():
    """还没授予的候选 bytes_resident 恒为 0——它还没占任何东西。"""
    assert w("video", 30).bytes_resident == 0
    assert not fits([w("chat", 80), w("video", 30)], 100 * GIB).ok


def test_noisy_measurement_never_makes_a_workload_contribute_headroom():
    """实测可能因采样噪声略大于 bytes_needed；负数会让一件重活反过来「贡献」额度。"""
    noisy = Workload("chat", "m", int(10 * GIB), "measured", bytes_resident=int(12 * GIB))
    verdict = fits([noisy], 1 * GIB)
    assert verdict.needed_bytes == 0
    assert verdict.ok


def test_bytes_resident_defaults_to_zero_so_existing_call_sites_keep_working():
    """既有几十处四参构造不用改——加字段必须带默认值。"""
    assert Workload("video", None, 1, "measured").bytes_resident == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_fits.py -q`
Expected: FAIL — `Workload.__init__() got an unexpected keyword argument 'bytes_resident'`

- [ ] **Step 3: 写最小实现**

```python
@dataclass(frozen=True)
class Workload:
    kind: str
    key: str | None
    bytes_needed: int
    source: str
    # 这件重活已经占掉、因而已经从 available_bytes 里扣除的字节数。只有被授予并
    # 驻留之后才有值；未驻留的候选恒为 0。默认值不能去掉：既有几十处四参构造靠它。
    bytes_resident: int = 0


def _unallocated(workload) -> int:
    """这件重活还会再吃掉多少内存。

    available_bytes 的口径（free+inactive+purgeable+speculative）已经排除了已分配的
    部分，所以只有尚未分配的那半还需要从余量里扣。实测的 bytes_resident 可能因采样
    噪声略大于 bytes_needed，夹到 0：负数会让一件重活反过来「贡献」额度。
    """
    return max(workload.bytes_needed - getattr(workload, "bytes_resident", 0), 0)


def fits(workloads, available_bytes: int) -> Verdict:
    """这一组重活能否共存。"""
    workloads = list(workloads)
    needed = sum(_unallocated(w) for w in workloads)
    source = weakest_source(workloads)
    ok = needed <= available_bytes
    if source == "unavailable" and len(workloads) > 1:
        ok = False
    return Verdict(
        ok=ok, needed_bytes=needed, available_bytes=available_bytes,
        source=source, shortfall_bytes=max(needed - available_bytes, 0),
    )
```

`plan()` 不用改：它内部调 `fits`，也用 `sum(w.bytes_needed for w in combo)` 算让出量——
**让出量用 `bytes_needed` 是对的**，因为卸掉一件重活释放的是它占掉的全部，
而候选的 `bytes_resident` 为 0 时两者相等；已驻留的那件让出后释放 `bytes_resident`，
这一点由 Task 2 的集成测试覆盖，本任务不动 `plan()`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_fits.py tests/test_budget_facade.py -q`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

1. 把 `_unallocated` 改成 `return workload.bytes_needed` → 「resident 不该扣两遍」变红。
2. 把 `max(..., 0)` 去掉 → 「噪声不该贡献额度」变红。
3. 把 `bytes_resident: int = 0` 的默认值删掉 → 「既有调用点不用改」变红，且一大批既有测试同时变红。

三次都确认变红后改回。

- [ ] **Step 6: 跑全量确认没有连带损伤**

Run: `python3 -m pytest tests -q`
Expected: PASS（基线 886 passed）

- [ ] **Step 7: 提交**

```bash
git add desk/budget/budget.py tests/test_budget_fits.py
git commit -m "fix(budget): 已驻留的内存不再扣两遍

实测：子进程真实占用 6 GiB，available_bytes 从 68.4 降到 63.7，释放后回升——
它确实已经排除了常驻内存。而 fits 把 resident 的 bytes_needed 整个加上去再和它比，
等于把已分配部分扣两遍，使所有共存判定系统性偏保守。

不能简单把 resident 整个排除：mlx-lm 的 KV 是懒分配的，权重占掉了（该排除）、
被授予的 KV 额度还没占（该保留为预留）。所以 Workload 记 bytes_resident，
fits 对它只计未分配的那半。测不到时为 0，退回今天的保守行为。"
```

---

### Task 2: 授予前后采样，把 bytes_resident 记进账

**Files:**
- Modify: `desk/arbiter/core.py`
- Test: `tests/test_arbiter_resident_accounting.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 `Workload(..., bytes_resident=)`
- Produces: `Arbiter._workloads[token]` 里存的 workload 带实测的 `bytes_resident`

**背景（实现者必读）**：`bytes_resident` 只能实测，不能估——这是这个子系统一贯的纪律。
测法与媒体标定同源：授予前记一次 `available_bytes`，等这件重活真正把内存占上之后再记一次，
差值即已分配量。

**但「真正占上」是个异步事件**：`acquire_heavy` 返回时模型还没开始加载。所以采样点不在
`acquire_heavy` 里，而在**下一次读内存快照时顺带回填**——`_decide` 每次都会取快照，
那时若某个 holder 的 workload 还没有 `bytes_resident`，就用「授予时的基线 − 当前可用」
回填它。这不需要新线程，也不需要改调用方。

**回填必须单调且只做一次**：回填后不再更新，否则 KV 慢慢长起来时 `bytes_resident` 会
跟着涨，把「未分配」越算越小，最终等于把这件重活当成不占内存。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_arbiter_resident_accounting.py
"""R-budget-12：已分配的字节由实测回填，不由估算。"""
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.budget.budget import Workload

GIB = 1024 ** 3


class StepMemory:
    """按调用次序吐出预设的 available_bytes，模拟「加载后可用内存下降」。"""

    def __init__(self, values):
        self._values = list(values)
        self.calls = 0

    def snapshot(self):
        value = self._values[min(self.calls, len(self._values) - 1)]
        self.calls += 1
        return SimpleNamespace(available_bytes=value, total_bytes=128 * GIB, pressure="normal")


class FixedBudget:
    def __init__(self, costs):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[kind]


def test_resident_bytes_are_backfilled_from_the_measured_drop():
    # 授予时可用 100 GiB；加载完成后降到 70 GiB ⇒ 实际占了 30 GiB
    # 前三个值覆盖 acquire 期间的全部快照读取（_decide 两次 + _grant→_state_for 一次），
    # 这样夹具不依赖精确的调用次数；第四个值是加载完成后的可用内存。
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 70 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 27 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    assert granted["ok"] is True

    arbiter.can_start_heavy("video", params={}, key=None)   # 这一次读快照，顺带回填

    held = list(arbiter._workloads.values())
    assert held and held[0].bytes_resident == 30 * GIB


def test_backfill_happens_once_and_never_grows():
    """回填后不再更新：KV 慢慢长起来时若跟着涨，未分配会越算越小，
    最终等于把这件重活当成不占内存。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 70 * GIB, 40 * GIB, 40 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    first = list(arbiter._workloads.values())[0].bytes_resident
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == first


def test_a_rise_in_available_memory_records_zero_not_a_negative():
    """别的进程释放内存导致可用不降反升时，记 0 而不是负数。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 120 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_arbiter_resident_accounting.py -q`
Expected: FAIL — `bytes_resident` 恒为 0（回填未实现）

- [ ] **Step 3: 写最小实现**

在 `Arbiter` 里记住每个 token 授予时的基线，并在每次拿到快照后回填一次：

```python
    def _record_baseline(self, token: str, available_bytes: int) -> None:
        """授予时的可用内存。回填 bytes_resident 要用它作差。"""
        self._grant_baseline[token] = available_bytes

    def _backfill_resident(self, available_bytes: int) -> None:
        """用「授予时基线 − 当前可用」回填已分配字节，只填一次。

        采样点不在 acquire_heavy 里：那时模型还没开始加载，量到的是 0。改为每次读
        快照时顺带回填，不需要新线程也不需要改调用方。

        只填一次是有意的：KV 慢慢长起来时若跟着涨，未分配会越算越小，最终等于把
        这件重活当成不占内存。可用内存不降反升（别的进程释放了）时记 0，不记负数。
        """
        with self._state_lock:
            for token, workload in list(self._workloads.items()):
                if workload.bytes_resident:
                    continue
                baseline = self._grant_baseline.get(token)
                if baseline is None:
                    continue
                measured = max(baseline - available_bytes, 0)
                if measured:
                    self._workloads[token] = replace(workload, bytes_resident=measured)
```

`__init__` 里加 `self._grant_baseline: dict[str, int] = {}`；
释放 token 时把 `_grant_baseline` 里那条一并删掉（否则 token 复用会拿到旧基线）。
需要 `from dataclasses import replace`。

**基线必须是做出该决策时的 `available_bytes`，不得在 `_grant` 里重新读快照**（预检裁决 R2）：
一次 `acquire_heavy` 期间会读 3 次快照（`_decide` 两次 + `_grant → _state_for` 一次），
重新读拿到的可能已经是加载后的值，差值就变成 0。`_grant` 目前的签名
`_grant(self, token, holder, workload)` 收不到它——加一个 `available_bytes` 参数，
由 `acquire_heavy` 把 `_decide` 返回的那个值传下去。

**回填要挂两处，不是一处**（预检裁决 R1）：
- `_decide` 取到 `available_bytes` 之后、读 `self._workloads` 之前；
- **以及 `_state_for`**（它第 155 行本来就读了快照）。

理由：Task 3 会让无参 `can_start_heavy` 在进 `_decide` 之前就返回，而生产里最频繁的
读者正是 2 秒一次的 `desk_state()`——它走 `_state_for`，不走 `_decide`。只挂 `_decide`
的话，回填在真实运行中几乎不发生，这个任务等于白做。回填只填一次，所以多挂一处是幂等的。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_arbiter_resident_accounting.py tests/test_arbiter_core.py -q`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

1. 把 `if workload.bytes_resident: continue` 删掉（每次都更新）→ 「只填一次」变红。
2. 把 `max(baseline - available_bytes, 0)` 的 `max` 去掉 → 「不记负数」变红。
3. 把 `_backfill_resident` 整个调用删掉 → 「按实测回填」变红。

三次都确认后改回。

- [ ] **Step 6: 提交**

```bash
git add desk/arbiter/core.py tests/test_arbiter_resident_accounting.py
git commit -m "fix(arbiter): 已分配字节由实测回填，不由估算

采样点不在 acquire_heavy 里——那时模型还没开始加载，量到的是 0。改为每次读
内存快照时顺带回填「授予时基线 − 当前可用」，不需要新线程也不需要改调用方。

只填一次是有意的：KV 慢慢长起来时若跟着涨，未分配会越算越小，最终等于把这件
重活当成不占内存。"
```

---

### Task 3: 无参查询只回答归属，不碰预算算术

**Files:**
- Modify: `desk/arbiter/core.py`
- Test: `tests/test_arbiter_core.py`

**Interfaces:**
- Consumes: 无
- Produces: `can_start_heavy(kind)`（无 `params` 且无 `key`）走归属分支，永不返回 `insufficient_budget`

**背景（实现者必读）**：R-budget-13。六个调用点问的是归属不是容量，见本计划开头的表。
归属分支的判据只有两条，都与内存无关：

1. 有 holder 正处于 `acquiring` → `transition_in_progress`
2. 想开媒体而已有媒体在跑 → `media_busy`（这是 R-arbiter-04 里唯一与容量无关的那半）

其余一律放行。**「聊天已被持有」不再是拒绝**——`llm_already_held` 这个码前端专门放行过
（`desk/static/js/main.js:90`），它表达的是「可以换模型」，归属分支要保留它。

**不要把这条写成「budget is None 就走老路」**：那是 legacy 兜底，与本条正交。
判据是「这次调用有没有给出容量输入」，不是「这个 Arbiter 有没有接预算」。

- [ ] **Step 1: 写失败的测试**

**先补一行**：`tests/test_arbiter_core.py` **没有定义 `GIB`**（既有测试用十进制字面量如
`40_000_000_000`），而下面的测试用到了它。在 `FakeBudget` 类附近加 `GIB = 1024 ** 3`
（预检裁决 R3）。

```python
# 追加到 tests/test_arbiter_core.py
def test_a_parameterless_query_never_answers_insufficient_budget():
    """R-budget-13：无参问的是归属，不是容量。拿不到参数就产出空壳 workload，
    再撞上「一件 unavailable 整组保守」，会与机器多大无关地恒为拒绝。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=60 * GIB))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 30 * GIB, "measured"),
        "video": Workload("video", None, 27 * GIB, "measured"),
    })
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")

    answer = arbiter.can_start_heavy("llm")          # 无参

    assert answer["reason"] is None or answer["reason"]["code"] != "insufficient_budget"


def test_the_model_switch_path_stays_reachable_with_a_model_resident():
    """已复现的回归：驻留模型后 desk_state 的 can_start.llm 恒为 insufficient_budget，
    前端只对 llm_already_held 放行，于是「换模型」按钮灰掉。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=60 * GIB))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 30 * GIB, "measured"),
        "video": Workload("video", None, 27 * GIB, "measured"),
    })
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")

    llm_button = arbiter.desk_state()["can_start"]["llm"]

    assert llm_button["ok"] is True or llm_button["reason"]["code"] == "llm_already_held"


def test_a_parameterless_media_query_still_reports_media_busy():
    """归属分支保留唯一与容量无关的那条拒绝：媒体在跑时不能开第二个媒体。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=200 * GIB))
    budget = FakeBudget({"video": Workload("video", None, 1, "measured"),
                         "music": Workload("music", None, 1, "measured"),
                         "llm": Workload("llm", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("video", "job-1", params={}, key=None)

    answer = arbiter.can_start_heavy("music")

    assert answer["ok"] is False
    assert answer["reason"]["code"] == "media_busy"


def test_a_query_with_params_still_does_the_budget_arithmetic():
    """反向：带参数的容量判定不受本任务影响，仍按预算判。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=10 * GIB))
    budget = FakeBudget({"llm": Workload("llm", "m", 5 * GIB, "measured"),
                         "video": Workload("video", None, 40 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)

    answer = arbiter.can_start_heavy("video", params={"width": 1024}, key="h3")

    assert answer["ok"] is False
    assert answer["reason"]["code"] == "insufficient_budget"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_arbiter_core.py -q -k "parameterless or model_switch_path"`
Expected: FAIL — 前两条返回 `insufficient_budget`

- [ ] **Step 3: 写最小实现**

在 `can_start_heavy` 与 `_state_for` 的 `can_start` 里，把无参分支引到一个不碰预算的判据上：

```python
    def _ownership_answer(self, kind: str, holders) -> dict:
        """无参查询的答案：只看谁占着，不看内存（R-budget-13）。

        六个调用点（下载闸、网关守卫、台面状态的两个按钮、两处测试台面）问的都是
        「现在谁占着、能不能开这一类」。无参进预算路径时 cost() 拿不到输入，产出
        bytes_needed=0 且 source=unavailable 的空壳，再撞上「一件 unavailable 整组
        保守」，会与机器多大无关地恒为 insufficient_budget。
        """
        if kind not in KINDS:
            return {"ok": False, "reason": self._reason("unknown_kind", f"unknown heavy kind: {kind!r}"),
                    "memory_warning": None, "release": []}
        if any(h.phase == PHASE_ACQUIRING for h in holders):
            return {"ok": False, "reason": self._reason(
                "transition_in_progress", "a heavy-work transition is in progress; retry shortly"),
                "memory_warning": None, "release": []}
        busy = next((h for h in holders if h.kind in MEDIA_KINDS), None)
        if kind in MEDIA_KINDS and busy is not None:
            return {"ok": False, "reason": self._reason("media_busy", f"{busy.kind} job {busy.label!r} is running"),
                    "memory_warning": None, "release": []}
        return {"ok": True, "reason": None, "memory_warning": None, "release": []}
```

`can_start_heavy` 开头加：

```python
        if self._budget is not None and params is None and key is None:
            with self._state_lock:
                holders = tuple(self._holders.values())
            return self._ownership_answer(kind, holders)
```

`_state_for` 里的 `can_start` 改为调 `self._ownership_answer(kind, holders)`
（它本来就只有 holders，没有参数可给）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_arbiter_core.py tests/test_gateway_guard.py tests/test_resources_downloader.py -q`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

1. 把 `can_start_heavy` 开头那段无参分支删掉 → 前两条变红。
2. 把 `_ownership_answer` 里的 `media_busy` 分支删掉 → 「媒体在跑仍报 media_busy」变红。
3. 把无参判据从 `params is None and key is None` 改成 `self._budget is None` → 「带参数仍做预算算术」应保持绿、前两条应保持绿；**若有任何一条变化，说明判据写错了**。

三次都确认后改回。

- [ ] **Step 6: 前端补兜底文案**

`desk/static/js/pure/desk_state.js` 的 `REASON_TEXT` 加一条 `insufficient_budget`
（分层之后按钮不该再撞上它，但兜底文案不能缺——缺了就直接把错误码显示给用户）。
文案：`"内存不够，先卸掉一个再来"`。

对应测试追加到 `tests/js/desk_state.test.js`：断言 `insufficient_budget` 有中文文案、
且不等于原始错误码。

- [ ] **Step 7: 跑全量**

Run: `python3 -m pytest tests -q && node --test "tests/js/**/*.test.js"`
Expected: PASS（基线 886 passed + JS 205）

- [ ] **Step 8: 提交**

```bash
git add desk/arbiter/core.py desk/static/js/pure/desk_state.js tests/
git commit -m "fix(arbiter): 无参查询只回答归属，不做预算算术

六个调用点（下载闸、网关守卫、台面状态两个按钮、两处测试台面）问的是
「现在谁占着」，不是「这个作业装不装得下」。无参进预算路径时 cost() 拿不到
输入，产出 bytes_needed=0、source=unavailable 的空壳，再撞上「一件 unavailable
整组保守」，与机器多大无关地恒为 insufficient_budget。

已复现的后果：驻留模型后「换模型」按钮灰掉（前端只对 llm_already_held 放行）、
下载可能被误拒、网关对外返回的错误码从 media_busy 漂移成 insufficient_budget。

判据是「这次调用有没有给出容量输入」，不是「这个 Arbiter 有没有接预算」——
后者是 legacy 兜底，与本条正交。"
```

---

### Task 4: 真机复核

**Files:**
- Create: `scripts/budget-readback.py`
- Test: 无（这是一次一次性核对，不是回归网）

**Interfaces:**
- Consumes: Task 1-3
- Produces: 一个只读脚本，打印本机六个模型的额度与当前共存判定

**背景（实现者必读）**：前三个任务全部用假件验证。Task 1 的 `bytes_resident` 语义、
Task 3 的六个调用点，都需要一次真实读数核对。**脚本只读**：不加载模型、不起作业、
不写任何文件，只打快照与纯函数结果。

这一步的价值在上一轮已经证明过：budget 子系统的两个洞（权重没减、record_turn 不落盘）
全套单测都没发现，是真机跑一次才现形的。

- [ ] **Step 1: 写脚本**

```python
#!/usr/bin/env python3
"""只读地打印本机的预算读数，供人工核对。不加载模型、不起作业、不写文件。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.arbiter.memory import MemoryReader
from desk.budget.budget import Budget, Workload, fits
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3


def main() -> int:
    snap = MemoryReader().snapshot()
    print(f"本机：总 {snap.total_bytes / GIB:.0f} GiB · 可用 {snap.available_bytes / GIB:.0f} GiB"
          f" · 压力 {snap.pressure}\n")
    budget = Budget(measurements=Measurements(), memory_reader=MemoryReader(),
                    media_estimate=estimate_bytes, now=lambda: 0.0)
    print(f"{'模型':34} {'权重GB':>6} {'窗口':>8} {'额度':>10} {'压缩点':>10}  来源")
    print("-" * 82)
    for directory in sorted((Path.home() / "LocalModelDesk/llms").glob("*/*/")):
        config_path = directory / "config.json"
        if not config_path.is_file():
            continue
        weights_gb = sum(f.stat().st_size for f in directory.glob("*.safetensors")) / 1e9
        chat = budget.for_chat(directory.name, json.loads(config_path.read_text()), weights_gb)
        print(f"{directory.name[:34]:34} {weights_gb:>6.0f} {str(chat.window or '—'):>8}"
              f" {chat.token_limit:>10,} {chat.compact_at:>10,}  {chat.source}")

    print("\n共存判定（驻留一个 30 GB 模型、其权重已分配时，还能不能开视频）：")
    resident = Workload("llm", "resident", int(60 * GIB), "measured", bytes_resident=int(30 * GIB))
    video = Workload("video", None, estimate_bytes("video", {}), "predicted")
    verdict = fits([resident, video], snap.available_bytes)
    print(f"  需要 {verdict.needed_bytes / GIB:.1f} GiB · 可用 {verdict.available_bytes / GIB:.1f} GiB"
          f" · 依据 {verdict.source} ⇒ {'装得下' if verdict.ok else '装不下'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 跑一次，人工核对**

Run: `python3 scripts/budget-readback.py`

核对三件事，任何一件不成立就回到对应任务：
- 权重大于当前可用内存的模型，额度应为 0（上一轮修过的洞，别再回归）
- MLA 模型（glm-4.7-flash）的来源应为 `unavailable`，其余为 `predicted`
- 共存那行的「需要」应约等于 `30 + 27 = 57 GiB`（resident 的已分配 30 GiB 不再计入），
  **而不是 87 GiB**——若是 87，说明 Task 1 没生效

- [ ] **Step 3: 提交**

```bash
git add scripts/budget-readback.py
git commit -m "chore(budget): 只读的真机读数脚本，供人工核对

前三个任务全部用假件验证。budget 子系统上一轮的两个洞（权重没减、
record_turn 不落盘）全套单测都没发现，是真机跑一次才现形的——所以留一个
随时能跑的只读核对入口。不加载模型、不起作业、不写文件。"
```

---

## Self-Review

**1. Spec coverage**

| 需求 | 落在 |
|---|---|
| R-budget-12 resident 只计未分配部分 | Task 1（`_unallocated` + 四条测试）、Task 2（实测回填） |
| R-budget-13 无参查询不做预算算术 | Task 3 |
| R-budget-01 每个额度带来源 | 不变；Task 3 的归属答案不产出额度，故不涉及 |
| R-budget-10 一组取最弱来源 | 不动。分层之后它只作用于带参数的容量判定——这正是它本来的意图 |
| R-arbiter-04 媒体在跑拒绝第二个媒体 | Task 3 的归属分支保留了这条（与容量无关的那半） |

**未覆盖且有意留下的**：F3（媒体在跑时聊天仍被无条件拒绝，`desk/llm/service.py` 的
`_chat_precheck` 与 `desk/gateway/guard.py`）。它不是算术错误，是**产品决定**——
「媒体在跑时要不要允许聊天」需要用户拍板，而且方向是放宽（风险增加），
不该混在一次修 bug 里。本计划修完之后 F3 的技术障碍就没了，可以单独提。

**2. Placeholder scan**

Task 2 Step 3 的 `__init__` / `_grant` / 释放路径三处改动只给了文字说明没给完整代码，
因为它们是三行插入而上下文有几十行。已点名每处该加什么、为什么（token 复用会拿到旧基线）。

Task 3 Step 6 的 JS 测试只给了断言要点。`tests/js/desk_state.test.js` 已存在，
实现者照该文件既有写法追加即可。

**3. Type consistency**

- `Workload` 五个字段（`kind, key, bytes_needed, source, bytes_resident=0`）在 Task 1 定义，
  Task 2 用 `dataclasses.replace` 更新第五个，Task 4 的脚本按关键字构造，三处一致。
- `_unallocated(workload)` 只在 `fits` 内部用，不导出。
- `_ownership_answer(kind, holders)` 在 Task 3 定义，`can_start_heavy` 与 `_state_for` 两处调用，
  返回形状与 `can_start_heavy` 既有返回一致（`ok` / `reason` / `memory_warning` / `release` 四键）。

**4. 与前两个计划的教训对照**

- 上一轮 `for_chat` 漏减权重，根因是计划代码与设计文档不符。本计划的每段实现代码都
  直接对应 spec 里刚写下的 R-budget-12/13 原文，且 Task 4 用真机读数做最后一道核对。
- 上一轮四条假测试全靠短接抓出。本计划每个任务的 Step 5 逐条点名短接什么、哪条该红，
  Task 3 第 3 条甚至是「短接后**不该**有变化」的反向检查。
- Global Constraints 里新增了两条只有这个仓库才知道的坑：冗余守卫让单点短接测不出来
  （已出现三次）、`__pycache__` 造成假红（已出现一次）。
