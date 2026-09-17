# 模块设计：budget（资源预算与上下文管理）

**日期** 2026-09-17
**对应 spec** `2026-09-17-budget-spec.md`
**覆盖需求** R-budget-01 … R-budget-10、R-context-01 … R-context-05，
并改写 R-arbiter-01 / 04 / 05 / 07

---

## 起因

用户报「生成时画面不动」之后追问「越聊越长怎么办」。查证结果：

- `wireMessages`（`desk/static/js/pure/chat_stream.js`）每轮把会话**全部消息原样**发上去，
  只过滤掉「中断且无内容」的助手消息。
- 服务端 `_upstream_payload`（`desk/llm/service.py:404`）直接转发 `request["messages"]`，
  只补 `max_tokens`——那是**输出**上限，与上下文无关。
- `desk/library/sessions.py` 没有任何长度限制。
- 全仓库没有一处读过模型的上下文窗口。

也就是说：**上下文管理为零**。

用户的判断是：本地模型产品的核心价值就是资源管理，这件事应当立成需求推导，
而不是作为聊天功能的一个参数。据此本设计覆盖两件事——资源预算子系统，
以及它的第一个消费者上下文压缩。

## 为什么不是一个公式

初版方案想从 `config.json` 算出每 token 的 KV 开销，乘可用内存得出额度。实测数据否定了它：

| 模型 | 层 × KV头 × head_dim | 每 token（fp16 估） |
|---|---|---|
| Qwen3.6-35B-A3B | 40 × 2 × 256 | 80 KB |
| Qwen3.8-27B | 64 × 4 × 256 | 256 KB |
| Llama-3.3-70B | 80 × 8 × 128 | 320 KB |
| glm-4.7-flash | 47 × 20 × 102 | 375 KB |
| gemma-4-31B | 60 × 16 × 256 | 960 KB |

同一台机器上开销差 **12 倍**，所以「N token 预算」这个旋钮本身就是错的设计：
32k tokens 在 Qwen3.6 上是 2.5GB，在 gemma-4 上是 30GB。

更要紧的是三处不可知：KV cache 的 dtype 是否量化、mlx 如何分页、
`--prompt-cache-size` 默认同时保 **10 份**缓存。任何纯预测公式都会系统性低估，
而且错了没人发现。

## 为什么可以实测

mlx-lm 自身提供了限额器与计量器，台面一处都没接：

| 能力 | mlx-lm | 台面现状 |
|---|---|---|
| 硬限额 | `--prompt-cache-bytes`，超限自动 `trim_to()` 驱逐 | 未传，等于无上限 |
| 缓存条数 | `--prompt-cache-size`，默认 10 | 未传 |
| 实际占用 | 每轮写日志 `Prompt Cache: N sequences, X GB` | 日志已在读（`backend.py::log_tail`），未解析此行 |

于是自校准成立：

```
实测每 token 字节 = 日志里的 Prompt Cache 字节数 ÷ 本轮 usage.prompt_tokens
```

**dtype、量化、分页全都不必知道——除一下就是这台机器上这个模型的真值。**

## 架构

新增 `desk/budget/`，与 `arbiter/` 平级。职责切分：

| 包 | 回答 | 性质 |
|---|---|---|
| `arbiter/` | **现在谁占着？** | 所有权与生命周期 |
| `budget/` | **还装得下什么？** | 容量与能力推导 |

今天 `arbiter` 两件都干，第二件只做了半条（R-arbiter-07 只在加载那一刻比对一次体积）。
把容量判断整体搬出，两个包各自可独立理解与测试。

### 包内文件，依赖单向

```
estimate.py   冷启动初值：读 config.json 算每 token 字节、读声明窗口
              纯函数，无 IO，dict 进数字出 —— 这一层承担绝大部分单测
      ↓
observe.py    传感器：解析 mlx-lm 日志的 Prompt Cache 行、读内存快照与压力
              只产出观察，不做决策；读不到就报 unavailable，绝不回落成猜测
      ↓
budget.py     合成额度，给出执行参数与消费者要的答案
```

### 对外接口

```python
@dataclass(frozen=True)
class Workload:
    kind: str            # "chat" | "video" | "music"
    key: str | None      # 模型 key，chat 才有
    bytes_needed: int    # 权重 + KV 额度，或作业峰值
    source: str          # predicted | measured | unavailable

class Budget:
    def cost(self, kind, key=None) -> Workload      # 单件重活要多少，带来源
    def fits(self, workloads) -> Verdict            # 一组能否共存 —— 纯函数
    def plan(self, wanted) -> Plan                  # 想跑这一组 ⇒ 该让出谁（最小让出）
    def for_chat(self) -> ChatBudget                # token 上限、压缩触发点、来源
    def launch_args(self, model_dir) -> list[str]   # 起 mlx-lm 的限额参数
    def snapshot(self) -> dict                      # 状态栏与诊断，每个数带来源
```

