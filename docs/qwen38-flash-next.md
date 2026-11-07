# Flash-Next：已验证的本地 oMLX 接入

2026-11-07，M5 Max 128 GiB：已安装独立运行时、实际加载权重并完成文本、图片、原生工具调用往返、流式工具往返、pi 真实读文件及 app 图片聊天验收。当前本机 app 已部署并加载 `qwen38-flash-next`；旧模型保留。**尚未验证完整 262144 窗口、视频输入和长时间稳定性。**

## 来源与运行时

[模型卡](https://huggingface.co/mlx-community/Qwen3.8-Flash-Next-Uncensored-oQ5e-mtp) 声明源为 OrcaRouter BF16 abliterated，保留完整视觉/视频塔及 Lightning MTP。本接入固定 HF revision `c7d915c693e37fa11810d600b617adb4c36ff596`；38 个文件按 manifest 大小重新核对全部匹配，共 **128,567,787,194 bytes**。使用已下载目录，没有重复下载权重。

运行时固定 [oMLX commit 2165e757](https://github.com/jundot/omlx/tree/2165e75726ba83d9651dbaced61c97728da77bba)，安装后的版本标识为 `0.7.4.dev1`，不是把模型卡作者的旧版版本号冒充本轮环境。源码核实了 `qwen4_exp` 专用兼容层、PLE mmap、原生 MTP、TurboQuant、预加载健康检查和 OpenAI 图像/工具协议；不使用 stock mlx-lm/mlx-vlm 作为此模型的替代加载器。

独立 Python：

```
~/Library/Application Support/LocalModelDesk/runtimes/omlx/bin/python
```

首次原生构建失败于缺少 Metal Toolchain；执行 Apple 官方 `xcodebuild -downloadComponent MetalToolchain` 后重试成功。attention、lowbit、quant_matmul、sparse_index 原生内核全部可用。完整依赖清单、失败及成功日志保留在验收证据中。

新安装使用 `scripts/install-omlx-runtime.sh /绝对路径/新的环境`。脚本拒绝覆盖已有环境；已经创建环境但构建失败时，应修复工具链后，使用脚本中的固定 `uv pip install --python ...` 命令继续安装，无需重新下载模型。设置中的 `omlx_python` 可指定独立 Python，留空采用上述默认数据目录。

## 实际修复与兼容

- `LocalBackend` 对 Flash-Next 使用专用 oMLX，对旧模型保留主目录现有的 mlx-lm/独立视觉后端分派、解释器和依赖环境。
- 首次 balanced 动态 guard 仅允许约80.6 GiB，低于预加载估算88.2 GiB，实际被拒绝。改为模型卡测量所用 aggressive 档，保留动态内存检查及 Apple 默认107.5 GiB Metal上限；没有 force、sudo sysctl 或取消 guard。
- 修复“服务健康但 pinned 模型加载失败”时继续等待900秒的问题：现在立即呈现加载错误、停止子进程并释放预算。
- 强制 SSD PLE offload，原生 MTP 3 drafts，TurboQuant 4-bit/skip-last，单请求并发，热缓存0，SSD KV缓存上限8GB。日志确认这些真实路径生效。
- 调度预留100 GiB、禁止与其他重任务共存。短请求测量不能证明满窗口需求，因此预算仍不伪造完整窗口实测来源；不拿磁盘119.7 GiB当常驻内存。
- oMLX使用专用数据/发现目录及稳定本地模型别名，离线运行，不自动下载权重。官方运行时另外会发布 `~/.omlx/bin/omlx-cluster-python` shim；其配置和模型目录仍独立，不宣称完全没有任何 `~/.omlx` 写入。
- OpenAI网关支持图片和工具循环；当前 tool_choice 仅 auto，strict/required/强制函数仍明确拒绝。Anthropic图片可转换，但工具协议未新增。没有新增视频输入UI。

## 主目录与部署

首次部署时，主目录的源代码未修改、提交、重置或覆盖。只读检查后，在 worktree 中整合了现有 pi 设置模块、管理回执/安装逻辑、视觉后端及相关 UI、打包和测试，分别解决与 Flash-Next 的重叠修改。未搬运模型或输出作为源码。

部署复用现有已验证 bundle 的 Python、视觉/图片/视频/音乐依赖及原生壳；更新审核后的 desk 源码和 pi provider，再用现有 Developer ID 签名。候选及实际部署包均执行签名/打包校验。该次部署没有公证、对外发布或合并。2026-11-08 按用户要求，将主目录既有 pi/视觉改动先提交，再整合 Flash-Next 分支；权重和 outputs 不纳入 Git。

已部署路径：`/Users/aa/LocalModelDesk/dist/LocalModelDesk.app`。

旧 app、原 config、pi 扩展/管理回执/默认 settings 的恢复副本：

```
~/Library/Application Support/LocalModelDesk/backups/flash-next-20261107-0315/
```

该目录的 `rollback.py` 可恢复旧 app 和原受管 pi provider，保留换下的 app，不删除模型。仅在没有 active chat 时执行：

```sh
python3 "$HOME/Library/Application Support/LocalModelDesk/backups/flash-next-20261107-0315/rollback.py"
```

pi 扩展已按其现有管理流程更新以列出第六个模型；默认 `settings.json` 逐字节未变。旧 Gemma 实际文字和图片推理部署后复验成功；Flash-Next 在真实 pi 进程中调用了 `read(stock.json)`，并正确依据工具结果输出 `LOCAL-731 / 17`。台面真实图片会话回答 West，无浏览器异常。

## 同题补测与内存

完整结果和原始请求/响应：

`/Users/aa/LocalModelDesk/outputs/llm-comparison-20261107/qwen38-flash-next/`

原五模型的请求、响应、summary未改写。复用保存的题目和显式采样参数，只改变模型；工具后续调用使用本次生成的 call ID。省略参数仍采用各运行时自身默认值，Flash启用MTP，不能把这次筛查当成统一后端的严格性能排名。

| 任务 | 本轮结果 | 请求总耗时 |
|---|---|---:|
| 区间合并 | 11/11 | 7.88s |
| 拓扑排序 | 10/10 | 6.19s |
| 公告信息提取 | 5/5，原始JSON有效 | 1.21s |
| 调度推理 / thinking | 两次均正确 | 0.69s / 3.26s |
| 图片柱状图 | 3/3，JSON外有代码围栏 | 2.08s |
| 库存工具调用 / 结果回传 | 原生调用和13件库存均正确 | 1.06s / 0.55s |
| 更新公告 | 189个汉字，无指定禁词 | 3.21s |
| 小说 | 324个汉字，出现禁词“仿佛”，物件衔接也有偏离 | 6.80s |

不能仅凭这些短题宣称全面替代旧模型。代码21个用例全过，但代码总耗时约14.07s，比原记录中Qwen35的6.30s长；输出长度和后端不同。Flash短调度题表现更好，写作约束仍有违例。

默认thinking开启时，CLI的32-token输出预算曾全部用于思考而未产生正文；改用256-token预算后实际回复OK（其中103个reasoning tokens），不把前一次空正文冒充成功短答。

运行时加载日志实际分配约84.33 GiB；隔离验收一次加载29.12s。部署后短请求及工具测试期间，`vmmap`时点 physical footprint **87.1 GiB**、截至该时点峰值 **87.6 GiB**。不能用仅约8–10 GiB的进程RSS代替GPU/进程总占用。原始vmmap、连续系统内存/OS压力/swap样本均保存。

首次冷加载出现显著换页，系统swap从约2.80 GiB升至峰值20.62 GiB，已主动停止并保留记录。后续重试和部署验收阶段OS压力曾短暂为warning(2)，完成后为normal(1)，没有critical(4)；后台保护在critical或额外swap增长超过4 GiB时会卸载验收模型，本轮未触发。**保留这些失败/换页事实，不把它描述成“低内存无压力运行”。** 本机同时运行其他应用时能否加载仍由动态guard决定。

## 验证范围

2026-11-07 最终相关 Python **250 passed**，JS **511 passed**，浏览器专项 **5 passed**，pi真实转换器/解析器协议 **15 passed**。另外完成了上述真实权重/API/SSE/pi/UI推理。实际部署包重新签名并核对源码，主目录选取源文件摘要及pi默认settings保持一致。

证据位于结果目录的 `evidence/`，包括环境安装、失败尝试、内存样本、实际部署协议、UI截图、签名校验、保留性核对。未验证完整262k、视频、压力场景或长期稳定性；没有删除任何旧模型。

## 2026-11-08 长任务补测

复用 `outputs/pi-threejs-runner-20261105/models/qwen35/TASK.md` 和原 evaluator，Flash-Next 开启 thinking，输出上限 65536，不设任务总时限。源码检查点在约 30.8 分钟完成独立验收 20/20，正常首次进入的交互验收通过；模型继续自测，约 36 分钟时人为停止。随后明确要求收尾文档，约 3.9 分钟自然结束，核心实现未改变。因此不能称为一次完全自主收尾。累计两段运行约 39.9 分钟；这是单次任务结果，不代表稳定胜率。

进程 footprint 测得约 87.0 GiB、峰值 96.5 GiB，采样内存压力正常。证据在本机忽略目录 `outputs/pi-flash-threejs-ceiling-20261108-retry/`，不随仓库发布。

首次尝试暴露长工具参数生成期间公共 SSE 无数据，客户端约 300 秒空闲断连。重跑仅在测试 provider 中绕过；本次合并将公共网关补为每 15 秒 SSE 注释保活，覆盖 OpenAI/Anthropic 两条流式路径。该修复另有真实 HTTP 阻塞生成器测试；尚未据此重跑整场模型任务，也未重新部署 app。
