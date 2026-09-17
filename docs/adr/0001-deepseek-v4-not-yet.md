# ADR-0001：暂不收录 DeepSeek V4 / V4.1 Flash

日期：2026-09-18　状态：已决定（可复议）

## 背景

有人提议把 [antirez/ds4](https://github.com/antirez/ds4)（DwarfStar，原生 Metal 引擎，自带 OpenAI 兼容的 `ds4-server`）作为第二个聊天引擎接入，用来跑 DeepSeek V4 Flash 与 V4.1 Flash。完整接入做过一轮（目录条目带 `engine` 字段、`Ds4Backend`、SSD 流式与视觉编码器启动参数、V4 Flash Q2 与 V4.1 Flash Q2 两个条目），测试全过后按决定整体撤回，仓库里没有留下任何相关代码。

## 核实过的事实

机器：M5 Max，128 GB，模型盘剩余约 251 GiB（2026-09-18）。

**mlx 路线走不通。**

- mlx-lm 钉在 0.31.3（2026-04-22），也是 PyPI 最新版；里面的 DeepSeek 模块只到 V3.2，没有 `deepseek_v4` / `deepseek_v41`。GitHub 主分支到 2026-09-17 同样没有。
- 上游 V4 的三个 PR 已关闭；V4 Flash（#1797，2026-08-28）和 V4.1（#1895，2026-09-16）的 PR 仍开着。
- Hugging Face 上的 MLX 权重都依赖第三方运行时：`mlx-community/DeepSeek-V4-Flash-2bit-DQ`（90 GiB）与 `…-0731-OptiQ-2bit`（92 GiB，需 mlx-optiq，专家从 SSD 流式读）；V4.1 的 MLX 2bit（222 GiB，作者私有运行时，256 GB 机器上约 9.5 t/s）。

**ds4 路线能跑，但代价明确。**

| 模型 | 磁盘 | 驻留主权重 | 这台机器上的跑法 | ds4 实测参照（M5 Max 128 GB） |
|---|---|---|---|---|
| V4 Flash Q2（`ds4f-q2`） | 81 GiB | 81 GiB | 全驻留 | 约 37 到 40 t/s |
| V4.1 Flash Q2（`ds41f-q2`） | 341 GiB | 152 GiB | 只能 `--ssd-streaming` | 无实测；同档 145 到 178 GiB 模型为 12 到 19 t/s |
| V4.1 Flash Q4（`ds41f-q4`） | 483 GiB | 294 GiB | 只能 SSD 流式 | 无实测；预期个位数 t/s |

- V4.1 的文件里 189 GiB 是 Engram 表，任何模式下都留在磁盘按需读。
- V4.1 Q2 加视觉编码器需要 342 GiB，超过当前剩余空间约 90 GiB。
- V4 Flash Q2（0731 文本检查点）没有视觉；V4 的视觉是另一个实验检查点。V4.1 Q2 视觉原生，编码器 0.9 GiB，仅 Metal。
- ds4 没有预编译包，每台机器要 `make`（Xcode 命令行工具，约一分钟）；`ds4-server` 先打开权重再监听端口，健康检查不会误判；图像走 OpenAI data URI 图像块，与台面网关的转发方式一致。

## 决定

暂不收录。理由不是做不到，而是：V4.1 在这台机器上只能流式跑，速度和磁盘代价都高；V4 Flash 能全驻留但只有文本；两者都要为此多养一个原生引擎，而 mlx 路线被上游卡住。

## 何时复议

- mlx-lm 合并并发布 V4 支持后：`mlx-community/DeepSeek-V4-Flash-2bit-DQ`（90 GiB，全驻留）可按现有 mlx 路线接入，只需在 `desk/resources/catalog.py` 加一条目录项并升级 `packaging/requirements-desk.txt` 里的 mlx-lm。
- 换到 256 GB 以上的机器，或明确接受流式速度：ds4 路线可以重做，上一轮的做法是目录条目加 `engine`、`files`（只下指定文件）、`ssd_streaming`、`vision_file` 四个字段，后端按 `engine` 分派。
