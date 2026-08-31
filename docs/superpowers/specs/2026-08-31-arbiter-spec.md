# 模块 spec：arbiter

**单一职责** 「同一时刻只干一件重活」的唯一权威。这是 README 里风险最高的一条，
所以它独立成模块、独立可证明，不并进 `llm`。

## 背景约束

现状 `_unload_llms()` 只终止本进程 spawn 的 mlx-lm 子进程。
上一次服务遗留在 :8767 的孤儿进程它看不见——`unload-llm.sh` 是按端口杀的，服务端不是。
这是互斥保证上的真实漏洞，本模块负责堵上。

`ram_gb: 128` 是写死的字面量，也在这里被真实读数取代。

## 状态机

```
idle ──acquire(llm)──> llm_held ──release──> idle
idle ──acquire(video)─> media_held ──release──> idle
idle ──acquire(music)─> media_held ──release──> idle
llm_held ──acquire(video|music)──> 先卸 llm ──> media_held
media_held ──acquire(任何)──> 拒绝
```

## 需求

- **R-arbiter-01** 聊天 LLM、视频生成、音乐生成三者互斥；持有者唯一，任何时刻至多一个重活。
  获取与释放必须是进程内串行化的（锁），并发获取只能有一个成功。
- **R-arbiter-02** 真实内存快照：总量、已用、可用、内存压力，取自操作系统（macOS 上 `vm_stat` / `sysctl`），
  **不得出现写死的 128 之类常量**。
- **R-arbiter-03** 按端口收割 LLM：找出监听 LLM 端口的**任何**进程并终止（先 TERM 后 KILL），
  包含本服务未曾 spawn 的孤儿。收割后必须确认端口确已释放才算成功。
- **R-arbiter-04** 媒体作业进行中拒绝加载 LLM；已有媒体作业时拒绝启动第二个媒体作业。拒绝必须带机器可读原因。
- **R-arbiter-05** 启动媒体作业前自动让出内存（卸掉 LLM）；让出失败必须导致启动失败，不得带着 LLM 硬上。
- **R-arbiter-06** 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活，
  以及若不能、为什么。这是状态条与菜单栏的唯一数据来源。
- **R-arbiter-07** 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。

## 暴露

`data:deskState`、`data:memorySnapshot`、`api:memorySnapshot`、`api:acquireHeavy`、
`api:releaseHeavy`、`api:currentHolder`、`api:reapLlmPort`、`api:canStartHeavy`、`event:heavyStateChanged`

## 消费

`api:resolvePaths`

## 验收取向

状态机与互斥用纯单元测试，含并发获取的竞态用例（多线程同时 acquire，断言只有一个成功）。
`api:reapLlmPort` 用一个测试起的假监听进程验证：起一个占端口的 `python -c` 子进程，
调用收割，断言端口释放且进程消失——这条不需要真的 mlx-lm。
`api:memorySnapshot` 断言字段存在、数值为正、总量与 `sysctl hw.memsize` 一致。
