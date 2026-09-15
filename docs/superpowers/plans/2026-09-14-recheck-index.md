# 2026-09-13 复盘缺口与新功能：计划索引

来源：`docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md`（21 条缺口、30 条未拉的线、P1–P4 四个缺陷模式）+ 用户新需求「看手气 / 优化提示词」。

## 计划与执行顺序

| 顺序 | 计划 | 内容 | 依赖 |
|---|---|---|---|
| 1 | [A 进程与生命周期](2026-09-14-recheck-A-process-lifecycle.md) | 孤儿进程、强杀、8767 被占、取消加载 | — |
| 2 | [B 聊天](2026-09-14-recheck-B-chat.md) | 空回答、中断持久化与重试、驱逐提示 | — |
| 3 | [C 可续传下载](2026-09-14-recheck-C-resumable-downloads.md) | 自带 Range 下载器、`.part` 进度 | A Task 1 |
| 4 | [D 构建、原生壳、配置、死契约](2026-09-14-recheck-D-shell-build-config.md) | 默认构建、卸载、坏配置恢复、网关横幅、菜单栏名、⌘,、错误页、P1 清理 | A（Task 9 删 harness 订阅前 A 已合入更稳） |
| 5 | [E 界面细节](2026-09-14-recheck-E-ui-details.md) | 键盘可达、2560 宽屏、音乐实际时长、hash 切换 | B Task 5（同改 `chat.js`，先 B 后 E 避免冲突） |
| 6 | [F 看手气 / 优化提示词](2026-09-14-prompt-assist-lucky-refine.md) | 新功能 | B Task 1、B Task 6（`api.js` 的 `request`） |

A、B 互相独立，可并行；C、D、E、F 按表中依赖排队。

## 缺口 → 任务

| 缺口 | 严重度 | 任务 |
|---|---|---|
| G1 默认构建 V3 失败 | high | D1 |
| G4 / J18 续传清空残片、取消后掉到 0% | high | C1–C4 |
| G11 聊天被驱逐：丢正文、露机器码 | high | B2、B5 |
| G12 退出时媒体 worker 成孤儿 | high | A1、A2 |
| J1 / G15 推理模型空回答（max_tokens 512） | high | B1、B5 |
| G14 / J25 坏配置无恢复入口 | high | D3、D4 |
| G17 壳被 kill -9 后 mlx_lm 孤儿 | high | A2 |
| G18 8767 被陌生进程占用，180 秒超时 | high | A3 |
| G2 `/api/config/reset` 零调用、对好配置也生效 | medium | D3、D4 |
| G3 残留 `.incomplete` 的显示 | medium | C4 |
| G5 会话列表键盘不可达 | medium | E1 |
| G6 死契约 / 干净 HEAD 上 e2e 红 | medium | D1（提交 e2e 修正）、D9 |
| G7 网关横幅显示过期错误 | medium | D5 |
| G8 ⌘, 无效 | medium | D7 |
| G10 素材库按请求时长标注歌曲 | medium | E4 |
| G13 2560 宽聊天列留白 46.7% | medium | E3 |
| G16 菜单栏显示目录 key | medium | D6 |
| G9 最小视频内存不足中止 | low | 不改：q18 在安静机器上重跑完成，q16 的中止来自同机其它实测官占用（见 ledger q16/q18） |

## 缺陷模式位点 → 任务

