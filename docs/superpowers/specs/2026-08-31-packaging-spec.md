# 模块 spec：packaging

**单一职责** 从干净 checkout 构建出可安装的 `LocalModelDesk.app`，签名、安装、卸载。

## 背景约束

人类明示：Developer ID Application 签名 + hardened runtime，**不做公证**。
本机已有证书 `Developer ID Application: SUPERSTRING TECH K.K. (B49F324XWZ)`。

Python 运行时与依赖内嵌进包（人类明示）：desk 侧依赖（`mlx_lm` 等）、
music 侧依赖（`mlx_minimax_music3`）、以及 `mlx-h3`，都要打进 `Contents/Resources`，
使 App 拷到 `/Applications` 即可运行，不依赖 Homebrew Python 或预装包。

## 需求

- **R-packaging-01** 一个构建脚本从干净 checkout 产出 `LocalModelDesk.app`；步骤可重复，中途失败要报错退出而非产出半成品。
- **R-packaging-02** 包内自带 Python 运行时与全部依赖；产物不依赖 `/opt/homebrew` 或任何用户级 site-packages。
- **R-packaging-03** `Info.plist` 含 bundle id、版本、图标、`LSMinimumSystemVersion`。
- **R-packaging-04** 用 Developer ID Application 证书签名，启用 hardened runtime 与时间戳；
  内嵌的二进制与动态库一并签（由内向外）。
- **R-packaging-05** 构建自动验证：`codesign --verify --deep --strict` 通过，
  并验证自包含性（包内不存在指向 `/opt/homebrew` 或 home checkout 的路径引用）。
- **R-packaging-06** 安装步骤把 App 放到 `/Applications`。
- **R-packaging-07** 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent；
  用户数据仅在显式选择时删除；**模型权重在任何情况下都不得被自动删除**。
- **R-packaging-08** 根目录旧脚本（`initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`）删除，
  并验证其行为在 App 内均可达（目录/下载、H3、Music、卸模型各有对应接口）。
- **R-packaging-09** README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、
  以及对外 API 监听 `0.0.0.0` 且无鉴权这一事实。

## 暴露

`api:buildAppBundle`、`api:signAppBundle`、`api:verifyAppBundle`、`api:installApp`、`api:uninstallApp`

## 消费

`api:spawnEmbeddedServer`、`ui:mainWindow`、`ui:deskShell`、`api:resolvePaths`

## 验收取向

- 构建脚本的结构与自包含检查可自动验证：编译产物存在、`Info.plist` 键齐、
  签名验证命令退出码 0、自包含扫描无外部路径引用、旧脚本确已不存在。
- 「拷到 `/Applications` 双击能起、首运能选目录、菜单栏状态对」标 `reality_gate`，附人工 runbook。
- 卸载脚本的破坏性动作在验收中只允许对临时假目录执行，**不得对真实 `/Applications` 或真实模型目录跑**。
