# budget 子系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让台面能回答「这台机器此刻还装得下什么」，答案从本机实测里长出来，而不是从写死的常数里来。

**Architecture:** 新增 `desk/budget/` 包，与 `desk/arbiter/` 平级。三层单向依赖：`estimate.py`（纯函数，读 `config.json` 算每 token 字节与声明窗口）→ `observe.py`（传感器，解析 mlx-lm 日志与内存快照）→ `budget.py`（合成额度、判定共存、给出 mlx-lm 限额参数）。`arbiter` 保留所有权与收割，容量判断整体搬到 `budget`。

**Tech Stack:** Python 3.13 标准库（无第三方依赖）、pytest、macOS `vm_stat`/`sysctl`（经 `desk/arbiter/memory.py` 已封装）、mlx-lm 的 `--prompt-cache-bytes` / `--prompt-cache-size`。

**Spec:** `docs/superpowers/specs/2026-09-17-budget-spec.md`（需求）与 `docs/superpowers/specs/2026-09-17-budget-design.md`（设计）

## Global Constraints

- **零第三方依赖**：`desk/` 只用标准库，与仓库现有约定一致。
- **每个额度必须带 `source` ∈ `predicted` / `measured` / `unavailable`**（R-budget-01）。任何输出额度的函数都要携带它。
- **一组重活的来源取最弱者**：只要有一件 `unavailable`，整组按 `unavailable` 走保守路径（R-budget-10）。
- **读不到就报 `unavailable`，绝不回落成猜测或沿用旧值**（R-budget-02、失败模式表）。
- **`estimate.py` 与 `budget.py` 必须是纯函数**：无 IO、无子进程、无文件读写。IO 只允许出现在 `observe.py` 与 `store.py`。
- **测试必须验证「功能失效时会变红」**：每写完一个测试，短接被测实现跑一次，确认失败，再改回（验收节）。双向行为要双向验证。
- 中文标识符不进代码；面向用户的文案用中文，与仓库现有风格一致。
- 不得写入 `~/LocalModelDesk/llms` 或 `~/Library/Application Support/LocalModelDesk`；测试一律用 `tmp_path`。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `desk/budget/__init__.py` | 导出 `Budget`、`Workload`、`Verdict`、`Plan`、`ChatBudget` |
| `desk/budget/estimate.py` | 纯函数：`per_token_bytes(config)`、`declared_window(config)` |
| `desk/budget/observe.py` | 传感器：`parse_cache_line(text)`、`Observer.latest_cache_bytes()` |
| `desk/budget/store.py` | 实测档案读写：`Measurements.load/save/model/media/record_*` |
| `desk/budget/budget.py` | `Budget` 门面：`cost` / `fits` / `plan` / `for_chat` / `launch_args` / `snapshot` |
| `desk/arbiter/state.py` | 改写：`plan_acquire` 接受持有者**集合**与预算判定结果 |
| `desk/arbiter/core.py` | 改写：`can_start_heavy` 转调 `Budget.fits`；持有者由单个变一组 |
| `desk/llm/backend.py` | 改：`spawn` 接受并透传额外 argv |
| `desk/llm/service.py` | 改：加载时向 `spawn` 传 `Budget.launch_args`；每轮完成后记录自校准读数 |
| `desk/media/service.py` | 改：`estimate_bytes` 的标定值改由 `Budget` 提供；作业期采样峰值 |
| `tests/test_budget_estimate.py` 等 | 与仓库现有 `tests/test_<模块>_<主题>.py` 命名一致 |

---

### Task 1: estimate.py —— 从 config.json 读窗口与每 token 字节

**Files:**
- Create: `desk/budget/__init__.py`
- Create: `desk/budget/estimate.py`
- Test: `tests/test_budget_estimate.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `declared_window(config: dict) -> int | None`
  - `per_token_bytes(config: dict) -> int | None`

**背景（实现者必读）**：本机六个模型的 `config.json` 窗口位置不统一。`llama` 与 `glm4_moe_lite` 放顶层；`qwen3_5`、`qwen3_5_moe`、`gemma4` 放在 `text_config` 里。`gemma4` **同时**有 `vision_config.max_position_embeddings = 131072` 和 `text_config.max_position_embeddings = 262144`——取错就凭空砍掉一半窗口。所以查找顺序是写死的规则，不是「递归找第一个」。

每 token 的 KV cache 字节数 = `层数 × KV头数 × head_dim × 2（K和V） × 2（fp16 字节）`。
fp16 是**保守**假设：若 mlx 量化了 KV，实际更小，我们会偏早压缩——这是安全方向。

**但这个公式只对标准 MHA/GQA 成立。** 本机的 glm-4.7-flash 是 **MLA 架构**
（`kv_lora_rank: 512`、`qk_nope_head_dim: 192`、`v_head_dim: 256`，**没有 `head_dim`**），
它每层每 token 只存一个压缩潜向量，结构完全不同。若对它套上面的公式，
并用 `hidden_size // num_attention_heads` 去凑 `head_dim`（2048/20 = 102.4，
连整数都不是），会得出约 375 KB/token，而实际约 53 KB/token——**高估 7 倍**。

所以规则是：**`head_dim` 必须显式存在，且 config 里不得出现 MLA 标记
（`kv_lora_rank` / `qk_nope_head_dim` / `v_head_dim`）；任一条不满足就返回 `None`。**
不要用 `hidden_size // num_attention_heads` 去补——那个推导在 MLA 上会凑出一个
看起来合理、实际错 7 倍的数，而且没人看得出来。返回 `None` 让它走 `unavailable`
的保守路径，一轮之后自校准就把真值填进来了。这正是本设计不信任纯预测公式的原因。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_estimate.py
"""R-budget-02：窗口读取顺序写死，且永不读 vision_config。"""
from desk.budget.estimate import declared_window, per_token_bytes

LLAMA = {"model_type": "llama", "max_position_embeddings": 131072,
         "num_hidden_layers": 80, "num_key_value_heads": 8, "head_dim": 128}
QWEN = {"model_type": "qwen3_5",
        "text_config": {"max_position_embeddings": 262144, "num_hidden_layers": 64,
                        "num_key_value_heads": 4, "head_dim": 256}}
GEMMA = {"model_type": "gemma4",
         "text_config": {"max_position_embeddings": 262144, "num_hidden_layers": 60,
                         "num_key_value_heads": 16, "head_dim": 256},
         "vision_config": {"max_position_embeddings": 131072}}


def test_top_level_window_is_read():
    assert declared_window(LLAMA) == 131072


def test_text_config_wins_over_top_level():
    nested = dict(QWEN, max_position_embeddings=8192)   # 顶层是个陷阱值
    assert declared_window(nested) == 262144


def test_vision_config_is_never_read():
    """gemma-4 的视觉塔是 131072，文本塔是 262144；取错砍掉一半窗口。"""
    assert declared_window(GEMMA) == 262144


def test_vision_only_config_reports_nothing():
    """只有 vision_config 时必须报「读不到」，不许拿视觉塔的数顶替。"""
    assert declared_window({"vision_config": {"max_position_embeddings": 131072}}) is None


def test_missing_window_is_none_not_a_default():
    assert declared_window({"model_type": "mystery"}) is None


def test_per_token_bytes_matches_the_hand_computed_value():
    # 80 层 × 8 KV 头 × 128 head_dim × 2 (K和V) × 2 (fp16) = 327680
    assert per_token_bytes(LLAMA) == 327_680


def test_per_token_bytes_reads_nested_config():
    # 64 × 4 × 256 × 2 × 2 = 262144
    assert per_token_bytes(QWEN) == 262_144


MLA = {"model_type": "glm4_moe_lite", "max_position_embeddings": 202752,
       "num_hidden_layers": 47, "num_key_value_heads": 20, "hidden_size": 2048,
       "num_attention_heads": 20, "kv_lora_rank": 512,
       "qk_nope_head_dim": 192, "qk_rope_head_dim": 64, "v_head_dim": 256}


def test_mla_architecture_reports_nothing_rather_than_a_wrong_number():
    """glm-4.7-flash 是 MLA：每层每 token 只存一个压缩潜向量，标准公式不适用。

    套标准公式并用 hidden_size // num_attention_heads 凑 head_dim（2048/20 = 102.4，
    连整数都不是）会得出约 375 KB/token，实际约 53 KB——高估 7 倍，而且看起来很合理。
    这种数比没有数更危险，所以宁可报 None 走保守路径，让自校准去填真值。
    """
    assert per_token_bytes(MLA) is None


def test_head_dim_is_never_derived_from_hidden_size():
    """没有显式 head_dim 就是算不出，不许用除法凑一个。"""
    cfg = {"num_hidden_layers": 2, "num_key_value_heads": 2,
           "hidden_size": 512, "num_attention_heads": 8}
    assert per_token_bytes(cfg) is None