| 模式 | 位点 | 任务 |
|---|---|---|
| P1 | `/api/config/reset` | D4 |
| P1 | `GET /api/paths`、`POST /api/llm/chat`、`GET /api/resources/status/{key}` | D9（标注为对外端点，保留） |
| P1 | `LlmService.on_heavy_state_changed`（harness 与生产行为漂移） | D9 |
| P1 | `Arbiter.current_holder`、`match_route`、`encode_sse`、`isWindowVisible` | D9（删除或挪进测试） |
| P1 | `PortGuard.ensureFree` | D9（标注测试缝） |
| P1 | `formatRate` | D9（接上资源面板） |
| P1 | `Holder.public_view` | D6 |
| P1 | `api.js revealOutput` 无参分支 | 不改：原生菜单「打开成品目录」走 `POST /api/outputs/reveal`，前端无参分支是同一契约的另一入口，保留 |
| P1 | `ctx.confirm` 注入缝 | 不改：单元测试在用（`media_panes.test.js` 等），F 计划沿用 |
| P1 | `ResourceEvents.emit_*` 零订阅者 | 不改：C 计划 Task 2 仍经 `events` 发进度，属模块内部通知口，暂无多余代码可删 |
| P2 | 会话卡片与改名/删除 | E1 |
| P2 | 首帧 / 尾帧 / 参考视频文件选择 | E2 |
| P2 | 素材库行 | 不改：行内已有原生「播放」按钮，键盘可达 |
| P2 | 确认弹层背景点击 | 不改：Esc 与「取消」按钮已覆盖键盘路径 |
| P3 | 路径 9 驱逐 | B2、B5 |
| P3 | 路径 2 上游 HTTP 失败、3 缺 usage、4 网络异常、5 前端合成中断、8 流中卸载 | B5（所有结局统一写回会话） |
| P3 | 路径 4b/11 预检拒绝 | B5（问句保留、回答标注中断、可重试） |
| P3 | 路径 6 页面关闭 | B6 |
| P3 | 路径 7 流中切换会话 | B5（写回原会话；重试按钮只在当前会话显示） |
| P3 | 路径 10 服务端写已断开客户端 | B3 |
| P4 | 媒体 worker | A1、A2 |
| P4 | mlx_lm | A2 |
| P4 | 下载子进程 | C5 |
| P4 | 壳启动超时只收割 leader | A5 |

## 未拉的线 → 处理