**核心是 `fits(workloads)` 而不是 `can_run(kind, alongside)`。** 共存是集合问题：
三件重活能否同时跑，不等于三个两两判断的合取。而且 R-arbiter-05 的「最小让出」
只有在集合上才算得出来——要腾出谁，取决于整组的组合。`plan()` 因此与 `fits()` 同层，
不是它的调用方。

`fits()` 是纯函数（一组 `Workload` 加一份内存快照进，`Verdict` 出），
所以组合爆炸的情况可以在单测里毫秒级穷举，不需要真装模型。

**整组来源取最弱的那个**：一组里只要有一件是 `unavailable`，整组按 `unavailable` 处理，
即保守路径。不允许「两件实测 + 一件没量过」被当成实测依据放行。

`snapshot()` 中每个数字必须带 `source` ∈ `predicted` / `measured` / `unavailable`。
这不是装饰：本方案立身于「实测修正预测」，界面与日志若分不出哪个数是猜的，
预测错了永远无人察觉。

不属于 `budget/` 的：怎么压缩（`llm/`，budget 只给触发点）、杀进程（`arbiter/`）、界面（`static/`）。

### 声明窗口的读取规则

实测六个模型，窗口位置不统一，必须按序判定：

1. 优先 `text_config.max_position_embeddings`（qwen3_5、qwen3_5_moe、gemma4 在此）
2. 否则取顶层 `max_position_embeddings`（llama、glm4_moe_lite 在此）
3. **永不取 `vision_config.max_position_embeddings`**——gemma-4 的视觉塔是 131072，
   文本塔是 262144，取错凭空砍半
4. 都读不到 → 该项记 `unavailable`，不猜

## 数据流

### 冷启动（本机首次装载该模型）

```
加载请求
  → estimate 读 config.json      ⇒ 每 token 字节（predicted）、声明窗口
  → catalog 的 ModelEntry.gb     ⇒ 权重占用（已有字段）
  → arbiter/memory 快照           ⇒ total / available / pressure
  → 媒体余量：档案无记录 ⇒ unavailable，本次不允许并行
  ⇒ 额度 = (available − 权重 − 安全余量) ÷ 每 token 字节
  ⇒ launch_args: --prompt-cache-bytes <额度 × 每 token 字节>、--prompt-cache-size <条数>
起 mlx-lm，硬边界自此由它自己 trim 守护
```

### 运行中（每轮答完自校准）

```
mlx-lm 日志  "Prompt Cache: 3 sequences, 12.40 GB"   ⇒ 实测占用
done 事件     usage.prompt_tokens                     ⇒ 本轮 token 数
实测每 token 字节 = 前者 ÷ 后者
```

### 修正，两个生效点

- **软触发**（压缩阈值）：立即采用实测值——它只是台面内存里的一个数。
- **硬边界**（`--prompt-cache-bytes`）：命令行参数不可改，**下次加载才生效**。

这个快慢分离是有意的：本轮安全由 mlx-lm 的 trim 兜底，不必等修正生效；
修正只让下次起得更准。

### 媒体余量同样自校准

作业启动前记 `available_bytes`，运行中周期采样取最低点，结束算差值
⇒ 本机 video / music 的峰值占用。首次运行无数据则保守（先卸 LLM），
跑过一次之后才有资格判断「富余充足，聊天模型不必卸」。

### 实测档案

落在 data_root，与 `config.json` 同级：

```json
{"models": {"<key>": {"bytes_per_token": 331776, "weights_gb": 70.2, "measured_at": "..."}},
 "media":  {"video": {"peak_bytes": 29000000000, "measured_at": "..."}}}
```

**作废规则**：条目记录权重大小，与 `ModelEntry.gb` 不符即丢弃重测——
重新量化过的同名模型不得沿用旧数。

## 互斥按预算重写

本项目尚未发布，不存在存量行为需要兼容，因此不做「降级迁移」，直接按预算写。

| 现状 | 改为 |
|---|---|
| R-arbiter-01 三者互斥，持有者唯一 | 重活能否并存由预算判定；预算不足时结果即互斥。持有者从单个变为一组 |
| R-arbiter-04 媒体在跑即拒绝加载 LLM | 拒绝条件改为 `fits()` 判否，理由码带数字（需要多少 / 现有多少 / 依据来源） |
| R-arbiter-05 开媒体前自动卸 LLM | 仅在预算不足时让出，且最小让出（卸最省的那个，非全卸） |
| R-arbiter-07 加载前比对一次体积 | 持续生效：会话中 KV 增长同样在预算内被监控 |
| R-arbiter-02 / 03 / 06 | 不动 |