def test_mla_window_is_still_readable():
    """算不出开销不影响读窗口——两件事互相独立。"""
    assert declared_window(MLA) == 202752


def test_incomplete_config_reports_nothing():
    """字段不全时报读不到，绝不套一个默认值——那会让预算悄悄建立在假数上。"""
    assert per_token_bytes({"num_hidden_layers": 80}) is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_estimate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'desk.budget'`

- [ ] **Step 3: 写最小实现**

```python
# desk/budget/__init__.py
"""budget：回答「这台机器此刻还装得下什么」。"""
```

```python
# desk/budget/estimate.py
"""冷启动初值：从模型 config.json 推算窗口与每 token 的 KV 开销。

纯函数，无 IO。窗口的查找顺序是写死的规则而不是「递归找第一个」：gemma-4 同时
有 text_config 和 vision_config 两个窗口，递归查找会撞上视觉塔的 131072，
把文本塔的 262144 砍掉一半。
"""
from __future__ import annotations

_WINDOW_KEY = "max_position_embeddings"
_KV_BYTES = 2      # fp16。若 mlx 量化了 KV，实际更小，我们偏早压缩——安全方向。
_K_AND_V = 2


def _text_scope(config: dict) -> dict:
    """文本塔的配置段。vision_config 永远不参与——它描述的是另一座塔。"""
    nested = config.get("text_config")
    return nested if isinstance(nested, dict) else config


def declared_window(config: dict) -> int | None:
    """模型声明的上下文窗口；读不到返回 None（R-budget-02）。"""
    nested = config.get("text_config")
    if isinstance(nested, dict) and isinstance(nested.get(_WINDOW_KEY), int):
        return nested[_WINDOW_KEY]
    value = config.get(_WINDOW_KEY)
    return value if isinstance(value, int) else None


# MLA（Multi-head Latent Attention）的标记。出现任一个，说明这个模型每层每 token
# 存的是一个压缩潜向量而不是 KV 头，下面的标准公式不适用。
_MLA_MARKERS = ("kv_lora_rank", "qk_nope_head_dim", "v_head_dim")


def per_token_bytes(config: dict) -> int | None:
    """每个 token 的 KV cache 字节数；算不出返回 None，绝不凑一个。

    只对标准 MHA/GQA 成立。head_dim 必须显式存在——用
    hidden_size // num_attention_heads 去补，在 glm-4.7-flash 这类 MLA 模型上
    会凑出 102（2048/20 = 102.4，连整数都不是），算出约 375 KB/token，
    而实际约 53 KB。高估 7 倍且看起来很合理的数，比没有数更危险。
    """
    scope = _text_scope(config)
    if any(marker in scope or marker in config for marker in _MLA_MARKERS):
        return None
    layers = scope.get("num_hidden_layers")
    kv_heads = scope.get("num_key_value_heads")
    head_dim = scope.get("head_dim")
    if not all(isinstance(v, int) for v in (layers, kv_heads, head_dim)):
        return None
    return layers * kv_heads * head_dim * _K_AND_V * _KV_BYTES
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_estimate.py -q`
Expected: PASS（9 passed）

- [ ] **Step 5: 验证测试会咬**

把 `declared_window` 里 `text_config` 那三行删掉（退化成只读顶层），跑测试，**必须变红**在 `test_text_config_wins_over_top_level` 与 `test_vision_config_is_never_read`。再把 `per_token_bytes` 的 `return None` 改成 `return 262_144`，**必须变红**在 `test_incomplete_config_reports_nothing`。两次都确认变红后改回。

Run: `python3 -m pytest tests/test_budget_estimate.py -q`
Expected: 短接时 FAIL，改回后 PASS

- [ ] **Step 6: 用真实模型 config 做回归 fixture**

把本机六个模型的 `config.json` 中与预算相关的字段抽成 fixture（不拷贝整份文件，只留 `model_type` / 窗口 / 层数 / KV 头数 / head_dim / hidden_size / num_attention_heads），存为 `tests/fixtures/budget/model_configs.json`，并加一条参数化测试断言六个模型都算得出窗口与每 token 字节：

```python
import json
from pathlib import Path
import pytest

