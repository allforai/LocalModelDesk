对账（SKILL.md = /Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md ；spec A = /Users/aa/LocalModelDesk/docs/superpowers/specs/2026-10-16-agent-skill-design.md 行232-257；spec B = .../2026-10-16-agent-media-design.md 行79-87）
A-80 name=local-model-desk: SKILL.md:2 name: local-model-desk（16字符，小写连字符）；目录名 .../bundled/local-model-desk/ 一致
A-80 description<=1024: SKILL.md:3 长度156
A-80 第一行 ---: SKILL.md:1 ---
A-81 本机本地模型台面: SKILL.md:3 「本机的本地模型台面（LocalModelDesk）」
A-81 文本场景: SKILL.md:3 「用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务」
A-81 图片按会话管理: SKILL.md:3 「用本地模型生成、迭代图片、视频、音乐素材并按会话管理」
A-81 触发词 本地模型/台面/本地生图: SKILL.md:3 「本地模型」「台面」「本地生图」均在
A-82 调用方式 lmdesk / ~/.local/bin/lmdesk: SKILL.md:12
A-82 耗时 排队/>=10分钟/不要重试: SKILL.md:14
A-82 image wait 不要重新 gen: SKILL.md:41
A-82 --no-wait 后 wait: SKILL.md:42
A-82 退出码3: SKILL.md:83 （含「如果是生图、视频或音乐…wait」）
A-82 退出码4 生图问用户加 --force / 对话模型建议换小: SKILL.md:84-86
A-82 退出码5 models / image sessions / image show: SKILL.md:87
A-82 退出码6 沙箱 + A-T9 放行方法: SKILL.md:88-90（Codex config.toml network_access=true；Claude Code 加 127.0.0.1 白名单）；A-T9 实测结果本问未核对
A-82 素材: 先 image sessions SKILL.md:30-31；--from SKILL.md:34,39；--out SKILL.md:32,39；不能删除会话 SKILL.md:40
A-82 对话 ask 一次性/--file/stdin: SKILL.md:20-21,24
A-82 两到三个典型示例: SKILL.md:94-97 （2个）
B-40 description 加视频音乐+触发词「本地生成视频」「本地生成音乐」: SKILL.md:3 均在；<=1024（156）
B-41 视频一律 --no-wait + wait: SKILL.md:54
B-41 串联示例 --first-frame image:<会话>:<尝试>: SKILL.md:56-58 (image:封面:<图片尝试id>)
B-41 --continue 续写 + join: SKILL.md:60-61
B-41 音乐必须有歌词: SKILL.md:73
B-41 纯音乐写法: SKILL.md:74 [instrumental]
B-41 退出码5补 video sessions/music sessions: SKILL.md:87
找不到的条目: 无
