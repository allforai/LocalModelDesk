# 本地模型台 → 可安装 App：总览

**日期** 2026-08-31
**目标** 把散落在根目录脚本 + 一个 1066 行单文件里的需求，收成一个可安装的 macOS App，
带完整的模型资源管理，并对外提供 OpenAI / Anthropic 兼容的推理接口。

## 出发点（实测）

| 位置 | 现状 |
|---|---|
| `media-gui/server.py` | 1066 行：HTTP 服务 + 内联 HTML/CSS/JS + 作业运行器 + 模型目录，全在一个文件 |
| `media-gui/macos/App.swift` | 74 行 WKWebView 外壳；硬编码 `~/localModelDesk`；仓库里没有构建脚本 |
| `initModels.sh` | 197 行；模型目录 **第二份拷贝**（`server.py` 里还有一份） |
| `run-h3.sh` | H3 调用参数 **第二份拷贝**（`server.py` 里还有一份） |
| `run-music3.py` / `unload-llm.sh` | 根目录游离脚本 |
| `media-gui/tests/test_desk.py` | 11 个测试，1 个失败（路径大小写 `localModelDesk` vs `LocalModelDesk`） |
| LaunchAgent | 已安装并运行，但 plist 不在仓库里 |

已实测存在的缺口：

- `model_present()` 只要目录里有 **任意一个** `.safetensors` 就判定 `present`——半个 103G 的 H3 会报“齐了”。
- `_unload_llms()` 只终止 **本进程 spawn 的** mlx-lm 子进程。上一次服务遗留在 :8767 的孤儿进程它看不见，
  内存互斥有真实漏洞（`unload-llm.sh` 是按端口杀的，服务端不是）。
- 浏览器直连 `127.0.0.1:8767` 发聊天，绕过了服务端自己的 `/api/llm/chat/stream` 代理——该代理有测试、是死代码。
- `main()` 在 `mlx-h3` 缺失时 `SystemExit`：视频二进制不在，聊天也一起死。
- `ram_gb: 128` 是写死的字面量，没有任何地方读真实内存。

## Phase 0 冻结的决定

| 决定 | 取值 | 来源 |
|---|---|---|
| App 形态 | 重构现有栈：Python 服务 + WKWebView 外壳 | 人类 |
| 安装形态 | 自包含 `.app`，服务代码与 Python 运行时打进 `Contents/Resources`，不依赖任何 checkout 目录 | 人类 |
| 模型位置 | 首运可选目录；默认 `~/Library/Application Support/LocalModelDesk/models`；已有 339G 走**收编**不重下 | 人类 |
| 资源管理范围 | 真实完整度校验 + App 内下载续传 + 删除与磁盘回收 + 内存实时可见 | 人类 |
| 自启 | **不自启**；卸载现有 LaunchAgent | 人类 |
| 旧脚本 | 全部吸进 App 后删除 | 人类 |
| 签名 | Developer ID Application 签名 + hardened runtime；**不做公证** | 人类 |
| 前端 | 原生 ES 模块，无构建链，仓库零 `node_modules` | 人类 |
| 聊天历史 | 多会话，可切换可删 | 人类 |
| 窗口/进程 | 菜单栏 + Dock 都在；关窗口不退；菜单栏 Quit 才终止服务 | 人类 |
| 对外 API | OpenAI + Anthropic 两种方言 | 人类 |
| 监听 | `0.0.0.0`，**无令牌鉴权** | 人类 |
| 无模型时 | 不自动加载，一律 503 报错 | 人类 |

### 已向人类声明的风险（人类已确认后仍选择）

`0.0.0.0` + 无鉴权 意味着同一网络上的任何设备、以及本机浏览器里任何知道端口的页面，
都可以驱动本机模型并读取输出。这与 README 现有的「推理不出门」冲突。
按人类明示执行，README 将改写为实际行为。收紧成令牌校验是 `gateway` 单模块约 20 行的改动。

## 环境能力（Phase -1 实测）