FIXTURES = json.loads((Path(__file__).parent / "fixtures/budget/model_configs.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,expected", [
    ("Llama-3.3-70B", (131072, 327_680)),
    ("glm-4.7-flash", (202752, None)),       # MLA：窗口读得到，开销算不出
    ("Qwen3.8-27B", (262144, 262_144)),
    ("Qwen3.6-35B-A3B", (262144, 81_920)),
    ("gemma-4-31B", (262144, 983_040)),
])
def test_every_installed_model_resolves(name, expected):
    cfg = FIXTURES[name]
    assert (declared_window(cfg), per_token_bytes(cfg)) == expected
```

抽 fixture 时**只读不写模型目录**。glm-4.7-flash 那条的期望是 `(202752, None)`——
它是 MLA，窗口读得到但开销算不出，这是有意的。

- [ ] **Step 7: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_estimate.py -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add desk/budget/__init__.py desk/budget/estimate.py tests/test_budget_estimate.py tests/fixtures/budget/
git commit -m "feat(budget): 从 config.json 读窗口与每 token KV 开销

窗口的查找顺序是写死的规则，不是递归找第一个：gemma-4 同时有 text_config
262144 和 vision_config 131072，递归会撞上视觉塔，把窗口砍掉一半。

字段不全时返回 None 而不是套默认值——套了默认值，预算就悄悄建立在假数上。"
```

---

### Task 2: observe.py —— 解析 mlx-lm 日志里的实际 KV 占用

**Files:**
- Create: `desk/budget/observe.py`
- Test: `tests/test_budget_observe.py`

**Interfaces:**
- Consumes: 无（`MemorySnapshot` 由调用方传入）
- Produces:
  - `parse_cache_line(text: str) -> int | None` —— 从日志文本取**最后一条** `Prompt Cache` 行的字节数
  - `measured_bytes_per_token(cache_bytes: int, prompt_tokens: int) -> int | None`

**背景（实现者必读）**：mlx-lm 每轮往它的日志里写一行形如
`Prompt Cache: 3 sequences, 12.40 GB`（见 mlx_lm `server.py::_log_cache_stats`，
用 `n_bytes / 1e9` 格式化，所以 GB 是十进制而非 GiB）。台面已经在读这个日志文件
（`desk/llm/backend.py::log_tail`），但没解析这一行。

**这是整个方案的心脏**：实测每 token 字节 = 该行字节数 ÷ 本轮 `usage.prompt_tokens`。
dtype 是否量化、mlx 如何分页，全都不必知道——除一下就是本机该模型的真值。

日志可能包含多轮，必须取**最后一条**；解析不到必须返回 `None` 让上层记
`unavailable`，**不许沿用上一次的值**——传感器坏了却继续报旧数，等于让预算
建立在一个已经不成立的观察上。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_observe.py
"""R-budget-04：自校准的读数来自 mlx-lm 日志，读不到就是读不到。"""
from desk.budget.observe import parse_cache_line, measured_bytes_per_token

LOG = """\
2026-09-17 10:00:01 INFO Starting server on 127.0.0.1:8767
2026-09-17 10:02:11 INFO Prompt Cache: 1 sequences, 3.20 GB
2026-09-17 10:05:42 INFO Prompt Cache: 3 sequences, 12.40 GB
2026-09-17 10:05:42 INFO - QuantizedKVCache: 3 sequences, 12.40 GB
"""


def test_reads_the_last_cache_line_not_the_first():
    """日志里有多轮；预算要的是此刻的占用，不是十分钟前的。"""
    assert parse_cache_line(LOG) == 12_400_000_000


def test_gb_is_decimal_because_mlx_divides_by_1e9():
    assert parse_cache_line("Prompt Cache: 1 sequences, 1.00 GB") == 1_000_000_000


def test_per_type_breakdown_lines_are_not_mistaken_for_the_total():
    """以 '- ' 开头的是分类型明细，累加进总数会让读数翻倍。"""
    assert parse_cache_line("- QuantizedKVCache: 3 sequences, 12.40 GB") is None


def test_absent_line_reports_nothing():
    assert parse_cache_line("nothing interesting here") is None


def test_changed_format_reports_nothing_rather_than_guessing():
    """mlx-lm 改了格式就老实说读不到，不猜。"""
    assert parse_cache_line("Prompt Cache: 3 seqs / 12.40 gigabytes") is None


def test_bytes_per_token_is_the_quotient():
    assert measured_bytes_per_token(12_400_000_000, 40_000) == 310_000


def test_zero_tokens_reports_nothing_instead_of_dividing_by_zero():
    assert measured_bytes_per_token(12_400_000_000, 0) is None


def test_missing_cache_reading_reports_nothing():
    assert measured_bytes_per_token(None, 40_000) is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_observe.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'desk.budget.observe'`

- [ ] **Step 3: 写最小实现**

```python
# desk/budget/observe.py
"""传感器：只产出观察，不做决策。

mlx-lm 每轮写一行 `Prompt Cache: N sequences, X GB`（server.py::_log_cache_stats，
用 n_bytes / 1e9 格式化，所以 GB 是十进制）。它下面还会跟若干以 "- " 开头的
分类型明细行，那些不是总数，混进来会让读数翻倍。

读不到一律返回 None：传感器坏了却沿用旧值，等于让预算建立在一个已经不成立的
观察上，而且没人看得出来。
"""
from __future__ import annotations

import re

_CACHE_LINE = re.compile(r"(?<!- )Prompt Cache:\s*\d+\s+sequences,\s*([\d.]+)\s*GB")
_GB = 1_000_000_000


def parse_cache_line(text: str) -> int | None:
    """日志里最后一条 Prompt Cache 行的字节数；读不到返回 None。"""
    matches = _CACHE_LINE.findall(text or "")
    if not matches:
        return None
    return int(float(matches[-1]) * _GB)


def measured_bytes_per_token(cache_bytes: int | None, prompt_tokens: int | None) -> int | None:
    """本机该模型每 token 的实测 KV 开销；任一读数缺失即返回 None。"""
    if not cache_bytes or not prompt_tokens:
        return None
    return int(cache_bytes / prompt_tokens)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_observe.py -q`
Expected: PASS（8 passed）

- [ ] **Step 5: 验证测试会咬**

把 `matches[-1]` 改成 `matches[0]`，**必须变红**在 `test_reads_the_last_cache_line_not_the_first`。
把正则里的 `(?<!- )` 去掉，**必须变红**在 `test_per_type_breakdown_lines_are_not_mistaken_for_the_total`。
把 `measured_bytes_per_token` 的 `if not cache_bytes or not prompt_tokens` 删掉，**必须变红**在
除零那条。三次都确认变红后改回。

- [ ] **Step 6: 提交**

```bash
git add desk/budget/observe.py tests/test_budget_observe.py
git commit -m "feat(budget): 解析 mlx-lm 日志里的实际 KV 占用

实测每 token 字节 = 这一行的字节数 ÷ 本轮 prompt_tokens。dtype 是否量化、
mlx 怎么分页，都不必知道——除一下就是本机该模型的真值。

读不到一律 None：传感器坏了却沿用旧值，等于让预算建立在一个已经不成立的
观察上，而且没人看得出来。"
```

---

### Task 3: store.py —— 本机实测档案

**Files:**
- Create: `desk/budget/store.py`
- Test: `tests/test_budget_store.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Measurements.load(path: Path) -> Measurements`
  - `Measurements.model_bytes_per_token(key: str, weights_gb: float) -> int | None`
  - `Measurements.record_model(key, bytes_per_token, weights_gb, now) -> None`
  - `Measurements.media_peak(kind: str) -> int | None`
  - `Measurements.record_media(kind, peak_bytes, now) -> None`
  - `Measurements.record_overrun(key: str, now) -> None` 与 `Measurements.overrun_factor(key) -> float`
  - `Measurements.save(path: Path) -> None`

**背景（实现者必读）**：档案落在 data_root，与 `config.json` 同级。

**作废规则（R-budget-04）**：条目记录写入时的模型权重大小；读取时与调用方给的
`weights_gb` 比对，不符即视为不存在。同名模型重新量化过（4bit 换 8bit）之后，
每 token 开销完全不同，沿用旧数会让预算错一倍以上。比对用相对容差 1%，避免
浮点表示差异造成的误判。

**失败要被记住（R-budget-08）**：预算判定装得下而实际触发内存压力时记一次
`overrun`，该模型的预算此后乘以收紧系数。收紧是**永久**的且**单调**的——
只从成功里学习的系统会反复犯同一个错误。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_store.py
"""R-budget-04 / R-budget-08：本机实测档案，含作废规则与失败记忆。"""
import json
from desk.budget.store import Measurements

T0 = 1_757_000_000.0


def test_missing_file_loads_empty(tmp_path):
    m = Measurements.load(tmp_path / "measurements.json")
    assert m.model_bytes_per_token("k", 70.2) is None
    assert m.media_peak("video") is None


def test_recorded_value_round_trips(tmp_path):
    path = tmp_path / "measurements.json"
    m = Measurements.load(path)
    m.record_model("llama-70b", 327_680, 70.2, T0)
    m.save(path)
    assert Measurements.load(path).model_bytes_per_token("llama-70b", 70.2) == 327_680


def test_weights_mismatch_invalidates_the_entry(tmp_path):
    """同名模型换了量化，每 token 开销完全不同；沿用旧数会错一倍以上。"""
    m = Measurements.load(tmp_path / "m.json")
    m.record_model("qwen-27b", 262_144, 28.0, T0)
    assert m.model_bytes_per_token("qwen-27b", 15.0) is None      # 8bit 换 4bit
    assert m.model_bytes_per_token("qwen-27b", 28.0) == 262_144   # 同一份仍可用


def test_weights_within_one_percent_still_match(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    m.record_model("k", 100, 70.20, T0)
    assert m.model_bytes_per_token("k", 70.25) == 100


def test_media_peak_round_trips(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    m.record_media("video", 29_000_000_000, T0)
    assert m.media_peak("video") == 29_000_000_000
    assert m.media_peak("music") is None


def test_overrun_tightens_permanently_and_monotonically(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    assert m.overrun_factor("k") == 1.0
    m.record_overrun("k", T0)
    once = m.overrun_factor("k")
    assert once < 1.0
    m.record_overrun("k", T0 + 60)
    assert m.overrun_factor("k") < once        # 单调收紧
    assert m.overrun_factor("other") == 1.0    # 只收紧撞过的那一个


def test_overrun_survives_a_reload(tmp_path):
    """收紧是永久的：重启之后还得记着这台机器上这个组合爆过。"""
    path = tmp_path / "m.json"
    m = Measurements.load(path)
    m.record_overrun("k", T0)
    m.save(path)
    assert Measurements.load(path).overrun_factor("k") < 1.0


def test_corrupt_file_loads_empty_instead_of_raising(tmp_path):
    """档案损坏不能让台面起不来——丢掉重测即可，它本来就是可重建的。"""
    path = tmp_path / "m.json"
    path.write_text("{not json", encoding="utf-8")
    assert Measurements.load(path).media_peak("video") is None


def test_save_is_atomic(tmp_path):
    """写档案不得留下半截文件：用临时文件加 os.replace。"""
    path = tmp_path / "m.json"
    m = Measurements.load(path)
    m.record_media("music", 28_000_000_000, T0)
    m.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["media"]["music"]["peak_bytes"] == 28_000_000_000
    assert list(tmp_path.glob(".tmp-*")) == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'desk.budget.store'`

- [ ] **Step 3: 写最小实现**

```python
# desk/budget/store.py
"""本机实测档案：这台机器上量到过什么。

档案是可重建的——损坏就当空的，重新量一次即可，绝不能因此让台面起不来。

作废规则：条目记着写入时的权重大小。同名模型重新量化过之后每 token 开销完全
不同，沿用旧数会让预算错一倍以上，所以权重对不上就当没有这条。

收紧是永久且单调的：预算说装得下而实际爆了，这台机器上这个组合此后一直按更保守
的额度算。只从成功里学习的系统会反复犯同一个错误。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

WEIGHTS_TOLERANCE = 0.01     # 1%，吸收浮点表示差异，挡得住 4bit/8bit 之别
OVERRUN_STEP = 0.8           # 每爆一次，该组合的额度乘 0.8


class Measurements:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}

    @classmethod
    def load(cls, path: Path) -> "Measurements":
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-measurements-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def model_bytes_per_token(self, key: str, weights_gb: float) -> int | None:
        entry = self._data.get("models", {}).get(key)
        if not entry:
            return None
        recorded = entry.get("weights_gb")
        if not recorded or abs(recorded - weights_gb) > recorded * WEIGHTS_TOLERANCE:
            return None
        return entry.get("bytes_per_token")

    def record_model(self, key: str, bytes_per_token: int, weights_gb: float, now: float) -> None:
        self._data.setdefault("models", {})[key] = {
            "bytes_per_token": int(bytes_per_token),
            "weights_gb": float(weights_gb),
            "measured_at": now,
        }

    def media_peak(self, kind: str) -> int | None:
        return (self._data.get("media", {}).get(kind) or {}).get("peak_bytes")

    def record_media(self, kind: str, peak_bytes: int, now: float) -> None:
        self._data.setdefault("media", {})[kind] = {
            "peak_bytes": int(peak_bytes), "measured_at": now,
        }

    def record_overrun(self, key: str, now: float) -> None:
        entry = self._data.setdefault("overruns", {}).setdefault(key, {"count": 0})
        entry["count"] += 1
        entry["last_at"] = now

    def overrun_factor(self, key: str) -> float:
        count = (self._data.get("overruns", {}).get(key) or {}).get("count", 0)
        return OVERRUN_STEP ** count

    def to_dict(self) -> dict:
        return dict(self._data)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_store.py -q`
Expected: PASS（9 passed）

- [ ] **Step 5: 验证测试会咬**

把 `model_bytes_per_token` 里的权重比对整段删掉，**必须变红**在
`test_weights_mismatch_invalidates_the_entry`。把 `overrun_factor` 改成恒返回 `1.0`，
**必须变红**在两条 overrun 测试。把 `save` 改成直接 `path.write_text(...)`，
`test_save_is_atomic` 仍会通过——**这说明那条测试只验了结果没验原子性**，
补一条：`save` 期间制造 `json.dump` 抛异常，断言原文件内容未被破坏。改回后重跑。

- [ ] **Step 6: 提交**

```bash
git add desk/budget/store.py tests/test_budget_store.py
git commit -m "feat(budget): 本机实测档案，含作废规则与失败记忆

权重对不上就当没有这条：同名模型重新量化过之后每 token 开销完全不同，
沿用旧数会让预算错一倍以上。

预算说装得下而实际爆了，这台机器上这个组合此后永久按更保守的额度算——
只从成功里学习的系统会反复犯同一个错误。"
```

---

### Task 4: budget.py —— cost / fits / plan

**Files:**
- Create: `desk/budget/budget.py`
- Modify: `desk/budget/__init__.py`（导出）
- Test: `tests/test_budget_fits.py`

**Interfaces:**
- Consumes: Task 1 的 `per_token_bytes` / `declared_window`、Task 3 的 `Measurements`
- Produces:
  - `Workload(kind: str, key: str | None, bytes_needed: int, source: str)` —— frozen dataclass
  - `Verdict(ok: bool, needed_bytes: int, available_bytes: int, source: str, shortfall_bytes: int)`
  - `Plan(ok: bool, release: tuple[Workload, ...], verdict: Verdict)`
  - `fits(workloads, available_bytes) -> Verdict` —— 模块级纯函数
  - `plan(wanted, resident, available_bytes) -> Plan` —— 模块级纯函数

**背景（实现者必读）**：`fits` 与 `plan` 都是**纯函数**（一组 `Workload` 加一个可用字节数进，结果出），所以组合可以在单测里穷举，不必真装模型。这是把它们写成纯函数的全部理由，不要往里面塞 IO。

**为什么不是 `can_run(kind, alongside)`**：共存是集合问题。三件重活能否同时跑，不等于三个两两判断的合取；而且「最小让出」只有在集合上才算得出来——腾出谁取决于整组的组合。

**来源取最弱者（R-budget-10）**：`unavailable` > `predicted` > `measured` 的保守序。一组里只要有一件 `unavailable`，整组即 `unavailable`；只要有一件 `predicted`，整组即 `predicted`。不允许「两件实测加一件没量过」被当成实测依据放行。

**`unavailable` 走保守路径**：整组来源为 `unavailable` 时，`fits` 只在**单件**重活时返回 ok——这就是「未经本机实测不放宽」的落点，也正好是今天的互斥行为。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_fits.py
"""R-budget-07 / R-budget-10：共存是集合问题，来源取最弱者。"""
import itertools
import pytest
from desk.budget.budget import Workload, fits, plan

GIB = 1024 ** 3


def w(kind, bytes_gib, source="measured", key=None):
    return Workload(kind=kind, key=key, bytes_needed=int(bytes_gib * GIB), source=source)


def test_one_workload_that_fits_is_ok():
    assert fits([w("chat", 80)], 120 * GIB).ok


def test_one_workload_that_does_not_fit_reports_the_shortfall():
    v = fits([w("chat", 150)], 120 * GIB)
    assert not v.ok
    assert v.shortfall_bytes == 30 * GIB
    assert v.needed_bytes == 150 * GIB and v.available_bytes == 120 * GIB


def test_two_that_fit_together_are_ok():
    assert fits([w("chat", 80), w("video", 30)], 120 * GIB).ok


def test_two_that_each_fit_alone_but_not_together_are_refused():
    """这是两两判断答不了的那一类：各自都装得下，合起来装不下。"""
    assert fits([w("chat", 80)], 120 * GIB).ok
    assert fits([w("video", 80)], 120 * GIB).ok
    assert not fits([w("chat", 80), w("video", 80)], 120 * GIB).ok


def test_three_way_is_not_the_conjunction_of_pairs():
    """三件两两都能共存，三件一起却装不下——合取判断会错放。"""
    trio = [w("chat", 40), w("video", 40), w("music", 40)]
    for a, b in itertools.combinations(trio, 2):
        assert fits([a, b], 100 * GIB).ok
    assert not fits(trio, 100 * GIB).ok


def test_source_is_the_weakest_of_the_group():
    assert fits([w("chat", 10), w("video", 10)], 100 * GIB).source == "measured"
    assert fits([w("chat", 10), w("video", 10, "predicted")], 100 * GIB).source == "predicted"
    assert fits([w("chat", 10, "measured"), w("video", 10, "predicted"),
                 w("music", 10, "unavailable")], 100 * GIB).source == "unavailable"


def test_unavailable_source_refuses_coexistence_even_when_the_numbers_fit():
    """没量过就不放宽：数字上装得下，也不许两件并存。"""
    pair = [w("chat", 10, "unavailable"), w("video", 10)]
    assert not fits(pair, 500 * GIB).ok
    assert fits([w("chat", 10, "unavailable")], 500 * GIB).ok    # 单件照常


def test_empty_group_fits():
    assert fits([], 0).ok


def test_plan_releases_the_cheapest_set_that_makes_room():
    """最小让出：腾出够用的那些，不是全卸。"""
    resident = [w("chat", 80, key="llama"), w("music", 10, key="m3")]
    p = plan([w("video", 30)], resident, 120 * GIB)
    assert p.ok
    assert [r.key for r in p.release] == ["m3"]      # 卸掉 10 就够，不必动 80


def test_plan_releases_nothing_when_it_already_fits():
    p = plan([w("video", 10)], [w("chat", 80, key="llama")], 120 * GIB)
    assert p.ok and p.release == ()


def test_plan_reports_failure_when_even_full_eviction_is_not_enough():
    p = plan([w("video", 200)], [w("chat", 80, key="llama")], 120 * GIB)
    assert not p.ok
    assert p.verdict.shortfall_bytes > 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_fits.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'desk.budget.budget'`

- [ ] **Step 3: 写最小实现**

```python
# desk/budget/budget.py
"""合成额度与共存判定。

fits 与 plan 是纯函数：一组 Workload 加一个可用字节数进，结果出。所以组合可以在
单测里穷举，不必真装一个 70GB 的模型。不要往这两个函数里塞 IO。

共存是集合问题，不是两两判断：三件重活能否同时跑，不等于三个两两判断的合取；
「最小让出」也只有在集合上才算得出来——腾出谁取决于整组的组合。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

SOURCES = ("measured", "predicted", "unavailable")   # 由强到弱


@dataclass(frozen=True)
class Workload:
    kind: str
    key: str | None
    bytes_needed: int
    source: str


@dataclass(frozen=True)
class Verdict:
    ok: bool
    needed_bytes: int
    available_bytes: int
    source: str
    shortfall_bytes: int


@dataclass(frozen=True)
class Plan:
    ok: bool
    release: tuple[Workload, ...]
    verdict: Verdict


def weakest_source(workloads) -> str:
    """一组的依据取最弱者：两件实测加一件没量过，整组仍是没量过（R-budget-10）。"""
    return max((w.source for w in workloads), key=SOURCES.index, default="measured")


def fits(workloads, available_bytes: int) -> Verdict:
    """这一组重活能否共存。"""
    workloads = list(workloads)
    needed = sum(w.bytes_needed for w in workloads)
    source = weakest_source(workloads)
    ok = needed <= available_bytes
    # 未经本机实测不放宽：来源不可用时，只允许单件——这正是今天的互斥行为。
    if source == "unavailable" and len(workloads) > 1:
        ok = False
    return Verdict(
        ok=ok, needed_bytes=needed, available_bytes=available_bytes,
        source=source, shortfall_bytes=max(needed - available_bytes, 0),
    )


def plan(wanted, resident, available_bytes: int) -> Plan:
    """想跑 wanted，当前驻留 resident ⇒ 该让出哪些（最小让出）。

    枚举 resident 的子集，取「能装下且让出总量最小」的那个。重活至多三件，
    子集至多 8 个，穷举比任何启发式都更容易证明是对的。
    """
    resident = list(resident)
    wanted = list(wanted)
    best = None
    for size in range(len(resident) + 1):
        for combo in itertools.combinations(resident, size):
            freed = sum(w.bytes_needed for w in combo)
            keep = [w for w in resident if w not in combo]
            verdict = fits(list(wanted) + keep, available_bytes + freed)
            if verdict.ok:
                released = sum(w.bytes_needed for w in combo)
                if best is None or released < best[0]:
                    best = (released, combo, verdict)
        if best is not None:
            break        # 子集按大小递增枚举，先找到的就是让出件数最少的
    if best is None:
        return Plan(ok=False, release=(), verdict=fits(wanted + resident, available_bytes))
    _, combo, verdict = best
    return Plan(ok=True, release=tuple(combo), verdict=verdict)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_fits.py -q`
Expected: PASS（11 passed）

- [ ] **Step 5: 验证测试会咬**

把 `weakest_source` 改成恒返回 `"measured"`，**必须变红**在
`test_source_is_the_weakest_of_the_group` 与 `test_unavailable_source_refuses_coexistence...`。
把 `fits` 里 `unavailable` 那两行删掉，**必须变红**在后者。
把 `plan` 改成「装不下就让出全部 resident」，**必须变红**在
`test_plan_releases_the_cheapest_set_that_makes_room`。三次都确认变红后改回。

- [ ] **Step 6: 导出公开名字**

```python
# desk/budget/__init__.py
"""budget：回答「这台机器此刻还装得下什么」。"""
from .budget import Plan, Verdict, Workload, fits, plan, weakest_source   # noqa: F401
from .estimate import declared_window, per_token_bytes                     # noqa: F401
from .observe import measured_bytes_per_token, parse_cache_line            # noqa: F401
from .store import Measurements                                            # noqa: F401
```

- [ ] **Step 7: 跑全部 budget 测试**

Run: `python3 -m pytest tests/test_budget_*.py -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add desk/budget/budget.py desk/budget/__init__.py tests/test_budget_fits.py
git commit -m "feat(budget): cost/fits/plan——共存是集合问题

三件重活能否同时跑，不等于三个两两判断的合取；测试里有一条正是这个反例：
两两都能共存，三件一起装不下。

最小让出用子集穷举而不是启发式：重活至多三件，子集至多 8 个，穷举比任何
启发式都更容易证明是对的。

一组的依据来源取最弱者，且来源不可用时只许单件——这就是「未经本机实测不放宽」
的落点，也正好是今天的互斥行为。"
```

---

### Task 5: Budget 门面 —— 接上真实读数与 mlx-lm 限额参数

**Files:**
- Modify: `desk/budget/budget.py`（加 `Budget` 类）
- Test: `tests/test_budget_facade.py`

**Interfaces:**
- Consumes: Task 1–4 全部
- Produces:
  - `ChatBudget(token_limit: int, compact_at: int, source: str, window: int | None)`
  - `Budget(measurements, memory_reader, media_estimate, now)` 构造
  - `Budget.cost(kind, *, key=None, params=None, config=None, weights_gb=None) -> Workload`
  - `Budget.for_chat(key, config, weights_gb) -> ChatBudget`
  - `Budget.launch_args(key, config, weights_gb) -> list[str]`
  - `Budget.record_turn(key, log_text, prompt_tokens, weights_gb) -> None`
  - `Budget.snapshot() -> dict`

**背景（实现者必读）**：`Budget` 是门面，负责把 IO（内存快照、日志文本、档案）接到纯函数上。构造时注入依赖，测试里全部用假实现——不起服务、不装模型。

`compact_at` 是压缩触发点，取 `token_limit` 的 75%。这个比例是本计划唯一的自由参数，写成模块常量 `COMPACT_FRACTION = 0.75` 并在 docstring 注明它是可调的策略值，不是推导出来的。

`launch_args` 产出 `["--prompt-cache-bytes", "<字节>", "--prompt-cache-size", "<条数>"]`。
**注意参数名**：mlx-lm 里是 `--prompt-cache-size`（缓存条数，默认 10），不是 `--num-prompt-caches`。
条数直接取 1：台面一次只服务一个会话，默认的 10 份会让 KV 占用凭空翻十倍。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_facade.py
"""R-budget-01/03/05：门面把 IO 接到纯函数上，每个数带来源。"""
from desk.budget.budget import Budget, ChatBudget
from desk.budget.store import Measurements

GIB = 1024 ** 3
LLAMA = {"max_position_embeddings": 131072, "num_hidden_layers": 80,
         "num_key_value_heads": 8, "head_dim": 128}          # 327680 B/token
MYSTERY = {"max_position_embeddings": 4096}                   # 算不出每 token 字节


class FakeMemory:
    def __init__(self, available_gib): self.available = available_gib * GIB
    def snapshot(self):
        class S:
            available_bytes = self.available
            total_bytes = 186 * GIB
            pressure = "normal"
        return S()


def make(available_gib=116, measurements=None):
    return Budget(measurements=measurements or Measurements(),
                  memory_reader=FakeMemory(available_gib),
                  media_estimate=lambda kind, params: 27 * GIB,
                  now=lambda: 1_757_000_000.0)


def test_cold_start_budget_is_predicted():
    b = make().for_chat("llama", LLAMA, weights_gb=70.2)
    assert b.source == "predicted"
    assert b.window == 131072


def test_declared_window_caps_the_budget():
    """内存够 100 万 token，窗口只有 131072——窗口封顶。"""
    b = make(available_gib=100_000).for_chat("llama", LLAMA, weights_gb=70.2)
    assert b.token_limit == 131072


def test_memory_caps_the_budget_when_it_is_the_tighter_one():
    b = make(available_gib=8).for_chat("llama", LLAMA, weights_gb=0.1)
    assert b.token_limit < 131072


def test_compact_threshold_is_below_the_limit():
    b = make().for_chat("llama", LLAMA, weights_gb=70.2)
    assert 0 < b.compact_at < b.token_limit


def test_unknown_per_token_cost_falls_back_to_window_and_says_so():
    """算不出每 token 字节时只用声明窗口，并标 unavailable——不套默认值。"""
    b = make().for_chat("mystery", MYSTERY, weights_gb=1.0)
    assert b.token_limit == 4096
    assert b.source == "unavailable"


def test_recorded_turn_switches_the_source_to_measured():
    m = Measurements()
    b = make(measurements=m)
    b.record_turn("llama", "Prompt Cache: 1 sequences, 12.40 GB", 40_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) == 310_000
    assert make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).source == "measured"


def test_unparsable_log_records_nothing_and_stays_predicted():
    """传感器坏了就保持 predicted，不许把上一次的数当成这一次的实测。"""
    m = Measurements()
    make(measurements=m).record_turn("llama", "格式变了", 40_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) is None


def test_launch_args_use_the_real_mlx_flag_names():
    args = make().launch_args("llama", LLAMA, weights_gb=70.2)
    assert "--prompt-cache-bytes" in args
    assert "--prompt-cache-size" in args
    assert args[args.index("--prompt-cache-size") + 1] == "1"   # 默认 10 份会让占用翻十倍


def test_launch_args_are_empty_when_the_cost_is_unknown():
    """算不出来就不传限额——传一个猜出来的上限比不传更危险。"""
    assert make().launch_args("mystery", MYSTERY, weights_gb=1.0) == []


def test_overrun_tightens_the_next_budget():
    m = Measurements()
    before = make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).token_limit
    m.record_overrun("llama", 1_757_000_000.0)
    assert make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).token_limit < before


def test_snapshot_labels_every_number_with_its_source():
    snap = make().snapshot()
    assert set(snap) >= {"available_bytes", "pressure", "media"}
    assert snap["media"]["video"]["source"] in ("predicted", "measured", "unavailable")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_facade.py -q`
Expected: FAIL — `ImportError: cannot import name 'Budget'`

- [ ] **Step 3: 写最小实现**

在 `desk/budget/budget.py` 末尾追加：

```python
COMPACT_FRACTION = 0.75    # 策略值，不是推导值：额度用到这个比例就压缩
SAFETY_FRACTION = 0.9      # 可用内存里留 10% 给系统与其它进程
CACHE_SLOTS = 1            # mlx-lm 默认保 10 份 KV 缓存；台面一次只服务一个会话


@dataclass(frozen=True)
class ChatBudget:
    token_limit: int
    compact_at: int
    source: str
    window: int | None


class Budget:
    """门面：把 IO（内存快照、日志文本、实测档案）接到纯函数上。

    依赖全部构造注入，所以测试不起服务、不装模型。
    """

    def __init__(self, measurements, memory_reader, media_estimate, now) -> None:
        self._m = measurements
        self._memory = memory_reader
        self._media_estimate = media_estimate
        self._now = now

    # ---- 单件开销 ----------------------------------------------------
    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None) -> Workload:
        if kind in ("video", "music"):
            measured = self._m.media_peak(kind)
            need = measured if measured else self._media_estimate(kind, params or {})
            return Workload(kind, key, int(need), "measured" if measured else "predicted")
        chat = self.for_chat(key, config or {}, weights_gb or 0.0)
        per_token = self._per_token(key, config or {}, weights_gb or 0.0)[0] or 0
        weights = int((weights_gb or 0.0) * GIB_F)
        return Workload(kind, key, weights + chat.token_limit * per_token, chat.source)

    # ---- 聊天额度 ----------------------------------------------------
    def _per_token(self, key, config, weights_gb):
        """(每 token 字节, 来源)。实测优先，否则预测，都没有就 unavailable。"""
        measured = self._m.model_bytes_per_token(key, weights_gb) if key else None
        if measured:
            return measured, "measured"
        predicted = per_token_bytes(config)
        return (predicted, "predicted") if predicted else (None, "unavailable")

    def for_chat(self, key, config, weights_gb) -> ChatBudget:
        window = declared_window(config)
        per_token, source = self._per_token(key, config, weights_gb)
        if per_token is None:
            limit = window or 0
            return ChatBudget(limit, int(limit * COMPACT_FRACTION), "unavailable", window)
        available = self._memory.snapshot().available_bytes
        usable = int(available * SAFETY_FRACTION * self._m.overrun_factor(key or ""))
        by_memory = max(usable // per_token, 0)
        limit = min(by_memory, window) if window else by_memory
        return ChatBudget(int(limit), int(limit * COMPACT_FRACTION), source, window)

    # ---- mlx-lm 限额参数 ---------------------------------------------
    def launch_args(self, key, config, weights_gb) -> list[str]:
        per_token, source = self._per_token(key, config, weights_gb)
        if per_token is None:
            return []       # 算不出来就不传：一个猜出来的上限比不传更危险
        chat = self.for_chat(key, config, weights_gb)
        return ["--prompt-cache-bytes", str(chat.token_limit * per_token),
                "--prompt-cache-size", str(CACHE_SLOTS)]

    # ---- 自校准 ------------------------------------------------------
    def record_turn(self, key, log_text, prompt_tokens, weights_gb) -> None:
        """一轮答完，把这台机器上的真值记下来（R-budget-04）。"""
        measured = measured_bytes_per_token(parse_cache_line(log_text), prompt_tokens)
        if measured:
            self._m.record_model(key, measured, weights_gb, self._now())

    def snapshot(self) -> dict:
        snap = self._memory.snapshot()
        media = {}
        for kind in ("video", "music"):
            peak = self._m.media_peak(kind)
            media[kind] = {"peak_bytes": peak, "source": "measured" if peak else "predicted"}
        return {"available_bytes": snap.available_bytes,
                "total_bytes": snap.total_bytes,
                "pressure": snap.pressure,
                "media": media}
```

在文件顶部补上需要的导入与常量：

```python
from .estimate import declared_window, per_token_bytes
from .observe import measured_bytes_per_token, parse_cache_line

GIB_F = float(1024 ** 3)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_facade.py -q`
Expected: PASS（11 passed）

- [ ] **Step 5: 验证测试会咬**

把 `for_chat` 里的 `min(by_memory, window)` 改成只用 `by_memory`，**必须变红**在
`test_declared_window_caps_the_budget`。把 `launch_args` 的 `return []` 改成
返回一个写死的上限，**必须变红**在 `test_launch_args_are_empty_when_the_cost_is_unknown`。
把 `record_turn` 的 `if measured` 去掉（让 `None` 也写进档案），**必须变红**在
`test_unparsable_log_records_nothing_and_stays_predicted`。把 `overrun_factor` 那一项
从 `usable` 里去掉，**必须变红**在 `test_overrun_tightens_the_next_budget`。四次都确认后改回。

- [ ] **Step 6: 导出 Budget 与 ChatBudget**

在 `desk/budget/__init__.py` 的第一行导入里追加 `Budget, ChatBudget`。

- [ ] **Step 7: 跑全部 budget 测试**

Run: `python3 -m pytest tests/test_budget_*.py -q`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add desk/budget/budget.py desk/budget/__init__.py tests/test_budget_facade.py
git commit -m "feat(budget): Budget 门面——接上真实读数与 mlx-lm 限额参数

参数名是 --prompt-cache-size 不是 --num-prompt-caches（翻了 mlx_lm 的 argparse
才确认）；条数传 1，默认的 10 份会让 KV 占用凭空翻十倍。

算不出每 token 字节时不传限额：传一个猜出来的上限比不传更危险。
传感器读不到就保持 predicted，不许把上一次的数当成这一次的实测。"
```

---

### Task 6: 接进 llm —— 启动传限额，每轮记实测

**Files:**
- Modify: `desk/llm/backend.py`（`spawn` 接受额外 argv）
- Modify: `desk/llm/service.py`（加载时传 `launch_args`；`chat_stream` 完成后 `record_turn`）
- Modify: `desk/runtime.py`（装配 `Budget`）
- Test: `tests/test_llm_budget_wiring.py`

**Interfaces:**
- Consumes: `Budget.launch_args(key, config, weights_gb)`、`Budget.record_turn(key, log_text, prompt_tokens, weights_gb)`
- Produces: 无新公开接口；`MlxLmBackend.spawn` 增加关键字参数 `extra_args: list[str] | None = None`

**背景（实现者必读）**：`MlxLmBackend.spawn`（`desk/llm/backend.py:47`）现在拼死的 argv 是
`[python, "-s", "-m", "mlx_lm", "server", "--model", ..., "--host", "127.0.0.1", "--port", ...]`。
额外参数追加在末尾。

自校准的两个读数分别来自：mlx-lm 的日志文件（路径见 `LlmService._log_path(roots)`，
即 `roots.logs_dir / "mlx-lm.log"`）与 `done` 事件里的 `usage.prompt_tokens`
（`desk/llm/service.py` 的流式路径，见 `usage = chunk["usage"]`）。

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_llm_budget_wiring.py
"""R-budget-03/04：起 mlx-lm 时传限额，每轮答完记实测。"""
from desk.llm.backend import MlxLmBackend


class RecordingPopen:
    calls = []
    def __init__(self, argv, **kwargs):
        RecordingPopen.calls.append(argv)


def test_spawn_appends_extra_args(monkeypatch, tmp_path):
    import subprocess
    RecordingPopen.calls.clear()
    monkeypatch.setattr(subprocess, "Popen", RecordingPopen)
    MlxLmBackend().spawn(tmp_path / "py", tmp_path / "model", 8767, tmp_path / "log",
                         extra_args=["--prompt-cache-bytes", "123", "--prompt-cache-size", "1"])
    argv = RecordingPopen.calls[-1]
    assert argv[-4:] == ["--prompt-cache-bytes", "123", "--prompt-cache-size", "1"]
    assert "--model" in argv and "--port" in argv     # 原有参数没被挤掉


def test_spawn_without_extra_args_is_unchanged(monkeypatch, tmp_path):
    import subprocess
    RecordingPopen.calls.clear()
    monkeypatch.setattr(subprocess, "Popen", RecordingPopen)
    MlxLmBackend().spawn(tmp_path / "py", tmp_path / "model", 8767, tmp_path / "log")
    assert "--prompt-cache-bytes" not in RecordingPopen.calls[-1]
```

对 `service.py` 的接线，用现有的假后端（参考 `tests/llm/` 下已有的测试夹具）写一条：
加载某模型时 `spawn` 收到的 `extra_args` 与 `Budget.launch_args` 的返回一致；
一轮流式结束后 `Budget.record_turn` 被调用一次，且 `prompt_tokens` 取自 `done` 事件。
**具体夹具名以 `tests/llm/` 现有文件为准**，实现者先读那里的既有写法再照着搭，
不要新造一套假后端。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_llm_budget_wiring.py -q`
Expected: FAIL — `spawn() got an unexpected keyword argument 'extra_args'`

- [ ] **Step 3: 写最小实现**

`desk/llm/backend.py`：`spawn` 与协议声明都加 `extra_args`：

```python
    def spawn(
        self, python: Path, model_path: Path, port: int, log_path: Path,
        extra_args: list[str] | None = None,
    ) -> BackendProcess:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        argv = [
            str(python), "-s", "-m", "mlx_lm", "server",
            "--model", str(model_path), "--host", "127.0.0.1",
            "--port", str(port),
            *(extra_args or []),
        ]
        with log_path.open("ab") as log_file:
            return subprocess.Popen(argv, stdout=log_file, stderr=log_file)
```

`desk/llm/service.py`：`_load_worker` 调 `spawn` 时传
`extra_args=self._budget.launch_args(entry.key, config, entry.gb)`（`config` 由
模型目录的 `config.json` 读入）；流式路径拿到 `usage` 之后调
`self._budget.record_turn(entry.key, self._backend.log_tail(log_path, 200), usage["prompt_tokens"], entry.gb)`。
`LlmService.__init__` 增加 `budget` 参数；`desk/runtime.py` 装配时构造并传入。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_llm_budget_wiring.py tests/llm -q`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

把 `argv` 里的 `*(extra_args or [])` 删掉，**必须变红**在 `test_spawn_appends_extra_args`。
把 `record_turn` 的调用注释掉，接线那条测试**必须变红**。确认后改回。

- [ ] **Step 6: 跑受影响的既有测试**

Run: `python3 -m pytest tests/test_production_runtime.py tests/llm tests/test_budget_*.py -q`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add desk/llm/backend.py desk/llm/service.py desk/runtime.py tests/test_llm_budget_wiring.py
git commit -m "feat(llm): 起 mlx-lm 时传限额，每轮答完记实测

不传 --prompt-cache-bytes 等于无上限，这是当前的缺陷。

自校准的两个读数：日志里的 Prompt Cache 行、done 事件里的 prompt_tokens。
除一下就是这台机器上这个模型的真值，dtype 和分页都不必知道。"
```

---

### Task 7: arbiter 按预算判定 —— 持有者由单个变一组

**Files:**
- Modify: `desk/arbiter/state.py`（`plan_acquire` 接受持有者集合）
- Modify: `desk/arbiter/core.py`（`can_start_heavy` 转调 `budget.fits` / `budget.plan`）
- Modify: `desk/media/service.py`（标定值改由 `Budget` 提供；作业期采样峰值）
- Test: `tests/test_arbiter_state.py`（扩充）、`tests/test_arbiter_core.py`（扩充）、`tests/test_budget_media_calibration.py`（新建）

**Interfaces:**
- Consumes: `fits(workloads, available_bytes) -> Verdict`、`plan(wanted, resident, available_bytes) -> Plan`、`Budget.cost(kind, *, key, params, config, weights_gb)`
- Produces:
  - `plan_acquire(holders: tuple[Holder, ...], kind: str, verdict) -> Decision`
  - `Measurements.record_media(kind, peak_bytes, now)` 由媒体作业结束时调用

**背景（实现者必读）**：这是本计划风险最高的一步，因为它改的是仓库里"风险最高的一条"
（`arbiter` 的 spec 原话）。三件事必须同时成立才算做完：

1. `plan_acquire` 的入参从 `Holder | None` 变成 `tuple[Holder, ...]`。现有的
   `transition_in_progress`（有人正在获取时拒绝）与 `unknown_kind` 两条分支**保持不变**。
2. 判定结果由传入的 `verdict` 决定，而不是由 `holder.kind in MEDIA_KINDS` 这类硬编码。
   `verdict.ok` 为假时，`reason_code` 用 `insufficient_budget`，`reason_message` 必须带
   需要多少、现有多少、依据来源三个数。
3. **`media/service.py` 现有的 `insufficient_memory` 警告路径不能退化**：它今天能告诉
   用户"生成约需 27.0 GiB，当前可用 X GiB"，改完之后必须仍能，且数字来源要跟着标。

媒体标定：作业启动前记 `available_bytes` 基线，运行中周期采样（复用媒体作业已有的
轮询点，不要新起线程），结束时 `基线 − 最低点` 即本机实测峰值，调 `record_media`。
**首次运行没有实测值时，`cost()` 返回 `predicted`，于是 `fits` 对多件重活判否**——
这就是"未经本机实测不放宽"。

- [ ] **Step 1: 写失败的测试（状态机）**

```python
# 追加到 tests/test_arbiter_state.py
"""R-arbiter-01 改写：能否并存由预算判定，不由持有者种类硬编码。"""
from desk.arbiter.state import Holder, plan_acquire
from desk.budget.budget import Verdict

OK = Verdict(True, 0, 0, "measured", 0)
NO = Verdict(False, 100, 80, "measured", 20)
UNKNOWN = Verdict(False, 100, 80, "unavailable", 20)


def holder(kind, token="t"):
    return Holder(kind=kind, label=kind, token=token, since=0.0, phase="held")


def test_empty_holders_grants():
    assert plan_acquire((), "llm", OK).action == "grant"


def test_budget_ok_grants_even_while_media_runs():
    """这正是被改掉的那条铁律：媒体在跑，预算够，聊天照样装得下。"""
    assert plan_acquire((holder("video"),), "llm", OK).action == "grant"


def test_budget_short_refuses_with_the_numbers():
    d = plan_acquire((holder("video"),), "llm", NO)
    assert d.action == "refuse"
    assert d.reason_code == "insufficient_budget"
    assert "80" in d.reason_message and "100" in d.reason_message


def test_reason_message_names_the_source():
    assert "unavailable" in plan_acquire((holder("video"),), "llm", UNKNOWN).reason_message


def test_transition_in_progress_still_refuses():
    """既有分支不能在重构里丢掉。"""
    acquiring = Holder(kind="video", label="v", token="t", since=0.0, phase="acquiring")
    assert plan_acquire((acquiring,), "llm", OK).reason_code == "transition_in_progress"


def test_unknown_kind_still_refuses():
    assert plan_acquire((), "banana", OK).reason_code == "unknown_kind"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_arbiter_state.py -q`
Expected: FAIL — `plan_acquire() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: 改写状态机**

```python
def plan_acquire(holders, kind: str, verdict) -> Decision:
    """能否再开一件重活：由预算判定，不由持有者种类硬编码（R-arbiter-01 改写）。

    互斥不再是公理，而是「预算不够时的结果」。种类相关的硬编码分支全部删除；
    留下的两条与容量无关：正在转换中、种类不认识。
    """
    if kind not in KINDS:
        return Decision("refuse", "unknown_kind", f"unknown heavy kind: {kind!r}")
    if any(h.phase == PHASE_ACQUIRING for h in holders):
        return Decision(
            "refuse", "transition_in_progress",
            "a heavy-work transition is in progress; retry shortly",
        )
    if verdict.ok:
        return Decision("grant")
    return Decision(
        "refuse", "insufficient_budget",
        f"需要 {verdict.needed_bytes} 字节，可用 {verdict.available_bytes} 字节"
        f"（依据：{verdict.source}）",
    )
```

`evict_then_grant` 这个动作由 `core.py` 依 `budget.plan()` 的结果发起，不再由状态机产生——
让出哪些是集合计算的结果，状态机看不到内存数字。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_arbiter_state.py -q`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

把 `if verdict.ok: return Decision("grant")` 改成 `if not holders:`（退回按持有者判定），
**必须变红**在 `test_budget_ok_grants_even_while_media_runs`。把 `reason_message` 里的数字
去掉，**必须变红**在 `test_budget_short_refuses_with_the_numbers`。确认后改回。

- [ ] **Step 6: core.py 接上 budget**

`Arbiter.__init__` 增加 `budget` 参数。`can_start_heavy(kind, params=None, key=None)` 改为：
用 `budget.cost(...)` 算本次的 `Workload`，用当前持有者集合算 `resident`，
调 `fits`；不 ok 时调 `plan` 求最小让出，若 `plan.ok` 则返回
`{"ok": True, "release": [...], ...}` 供调用方先让出再获取。
保留返回结构里的 `memory_warning` 键，让 `media/service.py` 的既有文案路径不退化。

为它写测试，断言：媒体在跑且预算够时 `can_start_heavy("llm")` 返回 ok；
预算不够但让出音乐够用时，返回的 `release` 只含音乐那一件而非全部。

- [ ] **Step 7: 媒体标定采样**

`desk/media/service.py`：作业启动前取 `available_bytes` 基线并存入作业状态；
复用既有的作业轮询点采样最低值；作业结束（成功或失败都算）时用
`基线 − 最低点` 调 `Measurements.record_media(kind, peak, now)` 并保存档案。

`tests/test_budget_media_calibration.py` 用假内存读数走一遍：基线 116 GiB、
运行中最低 89 GiB ⇒ 记录峰值 27 GiB；断言记录之后 `Budget.cost("video", ...)`
的 `source` 由 `predicted` 变为 `measured`。再断言**首次运行（无实测）时
`fits` 对「聊天 + 视频」判否**——这是"未经本机实测不放宽"的落点。

- [ ] **Step 8: 跑全部受影响的测试**

Run: `python3 -m pytest tests/test_arbiter_*.py tests/test_media_*.py tests/test_budget_*.py tests/test_production_runtime.py -q`
Expected: PASS

- [ ] **Step 9: 跑全量，确认没有连带损伤**

Run: `python3 -m pytest tests -q`
Expected: PASS（基线：本计划开始前是 807 passed）

- [ ] **Step 10: 提交**

```bash
git add desk/arbiter/ desk/media/service.py tests/
git commit -m "feat(arbiter): 按预算判定共存，互斥降为预算不够时的结果

plan_acquire 的入参从单个持有者变成一组，判定结果由 budget 的 Verdict 给出，
种类相关的硬编码分支全部删除；留下的两条与容量无关：正在转换中、种类不认识。

让出哪些不再由状态机产生——那是集合计算的结果，状态机看不到内存数字。

媒体标定改为本机采样：作业期记基线与最低点，差值即实测峰值。没量过之前
cost() 报 predicted，于是 fits 对多件重活判否——这就是「未经本机实测不放宽」。"
```

---

### Task 8: 状态栏与诊断暴露来源

**Files:**
- Modify: `desk/runtime.py`（`/api/budget` 路由）
- Modify: `desk/static/js/widgets/statusbar.js`（显示额度与来源）
- Test: `tests/test_budget_routes.py`、`tests/js/budget_status.test.js`

**Interfaces:**
- Consumes: `Budget.snapshot()`、`Budget.for_chat(...)`
- Produces: `GET /api/budget` 返回 `{"chat": {...}, "media": {...}, "available_bytes": N, "pressure": "..."}`

**背景（实现者必读）**：R-budget-01 要求每个数字带来源，且**在台面状态对象与诊断输出中可见**。
这不是装饰：整个方案立身于"实测修正预测"，界面若分不出哪个数是猜的、哪个是量的，
预测错了永远无人察觉。

文案（中文，与仓库现有风格一致）：
- `measured` → 「已实测」
- `predicted` → 「估算」
- `unavailable` → 「算不出」

- [ ] **Step 1: 写失败的测试**

```python
# tests/test_budget_routes.py
"""R-budget-01：每个数字的来源必须出现在 API 里。"""


def test_budget_route_reports_source_for_every_number(client):
    body = client.get("/api/budget").json()
    assert body["chat"]["source"] in ("measured", "predicted", "unavailable")
    assert body["media"]["video"]["source"] in ("measured", "predicted", "unavailable")
    assert isinstance(body["available_bytes"], int)
```

夹具 `client` 用 `tests/http_helpers.py` 里的既有写法，**先读那个文件再照着搭**。

```js
// tests/js/budget_status.test.js
import { budgetLabel } from "../../desk/static/js/pure/budget_label.js";

test("每种来源都有中文标签，且估算与实测分得开", () => {
  assert.equal(budgetLabel("measured"), "已实测");
  assert.equal(budgetLabel("predicted"), "估算");
  assert.equal(budgetLabel("unavailable"), "算不出");
  assert.notEqual(budgetLabel("predicted"), budgetLabel("measured"));
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_budget_routes.py -q && node --test tests/js/budget_status.test.js`
Expected: 两个都 FAIL

- [ ] **Step 3: 写最小实现**

新建 `desk/static/js/pure/budget_label.js`（纯函数，与仓库既有 `pure/` 风格一致）：

```js
/** 来源标签：估算和实测必须一眼分得开，否则预测错了没人看得出来。 */
const LABELS = { measured: "已实测", predicted: "估算", unavailable: "算不出" };

export function budgetLabel(source) {
  return LABELS[source] ?? "未知";
}
```

`desk/runtime.py` 加一行路由：
`("GET", "/api/budget", lambda _req: Response(200, budget.snapshot_with_chat()))`
（`snapshot_with_chat` 在 `Budget` 上实现，把 `snapshot()` 与当前驻留模型的
`for_chat()` 合成一个 dict；没有驻留模型时 `chat` 为 `{"source": "unavailable"}`）。

状态栏显示：`已用 X / 总 Y` 之后追加 `· 对话额度 N 字（已实测）`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_budget_routes.py -q && node --test tests/js/budget_status.test.js`
Expected: 两个都 PASS

- [ ] **Step 5: 验证测试会咬**

把 `budgetLabel` 改成恒返回 `"已实测"`，**必须变红**。把路由返回里的 `source` 键删掉，
**必须变红**。确认后改回。

- [ ] **Step 6: 跑全量**

Run: `python3 -m pytest tests -q && node --test "tests/js/**/*.test.js"`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add desk/runtime.py desk/static/js/pure/budget_label.js desk/static/js/widgets/statusbar.js tests/
git commit -m "feat(budget): 状态栏与 /api/budget 暴露每个数字的来源

估算和实测必须一眼分得开。整个方案立身于「实测修正预测」，界面若分不出
哪个数是猜的、哪个是量的，预测错了永远无人察觉。"
```

---

## Self-Review

**1. Spec coverage**

| 需求 | 落在 |
|---|---|
| R-budget-01 每个额度带来源 | Task 4（`weakest_source`）、Task 5（`ChatBudget.source`）、Task 8（API 与状态栏） |
| R-budget-02 窗口读取顺序 | Task 1 |
| R-budget-03 冷启动额度与 mlx-lm 限额参数 | Task 5（`launch_args`）、Task 6（接线） |
| R-budget-04 自校准 | Task 2（解析与相除）、Task 3（档案与作废规则）、Task 5（`record_turn`）、Task 6（接线） |
| R-budget-05 软硬两个生效点 | Task 5（`for_chat` 立即用实测）、Task 6（`launch_args` 仅加载时传） |
| R-budget-06 媒体按参数估算 + 本机标定 | Task 7 Step 7 |
| R-budget-07 `fits(workloads)` 与带数字的拒绝 | Task 4、Task 7 |
| R-budget-08 失败要被记住 | Task 3（`record_overrun`）、Task 5（`overrun_factor` 进额度） |
| R-budget-09 压力升高的处置顺序 | **本计划不覆盖，留给压缩那个计划** —— 见下 |
| R-budget-10 来源取最弱者 | Task 4 |
| R-budget-11 MLA 与缺 head_dim 一律算不出 | Task 1 |

**R-budget-09 本计划不覆盖，这是有意的。** 原写法「压力升高时令 mlx-lm trim」
已核实做不到：mlx-lm 只有 `/v1/completions`、`/v1/chat/completions`、
`/chat/completions`、`/v1/models`、`/health` 五个路由，没有管理端点；`trim_to()`
只在它自己的请求循环里按 `--prompt-cache-bytes` 调用，运行时改不了。spec 已改写成
「收紧对话额度并立即压缩 → 拒绝新的重活 → 才是卸模型或杀作业」，其中第一步依赖
压缩能力，属于第二个计划；第二步由 Task 7 的 `fits` 判否自然覆盖；第三步是既有行为。
所以本计划把 ① 留给压缩计划，不在这里硬塞一个做不到的实现。

**2. Placeholder scan**

Task 6 Step 1 与 Task 8 Step 1 出现了"具体夹具名以现有文件为准，先读再照着搭"。
这是**有意的**：仓库已有成套的假后端与 HTTP 夹具，凭空造一套新的会与既有测试分叉。
但它确实不满足"每步都给出可直接执行的内容"，实现者需要先读 `tests/llm/` 与
`tests/http_helpers.py`。已在对应步骤里点名了要读哪个文件。

Task 1 Step 6 的 fixture 抽取脚本未给出完整代码，只给了约束（只读模型目录）。
glm 的 `head_dim` 期望值（375 KB/token）来自 47 × 20 × 102，其中 102 不是整数除法的
自然结果，实现者需按其 config 实际字段校正。**这是一个已知的待核值**。

**3. Type consistency**

- `Workload` / `Verdict` / `Plan` / `ChatBudget` 四个 dataclass 在 Task 4、5 定义，
  Task 7 消费，字段名一致。
- `fits(workloads, available_bytes)` 与 `plan(wanted, resident, available_bytes)`
  在 Task 4 定义，Task 7 按同一签名调用。
- `Measurements` 的七个方法在 Task 3 定义，Task 5、7 按同名调用。
- `spawn(..., extra_args=None)` 在 Task 6 定义，无其它调用方。
- `Budget.cost(kind, *, key, params, config, weights_gb)` 在 Task 5 定义，Task 7 消费。

## 写计划时已核实的三项

1. **R-budget-09 的可行性**——已核实**做不到**：mlx-lm 无管理端点，限额是命令行参数，
   运行时改不了。spec 已改写，本计划不覆盖（理由见上）。
2. **glm-4.7-flash 的 `head_dim`**——已核实**不存在**：它是 MLA 架构
   （`kv_lora_rank: 512`、`qk_nope_head_dim: 192`、`v_head_dim: 256`）。
   初稿里的 375 KB/token 是用 `2048 // 20 = 102` 凑出来的假数，实际约 53 KB。
   Task 1 已加 MLA 检测与对应测试，fixture 期望改为 `(202752, None)`。
3. **媒体作业的轮询点**——`desk/media/service.py:147` 起 `_worker` 线程跑作业，
   `:193` 与 `:208` 是收尾等待循环，**不是作业期的周期采样点**。
   Task 7 Step 7 的实现者需在 `_worker` 内加一个采样循环（沿用 `time.sleep` 的写法，
   采样间隔 1 秒即可——峰值出现在文本编码阶段，持续数十秒，1 秒足够捕捉），
   而不是复用收尾循环。

## 实现前仍需注意

- Task 6 Step 1 与 Task 8 Step 1 要求先读 `tests/llm/` 与 `tests/http_helpers.py`
  的既有夹具再照着搭，不要新造一套——这是**有意**留给实现者的，因为凭空造会与既有测试分叉。
