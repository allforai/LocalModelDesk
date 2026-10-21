---
name: local-model-desk
description: 本机的本地模型台面（LocalModelDesk）。需要用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务，或者用本地模型生成、迭代图片、视频、音乐素材并按会话管理时使用。用户提到「本地模型」「台面」「本地生图」「本地生成视频」「本地生成音乐」「用本机模型」时使用。通过 lmdesk 命令调用。
---

# 本机模型台面（lmdesk）

台面是这台 Mac 上的本地模型应用。`lmdesk` 命令让你使用它的对话模型、图片模型、视频模型和音乐模型。台面会自己排队、按需加载模型。

## 调用

- 命令是 `lmdesk`。找不到时用 `~/.local/bin/lmdesk`。
- 加 `--json` 时，stdout 是单个 JSON 对象；进度和提示都在 stderr。
- **命令会自己排队等待**，生图或换模型可能要几分钟。把工具超时设得尽量长（至少 10 分钟），中途不要自己重试。

## 对话（一次性）

```bash
lmdesk models                                   # 本机有哪些对话模型、哪个已加载
lmdesk ask "把下面这段翻成英文" --model KEY --file draft.md
cat notes.txt | lmdesk ask "总结成三条要点"
```

- `ask` 不保留上下文。需要上下文时，用 `--file` 或 stdin 传入。
- 不写 `--model` 时，用台面当前已加载的模型。如果当前什么都没加载，会得到退出码 5，这时先运行 `lmdesk models`，按任务挑一个模型，再加 `--model` 重试。

## 生图与素材管理

```bash
lmdesk image sessions                            # 先看有没有合适的会话
lmdesk image new "首页 banner"                   # 没有就按用途新建，起有意义的名字
lmdesk image gen "首页 banner" "极简风格的山景插画" --size 1344x768 --out ./assets/hero.png
lmdesk image show "首页 banner"                  # 历史尝试：id、提示词、文件路径
lmdesk image gen "首页 banner" "改成黄昏色调" --from <尝试id> --strength 0.6 --out ./assets/hero.png
lmdesk image rename "首页 banner" "首页大图"
```

- 会话可以用名字或 id 指定。同名的有多个时，改用 id。
- 在满意的那张上继续改，用 `--from <尝试id>`；用 `--out` 把图放进项目。
- 不能删除会话。需要删的话，请用户在台面里删。
- 生图被你的工具超时打断时，stderr 里有一行 `lmdesk image wait <会话> <尝试id>`，**用它接着等，不要重新 gen**。生成会在台面继续进行。
- 能后台运行命令时，也可以先用 `lmdesk image gen … --no-wait` 提交，再用 `lmdesk image wait <会话> <尝试id>` 取结果。

## 视频

```bash
lmdesk video sessions
lmdesk video new "产品演示"
lmdesk video gen "产品演示" "湖面上的落日，微风吹起涟漪" --size 768x448 --frames 124 --no-wait
lmdesk video wait "产品演示" <尝试id> --out ./assets/sunset.mp4
lmdesk video show "产品演示"
```

- **视频一律用 `gen --no-wait` 提交，再用 `lmdesk video wait <会话> <尝试id>` 取结果**，生成往往要几分钟到几十分钟。
- `--frames` 只能取 49、73、124、192、243、362（约 2、3、5、8、10、15 秒），默认 124。`--size` 默认 768x448。
- 先生图、再用图片做首帧：
  1. `lmdesk image gen "封面" "雪山日出" --size 1344x768`，记下尝试 id；
  2. `lmdesk video gen "产品演示" "镜头缓缓推近" --first-frame image:封面:<图片尝试id> --no-wait`。
  - `--first-frame` 也可以是本地文件路径（png、jpg、jpeg、webp，不超过 32 MB）。
- 接着某一段往下生成：`--continue <尝试id>`（不能和 `--first-frame` 同用）。
- 把几段做成一个成片：
  - 续写的几段：`wait` 拿到的已经是从第一段到这一段的完整成片，不需要再 join 就能用。
  - 用户说要「合成」「拼接」，或者几段是各自单独生成的：用 `lmdesk video join "产品演示" <尝试id> <尝试id> [...]`，至少两段，台面会留下一条合成记录。续写的几段 join 出来，和续写成片的内容相同。

## 音乐

```bash
lmdesk music sessions
lmdesk music new "片头曲"
lmdesk music gen "片头曲" "温柔的民谣，木吉他伴奏，女声轻唱" --lyrics-file lyrics.txt --duration 60 --out ./assets/intro.wav
lmdesk music gen "片头曲" "电子氛围乐" --lyrics "[instrumental]" --continue <尝试id>
lmdesk music join "片头曲" <尝试id> <尝试id>
```

- **音乐必须有歌词**：`--lyrics` 和 `--lyrics-file` 二选一，不能都不给，也不能都给，否则退出码 2。
- 纯音乐：歌词只写 `[instrumental]`。段落用 `[verse]`、`[chorus]` 这样的方括号标记。
- 成品时长由模型按歌词决定，常短于 `--duration`（默认 60）。
- `--continue <尝试id>` 接着写下一段，`music join` 合成多段，规则与视频相同。

## 退出码

- 退出码 0：成功。
- 退出码 1：其他错误，原因在 stderr 最后一行。
- 退出码 2：参数错误或会话名有歧义。按提示修正。
- 退出码 3：没等到结果。看 stderr 最后一行（从上往下，按第一条匹配的处理）：
  - 含「仍在台面继续」或「已经完成」：用 stderr 前面那行 `lmdesk <image|video|music> wait <会话> <尝试id>` 取结果，不要重新 gen。
  - 含「取消」或「已经结束」：这次生成没有结果（通常是用户按了 Ctrl-C）。需要的话重新 gen。
  - 其他（`ask`，或者生成还没提交）：台面一直在忙，没排上队。告诉用户，稍后再试。
- 退出码 4：内存不足。
  - 生图、视频、音乐：先问用户，用户同意后加 `--force` 重试。
  - 对话模型：不能强制加载。告诉用户，建议换一个更小的模型。
- 退出码 5：模型、会话或尝试不存在。用 `lmdesk models`、`lmdesk image sessions`、`lmdesk video sessions`、`lmdesk music sessions`、`lmdesk image show` 查清楚再调用。
- 退出码 6：被沙箱拦截，访问不了本机网络（127.0.0.1）。先请求提升权限；拿不到权限时，把下面对应的放行方法**原样**告诉用户，然后停下：
  - Codex：默认的 workspace-write 沙箱关闭了网络。在 `~/.codex/config.toml` 里加上 `[sandbox_workspace_write]` 和 `network_access = true`，或者用 `codex -s workspace-write -c sandbox_workspace_write.network_access=true` 启动。
  - Claude Code 开启了沙箱时：把 `127.0.0.1` 加进沙箱的网络白名单。
  - 不要改用别的办法（自己翻译、自己写代码画图、联网下载）冒充本地模型的结果：用户要的就是本地模型。

## 例子

1. 用户说「用本地模型把 README 翻成英文」：
   `lmdesk models`，选一个对话模型，然后 `lmdesk ask "翻译成英文，保留 Markdown 格式" --model KEY --file README.md`。
2. 用户说「本地生成一张 app 图标放到 ./tmp」：
   `lmdesk image sessions`，没有合适的会话就 `lmdesk image new "app 图标"`，然后 `lmdesk image gen "app 图标" "扁平风格的山形图标，蓝色" --size 1024x1024 --out ./tmp/icon.png`。
