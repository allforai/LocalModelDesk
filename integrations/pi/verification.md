# 本地 pi 原生工具调用验收（2026-11-05）

## 已启用

- 控制面：台面 `127.0.0.1:8766`，负责预检和自动装载。
- 数据面：台面网关 `127.0.0.1:8770/v1`，原生 OpenAI tools/tool_calls、真实 usage。
- pi 适配器：`integrations/pi/lmdesk.ts`，已安装到 `~/.pi/agent/extensions/lmdesk.ts`，二者 SHA-256 一致：
  `6423b49d663a5f6613748fc723191aec812dac81446360978783baf6a720a85c`。
  （最终同步目录删除 `llama70`；原生工具与自动加载逻辑不变。）
- 台面：`dist/LocalModelDesk.app` 已换为本次隔离构建并重启；5 个修改的 Python 模块与隔离验收源码逐一核对一致。
- 初次升级前备份：`/var/folders/yk/1lzd8nn12m50n2l4gd8r28340000gp/T/lmdesk-native-backup.mg_k184j/`，包含旧 app 和旧提示式扩展。
- 最终合并打包替换前备份：`/var/folders/yk/1lzd8nn12m50n2l4gd8r28340000gp/T/lmdesk-native-backup.kdrhoumq/`。
- 最终合并构建产物：`/tmp/lmdesk-final-build.vZA9Do/LocalModelDesk.app`；初次原生验收产物保留在
  `/tmp/lmdesk-native-artifacts.CraXuo/build/LocalModelDesk.app`。
- Developer ID 签名及 verify-app 校验通过；**未公证**，本次用于本机，不声称可直接分发。

初次原生工具验收构建从基线导出，只带入网关/LLM/本次测试修改，没有混入当时另一会话的模型目录修改。
随后用户明确要求「全部一起提交推送」和「dist/ 打包」：最终合并打包纳入模型目录调整，
同步从 pi 列表删除已从目录移除的 `llama70`。合并源码相关回归为 Python 217 项、JavaScript 17 项通过；
最终打包前 pi 适配器重新验收 10/10 通过。上面的初次构建与下面的全量 1472 项记录保留各自实际范围，不混作新构建的全量测试。

## 结果

| 检查 | 结果 |
| --- | --- |
| 隔离 Gateway + LLM 回归 | 193 passed |
| pi 适配器 mock 协议测试 | 10 passed，使用 pi 自带转换器/解析器，无推理请求；合并打包前再次 10/10 通过 |
| 合并源码相关回归 | Python 217 passed；JavaScript 17 passed |
| 最终合并打包 | Developer ID 签名与 verify-app 校验通过；未公证；dist 已替换并启动，6 个模块与打包源码一致 |
| 最终包启动冒烟 | 已安装扩展自动加载 qwen35，实际回答「最新版打包验证通过」，active_chats 归零；目录已移除 llama70 |
| 真模型编程闭环 | qwen35：2 个测试失败 → read 源文件和测试 → edit 源文件 → 2 个测试通过 |
| 独立复验 | `python3 -m unittest -q`：2 passed；测试文件 SHA-256 未变 |
| 已安装扩展自动切换 | qwen35 → superqwen → qwen35，两次自动装载、两次正常回答 |
| 真模型原生协议 | 非流式 tool_calls、中文 role:tool 结果回传、流式 tool_calls、真实 usage、[DONE] 均通过 |
| 台面记账 | 流式请求期间 active_chats > 0，结束后归零 |
| 全量非 GUI 回归 | 1472 passed，200.76s；明确排除 Playwright E2E 和窗口快捷键权限用例 |

编程闭环由 pi 实际执行 6 次工具调用：bash×3、read×2、edit×1；其中 1 次工具失败是预期的初次测试失败，不是传输错误。运行元数据显示模型始终为 `lmdesk/qwen35`，累计输入/输出为 10421/569 token。

验收夹具：`/tmp/lmdesk-native-coding.hXfIQ1`。源码从 `unit_cents + quantity` 改为 `unit_cents * quantity`。
测试文件 SHA-256（运行前后相同）：`25be4f148f848c63e185b5b14f136d888a1865f86c0b22c3e9b409f48b53d040`。

流式协议实测该轮 usage：prompt 297、completion 57、total 354。
结构化证据见 [`evidence/2026-11-05/`](evidence/2026-11-05/)。

## 验收边界与中间失败

- 首轮 HTTP 往返测试帮助函数误用 Latin-1 发送中文，已改为显式 UTF-8并复验通过。
- 首轮隔离全量测试目录没有 Git 元数据，且把构建 app 放在源码树内，分别触发 build_id 和重复目录不变量检查；修正隔离布局后两项单独复验通过。
- 窗口 Cmd-W/Cmd-Q 两项测试被 macOS Accessibility 权限阻塞，**未通过**，未调整系统权限。
- Playwright E2E 未运行；最终非 GUI 回归明确排除 `tests/e2e` 和 `tests/test_shell_window.py`。
- 本次只增加 OpenAI 工具协议。Anthropic 工具块、图像输入、严格 schema、强制 tool_choice 未支持，明确拒绝；不丢掉调用后假装成功。
- 编程闭环验收只覆盖 qwen35。其他模型的编程能力未逐一验收；superqwen 已验证自动切换和普通对话。
- 原生协议和这些用例通过不代表模型能正确完成任意工程任务。

## 使用

新 pi：`pi --model lmdesk/qwen35`。
已有 pi：先 `/reload`，再 `/model` 选择 `lmdesk/qwen35`；第一条请求会按需自动加载。
台面已运行时不需要再手动 `lmdesk ask`。pi 的原有默认模型未修改。
配置和重跑命令见 [README](README.md)。