**未经实测不放宽**：媒体作业占多少内存，本项目从未量过。没量过的数字不能用来放宽限制——
在量出来之前，媒体与聊天不并存。这与本仓库其它地方的证据纪律一致：没有证据的结论不算结论。

**压力传感器作兜底**：`kern.memorystatus_vm_pressure_level`（R-arbiter-02 已在读）
一旦升高，第一动作是令 mlx-lm trim 掉 KV 缓存——便宜且可逆，
比卸模型或杀媒体作业温和得多。它不做决策，只当最后一道闸。

**失败要被记住**：预算判定「装得下」而实际触发内存压力，该次必须落盘，
并永久收紧该组合的预算。只从成功里学习的系统会反复犯同一个错误。

## 上下文管理

照 Claude Code 的机制搬。其结构化摘要含以下小节：
用户的原始意图（原话级）、关键技术概念、碰过的文件与代码片段、踩过的错误与修法、
已解决的问题、**用户说过的每一句话逐条列出**、待办与当前工作、下一步。

四个要点：

1. **摘要是填表，不是「总结一下」。** 固定模板、固定小节。本地 27B 模型做不了
   「判断什么重要」这种开放任务，但能填表；给它一张表，输出质量方差显著变小。
   这是对冲本地模型能力弱的主要手段。
2. **尾部原文保留。** 摘要替换较早的部分，最近若干轮原封不动（轮数由预算反推，见下）。
3. **用户原话单独成节。** 模型复述容易走样，用户说过的话一个字都不应被改写。
4. **原文有处可查。** Claude Code 留 transcript 文件路径；台面更直接——
   完整历史本就在会话文件里、在用户屏幕上。**压缩只影响发给模型的内容，
   不影响用户能看到的内容。**

### 台面形态

- 会话新增消息类型 `role: "summary"`，记录它替换掉的消息区间
- `wireMessages` 发送 `summary` + 尾部原文；较早消息留在磁盘但不发送
- **尾部保留多少不是一个常数**：按「尾部原文 + 摘要之和不超过触发点的一半」反推轮数，
  至少保留最近一轮完整问答。写死轮数会在 80KB/token 与 960KB/token 的模型之间差一个数量级
- 触发点取自 `Budget.for_chat()`
- 压缩发生在**两轮之间**，用当前驻留模型自己完成——不换模型，不违反重活规则
- 界面呈现一条可见分隔：「这里压缩了 24 条消息」，可展开查看摘要全文

### 台面能做而 Claude Code 做不到的

1. **摘要可编辑**——它只是会话里的一条消息。本地模型摘歪了，用户自己改，不必重开会话。
2. **可重压**——原文都在，随时能用更好的模型或更新的模板重做。

### 代价

压缩本身是一次模型调用，需把全部历史 prefill 一遍再生成摘要，
在长会话上不便宜，用户会感到停顿。界面必须明确告知「正在压缩」，不得静默卡住。

## 失败模式

| 失败 | 表现 | 处置 |
|---|---|---|
| 日志格式变化 | 解析不到 Prompt Cache 行 | 该项记 `unavailable`，退回 predicted，界面标注；**不静默沿用旧值** |
| config 字段缺失 | 算不出每 token 字节 | 仅用声明窗口，界面说明「此模型算不出内存预算」 |
| 预测偏差过大 | 实测与预测差一个数量级 | 落盘并告警——这是常数因子错了的信号，不是正常现象 |
| 预算说行但爆了 | 内存压力升高 | trim 兜底 + 永久收紧该组合（R-budget-08） |
| 摘要质量差 | 模型丢失关键信息 | 原文未丢；用户可编辑摘要或重压 |

## 测试策略

- `estimate.py` 纯函数：六个真实模型的 `config.json` 做 fixture，覆盖三种窗口位置
  与 gemma 的双窗口陷阱
- `observe.py` 解析：真实 mlx-lm 日志行做 fixture，含格式变化时的降级路径
- `budget.py` 合成：注入假观察，验证 predicted / measured / unavailable 三种来源
  下的额度与 `source` 标记；**`fits()` 穷举一到三件重活的全部组合**，
  含「两件实测加一件未测应整组保守」这条；`plan()` 验证让出的是最省的那组而非全部
- 自校准回路：给定日志字节数与 `prompt_tokens`，验证得出的每 token 字节与档案写入
- 压缩：e2e 验证触发点、尾部保留、原文不丢、`wireMessages` 只发摘要加尾部
- **每条测试都须验证其在功能失效时会失败**——短接被测行为，确认变红

## 实现顺序

两个独立可交付，建议分成两个实现计划：

1. **budget 子系统**（含 arbiter 改写）——先有额度，先接上限额器与计量器
2. **上下文压缩**——消费 `Budget.for_chat()` 的触发点

顺序不可颠倒：压缩的阈值若没有预算支撑，就退回成一个拍脑袋的常数，
正是本设计一开始否定的那个做法。