| 能力 | 判定 | 证据 |
|---|---|---|
| 显示/UI | `available` | 有图形登录会话，`/dev/console` 属主 `aa`；`~/Applications/LocalModelDesk.app` 可启动并存活 |
| 桌面 App 构建 | `available` | `swiftc` 在 `/usr/bin/swiftc`；Xcode 位于 `/Applications/Xcode.app` |
| Developer ID 签名 | `available` | `security find-identity -v -p codesigning` 返回 `Developer ID Application: SUPERSTRING TECH K.K. (B49F324XWZ)` |
| 公证 notarize | `absent` | `xcrun notarytool history --keychain-profile notary` → `No Keychain password item found`。**人类已决定不做公证**，故不是 reality gate，是范围外 |
| 本机重型推理（H3 / Music 3） | `flaky`（慢且独占） | 权重齐备；单次 H3 出片以分钟计并独占统一内存。**任何以“真跑一次生成”为验收的任务标为 reality gate** |
| 模拟器/仿真器 | `absent`（不适用） | 目标是 macOS 原生 App，无需模拟器 |
| 外部网络 / HF | `available` | `https://huggingface.co/` 返回 200；`hf` 位于 `/opt/homebrew/bin/hf` |
| GitHub / `gh` | `available` | 已登录 `j08069099777`；`origin git@github.com:allforai/LocalModelDesk.git` |
| 硬件 | `available` | `Mac17,7`，18 核，137438953472 字节（128 GiB）统一内存，macOS 26.6.2 |
| 磁盘 | 受限 | 启动卷剩余 436Gi；模型已占约 339G。**删除类验收必须用临时假目录，不得动真权重** |

规划规则：凡验收依赖“真实跑完一次 H3 或 Music 3 生成”的任务，一律 `reality_gate:true`
并给出人工验证 runbook；不得伪造生成证据，也不得把慢生成塞进自动验收。

## 模块与依赖

| # | 模块 | 单一职责 | 估算任务数 |
|---|---|---|---|
| 1 | `foundation` | 路径与配置的唯一真相源；首运目录选择；旧目录收编 | ~6 |
| 2 | `resources` | 模型目录、真实完整度校验、下载续传、删除与磁盘核算 | ~14 |
| 3 | `arbiter` | 「同一时刻只干一件重活」的唯一权威；真实内存；按端口收割 LLM | ~7 |
| 4 | `llm` | 聊天模型加载/卸载/健康/流式 | ~7 |
| 5 | `gateway` | OpenAI + Anthropic 兼容对外接口 | ~10 |
| 6 | `media` | H3 视频 + Music 3 歌曲作业运行器 | ~7 |
| 7 | `library` | 成品、历史、多会话聊天的持久化与回放 | ~9 |
| 8 | `ui` | 静态前端：五个面板 + 常驻状态条 | ~14 |
| 9 | `shell` | Swift 菜单栏 App 与内嵌服务生命周期 | ~8 |
| 10 | `packaging` | 构建、内嵌运行时、签名、安装、卸载旧 LaunchAgent | ~9 |
| 11 | `e2e` | UI 级自动化验收：Playwright 驱动真实浏览器跑通用户旅程（决策 D-0001 新增） | ~12 |

依赖顺序：

```
foundation
   ├── resources ──┐
   ├── arbiter ────┼── llm ── gateway ──┐
   ├── library ────┼── media ───────────┼── ui ── shell ── packaging
   └────────────────┘                   │
                                        └── e2e   （消费 ui 与各 api，自身不被消费）
```

### 粒度审计

| 模块 | 估算 | 判定 | 处置 |
|---|---|---|---|
| foundation | 6 | 通过 | — |
| resources | 14 | 通过 | 已合并 目录+校验+下载（共享同一套模型状态词汇） |
| arbiter | 7 | 通过 | **拒绝**并入 `llm`：互斥保证是 README 里风险最高的一条，必须能独立证明 |
| llm | 7 | 通过 | — |
| gateway | 10 | 通过 | Anthropic SSE 转译是主要体量 |
| media | 7 | 通过 | — |
| library | 9 | 通过 | 已合并 成品+历史+聊天会话（同一类本地持久化） |
| ui | 14 | 通过 | 五面板 + 状态条，接近上限但同一个关注点 |
| shell | 8 | 通过 | — |
| packaging | 9 | 通过 | — |
| e2e | 12 | 通过 | 拒绝并入 `ui`：合并后 26 任务将突破 20 任务拆分线 |

全部 ≤ 20，无需拆分。

## Roadmap（本轮明确不做）

- 公证（notarize）与对外分发：需要 App Store Connect 凭据，人类已选择跳过。
- 对外接口的令牌鉴权与 TLS。
- 任意 HF 仓库的自由添加（目录仍是选定的 8 项）。
- 多人排队、云端推理。
- 70B 与 H3 同时驻留。

