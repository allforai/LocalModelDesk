# 模块 spec：library

**单一职责** 成品、作业历史、多会话聊天的本地持久化与回放。

## 背景约束

现状历史写在 `outputs/history.jsonl`，聊天历史写在 `media-gui/chat-history.json`——
单会话、且落在代码目录里。安装成 App 后代码目录只读，两者都要挪到用户数据根。

多会话是人类明确要的（比 README 多走一步）。

## 需求

- **R-library-01** 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件
  （历史里没有但磁盘上有的成品也要看得见）。
- **R-library-02** 提供成品字节流并支持 HTTP `Range`，返回 `206` 与正确的 `Content-Range`，使播放器可拖动。
  路径必须限制在 outputs 根内，逃逸请求返回 404。
- **R-library-03** 每个作业追加一条历史：类别、提示词/全部参数、耗时、状态、产出文件名、时间戳。
  追加是原子的、并发安全的（多线程同时追加不得写坏行）。
- **R-library-04** 能把一条历史的参数原样取回，供前端回填表单（「再做一版」）。
- **R-library-05** 多会话聊天：新建、列出、切换、重命名、删除。
- **R-library-06** 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。
- **R-library-07** 历史与会话一律存于用户数据根之下，不得写进 bundle 或代码目录。

## 暴露

`api:listOutputs`、`api:serveOutput`、`api:listHistory`、`api:appendHistory`、`data:historyEntry`、
`api:listChatSessions`、`api:createChatSession`、`api:updateChatSession`、`api:deleteChatSession`、
`data:chatSession`

## 消费

`api:resolvePaths`、`data:pathRoots`

## 验收取向

全部纯单元测试，用 `tmp_path`：
- Range 请求断言 `206`、`Content-Range`、返回字节数与内容正确；含一个越界/逃逸被拒的用例；
- 历史追加的并发用例（多线程各写 N 条，断言总行数与每行都能解析）；
- 会话的增删改查往返，含「重启」（重新构造对象读同一目录）后仍在；
- 孤儿成品出现在列表里的用例。