| 线 | 处理 |
|---|---|
| README 构建输出位置、安装示例指向旧包 | D1 |
| uninstall bootout 失败被吞 | D2 |
| uninstall 自定义 LaunchAgents 目录仍 bootout 真实域 | D2 |
| reset 对合法配置也改名并回落 0.0.0.0 网关 | D3 |
| 删除确认默认聚焦危险按钮 | E2 |
| 全屏 2560 聊天不铺开 | E3 |
| 编辑/窗口菜单混入英文系统项 | 真机 2026-09-15：全部中文（编辑：撤销、重做、剪切、复制、粘贴、粘贴并匹配样式、删除、全选、写作工具、自动填充、开始听写…、表情与符号；窗口：填充、居中、移动与调整大小、全屏幕平铺、从组中移除窗口、最小化、全部最小化、进入全屏幕） |
| 右键菜单英文 Reload | 真机 2026-09-15：网页右键菜单只有「重新载入」 |
| 错误卡片详情只有日志路径 | D8 |
| hash 改变不切换标签页 | E5 |
| 流结束后仍显示「思考中…」、思考时长不准 | B5 |
| 媒体结束后持续橙色「让出内存」 | B7 |
| 模型根为空时加载按钮看起来可用 | B7 |
| 加载中无法取消 | A4 |
| 视频 / 音乐 worker 对父进程消失处理不同 | A1、A2（服务侧统一取消，不再依赖 worker 自觉） |
| SIGTERM 时 `llmPortFree=false` 误报 | 不改代码：取证时 8767 被主实例 mlx_lm 占着，属双实例环境；A3 之后占用者会被点名 |
| 被驱逐模型不是目录第一项时下拉框是否保持 | 不改：`renderLlm` 已按 `model_key` 回选（`chat.js` 驱逐分支），无反证 |
| 两个会话首问相同标题相同 | 不改：卡片元信息行已显示「模型 · 时:分」 |
| 首运页无「返回台面」、收编框预填扫描路径 | 2026-09-15 余项计划 Task 3–4：保留卡片「返回台面」；扫描结果改为「填入」建议。真机 2026-09-15：卡片「继续使用当前目录」显示「/Users/aa/LocalModelDesk 里已有 8 个模型」，收编框为空；「返回台面」按钮真机未测：两次真机检查（2026-09-15 Task 8、Task 10）进行中测试窗口被人操作，未能用键盘完成；由 `tests/e2e/test_firstrun.py::test_reset_models_root_can_return_to_the_desk_unchanged` 覆盖，列入用户试用清单 |
| 隔离数据根时 `discovered` 仍扫真实 `$HOME` | 2026-09-15 余项计划 Task 2：非默认数据根只扫显式目录。真机 2026-09-15：数据根 `/tmp/lmd-g/data` 的副本 `discovered` 只含 `/Users/aa/LocalModelDesk`——但那份副本的模型根本来就是 `/Users/aa/LocalModelDesk` 自身，旧代码在同样条件下会给出同一份列表，这条真机观察无法区分新旧代码，不能当作验证。修复由 `tests/test_foundation_firstrun.py::test_isolated_data_root_never_offers_the_real_home_or_checkout_tree` 覆盖 |
| 视频长参数耗时预期 | 2026-09-15 余项计划 Task 5：1024×576 且 ≥10 秒时提醒，不给分钟数 |
| VPN 隧道地址时 base URL 选哪个 | 不改：`lan.py` 跳过 `utun*` 与 100.64/10，单测覆盖；真机无隧道环境 |
| 菜单栏图标辨识度、状态滞后约 2 秒 | 不改：视觉与轮询策略取舍 |
| 作业列 2560 宽时视频预览贴左 | 不改：基线 L3 只约束两列之外的空区 |
| 原生窗口内容区 832 与 WebView 696 | 真机 2026-09-15：网页铺满窗口，无空带，关闭（1920×1050 窗口底边像素均为页面底色；聊天列两侧空白合计约 24%（Task 9 前）。真机最大 1920 宽，2560 由 `tests/e2e/test_chat_layout.py` 覆盖） |
| WKWebView 中 Tab 跳过按钮（真机 2026-09-15 新发现） | 2026-09-15 余项计划 Task 7：WKWebView 配置 `tabFocusesLinks = true`，由 `tests/test_shell_static.py::test_web_view_tab_key_reaches_buttons_without_system_keyboard_navigation` 覆盖；真机未测（Task 10 进行中测试窗口被人操作），列入用户试用清单。会话卡片焦点环与 Enter 切换已于 Task 6 真机通过 |
| cross-exam 视觉协议拒收 `width_range.min=null` / `reduced_motion` 轴 | 不属本仓库：是 superstorm 技能的校验器问题 |
| 宽窗口聊天列两侧大块空白（用户 2026-09-15 反馈） | 2026-09-15 余项计划 Task 9：消息列宽 = min(聊天区宽 − 48px, 1400px)，两侧各 24px、最宽 1400px；真机 2026-09-15：1920 宽窗口列宽到 1400 上限，两侧各约 104pt（旧 62vw 规则下约 210pt）；1440 宽窗口两侧各 24pt |

余项计划：docs/superpowers/plans/2026-09-15-recheck-leftovers.md

## 执行后复核

全部计划完成后，用 `/superstorm:cross-exam` 续盘本 run（`open_threads` 与 `patterns` 为起手牌），重点复核 J1、J18、J25 三条旅程和 G12/G17/G18 三个进程问题。

冻结的视觉基线（`docs/cross-exam/2026-09-13-localmodeldesk-recheck/visual/visual-baseline.json` 规则 L2）写的是消息列宽 `clamp(680px, 62vw, 1100px)` 居中；2026-09-15 用户改选：消息列表与输入区宽度 = `min(聊天区宽 − 48px, 1400px)`，未到上限时两侧各留 24px（详见余项计划 Task 9）。续盘 cross-exam 时，L2 的列宽子句以此为准替换，该文件本身不改；L2 里两侧留白合计不超过 40% 的上限条款不受影响，继续按原样核验。
