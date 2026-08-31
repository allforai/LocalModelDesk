# 模块 spec：resources

**单一职责** 模型资源的目录、真实完整度、下载续传、删除与磁盘核算。
这是「资源的管理」的落点，也是消灭 `initModels.sh` / `server.py` 双份目录的地方。

## 背景约束

现状 `model_present()` 只要目录里存在任意一个 `.safetensors` 就判 `present`——
半个 103G 的 H3 会被报成「齐了」。这条必须被真实清单校验取代。

目录共 8 项（3 组）：`h3`、`music3` 各一项，`llm` 组 6 项。
每项含：`key`、`name`、`group`(chat|video|music)、`hf_repo`、`relpath`、以及聊天模型的
`vision`/`quant`/`params`/`gb`。这份目录在仓库里**只能存在一处**。

## 需求

- **R-resources-01** 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费；
  仓库内不得存在第二份模型 repo/路径清单（`initModels.sh` 与 `server.py` 里现有的两份都要消失）。
- **R-resources-02** 完整度以 HF 仓库文件清单为准：取得每个期望文件的路径与字节数，
  逐个比对本地是否存在、大小是否一致。清单可缓存到 `<data root>` 以便离线复用，缓存失效时明确降级说明，不得假装校验过。
- **R-resources-03** 每项报出 `present` | `partial` | `missing`；`partial` 必须带完成百分比
  （按字节，不是按文件数）与缺失/短缺文件列表。
- **R-resources-04** 报出每项实际占盘字节数，以及 models 所在卷的剩余空间。
- **R-resources-05** 对某一目录项发起下载；中断后再次发起必须续传，已完整的文件不得重下。
- **R-resources-06** 取消/暂停进行中的下载；已下载的部分必须保持可续传状态，不得清空。
- **R-resources-07** 下载进行时可查询实时进度：已完成字节/总字节、当前文件、速率、预估剩余。
- **R-resources-08** 删除某一目录项的权重并回收磁盘，需要显式确认参数（无确认参数一律拒绝执行）。
  删除只允许发生在 models 根之下，路径逃逸必须拒绝。
- **R-resources-09** 同时至多一个下载在跑；`arbiter` 报告有重活（媒体生成）在跑时，下载必须拒绝启动并说明原因。

## 暴露

`data:modelEntry`、`data:modelStatus`、`data:downloadProgress`、
`api:listCatalog`、`api:verifyModel`、`api:verifyAllModels`、`api:startDownload`、
`api:cancelDownload`、`api:deleteModel`、`api:diskUsage`、
`event:downloadProgressed`、`event:downloadFinished`

## 消费

`api:resolvePaths`、`data:pathRoots`、`api:canStartHeavy`

## 验收取向

单元测试为主：用假的 HF 清单 + `tmp_path` 造出「齐/一半/没下」三种树，断言状态与百分比。
下载器对 `hf` 命令的调用用可替换的执行器接口，测试注入假执行器；**不在验收里真下 100G**。
删除测试只在 `tmp_path` 里跑，并必须包含一个「路径逃逸被拒绝」的用例。
「对真实的 8 项跑一次 `verifyAllModels` 并与磁盘吻合」这条标 `reality_gate`（要读 339G 的目录树，慢）。
