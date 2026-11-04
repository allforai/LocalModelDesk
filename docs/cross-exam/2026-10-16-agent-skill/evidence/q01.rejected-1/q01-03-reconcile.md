# q01-03 design vs SKILL.md (line numbers refer to SKILL.md)
A-80 name=local-model-desk, dir name local-model-desk, lowercase+hyphen, len 16 (<=64): L2 "name: local-model-desk" -> found
A-80 description <=1024: L3, python len 156 -> found
A-80 line 1 is '---': L1 "---" -> found
A-81 (1) 本机的本地模型台面: L3 "本机的本地模型台面（LocalModelDesk）。" -> found
A-81 (2a) 翻译/总结/改写/批量处理文本等离线或隐私敏感: L3 "需要用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务" -> found
A-81 (2b) 图片生成迭代并按会话管理: L3 "或者用本地模型生成、迭代图片、视频、音乐素材并按会话管理时使用" -> found (also covers video/music)
A-81 (3) 触发词 本地模型/台面/本地生图: L3 "「本地模型」「台面」「本地生图」「本地生成视频」「本地生成音乐」「用本机模型」" -> found all three
A-82 调用方式 lmdesk, ~/.local/bin/lmdesk: L12 "命令是 `lmdesk`。找不到时用 `~/.local/bin/lmdesk`。" -> found
A-82 排队/几分钟/超时>=10分钟/不要自己重试: L14 "命令会自己排队等待，生图或换模型可能要几分钟。把工具超时设得尽量长（至少 10 分钟），中途不要自己重试。" -> found
A-82 生图被超时打断用 stderr 的 image wait, 不要重新 gen: L41 -> found
A-82 能后台运行: gen --no-wait 再 wait: L42 -> found
A-82 退出码3 告知用户忙; 生图可稍后 wait: L83 "告诉用户。如果是生图、视频或音乐，稍后可以用对应的 wait 命令" -> found
A-82 退出码4 生图先问用户同意后 --force: L85 (生图、视频、音乐) -> found
A-82 退出码4 对话模型告知用户、建议换小模型: L86 "不能强制加载。告诉用户，建议换一个更小的模型。" -> found (文本未出现"内存不够"字样; L84 为"内存不足")
A-82 退出码5 先 models / image sessions / image show: L87 -> found
A-82 退出码6 沙箱，请求提升权限或告知放行本机网络: L88 -> found; 具体放行方法: L89-90 (Codex config.toml network_access=true / codex -s ... ; Claude Code 白名单 127.0.0.1) -> found
A-82 素材管理: image sessions 先看 L30; 没有就新建起有意义名字 L31 ("按用途新建，起有意义的名字"); --from L39; --out L39; 不能删除会话请用户在台面删 L40 -> found
A-82 对话 ask 一次性, 上下文用 --file 或 stdin: L24 -> found
A-82 两到三个典型示例: L94-97 共 2 个 -> found (2 个)
B-40 description 含视频、音乐及触发词「本地生成视频」「本地生成音乐」: L3 -> found; 总长 156 <=1024 -> found
B-41 视频一律 --no-wait + wait: L54 -> found
B-41 先生图再 --first-frame image:<会话>:<尝试>: L56-58, L58 "--first-frame image:封面:<图片尝试id>" -> found (占位为具体示例形式)
B-41 --continue 续写 + join 合成: L60 (--continue), L61 (video join) ; 音乐 L76 -> found
B-41 音乐必须有歌词: L73 ; 纯音乐写法: L74 "[instrumental]" -> found
B-41 退出码5 补 video sessions / music sessions: L87 -> found
