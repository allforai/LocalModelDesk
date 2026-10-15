# 验收记录：本机 agent 能力（A-T9）

**日期** 2026-10-16
**环境**
- 构建：`dist/LocalModelDesk.app`，版本 1.0.0，分支 feat/agent-skill
- agent 版本：Claude Code 2.1.300、codex-cli 0.160.1、pi 1.2.0
- 安装方式：调用设置页「应用」背后的 `POST /api/agent-skill`，targets 为 claude、codex、pi。codex 这一行装在 `~/.agents/skills`。

## 安装与发现

- **后台拉起台面**：台面没开时运行 `lmdesk status`，命令行用 `open -gj` 在后台拉起 dist 版 app，约 1.3 秒后就能连上；`version.cli == version.desk == 1.0.0`。
- **安装结果**：三个 agent 的 skill 链接和 `~/.local/bin/lmdesk` 都显示 `installed`；「检查」返回「lmdesk 能连上台面」。
- **Claude Code 实时识别**：安装后，正在运行的 Claude Code 会话立即在可用 skill 列表里出现了 `local-model-desk`。

## 场景结果

| agent | 场景 | 是否自己调用 lmdesk | 退出码 / 结果 | 备注 |
|---|---|---|---|---|
| Claude Code | 翻译 | 是：加载 skill，再调用 `ask` | 第一次 5（没指定模型），运行 `models` 后选 superqwen 重试，得到 0 | 完全按 SKILL.md 的退出码处理方式走 |
| pi | 翻译 | 是：读 SKILL.md，然后 `models`、`ask`（stdin 传入） | 0 | 工具超时按 skill 要求设成 600 秒 |
| Codex（`-s workspace-write`，默认不开网络） | 翻译 | 是 | 6（被沙箱拦截） | agent 如实告诉用户需要放行本机网络，符合 A-33 |
| Codex（加 `-c sandbox_workspace_write.network_access=true`） | 翻译 | 是 | 0 | 放行方法已写进 SKILL.md |
| Claude Code | 生图放进 ./tmp | 是：`image sessions`、`new "猫"`、`gen --out` | 0，约 160 秒 | 生成后用 Read 打开图片确认画面 |
| Codex（开网络） | 生图放进 ./tmp | 是：`image sessions`，然后复用「猫」会话 `gen --out` | 0 | 复用已有会话，没有重复新建 |
| pi | 生图放进 ./tmp | 是：`image sessions`、`image show "猫"`，然后在该会话 `gen --out` | 0 | 同样复用会话 |

## 被打断后续等

- **做法**：用 `BASH_MAX_TIMEOUT_MS=60000` 限制 Claude Code 单条命令最长 60 秒，再让它生成一张约 160 秒的图。
- **观察**：Claude Code 2.1.300 在命令超时后没有杀掉进程，而是把它转到后台继续运行，之后读取输出拿到结果。
  - 尝试数只增加 1，说明没有重新 gen。
  - 「被杀掉后用 `wait` 续等」这条路径在这个 agent 里没有被触发。
- **结论**：这条路径由自动化测试覆盖（`tests/agent_cli/test_image_cli.py` 中的 SIGTERM 测试和 `wait` 测试）。真实 agent 里的表现可以接受：没有重复生成，也拿到了结果。

## 未完成

- **DeepSeek Harness**：它是图形界面应用，需要用户手动试。skill 目录 `~/.dsh/skills` 是根据源码确定的，未实测。
  - 注意：codex 这一行装在 `~/.agents/skills`，DeepSeek Harness 也会读这个目录。所以本次只勾选了 codex，DeepSeek Harness 可能就已经能看到 skill 了。
