# 模块 spec：foundation

**单一职责** 路径与配置的唯一真相源。别的模块一律不得硬编码任何路径。

## 背景约束

App 装完之后不依赖任何 checkout 目录。代码在 `.app/Contents/Resources/`，
用户数据在 `~/Library/Application Support/LocalModelDesk/`。
开发时直接从仓库跑，也必须用同一套解析逻辑（靠是否存在 bundle 标记判断，不靠 if-dev 分支散落各处）。

## 目录约定（本模块定义，其余模块消费）

```
<bundle resources>/            # 只读：desk 包、静态前端、内嵌 venv、mlx-h3
~/Library/Application Support/LocalModelDesk/
  config.json                  # data:deskConfig
  outputs/                     # 成品
  history.jsonl                # 作业历史
  sessions/                    # 多会话聊天
  logs/                        # desk.log / mlx-lm.log
  models/                      # 默认模型根（可在首运改到外置盘）
    llms/<org>/<repo>/
    minimax-h3/
    minimax-music3/
```

## 需求

- **R-foundation-01** 所有路径由本模块单点解析，区分「只读 bundle 资源根」与「可写用户数据根」；
  其他模块只能通过 `api:resolvePaths` / `data:pathRoots` 取路径，仓库内不得出现第二处 `Path.home()` 拼接模型或输出目录。
- **R-foundation-02** 配置持久化到 `<data root>/config.json`，字段至少含：
  `models_root`、`outputs_root`、`first_run_done`、`gateway`（`enabled`/`host`/`port`）、`config_version`。
  读取时缺字段用默认值补齐，不得因为旧配置缺键而崩。
- **R-foundation-03** 首运语义：无配置或 `first_run_done` 为假时，`api:readConfig` 必须能表达 needs-setup 状态；
  `api:completeFirstRun` 接受一个选定的 models 根目录（默认 `<data root>/models`），校验可写后落盘并置 `first_run_done`。
  目录不可写必须返回明确错误，不得静默回退到默认目录。
- **R-foundation-04** 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`），
  `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`，
  以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。
  移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。
- **R-foundation-05** 服务在 `mlx-h3`、内嵌 venv、模型目录任一缺失时仍能启动并提供状态接口；
  缺失作为可查询的能力状态暴露，**不得 `SystemExit`**（现状是缺 `mlx-h3` 就整个服务起不来，聊天跟着死）。
- **R-foundation-06** 配置写入原子：先写同目录临时文件再 `os.replace`；写到一半崩掉不得留下损坏的 `config.json`。

## 暴露

`data:deskConfig`、`data:pathRoots`、`api:resolvePaths`、`api:readConfig`、`api:writeConfig`、
`api:completeFirstRun`、`api:adoptLegacyModels`

## 消费

无（这是根模块）。

## 验收取向

纯 Python 单元测试，全部用 `tmp_path` 造假目录树。收编与移动路径必须用假权重文件验证，
**不得触碰真实的 339G**。原子写用「写入过程中抛异常」的注入测试证明旧文件完好。
