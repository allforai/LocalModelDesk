# 模块 spec：media

**单一职责** H3 文生视频与 Music 3 文生歌曲的作业运行器。

## 背景约束

H3 的调用参数现在写了两遍（`run-h3.sh` 与 `server.py`），Music 的调用写在根目录 `run-music3.py`。
本模块之后这三处收成一处：**H3 参数与 Music 参数各只有一个定义点**，根目录脚本删除。

作业是长任务（H3 以分钟计），必须可流式看进度、可取消。

## 需求

- **R-media-01** 启动文生视频作业：提示词、画幅（宽高）、帧数、步数。H3 命令行的构造只存在一处。
- **R-media-02** 启动文生歌曲作业：风格描述、歌词、时长。Music 3 调用的构造只存在一处。
- **R-media-03** 作业运行中可流式读取进度/日志输出。
- **R-media-04** 作业产出落在 outputs 根，文件名带时间戳（视频 `h3-<stamp>.mp4`，音频 `music3-<stamp>.wav`），
  并通过 `api:appendHistory` 记录一条含全部参数的历史。
- **R-media-05** 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。
  启动前必须成功取得许可（其副作用是卸掉 LLM），失败即失败。
- **R-media-06** 作业失败记录失败与原因；**产出文件不存在时绝不报成功**（退出码 0 但无文件也算失败）。
- **R-media-07** 取消运行中的作业：终止子进程并释放 `arbiter` 许可，状态转为已取消。

## 暴露

`api:startVideoJob`、`api:startMusicJob`、`api:cancelJob`、`api:jobStatus`、
`data:jobState`、`event:jobFinished`

## 消费

`api:acquireHeavy`、`api:releaseHeavy`、`api:canStartHeavy`、
`api:resolvePaths`、`data:pathRoots`、`api:appendHistory`、`data:historyEntry`、`api:listCatalog`

## 验收取向

子进程执行走可替换的执行器接口，单元测试注入假执行器：
- 断言 H3 与 Music 的命令行参数构造（逐参数比对，防止两处漂移复发）；
- 假执行器模拟「成功且产出文件」「退出码 0 但无文件」「非零退出」「运行中被取消」四种，
  分别断言 R-media-04/06/07；
- 断言未取得 arbiter 许可时不会启动任何进程。
「真的出一条 5 秒视频 / 一首 30 秒歌」标 `reality_gate`，附人工 runbook。