<!-- megastorm-registry:start -->
```json
{
  "requirements": [
    "R-foundation-01",
    "R-foundation-02",
    "R-foundation-03",
    "R-foundation-04",
    "R-foundation-05",
    "R-foundation-06",
    "R-resources-01",
    "R-resources-02",
    "R-resources-03",
    "R-resources-04",
    "R-resources-05",
    "R-resources-06",
    "R-resources-07",
    "R-resources-08",
    "R-resources-09",
    "R-arbiter-01",
    "R-arbiter-02",
    "R-arbiter-03",
    "R-arbiter-04",
    "R-arbiter-05",
    "R-arbiter-06",
    "R-arbiter-07",
    "R-llm-01",
    "R-llm-02",
    "R-llm-03",
    "R-llm-04",
    "R-llm-05",
    "R-llm-06",
    "R-llm-07",
    "R-gateway-01",
    "R-gateway-02",
    "R-gateway-03",
    "R-gateway-04",
    "R-gateway-05",
    "R-gateway-06",
    "R-gateway-07",
    "R-gateway-08",
    "R-gateway-09",
    "R-gateway-10",
    "R-media-01",
    "R-media-02",
    "R-media-03",
    "R-media-04",
    "R-media-05",
    "R-media-06",
    "R-media-07",
    "R-library-01",
    "R-library-02",
    "R-library-03",
    "R-library-04",
    "R-library-05",
    "R-library-06",
    "R-library-07",
    "R-ui-01",
    "R-ui-02",
    "R-ui-03",
    "R-ui-04",
    "R-ui-05",
    "R-ui-06",
    "R-ui-07",
    "R-ui-08",
    "R-ui-09",
    "R-ui-10",
    "R-shell-01",
    "R-shell-02",
    "R-shell-03",
    "R-shell-04",
    "R-shell-05",
    "R-shell-06",
    "R-shell-07",
    "R-shell-08",
    "R-packaging-01",
    "R-packaging-02",
    "R-packaging-03",
    "R-packaging-04",
    "R-packaging-05",
    "R-packaging-06",
    "R-packaging-07",
    "R-packaging-08",
    "R-packaging-09",
    "R-e2e-01",
    "R-e2e-02",
    "R-e2e-03",
    "R-e2e-04",
    "R-e2e-05",
    "R-e2e-06",
    "R-e2e-07",
    "R-e2e-08",
    "R-e2e-09",
    "R-e2e-10",
    "R-e2e-11",
    "R-e2e-12"
  ],
  "interfaces": [
    "data:deskConfig",
    "data:pathRoots",
    "api:resolvePaths",
    "api:readConfig",
    "api:writeConfig",
    "api:completeFirstRun",
    "api:adoptLegacyModels",
    "data:modelEntry",
    "data:modelStatus",
    "data:downloadProgress",
    "api:listCatalog",
    "api:verifyModel",
    "api:verifyAllModels",
    "api:startDownload",
    "api:cancelDownload",
    "api:deleteModel",
    "api:diskUsage",
    "event:downloadProgressed",
    "event:downloadFinished",
    "data:deskState",
    "data:memorySnapshot",
    "api:memorySnapshot",
    "api:acquireHeavy",
    "api:releaseHeavy",
    "api:currentHolder",
    "api:reapLlmPort",
    "api:canStartHeavy",
    "event:heavyStateChanged",
    "data:llmState",
    "data:loadedModel",
    "api:loadLlm",
    "api:unloadLlm",
    "api:llmStatus",
    "api:chatStream",
    "api:chatCompletion",
    "data:gatewayStatus",
    "api:openaiListModels",
    "api:openaiChatCompletions",
    "api:anthropicMessages",
    "api:gatewayConfig",
    "data:jobState",
    "api:startVideoJob",
    "api:startMusicJob",
    "api:cancelJob",
    "api:jobStatus",
    "event:jobFinished",
    "data:historyEntry",
    "data:chatSession",
    "api:listOutputs",
    "api:serveOutput",
    "api:listHistory",
    "api:appendHistory",
    "api:listChatSessions",
    "api:createChatSession",
    "api:updateChatSession",
    "api:deleteChatSession",
    "ui:deskShell",
    "ui:statusBar",
    "ui:chatPane",
    "ui:videoPane",
    "ui:musicPane",
    "ui:resourcesPane",
    "ui:libraryPane",
    "ui:firstRunPane",
    "ui:settingsPane",
    "data:shellStatus",
    "ui:menuBarItem",
    "ui:mainWindow",
    "api:spawnEmbeddedServer",
    "api:terminateEmbeddedServer",
    "api:chooseModelsDirectory",
    "api:buildAppBundle",
    "api:signAppBundle",
    "api:verifyAppBundle",
    "api:installApp",
    "api:uninstallApp",
    "api:launchTestHarness"
  ],
  "models": {
    "think": "fable",
    "verify": "opus",
    "bulk": "sonnet"
  }
}
```
<!-- megastorm-registry:end -->
