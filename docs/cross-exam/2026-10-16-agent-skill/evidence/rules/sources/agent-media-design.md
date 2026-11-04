# 模块设计：lmdesk 补上视频与音乐（agent 能力第二期）

**日期** 2026-10-16
**来源** 用户 2026-10-16：「做完这个任务，再把视频和音乐等其他的补上，并且执行一下 cross-exam」。用户已离开；按既定做法「全部按推荐来」推进，以下各项都是推荐选项。
**上游** `2026-10-16-agent-skill-design.md`（A-xx，第一期：对话、图片、安装）；视频会话 `2026-09-27-video-sessions-design.md`；音乐会话 `2026-09-27-music-sessions-design.md`；合成与配乐 `2026-09-27-video-soundtrack-design.md`。

每条 **[B-xx]** 可写成测试断言。第一期的 A-xx 规则全部继续适用，包括退出码、排队等待、续等、`origin: agent`。

---

## 0. 范围与非目标

- 范围：
  - `lmdesk video` 和 `lmdesk music`：`sessions|new|show|gen|wait|rename`，与图片完全同构；
  - `lmdesk video join` 和 `lmdesk music join`：把同一会话里的几段合成成片；
  - 视频首帧可以来自本地文件，也可以来自图片会话里的某次尝试；
  - 预检接口支持视频和音乐；
  - SKILL.md 补上视频、音乐的用法。
- [B-00a] 不做配乐（soundtrack）、参考视频（reference）、配乐参考（music_ref）、尾帧。这几项素材组合复杂，agent 用得少，以后再加。
- [B-00b] 不改界面、不改安装。设置页和 skill 链接都不变。
- [B-00c] 不改媒体服务的生成规则。参数校验仍由服务端负责，命令行只做格式解析。

## 1. 结构

- [B-01] 把 `desk/agent_cli/images.py` 泛化为 `desk/agent_cli/media.py`：由一张按 kind 区分的配置表驱动 image、video、music 三种媒体。会话解析、`show`、`wait`、`--out`、提交时挂起信号、SIGINT 取消、SIGTERM 续等提示，三种媒体共用同一份代码。
  - 不保留 `images.py` 作为兼容层（台面未发布）。
  - 测试 `tests/agent_cli/test_image_cli.py` 原样保留，并继续通过。
- [B-02] `decide()` 的 `op` 取值扩展为 `chat`、`image`、`video`、`music`、`compose`。
  - `image`、`video`、`music` 走同一套媒体规则（A-20 表格的「图片」那一列）。
  - `compose` 只用 ffmpeg，不经过 arbiter（见现有 `start_compose_job`），所以它的规则是：
    - 媒体任务在跑：等待；
    - 其余情况：直接提交，不需要预检。

## 2. 视频

```
lmdesk video gen <会话> "提示词" [--size WxH] [--frames N] [--steps N] [--seed N]
                 [--continue <尝试id>] [--first-frame PATH | --first-frame image:<图片会话>:<尝试id>]
                 [--out PATH] [--force] [--no-wait]
lmdesk video join <会话> <尝试id> <尝试id> [...] [--out PATH] [--no-wait]
```

- [B-10] 默认值与界面一致：
  - `--size` 默认 768x448，即标准横屏档；
  - `--frames` 默认 124，约 5 秒，取值来自 `desk/static/js/pure/video_session.js` 的 `DURATIONS`；
  - `--steps` 用界面的默认步数，实现时从 `desk/static/index.html` 里视频页步数输入框的 `value` 读出，写成常量。
- [B-11] `--frames` 只接受 `DURATIONS` 里的帧数：49、73、124、192、243、362。其他值以退出码 2 拒绝，并列出可选值和对应的秒数。
- [B-12] `--continue <尝试id>`：接着这一段往下生成。对应接口字段 `continues`。与 `--first-frame` 同时使用时，以退出码 2 拒绝。
- [B-13] `--first-frame` 两种写法：
  - 本地文件路径：先 `POST /api/media/inputs`，请求体为 `{name, data: base64}`，拿到素材 id，再以 `mode: "image", first_frame: <id>` 提交。文件不存在、扩展名不是 png、jpg、jpeg、webp，或超过 32 MB 时，以退出码 2 拒绝。
  - `image:<图片会话>:<尝试id>`：引用图片会话里的某次尝试，`<图片会话>` 可以填名字或 id（规则同 A-10）。以 `mode: "image", refs: {"first_frame": {"kind": "image", "session_id", "attempt_id"}}` 提交。
- [B-14] `video join`：调用 `POST /api/media/compose`，请求体为 `{kind: "video", session_id, parts: [尝试id…]}`，至少两段，不足两段以退出码 2 拒绝。合成会在会话里产生一条 `op: "compose"` 的尝试，然后按 A-27 的规则等待这条尝试并输出成片路径。
- [B-15] 视频生成往往要几分钟到几十分钟。SKILL.md 推荐视频一律用 `gen --no-wait` 提交，再用 `video wait` 取回结果。

