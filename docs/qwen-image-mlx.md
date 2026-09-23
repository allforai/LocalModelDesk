# Qwen Image 2.1 + Heretic 的本机 MLX 验证

后端已接入 `POST /api/media/image`、共用任务状态/取消、内存仲裁及资源模型清单。
图片页、PNG 预览、素材库和历史参数回填已接入。完整原生构建需单独验收；
下述各阶段证据不可相互替代，完整结果记录在 `.allforai/bootstrap/records/image-acceptance.json`。
不把文本编码器的文字拒答率当作图片无审查率。

## 在应用中使用

1. 在「资源」页下载或校验 Qwen-Image 2.1 + Heretic；已有对应完整模型会复用。
2. 打开「图片」，填写提示词，建议保留 1024×1024、40 步、种子 42，然后点「生成图片」。
3. 加载期间显示不定进度，采样时显示真实步数进度；可随时取消。完成后直接预览 PNG，
   或在「素材库」预览、在访达中显示、回填提示词与全部参数。

模型或 MLX 环境未就绪时生成按钮禁用；运行中的作业不能重复提交。
分辨率必须为 256–2048 范围内的 16 倍数。文件写入当前配置的成品目录，
不会上传到云端。本次新增的是单张文生图，不包含图生图或提示词助手。

## 固定来源

