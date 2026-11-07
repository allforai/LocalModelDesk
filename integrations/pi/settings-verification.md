# pi 设置接入验收（2026-11-05）

范围：接手完整安装入口，并增加版本/用途命名及缺少 pi 时 Homebrew 自动安装。
与 `verification.md` 的原生工具链验收分开记录；不把旧结果冒充本轮结果。

## 已验证

- 专项：Python 76 passed；JS 2 passed；pi 真转换器/解析器 mock 14 passed；Playwright 8 passed。
- 最终增补：Python + Playwright 39 passed；JS 2 passed，包含 brew 状态自动刷新、失败日志与重试按钮。
- 模型 key 不变；设置显示五个完整版本、用途与复制命令；pi 名称包含相同信息。
- 临时 HOME 内验证安装/更新/接管/冲突保护/移除/孤立回执恢复/部分写入失败恢复；默认模型文件未改。
- brew 分支使用受控进程替身：固定 argv、只在点击后启动、单飞、成功后才装扩展、失败/超时/退出处理。没有卸载本机 pi 来制造“未安装”。
- Homebrew `pi-coding-agent` 确认来自 core，homepage `pi.dev`，上游 `@earendil-works/pi-coding-agent`；当次 stable 1.4.0。
- 初始独立完整构建 Developer ID 签名、verify-app 均通过，未公证。

## 收尾状态

- 最终 Python 非 GUI 全量回归：**1508 passed / 194.46s**（带 Git 元数据的独立源码快照，排除 tests/e2e、test_shell_window.py）。JS 全量补验中。
- Pi 1.2.0 / Homebrew 1.4.0：分别 14/14 适配器测试通过，使用各自真实转换器/解析器，未改系统已安装的 1.2.0。
- 最终 app 已重新签名、verify-app 通过（Developer ID、未公证），已部署并启动 `dist/LocalModelDesk.app`。
- 170 个 desk 源文件与最终包逐一一致；设置接口实际接管旧扩展，状态 installed，控制面/网关检查通过，pi 默认 settings 文件逐字节未变。
- 实装扩展 SHA-256：`9bb75310258083c814b0006fcfb55e150edbb42692fc88536f992456e1534301`；旧 app/扩展备份 `/tmp/lmdesk-settings-backup.p8OaZd`。
- 实际已部署 app 的浏览器 UI：已安装、五模型完整版本/用途、无页面异常；截图 `deployed-settings.png`。实际 `pi --list-models lmdesk` 成功发现五个稳定 key，全部仅声明文本输入。

## 中间失败与边界

- 首次 mock 新测试失败：cleanup 直接替换 `process.env` 对象，导致 `os.homedir()` 仍从原生旧 HOME 取值。最小 Node 对照复现后改成原环境代理原地恢复；14 项重跑通过。
- 第一次全量快照缺 Git 元数据：1507 passed，1 个 build_id 基础设施断言失败；没有隐藏为绿灯。最终快照含本地验证专用 Git 提交（不在项目 main 提交），重新全量跑。
- 临时 npm 安装 1.4.0 的首次测试入口假定依赖嵌套，npm 实际提升到外层；修改测试的包路径发现方式后，两版各 14/14 通过，不改变 provider 运行逻辑。
- JS 全量首次 508/509：严格 API 导出清单还未登记新增的三个命名操作；补齐清单以及 GET/status、POST/install、POST/remove、POST/check 的请求合同断言，保留原来的穷尽断言，不删测试来过关。
- 完整构建启动后补了一个 JS 的“brew 立即失败”结果提示；最终包同步该 JS 后重新签名和验证。其余 169 个 desk 源文件与完整构建逐项摘要一致。
- 用途为选用建议，不宣称五模型横向排名；GLM 不标最快，Gemma 看图只限台面，全部 pi 输入仍为文本。
- 未实际执行本机 Homebrew 新装分支（本机已有 pi 1.2.0）；无真实 brew 新装成功的冒充证据。检测公式和隔离 npm 版本兼容性不能替代 Homebrew 网络/权限成功保证。
- 完整非 GUI 回归不包含窗口快捷键测试或全量 E2E；本轮只跑与设置接入相关的浏览器操作。

证据：`evidence/2026-11-05-settings/`。本轮不改变 pi 默认模型。

## 后续修正

上文的“Gemma 看图只限台面”未经当时端到端核实，结论无效。当时台面和 pi 都在使用文本后端。本轮已为三个含视觉权重的模型接入独立视觉后端；最新能力与真实证据见 `vision-verification.md`。