## 3. 音乐

```
lmdesk music gen <会话> "风格描述" (--lyrics "…" | --lyrics-file PATH) [--duration 秒] [--seed N]
                 [--continue <尝试id>] [--out PATH] [--force] [--no-wait]
lmdesk music join <会话> <尝试id> <尝试id> [...] [--out PATH] [--no-wait]
```

- [B-20] Music 3 必须有歌词。`--lyrics` 和 `--lyrics-file` 必须给一个，两个都没给、或者两个都给了，以退出码 2 拒绝。纯音乐的写法在 SKILL.md 里说明，按 Music 3 的歌词标记约定写，例如只写 `[instrumental]`；具体写法以 `desk/static/js/panes/music.js` 和音乐会话设计里的约定为准。
- [B-21] `--duration` 的默认值与界面一致，从 `desk/static/index.html` 音乐页时长输入框的 `value` 读出。
- [B-22] `--continue`：对应接口字段 `continues`。`music join` 与 B-14 同理，`kind` 为 `"music"`。

## 4. 预检与输出

- [B-30] 预检接口 `/api/agent/precheck` 增加两种 op：
  - `op=video&width=&height=&frames=&steps=`
  - `op=music&duration=`
  - 由 `MediaService.precheck_media(kind, params)` 调用 `arbiter.can_start_heavy(kind, params=…, key=…)`，key 分别是 `h3` 和 `music3`，与 `_admit_heavy` 用的 catalog key 一致。
  - 原来的 `precheck_image` 改为调用它，避免两份逻辑。
- [B-31] `wait` 和 `gen` 的输出路径：有 `joined_output` 时用它（续写后，这就是到当前这一段为止的完整成片），否则用 `output`。这条规则已经存在于 `_attempt_view`，三种媒体统一沿用。
- [B-32] `show` 的 `prompt` 字段：视频取 `params.prompt`，音乐取 `params.caption`，合成尝试取 `"合成：" + 各段 id`。

## 5. SKILL.md

- [B-40] description 加上视频、音乐，并补充触发词「本地生成视频」「本地生成音乐」。总长仍然不超过 1024 字符（A-80）。
- [B-41] 正文增加视频、音乐两节，必须包含：
  - 视频一律用 `--no-wait` 加 `wait`；
  - 先生图、再用 `--first-frame image:<会话>:<尝试>` 生成视频的串联示例；
  - 用 `--continue` 续写，再用 `join` 合成成片；
  - 音乐必须有歌词，以及纯音乐的写法；
  - 退出码 5 那条补上 `lmdesk video sessions` 和 `lmdesk music sessions`。

## 6. 测试

- [B-T1] `decide()`：`video`、`music` 与 `image` 的规则相同（参数化同一组用例）；`compose` 在媒体任务进行中时等待、空闲时提交，并且不读取预检结果。
- [B-T2] 命令行集成测试（`launch_test_harness`，`model_states` 中让 `h3`、`music3` 为 present，并打开对应的 runtime 开关；具体写法参照现有的 `tests/e2e/test_video_sessions.py`、`test_music_sessions.py` 是如何让 harness 跑视频、音乐的），覆盖：
  - `video new/gen/show/wait/rename`；
  - `--continue` 之后 `wait` 输出 `joined_output`；
  - `--first-frame` 的本地文件和 `image:` 引用两种写法各一例，断言服务端收到的 `mode`、`first_frame` 或 `refs`；
  - `--frames 50` 返回退出码 2；
  - `video join` 少于两段返回 2，两段时得到成片；
  - `music gen` 不带歌词返回 2，带 `--lyrics-file` 成功；
  - `music join`；
  - 视频生成时收到 SIGTERM 不取消任务，之后 `wait` 能取回结果。
- [B-T3] 预检路由：`op=video`、`op=music` 返回 200，结构为 `{ok, reason, release, memory_warning}`；参数不是整数时返回 400。
- [B-T4] SKILL.md 格式检查扩展：包含 `lmdesk video wait`、`--first-frame image:`、`lmdesk music gen`、`--lyrics-file`、`join`。

## 7. 任务

1. 服务端：`precheck_media` 与路由的 op 扩展（B-30、B-T3）。
2. 命令行：`decide()` 扩展（B-02、B-T1）。
3. 命令行：`images.py` 泛化为 `media.py`；增加视频、音乐、join 命令；`cli.py` 注册三个子命令（B-01、B-10 至 B-22、B-31、B-32、B-T2）。
4. SKILL.md 与格式检查（B-40、B-41、B-T4）。
5. 全量回归：Python 单元测试、node 测试、e2e。