- 生图主体：[Qwen/Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)，revision `790c92633540aa0cb11d9abf19eb46d861714758`。
- 文本编码器：[pottokao/Qwen-Image-2.1-Text-Encoder-Heretic](https://huggingface.co/pottokao/Qwen-Image-2.1-Text-Encoder-Heretic)，revision `047e54342fc4bfcd2addd54049db9c90bb74731e`。
- 推理：[MFLUX](https://github.com/mflux-community/mflux)，commit `bd6c908fea288ea40a4e01db56cc3d923d221613`。

仅下载官方 transformer、VAE、processor，以及 Heretic 的 HF BF16 分片。
不下载原版文本编码器，不使用 GGUF、NVFP4 或 ComfyUI 重打包文件。
Heretic 与原编码器的参数键布局相同；MFLUX 自带映射覆盖被修改的 `o_proj` 和 `down_proj`。
整个生成管线使用 MLX，环境中的 PyTorch 是上游加载依赖，并非 MPS 推理后端。

## 安装与下载

在此工作树根目录执行：

```sh
uv venv --python 3.12 .venv-image
uv pip install --python .venv-image/bin/python --excludes packaging/excludes-image.txt -r packaging/requirements-image.txt
.venv-image/bin/python scripts/prepare-qwen-image.py \
  --output /absolute/path/to/image-models/qwen-image-2.1-heretic
```

下载约 33 GB。重复执行同一命令可续传；不向已有未知模型目录覆盖文件。
目录内 `localmodeldesk-image.json` 记录两个源 revision 和下载完成状态。
资源目录相对于应用配置的 `models_root`：`image-models/qwen-image-2.1-heretic`。
资源页与准备脚本使用同一固定文件清单（`desk/media/image_model.py`），逐文件记录源仓库、
revision、目标路径和精确字节数；两源都校验通过才显示已安装。字节数校验不是内容哈希校验。
下载保留 `.cache/localmodeldesk/parts/*.part`，失败后续传；已有完整文件会跳过。

开发服务默认使用本工作树 `.venv-image/bin/python`；可用 `LOCALMODELDESK_IMAGE_PYTHON`
指定其他图片解释器。`GET /api/capabilities` 暴露 `image_runtime.present/detail`，
能力检查最多缓存 10 秒，修复运行环境后可自动恢复。构建脚本独立安装 `pylibs/image`，
图片工作进程不复用音乐或聊天依赖目录。
图片依赖使用 `packaging/excludes-image.txt` 显式排除 OpenCV：它是上游
ControlNet/OpenPose 的依赖，当前仅开放的 QwenImage21 文生图不使用它。
解析锁文件与安装均须传入该排除文件；此环境不是完整 MFLUX 通用环境。
这避免携带未使用的 OpenCV 动态库及其 Homebrew 路径；完整产物须通过自包含、
签名、包内 Python 导入和原生窗口实际出图验收，不能仅凭依赖安装成功认定可用。
此依赖调整未改变 Qwen/Heretic 权重、MFLUX commit 或 MLX 版本。

### 验收记录

开发服务和原生开发窗口已实测出图、预览、素材库回填、取消和重试。
完整 `.app` 的最终状态、当前源码摘要、测试数量与六态独立评审以
`.allforai/bootstrap/records/image-acceptance.json` 为准。
前两次构建的失败日志保留：Developer ID 统一签名解决动态库签名问题，
OpenCV 自包含问题在用户确认后进入第三轮修复。没有关闭校验、
修改安全权限或覆盖现有应用。签名不等于公证；本次不公证、不发布安装。

HTTP 参数：非空 `prompt`；`width/height` 为 256–2048 内的 16 倍数；
`steps` 为 1–100，`seed` 为 uint32；默认 1024×1024、40 步、seed 42。
无效参数、缺失/不完整模型、缺失运行环境在启动前拒绝；内存预算沿用现有预警及显式确认。
图片内存是保守预测值（1024² 约 52 GiB，随更大画幅上调），不是实测 RSS。
每个任务输出唯一 PNG 名称和同名来源/参数 JSON；历史记录保存所有输入参数。

## 离线出图

```sh
.venv-image/bin/python -m desk.media.image_cli \
  --root /absolute/path/to/image-models/qwen-image-2.1-heretic \
  --prompt '一只橘猫坐在雨后的咖啡店窗边，窗上写着「午后咖啡」，写实摄影，暖色灯光。' \
  --width 1024 --height 1024 --steps 40 --seed 42 \
  --output outputs/qwen21-heretic-cat.png
```

生成时强制 HF/Transformers 离线模式；输出 PNG、同名 JSON 参数与耗时记录，
标准输出逐步打印 JSON 进度。BF16 保留原精度，文本编码器不量化。
`peak_mlx_bytes` 是 MLX 分配峰值，并非整机内存或进程 RSS。
这条验证命令尚未接入应用仲裁器，运行时须确保其他大模型已卸载。
应用 HTTP 入口已接入仲裁，取消向整个工作进程组发送 TERM，必要时升级 KILL。

## 验证边界

普通图片实际生成成功才能说明 MLX 接入成功；仅导入、单元测试或文字拒答测试均不能替代。
Heretic 修改可能改变提示词理解、画质或构图，需要与原编码器做同提示词对比后再决定是否作为默认。
目前 MFLUX 的 Qwen Image 2.1 实现不提供完整指令编辑、LoRA 和透明图片输出支持，不能把官方全功能直接视为已接入。

## 2026-09-23 本机实测

硬件：Apple M5 Max，40 核 GPU，128 GiB 统一内存。
运行版本：mflux 0.20.0（上述 commit），MLX 0.32.2，Python 3.12.13。

- 已下载目录：`/Users/aa/LocalModelDesk/image-models/qwen-image-2.1-heretic`，约 31 GiB。
- Heretic 编码器的 398 个 MLX 映射项全部匹配源分片索引。
- 离线生成成功，进程退出码 0：1024×1024，40 步，seed 42，BF16。
- 加载 3.96 秒，总耗时 114.63 秒，MLX 峰值 45,820,375,380 字节（约 42.7 GiB）。
- 实际成品：工作树 `outputs/qwen21-heretic-cat.png`；参数和来源记录在同名 `.json`。
- 已人工查看：橘猫、咖啡店、雨后街道和暖色调正常；要求的中文「午后咖啡」没有准确生成。
- 3 项新增模型检查测试及既有媒体命令、服务、进程执行测试合计 61 项通过。

此结果确认 MLX 兼容性和真实出图，不证明完全无审查，也不证明优于原版；尚未做原编码器 A/B 对比。

## 应用后端与 Python 3.13 阶段验证

`scripts/verify-image-runtime.py --evidence <全新目录> --models-root <模型根>` 启动真实生产
HTTP 服务（随机 localhost 端口、独立配置/输出目录、关闭网关），不使用 mock。
它检验既有模型下载复用、真实 PNG、取消退出与仲裁释放；生成仍强制 HF/Transformers 离线。
512²/4 步只证明链路，不作为画质验收；画质请用默认 40 步。

2026-09-23 已验证 Python 3.12.13 和独立 Python 3.13.15 + `pylibs/image` 依赖布局，
二者真实 HTTP 出图后均能取消下一任务，子进程退出并释放 holder。
Python 3.13 依赖解析及 `QwenImage21` 导入成功，锁文件无需降级。
这不是签名后的 `.app` 验收；最终构建产物仍须运行 `scripts/verify-app.sh` 并真实出图。
